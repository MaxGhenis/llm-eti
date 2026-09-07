import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from llm_eti.lab_checkpoint import checkpoint_lock
from llm_eti.simulation_engine import LabExperimentSimulation
from tests.offline_lab_client import OfflineLabClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def experiment():
    return LabExperimentSimulation(OfflineLabClient())


def run(experiment, path, **kwargs):
    return experiment.run_experiment(
        treatments=kwargs.pop("treatments", ["Prog,Flat25"]),
        rounds=kwargs.pop("rounds", 8),
        subjects_per_treatment=kwargs.pop("subjects_per_treatment", 1),
        checkpoint_path=path,
        **kwargs,
    )


def test_eight_round_checkpoint_cannot_resume_as_sixteen(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"
    run(experiment, path)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="Incompatible experiment manifest"):
        run(experiment, path, rounds=16)
    assert len(experiment.client.calls) == 8
    assert path.read_bytes() == original


def test_manifest_and_full_design_exist_before_first_request(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"

    def inspect_before_request(scenario):
        manifest = json.loads(path.with_suffix(".csv.manifest.json").read_text())
        assert len(manifest["scenarios"]) == 16
        assert all(
            row["tax_schedule"] == "progressive" and not row["post_reform"]
            for row in manifest["scenarios"][:8]
        )
        assert all(
            row["tax_schedule"] == "flat25" and row["post_reform"]
            for row in manifest["scenarios"][8:]
        )

    experiment.client.before_request = inspect_before_request
    result = run(experiment, path, rounds=16)
    assert len(result) == 16
    assert result["scenario_id"].nunique() == 16


@pytest.mark.parametrize(
    "change",
    [
        "model",
        "cache",
        "wage",
        "bounds",
        "prompt",
        "seed",
        "rates",
        "subjects",
        "treatments",
    ],
)
def test_semantically_different_experiments_fail_without_requests(
    experiment, tmp_path, change
):
    path = tmp_path / "checkpoint.csv"
    run(experiment, path)
    before = path.read_bytes()
    kwargs = {}
    if change == "model":
        experiment.client.model = "different-model"
    elif change == "cache":
        experiment.client.use_cache = True
    elif change in {"wage", "bounds"}:
        experiment.config = dict(experiment.config)
        experiment.config[
            "wage_per_unit" if change == "wage" else "labor_endowment_min"
        ] += 1
    elif change == "prompt":
        experiment.client.create_instructions_text = (
            lambda **kwargs: "Changed instructions"
        )
    elif change == "seed":
        kwargs["seed"] = 1
    elif change == "rates":
        kwargs["low_rate"] = 25.5
    elif change == "subjects":
        kwargs["subjects_per_treatment"] = 2
    else:
        kwargs["treatments"] = ["Prog,Flat50"]
    with pytest.raises(ValueError, match="Incompatible experiment manifest"):
        run(experiment, path, **kwargs)
    assert len(experiment.client.calls) == 8
    assert path.read_bytes() == before


def test_identical_resume_makes_no_calls_and_preserves_zero(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"
    result = run(experiment, path)
    before = path.read_bytes()
    assert result.iloc[0]["income"] == 0
    resumed = run(experiment, path)
    assert len(experiment.client.calls) == 8
    assert len(resumed) == 8
    assert resumed.iloc[0]["income"] == 0
    assert path.read_bytes() == before


def test_failures_remain_in_ledger_and_are_retried(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"
    experiment.client.fail_rounds = {3}
    first = run(experiment, path)
    assert first.loc[first["round"] == 3, "status"].item() == "retryable_failure"
    before = path.read_bytes()
    experiment.client.fail_rounds.clear()
    resumed = run(experiment, path)
    assert len(experiment.client.calls) == 9
    assert resumed["status"].eq("success").all()
    assert len(resumed) == 8
    assert path.read_bytes().startswith(before)
    rows = list(csv.DictReader(path.open(newline="")))
    assert len(rows) == 9
    assert rows[2]["response_raw"] == 'provider returned "invalid"\nsecond line'
    assert rows[-1]["attempt"] == "2"
    assert rows[-1]["scenario_id"] == rows[2]["scenario_id"]


def test_transport_exception_is_recorded_then_resumable(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"
    experiment.client.raise_rounds = {3}
    with pytest.raises(RuntimeError, match="Offline transport interruption"):
        run(experiment, path)
    rows = list(csv.DictReader(path.open(newline="")))
    assert len(rows) == 3
    assert rows[-1]["status"] == "retryable_failure"
    experiment.client.raise_rounds.clear()
    result = run(experiment, path)
    assert len(result) == 8
    assert len(experiment.client.calls) == 9


@pytest.mark.parametrize("cut_bytes", [1, 2, 10])
def test_truncated_scalar_tail_is_rejected_before_retry(
    experiment, tmp_path, cut_bytes
):
    path = tmp_path / "checkpoint.csv"
    experiment.client.fail_rounds = {8}
    run(experiment, path)
    path.write_bytes(path.read_bytes()[:-cut_bytes])
    before = path.read_bytes()
    experiment.client.fail_rounds.clear()
    with pytest.raises(ValueError, match="Incomplete checkpoint record"):
        run(experiment, path)
    assert len(experiment.client.calls) == 8
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "timestamp",
    ["", "2026-09-07", "2026-09-07T21:41:06.8251", "2026-09-07T21:41:06+01:00"],
)
def test_invalid_timestamp_is_rejected_before_retry(experiment, tmp_path, timestamp):
    path = tmp_path / "checkpoint.csv"
    experiment.client.fail_rounds = {8}
    run(experiment, path)
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        rows = list(reader)
    rows[-1]["recorded_at"] = timestamp
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    before = path.read_bytes()
    experiment.client.fail_rounds.clear()
    with pytest.raises(ValueError, match="Invalid checkpoint timestamp"):
        run(experiment, path)
    assert len(experiment.client.calls) == 8
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "corruption",
    [
        "legacy",
        "bad_manifest",
        "partial",
        "duplicate",
        "wrong_schedule",
        "wrong_id",
        "wrong_income",
    ],
)
def test_corrupt_or_legacy_checkpoint_is_preserved_and_never_reused(
    experiment, tmp_path, corruption
):
    path = tmp_path / "checkpoint.csv"
    run(experiment, path)
    manifest_path = path.with_suffix(".csv.manifest.json")
    if corruption == "legacy":
        manifest_path.unlink()
    elif corruption == "bad_manifest":
        manifest_path.write_text('{"schema_version":')
    elif corruption == "partial":
        with path.open("a") as stream:
            stream.write('"interrupted,unterminated')
    else:
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            rows = list(reader)
        if corruption == "duplicate":
            rows.append(rows[0])
        else:
            key, value = {
                "wrong_schedule": ("tax_schedule", "progressive"),
                "wrong_id": ("experiment_id", "0" * 64),
                "wrong_income": ("income", "inf"),
            }[corruption]
            rows[-1][key] = value
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        run(experiment, path)
    assert path.read_bytes() == before
    assert len(experiment.client.calls) == 8


def test_lock_rejects_second_writer_before_requests(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"
    with checkpoint_lock(path):
        with pytest.raises(ValueError, match="in use"):
            run(experiment, path)
    assert experiment.client.calls == []


def test_manifest_only_crash_can_resume(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"
    manifest = experiment.experiment_manifest(
        ["Prog,Flat25"], rounds=8, subjects_per_treatment=1
    )
    path.with_suffix(".csv.manifest.json").write_text(json.dumps(manifest))
    assert len(run(experiment, path)) == 8


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rounds": 0},
        {"rounds": True},
        {"seed": -1},
        {"subjects_per_treatment": 0},
        {"low_rate": float("nan")},
        {"high_rate": float("inf")},
        {"treatments": ["unknown"]},
        {"treatments": ["Prog,Flat25", "Prog,Flat25"]},
    ],
)
def test_invalid_design_fails_before_requests(experiment, tmp_path, kwargs):
    with pytest.raises(ValueError):
        run(experiment, tmp_path / "checkpoint.csv", **kwargs)
    assert experiment.client.calls == []


@pytest.mark.parametrize(
    "low,high,labels",
    [
        (25.1, 25.9, {"Prog,Flat25.1", "Prog,Flat25.9"}),
        (50, 60, {"Prog,Flat50", "Prog,Flat60"}),
        (25.000001, 25.000002, {"Prog,Flat25.000001", "Prog,Flat25.000002"}),
    ],
)
def test_fractional_rates_have_distinct_output_labels(experiment, low, high, labels):
    manifest = experiment.experiment_manifest(
        ["Prog,Flat25", "Prog,Flat50"],
        rounds=2,
        subjects_per_treatment=1,
        low_rate=low,
        high_rate=high,
    )
    assert {row["treatment"] for row in manifest["scenarios"]} == labels


def test_runner_preserves_close_rates_in_separate_filenames(tmp_path, monkeypatch):
    from book.scripts import run_pknf_simulation as runner

    monkeypatch.setenv("EXPECTED_PARROT_API_KEY", "offline-test-sentinel")
    monkeypatch.setattr(runner, "EDSLClient", lambda **kwargs: OfflineLabClient())
    for low in ("25.000001", "25.000002"):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "runner",
                "--test",
                "--model",
                "offline",
                "--low-rate",
                low,
                "--high-rate",
                "60",
                "--output-dir",
                str(tmp_path),
            ],
        )
        runner.main()
    names = {path.name for path in tmp_path.glob("*.csv")}
    assert names == {
        "pknf_results_offline_25.000001pct_60pct_2rounds_seed0_test.csv",
        "pknf_results_offline_25.000002pct_60pct_2rounds_seed0_test.csv",
    }
    assert {path.name for path in (tmp_path / "checkpoints").glob("*.csv")} == names


