"""Offline experiment identity and an append-only, validated lab checkpoint.

This preserves the legacy independent-round protocol; it does not validate that
protocol, provider revisions, cache independence, or any economic estimator.
"""

from __future__ import annotations

import csv
import fcntl
import hashlib
import inspect
import json
import math
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np

from .pknf_types import Treatment

SCHEMA_VERSION = 1
DESIGN_FIELDS = (
    "scenario_id",
    "treatment",
    "subject_id",
    "round",
    "tax_schedule",
    "labor_endowment",
    "wage_per_unit",
    "rounds",
    "low_rate",
    "high_rate",
    "post_reform",
)
RECORD_FIELDS = (
    "experiment_id",
    *DESIGN_FIELDS,
    "model",
    "attempt",
    "status",
    "income",
    "labor_supply",
    "response_error",
    "response_raw",
    "recorded_at",
)


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def rate_label(rate: float) -> str:
    """Retain round-trip-safe rates in exported treatment labels and filenames."""
    value = float(rate)
    return str(int(value)) if value.is_integer() else repr(value)


def build_manifest(
    client, config, treatments, rounds, subjects, low_rate, high_rate, seed
) -> dict:
    """Materialize the complete design before requests, using a stable RNG seed."""
    for name, value, minimum in (
        ("rounds", rounds, 2),
        ("subjects", subjects, 1),
        ("seed", seed, 0),
    ):
        if type(value) is not int or value < minimum:
            raise ValueError(f"{name} must be an integer >= {minimum}")
    if not treatments or len(set(treatments)) != len(treatments):
        raise ValueError("Treatments must be nonempty and unique")
    parsed_treatments = [Treatment.from_label(label) for label in treatments]
    if not (0 <= low_rate < high_rate <= 100):
        raise ValueError("Require finite rates: 0 <= low_rate < high_rate <= 100")
    lower, upper = config["labor_endowment_min"], config["labor_endowment_max"]
    if type(lower) is not int or type(upper) is not int or not 0 <= lower <= upper:
        raise ValueError("Labor endowment bounds must be nonnegative ordered integers")
    wage = config["wage_per_unit"]
    if not math.isfinite(wage) or wage <= 0:
        raise ValueError("Wage must be positive and finite")
    if not isinstance(client.model, str) or not client.model:
        raise ValueError("A model identity is required")
    if type(client.use_cache) is not bool:
        raise ValueError("An explicit boolean cache setting is required")
    instructions = client.create_instructions_text(rounds=rounds, wage_per_unit=wage)
    try:
        edsl_version = version("edsl")
    except PackageNotFoundError:
        edsl_version = "not-installed"
    spec = {
        "protocol": "legacy-independent-rounds-v1-unvalidated",
        "rounds": rounds,
        "reform_after_round": rounds // 2,
        "subjects_per_treatment": subjects,
        "treatments": treatments,
        "low_rate": float(low_rate),
        "high_rate": float(high_rate),
        "seed": seed,
        "rng": "numpy.PCG64",
        "numpy_version": np.__version__,
        "model": client.model,
        "use_cache": client.use_cache,
        "provider_revision": "not-recorded",
        "edsl_version": edsl_version,
        "config": dict(config),
        "instructions": instructions,
        "client_source_sha256": {
            name: hashlib.sha256(
                inspect.getsource(getattr(client, name)).encode()
            ).hexdigest()
            for name in ("create_lab_experiment_survey", "run_batch_surveys")
        },
        "implementation_sha256": {
            name: hashlib.sha256(
                Path(__file__).with_name(name).read_bytes()
            ).hexdigest()
            for name in (
                "lab_checkpoint.py",
                "simulation_engine.py",
                "edsl_client.py",
                "pknf_types.py",
            )
        },
    }
    spec_id = digest(spec)
    scenarios = []
    for treatment in parsed_treatments:
        components = {
            "Prog": "Prog",
            "Flat25": f"Flat{rate_label(low_rate)}",
            "Flat50": f"Flat{rate_label(high_rate)}",
        }
        output_label = ",".join(components[part] for part in treatment.label.split(","))
        for subject in range(subjects):
            subject_seed = int(digest([seed, treatment.label, subject]), 16)
            rng = np.random.Generator(np.random.PCG64(subject_seed))
            endowments = rng.integers(lower, upper + 1, size=rounds)
            for round_index, endowment in enumerate(endowments, 1):
                scenario = {
                    "treatment": output_label,
                    "subject_id": subject,
                    "round": round_index,
                    "tax_schedule": treatment.get_schedule_for_round(
                        round_index, rounds
                    ).value,
                    "labor_endowment": int(endowment),
                    "wage_per_unit": wage,
                    "rounds": rounds,
                    "low_rate": float(low_rate),
                    "high_rate": float(high_rate),
                    "post_reform": round_index > rounds // 2,
                }
                scenario["scenario_id"] = digest([spec_id, treatment.label, scenario])
                scenarios.append(scenario)
    manifest = {"schema_version": SCHEMA_VERSION, "spec": spec, "scenarios": scenarios}
    return {"experiment_id": digest(manifest), **manifest}


