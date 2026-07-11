import json
from pathlib import Path

import numpy as np
import pytest

from llm_eti.study2 import (
    EQUAL_YEAR_WEIGHT_SPECIFICATION,
    LOG1P_SPECIFICATION,
    PROPORTIONAL_CHANGE_SPECIFICATION,
    TAX_CUT_SPECIFICATION,
    TAX_INCREASE_SPECIFICATION,
    boundary_incidence_summary,
    clean_positive_pair_ids,
    collapse_repetitions,
    completion_summary,
    direction_symmetry_test,
    model_summary,
    primary_analysis_scenario_ids,
    primary_balanced_scenario_ids,
    prompt_income,
    prompt_rate,
    same_rate_summary,
    selection_balance_summary,
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


@pytest.mark.parametrize(
    (
        "model_key",
        "mean_ratio",
        "intercept",
        "r_squared",
        "broad_intercept",
        "broad_r_squared",
    ),
    [
        (
            "claude_haiku_4_5",
            0.841222677674,
            -0.005693766450,
            0.457020003664,
            -0.003098813429,
            0.611191150839,
        ),
        (
            "deepseek_v3",
            0.457632448497,
            -0.004515741037,
            0.329012305894,
            -0.000003921412,
            0.005122910614,
        ),
        (
            "gemma_4_26b",
            0.147433975324,
            0.002220388468,
            0.008497440974,
            -0.000187950636,
            0.052320076117,
        ),
        (
            "gpt_4o_mini",
            0.319714791777,
            -0.006338297723,
            0.159530637999,
            -0.001486564533,
            0.033925062240,
        ),
    ],
)
def test_primary_regression_diagnostics_and_ratio_means(
    study_data,
    model_key,
    mean_ratio,
    intercept,
    r_squared,
    broad_intercept,
    broad_r_squared,
):
    _, results = study_data
    summary = model_summary(
        results, scenario_ids=primary_analysis_scenario_ids(results)
    ).set_index("model_key")
    row = summary.loc[model_key]

    assert row["mean_implied_eti"] == pytest.approx(mean_ratio, abs=1e-12)
    assert row["intercept"] == pytest.approx(intercept, abs=1e-12)
    assert row["r_squared"] == pytest.approx(r_squared, abs=1e-12)
    assert row["broad_intercept"] == pytest.approx(broad_intercept, abs=1e-12)
    assert row["broad_r_squared"] == pytest.approx(broad_r_squared, abs=1e-12)
    assert row["broad_n_scenarios"] == 603
    assert row["broad_n_clusters"] == 600


def test_same_rate_summary_labels_response_and_pair_levels(study_data):
    _, results = study_data
    summary = same_rate_summary(
        results, primary_balanced_scenario_ids(results)
    ).set_index("model_key")

    expected = {
        "claude_haiku_4_5": (378, 378, 189, 189),
        "deepseek_v3": (378, 354, 189, 173),
        "gemma_4_26b": (378, 376, 189, 187),
        "gpt_4o_mini": (378, 369, 189, 184),
    }
    for model_key, counts in expected.items():
        row = summary.loc[model_key]
        assert (
            tuple(
                int(row[column])
                for column in [
                    "response_records",
                    "unchanged_responses",
                    "scenario_pairs",
                    "both_unchanged_pairs",
                ]
            )
            == counts
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


@pytest.mark.parametrize(
    ("model_key", "tax_cut", "tax_increase", "equal_year", "proportional"),
    [
        (
            "claude_haiku_4_5",
            (0.525752, 0.337166, 0.714338),
            (0.448267, 0.235499, 0.661035),
            (0.719466, 0.646628, 0.792304),
            (0.747499, 0.675551, 0.819447),
        ),
        (
            "deepseek_v3",
            (0.174990, 0.062950, 0.287029),
            (0.539225, 0.323077, 0.755373),
            (0.418893, 0.350989, 0.486796),
            (0.414635, 0.354948, 0.474323),
        ),
        (
            "gemma_4_26b",
            (0.416070, -0.121658, 0.953797),
            (0.422911, -0.077373, 0.923196),
            (0.323064, -0.066809, 0.712937),
            (1.232939, -0.151472, 2.617351),
        ),
        (
            "gpt_4o_mini",
            (0.325101, 0.023290, 0.626911),
            (0.577056, 0.315606, 0.838505),
            (0.348442, 0.261722, 0.435162),
            (1.181449, 0.758846, 1.604051),
        ),
    ],
)
def test_additive_direction_scale_and_year_sensitivities(
    study_data, model_key, tax_cut, tax_increase, equal_year, proportional
):
    scenarios, results = study_data
    analysis_ids = primary_analysis_scenario_ids(results)
    identified_ids = set(
        scenarios.loc[
            scenarios["scenario_id"].isin(primary_balanced_scenario_ids(results))
            & scenarios["displayed_rate_change"],
            "scenario_id",
        ]
    )
    rows = sensitivity_summary(results, analysis_ids, identified_ids).set_index(
        ["model_key", "specification"]
    )

    expected = {
        TAX_CUT_SPECIFICATION: (298, 297, tax_cut),
        TAX_INCREASE_SPECIFICATION: (305, 304, tax_increase),
        EQUAL_YEAR_WEIGHT_SPECIFICATION: (603, 600, equal_year),
        PROPORTIONAL_CHANGE_SPECIFICATION: (632, 629, proportional),
    }
    for label, (n_scenarios, n_clusters, estimates) in expected.items():
        row = rows.loc[(model_key, label)]
        assert row["n_scenarios"] == n_scenarios
        assert row["n_clusters"] == n_clusters
        assert row["slope"] == pytest.approx(estimates[0], abs=1e-6)
        assert row["slope_ci_lower"] == pytest.approx(estimates[1], abs=1e-6)
        assert row["slope_ci_upper"] == pytest.approx(estimates[2], abs=1e-6)

    log1p = rows.loc[(model_key, LOG1P_SPECIFICATION)]
    assert log1p["n_scenarios"] == 632
    assert log1p["n_clusters"] == 629


def test_deepseek_direction_symmetry_test(study_data):
    _, results = study_data
    model = collapse_repetitions(results)
    model = model[
        model["model_key"].eq("deepseek_v3")
        & model["scenario_id"].isin(primary_analysis_scenario_ids(results))
    ]
    test = direction_symmetry_test(model)

    assert test["n_scenarios"] == 603
    assert test["n_clusters"] == 600
    assert test["tax_cut_slope"] == pytest.approx(0.174990, abs=1e-6)
    assert test["tax_increase_slope"] == pytest.approx(0.539225, abs=1e-6)
    assert test["slope_difference"] == pytest.approx(0.364235, abs=1e-6)
    assert test["p_value"] == pytest.approx(0.00336627, abs=1e-8)


def test_boundary_incidence_by_model_and_direction(study_data):
    scenarios, results = study_data
    identified_ids = set(
        scenarios.loc[
            scenarios["scenario_id"].isin(primary_balanced_scenario_ids(results))
            & scenarios["displayed_rate_change"],
            "scenario_id",
        ]
    )
    incidence = boundary_incidence_summary(results, identified_ids).set_index(
        ["model_key", "direction"]
    )

    expected = {
        ("claude_haiku_4_5", "Tax decrease"): (604, 0, 302, 0),
        ("claude_haiku_4_5", "Tax increase"): (660, 0, 330, 0),
        ("deepseek_v3", "Tax decrease"): (604, 0, 302, 0),
        ("deepseek_v3", "Tax increase"): (660, 0, 330, 0),
        ("gemma_4_26b", "Tax decrease"): (604, 3, 302, 2),
        ("gemma_4_26b", "Tax increase"): (660, 16, 330, 10),
        ("gpt_4o_mini", "Tax decrease"): (604, 5, 302, 3),
        ("gpt_4o_mini", "Tax increase"): (660, 32, 330, 22),
        ("any_primary", "Tax decrease"): (2_416, 8, 302, 4),
        ("any_primary", "Tax increase"): (2_640, 48, 330, 25),
    }
    for key, values in expected.items():
        row = incidence.loc[key]
        assert (
            tuple(
                int(row[column])
                for column in [
                    "response_records",
                    "nonpositive_records",
                    "scenarios",
                    "affected_scenarios",
                ]
            )
            == values
        )


def test_retained_vs_omitted_selection_balance(study_data):
    scenarios, results = study_data
    balanced_ids = primary_balanced_scenario_ids(results)
    analysis_ids = primary_analysis_scenario_ids(results)
    identified_ids = set(
        scenarios.loc[
            scenarios["scenario_id"].isin(balanced_ids)
            & scenarios["displayed_rate_change"],
            "scenario_id",
        ]
    )
    balance = selection_balance_summary(
        scenarios, identified_ids, analysis_ids
    ).set_index("sample")

    retained = balance.loc["Retained"]
    omitted = balance.loc["Omitted"]
    assert retained["n_scenarios"] == 603
    assert omitted["n_scenarios"] == 29
    assert retained["median_broad_income"] == 76_500
    assert omitted["median_broad_income"] == 23_010
    assert retained["median_taxable_income"] == 53_616
    assert omitted["median_taxable_income"] == 6_150
    assert retained["tax_increase_count"] == 305
    assert omitted["tax_increase_count"] == 25
    assert retained["year_2023_count"] == 396
    assert omitted["year_2023_count"] == 17
