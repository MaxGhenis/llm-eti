"""Read-only adapter for two exact retained lab archives, withhold estimation.

These are not the six canonical Study 2 inputs. A historical collection script
is corroborating evidence, not a run-bound instrument or a planned inventory.
No completed-row roster can establish entirely missing subjects or independence.
"""

from __future__ import annotations

import csv
import hashlib
import io
import pickle
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NoReturn

import pandas as pd

from llm_eti.lab_methods.estimands import ENDOWMENTS, DesignError, notch_identification

ARCHIVES = {
    "legacy_pickle": (
        "PKNF_replication_results.pkl",
        "43b22a36e9ab387ea511b60aa77373257cef9d420f05b31ebc58737a52899438",
    ),
    "gemini_minimal": (
        "pknf_results_gemini-2.5-flash_minimal.csv",
        "e3b890dae7b5152b1a43c0ead2235ad3963fc0c3b2fbea473d7886f25eb547bd",
    ),
}
MISSING_PROVENANCE = (
    "full_planned_subject_and_row_inventory_including_absent_subjects",
    "run_bound_delivered_instrument_and_assignment_version",
    "complete_attempt_failure_retry_and_cache_inventory",
    "independent_draw_units_and_state_history_provenance",
)


class _Record:
    """Inert container for archived Pydantic state; never import provider SDKs."""


class _RetainedUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        inert = {
            ("openai.types.chat.chat_completion", "ChatCompletion"),
            ("openai.types.chat.chat_completion", "Choice"),
            ("openai.types.chat.chat_completion_message", "ChatCompletionMessage"),
            ("openai.types.completion_usage", "CompletionUsage"),
            ("openai.types.completion_usage", "CompletionTokensDetails"),
            ("openai.types.completion_usage", "PromptTokensDetails"),
        }
        if (module, name) in inert:
            return _Record
        allowed = {
            ("pandas.core.frame", "DataFrame"),
            ("pandas.core.internals.managers", "BlockManager"),
            ("pandas._libs.internals", "_unpickle_block"),
            ("numpy.core.multiarray", "_reconstruct"),
            ("numpy", "ndarray"),
            ("numpy", "dtype"),
            ("builtins", "slice"),
            ("pandas.core.indexes.base", "_new_Index"),
            ("pandas.core.indexes.base", "Index"),
            ("pandas.core.indexes.range", "RangeIndex"),
        }
        if (module, name) not in allowed:
            raise DesignError(f"Unsupported retained pickle class: {module}.{name}")
        return super().find_class(module, name)


def _read_verified(directory: Path, archive: str) -> bytes:
    if archive not in ARCHIVES:
        raise DesignError("Unknown retained archive; no generic real-data adapter")
    filename, expected = ARCHIVES[archive]
    raw = (directory / filename).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise DesignError(f"Retained archive hash mismatch: {filename}")
    return raw


def _state(record: _Record) -> dict[str, Any]:
    state: dict[str, Any] = vars(record)["__dict__"]
    return state