def test_changed_prompt_builder_source_rejects_resume(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"
    run(experiment, path)

    class DifferentPrompt(OfflineLabClient):
        def create_lab_experiment_survey(self, **kwargs):
            raise AssertionError("Only inspect source; never create or run a survey")

    client = DifferentPrompt()
    with pytest.raises(ValueError, match="Incompatible experiment manifest"):
        run(LabExperimentSimulation(client), path)
    assert client.calls == []


def test_actual_checkpoint_resumes_in_a_fresh_interpreter(experiment, tmp_path):
    path = tmp_path / "checkpoint.csv"
    run(experiment, path)
    before = path.read_bytes()
    code = """
import sys
from pathlib import Path
from llm_eti.simulation_engine import LabExperimentSimulation
from tests.offline_lab_client import OfflineLabClient
client = OfflineLabClient()
result = LabExperimentSimulation(client).run_experiment(
    ['Prog,Flat25'], rounds=8, subjects_per_treatment=1, checkpoint_path=Path(sys.argv[1]))
assert len(result) == 8 and client.calls == []
"""
    subprocess.run(
        [sys.executable, "-c", code, str(path)],
        cwd=ROOT,
        env={**os.environ, "PYTHONHASHSEED": "918"},
        check=True,
        capture_output=True,
        text=True,
    )
    assert path.read_bytes() == before


def test_design_is_identical_in_fresh_interpreters_with_different_hash_seeds():
    code = """
import json
from llm_eti.simulation_engine import LabExperimentSimulation
from tests.offline_lab_client import OfflineLabClient
manifest = LabExperimentSimulation(OfflineLabClient()).experiment_manifest(
    ['Prog,Flat25', 'Flat25,Prog'], rounds=16, subjects_per_treatment=2, seed=314)
print(json.dumps(manifest, sort_keys=True))
"""
    outputs = []
    for seed in ("1", "72", "random"):
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONHASHSEED": seed},
            check=True,
            capture_output=True,
            text=True,
        )
        outputs.append(json.loads(completed.stdout))
    assert outputs[0] == outputs[1] == outputs[2]
    assert len(outputs[0]["scenarios"]) == 64
