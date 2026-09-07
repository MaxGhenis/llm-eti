"""Real retained-input regressions: no fabricated successful experiment fixture."""

import hashlib
import json
from pathlib import Path

import pytest

from llm_eti.lab_archive import (
    ARCHIVES,
    MISSING_PROVENANCE,
    _csv_audit,
    _grid,
    audit_archive,
    audit_markdown,
    load_for_estimation,
    publication_audit,
)
from llm_eti.lab_methods.estimands import DesignError

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "legacy_lab"


@pytest.mark.parametrize("archive", ARCHIVES)
def test_actual_archive_is_byte_preserved_and_never_accepted(archive):
    filename, expected = ARCHIVES[archive]
    assert hashlib.sha256((DATA / filename).read_bytes()).hexdigest() == expected
    audit = audit_archive(DATA, archive)
    assert set(MISSING_PROVENANCE) <= set(audit["blockers"])
    assert audit["status"] == "withheld"
    for field in (
        "zero_inclusive_standardized_outcomes",
        "subject_bootstrap",
        "sequence_or_reform_contrast",
        "finite_sample_completion_bounds",
    ):
        assert audit[field] is None
    for field in ("estimate", "lower_bound", "upper_bound"):
        assert audit["structural_notch_eti"][field] is None
    with pytest.raises(DesignError, match="full_planned_subject_and_row_inventory"):
        load_for_estimation(DATA, archive)


def test_real_pickle_answer_reconciliation_and_incompatible_caps():
    audit = audit_archive(DATA, "legacy_pickle")["observations"]
    assert audit["rows"] == 320
    assert audit["observed_subject_labels"] == 20
    assert audit["unique_retained_response_ids"] == 320
    assert audit["raw_answer_payload_mismatches"] == 0
    assert audit["stored_schedule_vs_historical_code_mismatches"] == 0
    assert audit["outside_original_cap_support_rows"] == 70
    assert audit["cap_counts"][26] == 40
    assert audit["cap_counts"][28] == 30
    assert audit["subjects_with_complete_original_grid"] == 0
    assert audit["recorded_task_choice_zero_rows"] is None
    assert audit["full_planned_subject_count"] is None
    assert audit["independent_subject_count"] is None


def test_real_gemini_has_no_control_or_original_grid():
    audit = audit_archive(DATA, "gemini_minimal")
    obs = audit["observations"]
    assert obs["rows"] == 32
    assert obs["observed_subject_labels"] == 2
    assert obs["treatment_label_counts"] == {"Prog,Flat25": 32}
    assert obs["outside_original_cap_support_rows"] == 16
    assert obs["subjects_with_complete_original_grid"] == 0
    assert obs["income_or_phase_inconsistencies"] == 0
    assert obs["recorded_task_choice_zero_rows"] == 0
    assert obs["recorded_task_choice_cap_rows"] == 31
    assert "no_Prog_Prog_comparison_arm" in audit["blockers"]


@pytest.mark.parametrize("archive", ARCHIVES)
def test_modified_input_rejected_before_deserialization(tmp_path, archive):
    filename, _ = ARCHIVES[archive]
    (tmp_path / filename).write_bytes((DATA / filename).read_bytes() + b"\n")
    with pytest.raises(DesignError, match="hash mismatch"):
        audit_archive(tmp_path, archive)


def test_unrecognized_run_cannot_borrow_old_provenance():
    with pytest.raises(DesignError, match="Unknown retained archive"):
        load_for_estimation(DATA, "new_prospective_treatment")


def test_observed_complete_grid_does_not_invent_missing_subject_inventory():
    # Explicitly synthetic metadata. Even perfect observed coverage says
    # nothing about subjects whose every planned response is missing.
    from llm_eti.lab_methods.estimands import ENDOWMENTS

    rows = [
        {
            "subject_label": "synthetic",
            "round": 8 * phase + i + 1,
            "phase": phase,
            "cap": cap,
        }
        for phase in (0, 1)
        for i, cap in enumerate(ENDOWMENTS)
    ]
    result = _grid(rows)
    assert result["subjects_with_complete_original_grid"] == 1
    assert result["full_planned_subject_count"] is None
    assert result["independent_subject_count"] is None


def test_synthetic_csv_zero_is_preserved_missing_is_rejected():
    # Exact retained schema, synthetic choice; never passes the hash gate.
    header = (DATA / ARCHIVES["gemini_minimal"][0]).read_text().splitlines()[0]
    row = '"Prog,Flat25",synthetic,1,progressive,22,0,0,False,synthetic'
    result = _csv_audit((header + "\n" + row + "\n").encode())
    assert result["rows"] == 1
    assert result["recorded_task_choice_zero_rows"] == 1
    with pytest.raises(ValueError):
        _csv_audit((header + "\n" + row.replace(",22,0,0,", ",22,,0,") + "\n").encode())


def test_publication_audit_has_no_nonfinite_or_empirical_estimands():
    report = publication_audit(DATA)
    json.dumps(report, allow_nan=False)
    assert report["empirical_lab_estimates_released"] is False
    assert all(a["human_Table_6_reproduced"] is False for a in report["archives"])
    table = audit_markdown(report)
    assert "Complete reference grids" in table
    assert "Complete original grids" not in table
    assert "observed labels covering all eight source-menu caps in each phase" in table
    assert "not a verified human assignment protocol or planned roster" in table