def _atomic_json(path: Path, value) -> None:
    """Readers see a complete manifest or none, even after an interrupted write."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(canonical(value) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def checkpoint_lock(path: Path | None):
    """A second local writer fails immediately; OS releases the lock after a crash."""
    if path is None:
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(f"Checkpoint is in use: {path}") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def prepare_checkpoint(path: Path | None, manifest) -> list[dict]:
    """Reject incompatible, legacy, duplicate, or corrupt state without overwriting it."""
    if path is None:
        return []
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
        except (OSError, ValueError) as error:
            raise ValueError(
                f"Cannot read checkpoint manifest: {manifest_path}"
            ) from error
        if existing != manifest:
            raise ValueError(
                "Incompatible experiment manifest; use a new checkpoint path"
            )
    elif path.exists():
        raise ValueError(
            "Legacy checkpoint lacks a manifest; retain it and use a new path"
        )
    else:
        _atomic_json(manifest_path, manifest)
    if not path.exists():
        return []
    # csv.DictReader accepts an unquoted scalar at EOF. Our writer always ends
    # a complete record with CRLF; appending to any shorter tail corrupts it.
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() < 2:
            raise ValueError("Incomplete checkpoint record")
        stream.seek(-2, os.SEEK_END)
        if stream.read() != b"\r\n":
            raise ValueError("Incomplete checkpoint record")
    planned = {item["scenario_id"]: item for item in manifest["scenarios"]}
    attempts: dict[str, int] = {}
    completed = set()
    records = []
    try:
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != list(RECORD_FIELDS):
                raise ValueError("Checkpoint schema mismatch or incomplete header")
            for row in reader:
                if set(row) != set(RECORD_FIELDS) or any(
                    value is None for value in row.values()
                ):
                    raise ValueError("Incomplete or extra checkpoint fields")
                try:
                    recorded = datetime.fromisoformat(row["recorded_at"])
                    if (
                        recorded.tzinfo != timezone.utc
                        or recorded.isoformat() != row["recorded_at"]
                    ):
                        raise ValueError("Noncanonical UTC timestamp")
                except ValueError as error:
                    raise ValueError("Invalid checkpoint timestamp") from error
                scenario_id = row["scenario_id"]
                if scenario_id not in planned:
                    raise ValueError("Checkpoint has an unplanned scenario")
                scenario = planned[scenario_id]
                if row["experiment_id"] != manifest["experiment_id"]:
                    raise ValueError("Checkpoint experiment identity mismatch")
                if row["model"] != manifest["spec"]["model"]:
                    raise ValueError("Checkpoint model mismatch")
                for field in DESIGN_FIELDS:
                    if row[field] != str(scenario[field]):
                        raise ValueError(f"Checkpoint design mismatch: {field}")
                attempt = int(row["attempt"])
                if (
                    attempt != attempts.get(scenario_id, 0) + 1
                    or scenario_id in completed
                ):
                    raise ValueError(
                        "Duplicate, out-of-order, or already completed checkpoint attempt"
                    )
                attempts[scenario_id] = attempt
                if row["status"] == "success":
                    income = float(row["income"])
                    if (
                        not valid_income(income, scenario)
                        or row["response_error"] != "False"
                    ):
                        raise ValueError("Invalid successful checkpoint income")
                    if float(row["labor_supply"]) != income / scenario["wage_per_unit"]:
                        raise ValueError("Checkpoint labor supply mismatch")
                    completed.add(scenario_id)
                elif row["status"] == "retryable_failure":
                    if (
                        row["income"]
                        or row["labor_supply"]
                        or row["response_error"] != "True"
                    ):
                        raise ValueError("Invalid failed checkpoint row")
                    income = None
                else:
                    raise ValueError("Unknown checkpoint status")
                records.append(
                    {
                        **row,
                        **scenario,
                        "attempt": attempt,
                        "income": income,
                        "labor_supply": (
                            None
                            if income is None
                            else income / scenario["wage_per_unit"]
                        ),
                        "response_error": row["status"] != "success",
                    }
                )
    except (csv.Error, KeyError, TypeError, OverflowError) as error:
        raise ValueError(f"Malformed checkpoint: {path}") from error
    return records


def valid_income(income, scenario) -> bool:
    return (
        isinstance(income, (int, float))
        and not isinstance(income, bool)
        and math.isfinite(income)
        and 0 <= income <= scenario["labor_endowment"] * scenario["wage_per_unit"]
    )


def append_record(path: Path | None, row) -> None:
    if path is None:
        return
    with path.open("a", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=RECORD_FIELDS)
        if stream.tell() == 0:
            writer.writeheader()
        writer.writerow(row)
        stream.flush()
        os.fsync(stream.fileno())
