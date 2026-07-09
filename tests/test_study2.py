import json
from pathlib import Path

import numpy as np
import pytest

from llm_eti.study2 import (
    clean_positive_pair_ids,
    completion_summary,
    model_summary,
    primary_analysis_scenario_ids,
    primary_balanced_scenario_ids,
    prompt_income,
    prompt_rate,
    sensitivity_summary,
)

ROOT = Path(__file__).resolve().parents[1]


def test_prompt_rendering_matches_legacy_python_formatting():
    assert prompt_income(12_345.5) == 12_346
    assert prompt_income(12_344.5) == 12_344
    assert prompt_rate(0.2799) == 0.27
    assert prompt_rate(-0.2799) == -0.27


def test_scenario_integrity(study_data):
    scenarios, _ = study_data
    assert len(scenarios) == 1_000
    assert scenarios["scenario_id"].nunique() == 1_000
    assert scenarios["duplicate_delivered_prompt"].sum() == 10
    assert (~scenarios["displayed_rate_change"]).sum() == 224
    assert scenarios["prompt_mtr"].lt(0).sum() == 17


def test_conservative_sample_flow(study_data):
    scenarios, results = study_data
    balanced = primary_balanced_scenario_ids(results)
    analysis = primary_analysis_scenario_ids(results)
    identified = scenarios[
        scenarios["scenario_id"].isin(balanced) & scenarios["displayed_rate_change"]
    ]

    assert len(results) == 8_087
    assert results["ambiguous_rerun"].sum() == 8
    assert len(balanced) == 821
    assert len(identified) == 632
    assert len(analysis) == 603


def test_completion_counts(study_data):
    scenarios, results = study_data
    completion = completion_summary(scenarios, results).set_index("model_key")

    assert completion["source_records"].to_dict() == {
        "claude_haiku_4_5": 2_000,
        "deepseek_v3": 1_678,
        "gemma_4_26b": 1_974,
        "gpt_4o_mini": 1_997,
        "gpt_4o": 446,
    }
    assert completion["completed_scenarios"].to_dict() == {
        "claude_haiku_4_5": 1_000,
        "deepseek_v3": 835,
        "gemma_4_26b": 987,
        "gpt_4o_mini": 999,
        "gpt_4o": 245,
    }


@pytest.mark.parametrize(
    ("model_key", "taxable", "taxable_ci", "broad", "broad_ci", "directional"),
    [
        (
            "claude_haiku_4_5",
            0.712642,
            (0.654093, 0.771190),
            0.424497,
            (0.398850, 0.450144),
            0.990,
        ),
        (
            "deepseek_v3",
            0.410232,
            (0.347147, 0.473317),
            0.000146,
            (-0.000109, 0.000402),
            0.955453149,
        ),
        (
            "gemma_4_26b",
            0.261423,
            (-0.013805, 0.536651),
            0.017850,
            (0.003442, 0.032258),
            0.667,
        ),
        (
            "gpt_4o_mini",
            0.356886,
            (0.266829, 0.446942),
            0.051619,
            (0.026664, 0.076574),
            0.841,
        ),
    ],
)
def test_primary_slopes_reproduce_audit(
    study_data, model_key, taxable, taxable_ci, broad, broad_ci, directional
):
    _, results = study_data
    summary = model_summary(
        results, scenario_ids=primary_analysis_scenario_ids(results)
    ).set_index("model_key")
    row = summary.loc[model_key]

    assert row["n_scenarios"] == 603
    assert row["n_clusters"] == 600
    assert row["slope"] == pytest.approx(taxable, abs=1e-6)
    assert row["slope_ci_lower"] == pytest.approx(taxable_ci[0], abs=1e-6)
    assert row["slope_ci_upper"] == pytest.approx(taxable_ci[1], abs=1e-6)
    assert row["broad_slope"] == pytest.approx(broad, abs=1e-6)
    assert row["broad_slope_ci_lower"] == pytest.approx(broad_ci[0], abs=1e-6)
    assert row["broad_slope_ci_upper"] == pytest.approx(broad_ci[1], abs=1e-6)
    assert row["directional_consistency_nonzero"] == pytest.approx(
        directional, abs=5e-4
    )


def test_same_displayed_rate_has_no_prompt_implied_ratio(study_data):
    _, results = study_data
    unidentified = results[~results["displayed_rate_change"]]
    assert unidentified["prompt_implied_eti"].isna().all()
    assert np.isfinite(unidentified["log1p_taxable_income_change"]).all()


def test_one_dollar_change_is_not_classified_as_unchanged(study_data):
    _, results = study_data
    dollar_change = (
        (results["taxable_income_this"] - results["prompt_taxable_income"]).abs().eq(1)
    )
    assert dollar_change.any()
    assert not results.loc[dollar_change, "taxable_income_unchanged"].any()


def test_static_manifest_hashes_match_generated_summary():
    run_manifest = json.loads((ROOT / "data" / "run_manifest.json").read_text())
    analysis_summary = json.loads(
        (ROOT / "paper" / "generated" / "analysis_summary.json").read_text()
    )
    expected = {
        path: metadata["sha256"] for path, metadata in run_manifest["files"].items()
    }
    assert analysis_summary["source_sha256"] == expected


@pytest.mark.parametrize(
    ("model_key", "identified_scenarios", "slope"),
    [
        ("claude_haiku_4_5", 769, 0.8166),
        ("deepseek_v3", 641, 0.4230),
        ("gemma_4_26b", 743, 0.2590),
        ("gpt_4o_mini", 727, 0.3651),
    ],
)
def test_model_specific_clean_pair_sensitivity(
    study_data, model_key, identified_scenarios, slope
):
    _, results = study_data
    analysis_ids = primary_analysis_scenario_ids(results)
    identified_ids = set(
        results.loc[
            results["scenario_id"].isin(primary_balanced_scenario_ids(results))
            & results["displayed_rate_change"],
            "scenario_id",
        ]
    )
    sensitivities = sensitivity_summary(results, analysis_ids, identified_ids)
    row = sensitivities[
        sensitivities["model_key"].eq(model_key)
        & sensitivities["specification"].eq("All clean completed pairs, intercept")
    ].iloc[0]

    assert len(clean_positive_pair_ids(results, model_key)) >= identified_scenarios
    assert row["n_scenarios"] == identified_scenarios
    assert row["slope"] == pytest.approx(slope, abs=5e-5)


def test_two_point_rate_change_sensitivity(study_data):
    _, results = study_data
    analysis_ids = primary_analysis_scenario_ids(results)
    identified_ids = set(
        results.loc[
            results["scenario_id"].isin(primary_balanced_scenario_ids(results))
            & results["displayed_rate_change"],
            "scenario_id",
        ]
    )
    rows = sensitivity_summary(results, analysis_ids, identified_ids)
    rows = rows[
        rows["specification"].eq("Balanced, at least 2-point rate change")
    ].set_index("model_key")

    assert rows["n_scenarios"].eq(291).all()
    assert rows.loc["claude_haiku_4_5", "slope"] == pytest.approx(0.661, abs=0.001)
    assert rows.loc["deepseek_v3", "slope"] == pytest.approx(0.397, abs=0.001)
    assert rows.loc["gemma_4_26b", "slope"] == pytest.approx(0.289, abs=0.001)
    assert rows.loc["gpt_4o_mini", "slope"] == pytest.approx(0.378, abs=0.001)