def _grid(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Observed labels only; this is NOT a planned inventory or inference unit."""
    subjects: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        subjects[row["subject_label"]].append(row)
    missing = []
    for subject, group in sorted(subjects.items()):
        for phase in (0, 1):
            seen = {r["cap"] for r in group if r["phase"] == phase}
            for cap in ENDOWMENTS:
                if cap not in seen:
                    missing.append(
                        {"subject_label": subject, "phase": phase, "cap": cap}
                    )
    return {
        "observed_subject_labels": len(subjects),
        "observed_rounds_by_label": {
            subject: sorted(row["round"] for row in group)
            for subject, group in sorted(subjects.items())
        },
        "duplicate_label_rounds": len(rows)
        - len({(r["subject_label"], r["round"]) for r in rows}),
        "cap_counts": dict(sorted(Counter(r["cap"] for r in rows).items())),
        "outside_original_cap_support_rows": sum(
            r["cap"] not in ENDOWMENTS for r in rows
        ),
        "missing_observed_subject_phase_cap_cells": missing,
        "subjects_with_complete_original_grid": len(subjects)
        - len({r["subject_label"] for r in missing}),
        "full_planned_subject_count": None,
        "independent_subject_count": None,
    }


def _pickle_audit(raw: bytes) -> dict[str, Any]:
    # Called only after exact SHA256 verification; not a general safe-pickle API.
    frame = _RetainedUnpickler(io.BytesIO(raw)).load()
    if not isinstance(frame, pd.DataFrame) or list(frame.columns) != [
        "obs_number",
        "sim_num",
        "round_num",
        "treatment",
        "model_answer",
        "model_response",
        "rate1",
        "rate2",
        "max_labor",
    ]:
        raise DesignError("Unexpected retained DataFrame schema")
    rows = []
    mismatch = 0
    response_ids = []
    models: Counter[str] = Counter()
    # Mapping corroborated by the archived script. It is checked against each
    # stored rate pair, but cannot authenticate the unretained delivered prompt.
    sequences = {
        1: ((25, 50), (25, 50)),
        2: ((25, 50), (25, 25)),
        3: ((25, 50), (50, 50)),
        4: ((25, 25), (25, 50)),
        5: ((50, 50), (25, 50)),
    }
    schedule_mismatch = 0
    for record in frame.itertuples(index=False):
        phase = int(record.round_num >= 8)
        state = _state(record.model_response)
        text = "".join(
            _state(_state(choice)["message"])["content"] for choice in state["choices"]
        )
        mismatch += text != record.model_answer
        response_ids.append(state["id"])
        models[state["model"]] += 1
        schedule_mismatch += (record.rate1, record.rate2) != sequences[
            record.treatment
        ][phase]
        rows.append(
            {
                "subject_label": str(record.sim_num),
                "round": int(record.round_num) + 1,
                "phase": phase,
                "cap": int(record.max_labor),
            }
        )
    return {
        "rows": len(rows),
        "schema": list(frame.columns),
        **_grid(rows),
        "raw_answer_payload_mismatches": mismatch,
        "unique_retained_response_ids": len(set(response_ids)),
        "response_model_labels": dict(sorted(models.items())),
        "stored_schedule_vs_historical_code_mismatches": schedule_mismatch,
        "treatment_label_counts": {
            str(k): int(v) for k, v in sorted(Counter(frame.treatment).items())
        },
        "recorded_task_choice_zero_rows": None,
        "choice_status": "Free text retained; no prospectively validated task-choice parser",
        "round_adapter": "Stored zero-based round_num + 1; no rows deleted",
    }


def _csv_audit(raw: bytes) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(raw.decode()))
    expected = [
        "treatment",
        "subject_id",
        "round",
        "tax_schedule",
        "labor_endowment",
        "labor_supply",
        "income",
        "post_reform",
        "model",
    ]
    if reader.fieldnames != expected:
        raise DesignError("Unexpected retained Gemini CSV schema")
    rows = []
    zero = at_cap = inconsistent = invalid = 0
    arms: Counter[str] = Counter()
    schedules: Counter[str] = Counter()
    for record in reader:
        if None in record or any(v is None for v in record.values()):
            raise DesignError("Malformed retained Gemini row")
        cap, q, income, round_number = (
            int(record[k])
            for k in ("labor_endowment", "labor_supply", "income", "round")
        )
        phase = int(round_number > 8)
        invalid += not 0 <= q <= cap
        inconsistent += income != 20 * q
        inconsistent += record["post_reform"] != str(bool(phase))
        zero += q == 0
        at_cap += q == cap
        arms[record["treatment"]] += 1
        schedules[record["tax_schedule"]] += 1
        rows.append(
            {
                "subject_label": record["subject_id"],
                "round": round_number,
                "phase": phase,
                "cap": cap,
            }
        )
    return {
        "rows": len(rows),
        "schema": expected,
        **_grid(rows),
        "treatment_label_counts": dict(sorted(arms.items())),
        "tax_schedule_label_counts": dict(sorted(schedules.items())),
        "recorded_task_choice_zero_rows": zero,
        "recorded_task_choice_cap_rows": at_cap,
        "invalid_recorded_task_choices": invalid,
        "income_or_phase_inconsistencies": inconsistent,
        "raw_answer_payload_mismatches": None,
        "choice_status": "Recorded numeric choices only; raw provider answers not retained",
        "round_adapter": "Stored one-based round; no rows deleted",
    }


def audit_archive(directory: Path, archive: str) -> dict[str, Any]:
    raw = _read_verified(directory, archive)
    details = _pickle_audit(raw) if archive == "legacy_pickle" else _csv_audit(raw)
    blockers = list(MISSING_PROVENANCE)
    if details["outside_original_cap_support_rows"]:
        blockers.append("observed_caps_incompatible_with_original_instrument")
    if details["missing_observed_subject_phase_cap_cells"]:
        blockers.append("incomplete_observed_subject_phase_original_cap_grid")
    if archive == "legacy_pickle":
        blockers.append("no_validated_task_choice_parser_for_retained_free_text")
    else:
        blockers.extend(
            ["no_Prog_Prog_comparison_arm", "no_retained_raw_provider_answers"]
        )
    return {
        "archive": archive,
        "file": ARCHIVES[archive][0],
        "sha256": ARCHIVES[archive][1],
        "status": "withheld",
        "blockers": blockers,
        "observations": details,
        "zero_inclusive_standardized_outcomes": None,
        "sequence_or_reform_contrast": None,
        "subject_bootstrap": None,
        "finite_sample_completion_bounds": None,
        "structural_notch_eti": notch_identification(),
        "human_Table_6_reproduced": False,
    }


def load_for_estimation(directory: Path, archive: str) -> NoReturn:
    """No retained run satisfies the reviewed real-data acceptance contract.

    Do not infer an inventory from completed rows or enable estimation by
    declaring an independence boolean. A future compatible archive needs a
    separately reviewed adapter tied to its actual provenance.
    """
    audit = audit_archive(directory, archive)
    raise DesignError("Estimate withheld: " + "; ".join(audit["blockers"]))


def publication_audit(directory: Path) -> dict[str, Any]:
    return {
        "scope": "Retained legacy lab archive audit; separate from 8095 Study 2 responses",
        "reference_methods_head": "1f6c23a0c00f0c197cd16e5b235f1e8420d9ee49",
        "archives": [audit_archive(directory, name) for name in ARCHIVES],
        "empirical_lab_estimates_released": False,
    }


def audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "| Retained archive | Rows | Observed subject labels | Rows outside original cap menu | Complete original grids |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in audit["archives"]:
        obs = item["observations"]
        label = (
            "Historical pickle"
            if item["archive"] == "legacy_pickle"
            else "Gemini minimal CSV"
        )
        lines.append(
            f"| {label} | {obs['rows']} | {obs['observed_subject_labels']} | "
            f"{obs['outside_original_cap_support_rows']} | {obs['subjects_with_complete_original_grid']} |"
        )
    lines.extend(
        [
            "",
            "Counts describe stored records, not planned or independent subjects. Both archives fail the analysis contract; all standardized lab estimates and completion bounds are withheld.",
        ]
    )
    return "\n".join(lines) + "\n"
