"""Offline regressions for the streamline_api + PR #44 integration.

No API client is constructed and no model is called: the lab tests use the
offline fixture client, and the tax test replaces EDSL's Jobs with a recorder.
"""

import importlib
import json
from pathlib import Path

import pandas as pd
import pytest

from llm_eti import edsl_client as edsl_client_module
from llm_eti.edsl_client import EDSLClient
from llm_eti.simulation_engine import LabExperimentSimulation
from tests.offline_lab_client import OfflineLabClient


def run(experiment, path, **kwargs):
    return experiment.run_experiment(
        treatments=kwargs.pop("treatments", ["Prog,Flat25"]),
        rounds=kwargs.pop("rounds", 8),
        subjects_per_treatment=kwargs.pop("subjects_per_treatment", 1),
        checkpoint_path=path,
        **kwargs,
    )


def ledger(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, keep_default_na=False)


def test_batched_run_writes_every_result_to_the_ledger(tmp_path):
    client = OfflineLabClient()
    path = tmp_path / "checkpoint.csv"
    result = run(LabExperimentSimulation(client), path, batch_size=3)
    assert client.batch_sizes == [3, 3, 2]
    rows = ledger(path)
    assert len(rows) == 8 and set(rows["status"]) == {"success"}
    assert rows.loc[rows["round"] == 1, "income"].tolist() == [0]  # zero kept
    assert len(result) == 8
    manifest = json.loads(path.with_suffix(".csv.manifest.json").read_text())
    assert manifest["spec"]["execution"] == "batched"

    resumed = OfflineLabClient()
    run(LabExperimentSimulation(resumed), path, batch_size=3)
    assert resumed.calls == []
    assert len(ledger(path)) == 8


def test_batched_failures_and_omissions_are_recorded_then_retried(tmp_path):
    client = OfflineLabClient()
    client.fail_rounds = {2}
    client.omit_rounds = {3}
    path = tmp_path / "checkpoint.csv"
    run(LabExperimentSimulation(client), path, batch_size=4)
    rows = ledger(path)
    failed = rows[rows["status"] == "retryable_failure"]
    assert sorted(failed["round"].tolist()) == [2, 3]
    assert (
        "no result returned" in failed.loc[failed["round"] == 3].iloc[0]["response_raw"]
    )

    retry = OfflineLabClient()
    run(LabExperimentSimulation(retry), path, batch_size=4)
    assert sorted(call["round_num"] for call in retry.calls) == [2, 3]
    latest = ledger(path).groupby("scenario_id").tail(1)
    assert set(latest["status"]) == {"success"}
    assert sorted(latest.loc[latest["round"].isin([2, 3]), "attempt"]) == [2, 2]


def test_batched_chunk_exception_keeps_completed_chunks(tmp_path):
    client = OfflineLabClient()
    client.raise_rounds = {5}
    path = tmp_path / "checkpoint.csv"
    with pytest.raises(RuntimeError, match="Offline batch failure"):
        run(LabExperimentSimulation(client), path, batch_size=4)
    assert sorted(ledger(path)["round"].tolist()) == [1, 2, 3, 4]

    retry = OfflineLabClient()
    run(LabExperimentSimulation(retry), path, batch_size=4)
    assert sorted(call["round_num"] for call in retry.calls) == [5, 6, 7, 8]


@pytest.mark.parametrize(
    "first, second", [(None, 3), (3, None)], ids=["serial-then-batched", "reverse"]
)
def test_serial_and_batched_ledgers_cannot_be_mixed(tmp_path, first, second):
    path = tmp_path / "checkpoint.csv"
    run(LabExperimentSimulation(OfflineLabClient()), path, batch_size=first)
    client = OfflineLabClient()
    with pytest.raises(ValueError, match="Incompatible experiment manifest"):
        run(LabExperimentSimulation(client), path, batch_size=second)
    assert client.calls == []


def test_batched_lab_prompt_fields_match_streamline_api(tmp_path):
    client = OfflineLabClient()
    run(LabExperimentSimulation(client), tmp_path / "c.csv", batch_size=8)
    first = client.calls[0]
    assert first["work_id"] == first["scenario_id"]
    assert first["max_income"] == first["labor_endowment"] * first["wage_per_unit"]
    assert first["tax_text"].startswith("In this round, the tax rate is 25.0%")


class _RecordingJobs:
    calls: list = []

    def __init__(self, survey, agents, models, scenarios):
        self.scenarios = scenarios

    def run(self, **kwargs):
        _RecordingJobs.calls.append(kwargs)
        scenarios = self.scenarios
        n = kwargs.get("n", 1)

        class Pending:
            def fetch(self, polling_interval):
                class Results:
                    def to_pandas(self):
                        return pd.DataFrame(
                            [
                                {
                                    "scenario.work_id": s["work_id"],
                                    "iteration.iteration": i,
                                }
                                for s in scenarios
                                for i in range(n)
                            ]
                        )

                return Results()

        return Pending()


def test_batched_tax_survey_requests_every_response(monkeypatch):
    _RecordingJobs.calls = []
    monkeypatch.setattr(edsl_client_module, "Jobs", _RecordingJobs)
    client = EDSLClient.__new__(EDSLClient)  # no API key, no dotenv, no network
    client.model = "offline-recorder"
    client.use_cache = False
    monkeypatch.setattr(client, "_make_model", lambda: None)
    monkeypatch.setattr(
        client,
        "_extract_tax_result_from_row",
        lambda scenario, row, attempt: dict(scenario),
    )
    scenarios = [{"work_id": f"tax-{i}"} for i in range(3)]
    results = client.run_batched_surveys(
        scenarios, survey_type="tax", responses_per_scenario=2, batch_size=2
    )
    assert [call["n"] for call in _RecordingJobs.calls] == [2, 2]
    assert len(results) == 6
    assert sorted({r["response_number"] for r in results}) == [1, 2]


@pytest.mark.parametrize(
    "name, expected",
    [
        ("pknf_results_gpt-4o-mini_25pct_50pct.csv", ("gpt-4o-mini", 0.25, 0.5)),
        (
            "pknf_results_google_gemma-4-26B-A4B-it_25pct_40pct.csv",
            ("google_gemma-4-26B-A4B-it", 0.25, 0.4),
        ),
        (
            "pknf_results_deepseek-ai_DeepSeek-V3_25pct_50pct_16rounds_seed0.csv",
            ("deepseek-ai_DeepSeek-V3", 0.25, 0.5),
        ),
        (
            "pknf_results_offline_25.000001pct_60pct_2rounds_seed0.csv",
            ("offline", 0.25000001, 0.6),
        ),
    ],
)
def test_results_filenames_from_both_runners_parse(name, expected):
    parse_filename = importlib.import_module(
        "book.scripts.make_pknf_results"
    ).parse_filename

    model, flat, top = parse_filename(Path(name))
    assert model == expected[0]
    assert flat == pytest.approx(expected[1]) and top == pytest.approx(expected[2])


def test_unrecognized_results_filename_is_rejected():
    parse_filename = importlib.import_module(
        "book.scripts.make_pknf_results"
    ).parse_filename

    with pytest.raises(ValueError, match="Unrecognized"):
        parse_filename(Path("pknf_results_gpt-4o-mini_25pct_50pct_test.csv"))
