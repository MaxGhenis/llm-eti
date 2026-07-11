"""Validated analysis utilities for the taxable-income response experiment.

The raw result files were produced in June 2026.  The functions in this module
reconstruct the values that were actually displayed in the prompt before
estimating any response elasticities.  This matters because the prompt rounded
incomes to whole dollars and truncated marginal tax rates to integer
percentages, while the legacy ``implied_eti_*`` columns used unrounded inputs.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

SCENARIO_KEY = [
    "tax_unit_id",
    "broad_income",
    "taxable_income",
    "mtr",
    "mtr_prime",
]
DELIVERED_PROMPT_KEY = [
    "prompt_broad_income",
    "prompt_taxable_income",
    "prompt_mtr",
    "prompt_mtr_prime",
]
EXPECTED_RESPONSES_PER_SCENARIO = 2
CLEAN_PAIRS_SPECIFICATION = "All clean completed pairs, intercept"
TAX_CUT_SPECIFICATION = "Primary positive-output panel, tax cuts only"
TAX_INCREASE_SPECIFICATION = "Primary positive-output panel, tax increases only"
EQUAL_YEAR_WEIGHT_SPECIFICATION = (
    "Primary positive-output panel, equal total weight by year"
)
PROPORTIONAL_CHANGE_SPECIFICATION = (
    "Identified balanced panel, proportional changes, zeros included"
)
LOG1P_SPECIFICATION = "Boundary stress test including zeros (log1p)"


@dataclass(frozen=True)
class ModelSpec:
    """A frozen model result file and its role in the analysis."""

    key: str
    display_name: str
    filename: str
    primary: bool = True


MODEL_SPECS = (
    ModelSpec(
        "claude_haiku_4_5",
        "Claude Haiku 4.5",
        "gruber_saez_results_claude-haiku-4-5-20251001.csv",
    ),
    ModelSpec(
        "deepseek_v3",
        "DeepSeek V3",
        "gruber_saez_results_deepseek-ai_DeepSeek-V3.csv",
    ),
    ModelSpec(
        "gemma_4_26b",
        "Gemma 4 26B",
        "gruber_saez_results_google_gemma-4-26B-A4B-it.csv",
    ),
    ModelSpec(
        "gpt_4o_mini",
        "GPT-4o mini",
        "gruber_saez_results_gpt-4o-mini.csv",
    ),
    ModelSpec(
        "gpt_4o",
        "GPT-4o (partial run)",
        "gruber_saez_results_gpt-4o.csv",
        primary=False,
    ),
)


def _require_columns(df: pd.DataFrame, columns: Iterable[str], source: Path) -> None:
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def _cluster_id(frame: pd.DataFrame) -> pd.Series:
    """Build the year × source-tax-unit key used for cluster-robust inference."""

    return frame["year"].astype(str) + "-" + frame["tax_unit_id"].astype(str)


def prompt_income(value: float) -> float:
    """Return the whole-dollar income shown by ``f'{value:,.0f}'``."""

    return float(f"{value:.0f}")


def prompt_rate(value: float) -> float:
    """Return the decimal rate shown by ``int(value * 100)`` in the prompt."""

    return int(value * 100) / 100


def load_scenarios(path: Path) -> pd.DataFrame:
    """Load the immutable PolicyEngine-derived scenario sample."""

    # The frozen scenario file encodes the float key columns with one more
    # significant digit than the response CSVs; the two encodings are one unit
    # in the last place apart as exact doubles.  The merge in
    # ``load_model_results`` matches only because pandas' default "high"
    # parser rounds both encodings onto the same float64, so that parser is
    # pinned here and there; ``float_precision="round_trip"`` leaves roughly
    # half of the response rows unmatched.
    scenarios = pd.read_csv(path, float_precision="high")
    required = ["year", "household_weight", *SCENARIO_KEY]
    _require_columns(scenarios, required, path)

    if len(scenarios) != 1_000:
        raise ValueError(f"Expected 1,000 scenarios in {path}, found {len(scenarios)}")
    if scenarios.duplicated(SCENARIO_KEY).any():
        raise ValueError(f"Scenario keys are not unique in {path}")
    if (scenarios[["broad_income", "taxable_income"]] <= 0).any().any():
        raise ValueError(f"Non-positive baseline income found in {path}")
    if ((1 - scenarios[["mtr", "mtr_prime"]]) <= 0).any().any():
        raise ValueError(f"Net-of-tax rate is non-positive in {path}")

    scenarios = scenarios.copy()
    scenarios.insert(0, "scenario_id", [f"S{i:04d}" for i in range(1, 1_001)])
    scenarios["prompt_broad_income"] = scenarios["broad_income"].map(prompt_income)
    scenarios["prompt_taxable_income"] = scenarios["taxable_income"].map(prompt_income)
    scenarios["prompt_mtr"] = scenarios["mtr"].map(prompt_rate)
    scenarios["prompt_mtr_prime"] = scenarios["mtr_prime"].map(prompt_rate)
    scenarios["log_net_of_tax_change"] = np.log(
        (1 - scenarios["prompt_mtr_prime"]) / (1 - scenarios["prompt_mtr"])
    )
    scenarios["proportional_net_of_tax_change"] = np.expm1(
        scenarios["log_net_of_tax_change"]
    )
    scenarios["displayed_rate_change"] = (
        scenarios["prompt_mtr"] != scenarios["prompt_mtr_prime"]
    )
    scenarios["duplicate_delivered_prompt"] = scenarios.duplicated(
        DELIVERED_PROMPT_KEY, keep=False
    )
    return scenarios


def _deduplicate_repeated_runs(df: pd.DataFrame, source: Path) -> pd.DataFrame:
    """Flag and collapse ambiguous reruns while retaining intended repetitions."""

    group_columns = [*SCENARIO_KEY, "response_number"]
    df = df.copy()
    df["ambiguous_rerun"] = (
        df.groupby(group_columns, dropna=False)["response_number"].transform("size") > 1
    )
    return (
        df.sort_values(["timestamp", "response_number"], kind="stable")
        .drop_duplicates(group_columns, keep="first")
        .reset_index(drop=True)
    )


def load_model_results(
    spec: ModelSpec, data_dir: Path, scenarios: pd.DataFrame
) -> pd.DataFrame:
    """Load, validate, deduplicate, and align one model's result file."""

    source = data_dir / spec.filename
    # Pinned to match ``load_scenarios``; see the float-encoding note there.
    results = pd.read_csv(source, float_precision="high")
    source_record_count = len(results)
    required = [
        "timestamp",
        "response_number",
        "taxable_income_this",
        "broad_income_this",
        "model",
        "income_response_raw",
        *SCENARIO_KEY,
    ]
    _require_columns(results, required, source)
    results = _deduplicate_repeated_runs(results, source)
    results["source_record_count"] = source_record_count

    if not results["response_number"].isin([1, 2]).all():
        raise ValueError(f"Unexpected response number in {source}")

    results = results.merge(
        scenarios,
        on=SCENARIO_KEY,
        how="left",
        validate="many_to_one",
        suffixes=("", "_scenario"),
        indicator=True,
    )
    unmatched = results["_merge"] != "both"
    if unmatched.any():
        raise ValueError(f"{unmatched.sum()} rows in {source} do not match a scenario")
    results = results.drop(columns="_merge")

    results["clean_row"] = (
        ~results["duplicate_delivered_prompt"] & ~results["ambiguous_rerun"]
    )
    results["model_key"] = spec.key
    results["model_display"] = spec.display_name
    results["primary_model"] = spec.primary
    results["cluster_id"] = _cluster_id(results)
    results["valid_income_response"] = (
        results["taxable_income_this"].ge(0)
        & results["broad_income_this"].ge(0)
        & results["taxable_income_this"].notna()
        & results["broad_income_this"].notna()
    )
    results["positive_income_response"] = results["taxable_income_this"].gt(
        0
    ) & results["broad_income_this"].gt(0)

    results["log_taxable_income_change"] = np.nan
    results["log_broad_income_change"] = np.nan
    positive = results["positive_income_response"]
    results.loc[positive, "log_taxable_income_change"] = np.log(
        results.loc[positive, "taxable_income_this"]
        / results.loc[positive, "prompt_taxable_income"]
    )
    results.loc[positive, "log_broad_income_change"] = np.log(
        results.loc[positive, "broad_income_this"]
        / results.loc[positive, "prompt_broad_income"]
    )
    results["log1p_taxable_income_change"] = np.where(
        results["valid_income_response"],
        np.log1p(results["taxable_income_this"])
        - np.log1p(results["prompt_taxable_income"]),
        np.nan,
    )
    results["proportional_taxable_income_change"] = np.where(
        results["valid_income_response"],
        results["taxable_income_this"] / results["prompt_taxable_income"] - 1,
        np.nan,
    )
    results["taxable_income_unchanged"] = np.isclose(
        results["taxable_income_this"],
        results["prompt_taxable_income"],
        atol=0.5,
        rtol=0,
    )
    results["directionally_consistent"] = (
        results["log_taxable_income_change"] * results["log_net_of_tax_change"] > 0
    )
    results["prompt_implied_eti"] = np.where(
        results["displayed_rate_change"],
        results["log_taxable_income_change"] / results["log_net_of_tax_change"],
        np.nan,
    )
    return results


def load_study2_data(
    scenario_path: Path, data_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load all scenarios and all archived model responses."""

    scenarios = load_scenarios(scenario_path)
    results = pd.concat(
        [load_model_results(spec, data_dir, scenarios) for spec in MODEL_SPECS],
        ignore_index=True,
    )
    return scenarios, results


def completed_scenario_ids(
    results: pd.DataFrame,
    model_keys: Iterable[str],
    *,
    require_both_repetitions: bool = True,
) -> set[str]:
    """Return unambiguous scenarios completed by every selected model."""

    requested = list(model_keys)
    eligible = results[
        results["model_key"].isin(requested)
        & results["valid_income_response"]
        & results["clean_row"]
    ]
    by_model = eligible.groupby(["scenario_id", "model_key"])[
        "response_number"
    ].nunique()
    required_repetitions = 2 if require_both_repetitions else 1
    complete_models = by_model[by_model.ge(required_repetitions)].reset_index()
    counts = complete_models.groupby("scenario_id")["model_key"].nunique()
    return set(counts[counts.eq(len(requested))].index)


def primary_balanced_scenario_ids(results: pd.DataFrame) -> set[str]:
    """Return the common scenario set for the four primary models."""

    return completed_scenario_ids(
        results, [spec.key for spec in MODEL_SPECS if spec.primary]
    )


def primary_analysis_scenario_ids(results: pd.DataFrame) -> set[str]:
    """Return the positive-income, changed-rate primary analysis panel."""

    balanced = primary_balanced_scenario_ids(results)
    primary = results[
        results["primary_model"]
        & results["scenario_id"].isin(balanced)
        & results["displayed_rate_change"]
    ]
    positive_counts = primary.groupby("scenario_id")["positive_income_response"].agg(
        ["sum", "size"]
    )
    required_rows = (
        sum(spec.primary for spec in MODEL_SPECS) * EXPECTED_RESPONSES_PER_SCENARIO
    )
    return set(
        positive_counts[
            positive_counts["sum"].eq(positive_counts["size"])
            & positive_counts["size"].eq(required_rows)
        ].index
    )


def clean_positive_pair_ids(results: pd.DataFrame, model_key: str) -> set[str]:
    """Return scenarios with two clean, strictly positive responses for a model."""

    eligible = results[
        results["model_key"].eq(model_key)
        & results["positive_income_response"]
        & results["clean_row"]
    ]
    counts = eligible.groupby("scenario_id").agg(
        records=("response_number", "size"),
        repetitions=("response_number", "nunique"),
    )
    return set(counts[counts["records"].eq(2) & counts["repetitions"].eq(2)].index)


def collapse_repetitions(
    results: pd.DataFrame, *, clean_only: bool = True
) -> pd.DataFrame:
    """Average repetitions so each model-scenario is one observation.

    The default excludes delivered-prompt collisions and ambiguous recovery
    reruns.  Those records remain available in the archived-response and
    completion diagnostics, but no inferential specification silently uses
    them.
    """

    valid = results[results["valid_income_response"]].copy()
    if clean_only:
        valid = valid[valid["clean_row"]]
    group_columns = [
        "model_key",
        "model_display",
        "primary_model",
        "scenario_id",
        "year",
        "tax_unit_id",
        "prompt_mtr",
        "prompt_mtr_prime",
        "prompt_broad_income",
        "prompt_taxable_income",
        "displayed_rate_change",
        "log_net_of_tax_change",
        "proportional_net_of_tax_change",
    ]
    return (
        valid.groupby(group_columns, as_index=False, dropna=False)
        .agg(
            taxable_income_this=("taxable_income_this", "mean"),
            broad_income_this=("broad_income_this", "mean"),
            log_taxable_income_change=("log_taxable_income_change", "mean"),
            log_broad_income_change=("log_broad_income_change", "mean"),
            log1p_taxable_income_change=("log1p_taxable_income_change", "mean"),
            proportional_taxable_income_change=(
                "proportional_taxable_income_change",
                "mean",
            ),
            repetitions=("response_number", "nunique"),
            taxable_income_unchanged=("taxable_income_unchanged", "mean"),
            directionally_consistent=("directionally_consistent", "mean"),
        )
        .assign(
            cluster_id=_cluster_id,
            prompt_implied_eti=lambda df: np.where(
                df["displayed_rate_change"],
                df["log_taxable_income_change"] / df["log_net_of_tax_change"],
                np.nan,
            ),
        )
    )


def fit_log_response(
    data: pd.DataFrame,
    *,
    outcome: str = "log_taxable_income_change",
    predictor: str = "log_net_of_tax_change",
    include_intercept: bool = True,
    weight_column: str | None = None,
) -> dict[str, float | int]:
    """Estimate a model-implied response slope with cluster-robust inference.

    The archived sample can contain the same source tax unit in both years, so
    the primary covariance estimator clusters by year and source tax unit.  A
    HC3 fallback is retained for standalone frames without a ``cluster_id``.
    """

    eligible = (
        data["displayed_rate_change"]
        & data[outcome].notna()
        & np.isfinite(data[outcome])
        & data[predictor].notna()
        & np.isfinite(data[predictor])
    )
    if weight_column is not None:
        eligible &= (
            data[weight_column].notna()
            & np.isfinite(data[weight_column])
            & data[weight_column].gt(0)
        )
    sample = data[eligible]
    if len(sample) < 3:
        raise ValueError("At least three identified scenarios are required")

    x = sample[[predictor]]
    if include_intercept:
        x = sm.add_constant(x, has_constant="add")
    estimator = (
        sm.OLS(sample[outcome], x)
        if weight_column is None
        else sm.WLS(sample[outcome], x, weights=sample[weight_column])
    )
    if "cluster_id" in sample:
        fit = estimator.fit(
            cov_type="cluster",
            cov_kwds={"groups": sample["cluster_id"], "use_correction": True},
            use_t=False,
        )
    else:
        fit = estimator.fit(cov_type="HC3", use_t=False)
    slope = float(fit.params[predictor])
    slope_se = float(fit.bse[predictor])
    ci = fit.conf_int().loc[predictor]
    intercept = float(fit.params.get("const", 0.0))
    intercept_se = float(fit.bse.get("const", 0.0))
    return {
        "n_scenarios": int(len(sample)),
        "slope": slope,
        "slope_se": slope_se,
        "slope_ci_lower": float(ci.iloc[0]),
        "slope_ci_upper": float(ci.iloc[1]),
        "intercept": intercept,
        "intercept_se": intercept_se,
        "r_squared": float(fit.rsquared),
        "n_clusters": (
            int(sample["cluster_id"].nunique())
            if "cluster_id" in sample
            else int(len(sample))
        ),
    }


def direction_symmetry_test(data: pd.DataFrame) -> dict[str, float | int]:
    """Test equality of tax-cut and tax-increase slopes on one model panel."""

    sample = data[
        data["displayed_rate_change"]
        & data["log_taxable_income_change"].notna()
        & np.isfinite(data["log_taxable_income_change"])
        & np.isfinite(data["log_net_of_tax_change"])
    ].copy()
    if len(sample) < 6:
        raise ValueError("At least six identified scenarios are required")

    sample["tax_increase"] = sample["prompt_mtr_prime"].gt(sample["prompt_mtr"])
    sample["direction_interaction"] = (
        sample["log_net_of_tax_change"] * sample["tax_increase"]
    )
    x = sm.add_constant(
        sample[
            ["log_net_of_tax_change", "tax_increase", "direction_interaction"]
        ].astype(float),
        has_constant="add",
    )
    estimator = sm.OLS(sample["log_taxable_income_change"], x)
    if "cluster_id" in sample:
        fit = estimator.fit(
            cov_type="cluster",
            cov_kwds={"groups": sample["cluster_id"], "use_correction": True},
            use_t=False,
        )
    else:
        fit = estimator.fit(cov_type="HC3", use_t=False)

    tax_cut_slope = float(fit.params["log_net_of_tax_change"])
    difference = float(fit.params["direction_interaction"])
    return {
        "n_scenarios": int(len(sample)),
        "n_clusters": (
            int(sample["cluster_id"].nunique())
            if "cluster_id" in sample
            else int(len(sample))
        ),
        "tax_cut_slope": tax_cut_slope,
        "tax_increase_slope": tax_cut_slope + difference,
        "slope_difference": difference,
        "slope_difference_se": float(fit.bse["direction_interaction"]),
        "p_value": float(fit.pvalues["direction_interaction"]),
    }


def boundary_incidence_summary(
    results: pd.DataFrame, identified_balanced_ids: set[str]
) -> pd.DataFrame:
    """Summarize zero and nonpositive outputs by model and tax direction."""

    sample = results[
        results["primary_model"]
        & results["scenario_id"].isin(identified_balanced_ids)
        & results["valid_income_response"]
    ].copy()
    sample["direction"] = np.where(
        sample["prompt_mtr_prime"].gt(sample["prompt_mtr"]),
        "Tax increase",
        "Tax decrease",
    )
    sample["nonpositive_output"] = sample["taxable_income_this"].le(0) | sample[
        "broad_income_this"
    ].le(0)

    records = (
        sample.groupby(["model_key", "model_display", "direction"], as_index=False)
        .agg(
            response_records=("scenario_id", "size"),
            zero_taxable_records=(
                "taxable_income_this",
                lambda values: int(values.eq(0).sum()),
            ),
            zero_broad_records=(
                "broad_income_this",
                lambda values: int(values.eq(0).sum()),
            ),
            nonpositive_records=("nonpositive_output", "sum"),
        )
        .astype(
            {
                "response_records": int,
                "zero_taxable_records": int,
                "zero_broad_records": int,
                "nonpositive_records": int,
            }
        )
    )
    scenarios = (
        sample.groupby(
            ["model_key", "model_display", "direction", "scenario_id"],
            as_index=False,
        )["nonpositive_output"]
        .any()
        .groupby(["model_key", "model_display", "direction"], as_index=False)
        .agg(
            scenarios=("scenario_id", "size"),
            affected_scenarios=("nonpositive_output", "sum"),
        )
        .astype({"scenarios": int, "affected_scenarios": int})
    )
    by_model = records.merge(
        scenarios,
        on=["model_key", "model_display", "direction"],
        validate="one_to_one",
    )
    overall_records = (
        sample.groupby("direction", as_index=False)
        .agg(
            response_records=("scenario_id", "size"),
            zero_taxable_records=(
                "taxable_income_this",
                lambda values: int(values.eq(0).sum()),
            ),
            zero_broad_records=(
                "broad_income_this",
                lambda values: int(values.eq(0).sum()),
            ),
            nonpositive_records=("nonpositive_output", "sum"),
        )
        .astype(
            {
                "response_records": int,
                "zero_taxable_records": int,
                "zero_broad_records": int,
                "nonpositive_records": int,
            }
        )
    )
    overall_scenarios = (
        sample.groupby(["direction", "scenario_id"], as_index=False)[
            "nonpositive_output"
        ]
        .any()
        .groupby("direction", as_index=False)
        .agg(
            scenarios=("scenario_id", "size"),
            affected_scenarios=("nonpositive_output", "sum"),
        )
        .astype({"scenarios": int, "affected_scenarios": int})
    )
    overall = overall_records.merge(
        overall_scenarios, on="direction", validate="one_to_one"
    ).assign(model_key="any_primary", model_display="Any primary model")
    return pd.concat([by_model, overall[by_model.columns]], ignore_index=True)


def selection_balance_summary(
    scenarios: pd.DataFrame,
    identified_balanced_ids: set[str],
    analysis_ids: set[str],
) -> pd.DataFrame:
    """Compare scenarios retained and omitted by the all-positive restriction."""

    sample = scenarios[scenarios["scenario_id"].isin(identified_balanced_ids)].copy()
    sample["sample"] = np.where(
        sample["scenario_id"].isin(analysis_ids), "Retained", "Omitted"
    )
    sample["tax_increase"] = sample["prompt_mtr_prime"].gt(sample["prompt_mtr"])
    rows = []
    for label in ["Retained", "Omitted"]:
        group = sample[sample["sample"].eq(label)]
        rows.append(
            {
                "sample": label,
                "n_scenarios": int(len(group)),
                "median_broad_income": float(group["prompt_broad_income"].median()),
                "median_taxable_income": float(group["prompt_taxable_income"].median()),
                "median_initial_mtr": float(group["prompt_mtr"].median()),
                "median_new_mtr": float(group["prompt_mtr_prime"].median()),
                "median_absolute_rate_change": float(
                    (group["prompt_mtr_prime"] - group["prompt_mtr"]).abs().median()
                ),
                "tax_increase_count": int(group["tax_increase"].sum()),
                "tax_increase_share": float(group["tax_increase"].mean()),
                "year_2023_count": int(group["year"].eq(2023).sum()),
                "year_2023_share": float(group["year"].eq(2023).mean()),
                "year_2024_count": int(group["year"].eq(2024).sum()),
                "year_2024_share": float(group["year"].eq(2024).mean()),
            }
        )
    return pd.DataFrame(rows)


def same_rate_summary(
    results: pd.DataFrame, balanced_scenario_ids: set[str]
) -> pd.DataFrame:
    """Summarize same-rate stability at response and scenario-pair levels."""

    sample = results[
        results["primary_model"]
        & results["scenario_id"].isin(balanced_scenario_ids)
        & ~results["displayed_rate_change"]
        & results["valid_income_response"]
    ]
    rows = []
    for model_key, model in sample.groupby("model_key", sort=False):
        pairs = model.groupby("scenario_id").agg(
            responses=("response_number", "nunique"),
            both_unchanged=("taxable_income_unchanged", "all"),
        )
        pairs = pairs[pairs["responses"].eq(EXPECTED_RESPONSES_PER_SCENARIO)]
        rows.append(
            {
                "model_key": model_key,
                "model": model["model_display"].iloc[0],
                "response_records": int(len(model)),
                "unchanged_responses": int(model["taxable_income_unchanged"].sum()),
                "unchanged_response_share": float(
                    model["taxable_income_unchanged"].mean()
                ),
                "scenario_pairs": int(len(pairs)),
                "both_unchanged_pairs": int(pairs["both_unchanged"].sum()),
                "both_unchanged_pair_share": float(pairs["both_unchanged"].mean()),
            }
        )
    return pd.DataFrame(rows)


def completion_summary(scenarios: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Summarize archived run completion without hiding failed scenarios."""

    rows = []
    total = len(scenarios)
    for spec in MODEL_SPECS:
        model = results[results["model_key"].eq(spec.key)]
        valid = model[model["valid_income_response"]]
        completed = valid["scenario_id"].nunique()
        complete_pairs = int(
            valid.groupby("scenario_id")["response_number"].nunique().eq(2).sum()
        )
        rows.append(
            {
                "model_key": spec.key,
                "model": spec.display_name,
                "primary": spec.primary,
                "completed_scenarios": completed,
                "total_scenarios": total,
                "scenario_completion_rate": completed / total,
                "source_records": int(model["source_record_count"].max()),
                "valid_responses": len(valid),
                "complete_pairs": complete_pairs,
                "expected_responses": total * EXPECTED_RESPONSES_PER_SCENARIO,
                "response_completion_rate": len(valid)
                / (total * EXPECTED_RESPONSES_PER_SCENARIO),
            }
        )
    return pd.DataFrame(rows)


def model_summary(
    results: pd.DataFrame,
    *,
    scenario_ids: set[str],
    primary_only: bool = True,
) -> pd.DataFrame:
    """Return regression and robust descriptive results by model."""

    collapsed = collapse_repetitions(results)
    collapsed = collapsed[collapsed["scenario_id"].isin(scenario_ids)]
    if primary_only:
        collapsed = collapsed[collapsed["primary_model"]]

    rows = []
    for model_key, model in collapsed.groupby("model_key", sort=False):
        identified = model[model["displayed_rate_change"]]
        fit = fit_log_response(model)
        broad_fit = fit_log_response(model, outcome="log_broad_income_change")
        eti = identified["prompt_implied_eti"].replace([np.inf, -np.inf], np.nan)
        raw_model = results[
            results["model_key"].eq(model_key)
            & results["scenario_id"].isin(scenario_ids)
            & results["valid_income_response"]
        ]
        changed_responses = raw_model[~raw_model["taxable_income_unchanged"]]
        paired = raw_model.pivot_table(
            index="scenario_id",
            columns="response_number",
            values=["taxable_income_this", "broad_income_this"],
            aggfunc="first",
        ).dropna()
        repeat_agreement = (
            (paired[("taxable_income_this", 1)] == paired[("taxable_income_this", 2)])
            & (paired[("broad_income_this", 1)] == paired[("broad_income_this", 2)])
        ).mean()
        rows.append(
            {
                "model_key": model_key,
                "model": model["model_display"].iloc[0],
                **fit,
                "broad_slope": broad_fit["slope"],
                "broad_slope_se": broad_fit["slope_se"],
                "broad_slope_ci_lower": broad_fit["slope_ci_lower"],
                "broad_slope_ci_upper": broad_fit["slope_ci_upper"],
                "broad_intercept": broad_fit["intercept"],
                "broad_intercept_se": broad_fit["intercept_se"],
                "broad_r_squared": broad_fit["r_squared"],
                "broad_n_scenarios": broad_fit["n_scenarios"],
                "broad_n_clusters": broad_fit["n_clusters"],
                "mean_implied_eti": float(eti.mean()),
                "median_implied_eti": float(eti.median()),
                "eti_q25": float(eti.quantile(0.25)),
                "eti_q75": float(eti.quantile(0.75)),
                "unchanged_share": float(model["taxable_income_unchanged"].mean()),
                "directional_consistency_nonzero": (
                    float(changed_responses["directionally_consistent"].mean())
                    if len(changed_responses)
                    else np.nan
                ),
                "mean_repetitions": float(model["repetitions"].mean()),
                "zero_taxable_income_share": float(
                    raw_model["taxable_income_this"].eq(0).mean()
                ),
                "repeat_agreement_share": float(repeat_agreement),
            }
        )
    return pd.DataFrame(rows)


def sensitivity_summary(
    results: pd.DataFrame,
    analysis_ids: set[str],
    identified_balanced_ids: set[str] | None = None,
) -> pd.DataFrame:
    """Estimate the reported exploratory sample/specification sensitivities."""

    collapsed = collapse_repetitions(results)
    if identified_balanced_ids is None:
        identified_balanced_ids = analysis_ids
    rows = []
    for spec in MODEL_SPECS:
        if not spec.primary:
            continue
        model_clean = collapsed[collapsed["model_key"].eq(spec.key)]
        model_all_positive = model_clean[
            model_clean["scenario_id"].isin(clean_positive_pair_ids(results, spec.key))
        ]
        model_balanced = model_clean[model_clean["scenario_id"].isin(analysis_ids)]
        model_balanced = model_balanced.copy()
        model_balanced["equal_year_weight"] = 1 / model_balanced.groupby("year")[
            "scenario_id"
        ].transform("size")
        model_2023 = model_balanced[model_balanced["year"].eq(2023)]
        model_2024 = model_balanced[model_balanced["year"].eq(2024)]
        model_with_zeros = model_clean[
            model_clean["scenario_id"].isin(identified_balanced_ids)
        ]
        positive_rate = model_balanced[model_balanced["prompt_mtr"].ge(0)]
        tax_cuts = model_balanced[
            model_balanced["prompt_mtr_prime"].lt(model_balanced["prompt_mtr"])
        ]
        tax_increases = model_balanced[
            model_balanced["prompt_mtr_prime"].gt(model_balanced["prompt_mtr"])
        ]
        two_point_change = model_balanced[
            (model_balanced["prompt_mtr_prime"] - model_balanced["prompt_mtr"])
            .abs()
            .ge(0.019999)
        ]
        first_response = results[
            results["model_key"].eq(spec.key)
            & results["scenario_id"].isin(analysis_ids)
            & results["response_number"].eq(1)
            & results["valid_income_response"]
        ]
        winsorized = model_balanced.copy()
        lower, upper = winsorized["log_taxable_income_change"].quantile([0.01, 0.99])
        winsorized["log_taxable_income_change"] = winsorized[
            "log_taxable_income_change"
        ].clip(lower, upper)

        specifications: list[tuple[str, pd.DataFrame, bool, str, str, str | None]] = [
            (
                "Balanced, intercept",
                model_balanced,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                TAX_CUT_SPECIFICATION,
                tax_cuts,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                TAX_INCREASE_SPECIFICATION,
                tax_increases,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                EQUAL_YEAR_WEIGHT_SPECIFICATION,
                model_balanced,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                "equal_year_weight",
            ),
            (
                "Balanced, 2023 only",
                model_2023,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                "Balanced, 2024 only",
                model_2024,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                "Balanced, through origin",
                model_balanced,
                False,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                CLEAN_PAIRS_SPECIFICATION,
                model_all_positive,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                "Balanced, nonnegative initial MTR",
                positive_rate,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                "Balanced, at least 2-point rate change",
                two_point_change,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                "Balanced, first response only",
                first_response,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                "Balanced, 1% winsorized outcome",
                winsorized,
                True,
                "log_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
            (
                PROPORTIONAL_CHANGE_SPECIFICATION,
                model_with_zeros,
                True,
                "proportional_taxable_income_change",
                "proportional_net_of_tax_change",
                None,
            ),
            (
                LOG1P_SPECIFICATION,
                model_with_zeros,
                True,
                "log1p_taxable_income_change",
                "log_net_of_tax_change",
                None,
            ),
        ]
        for (
            label,
            sample,
            include_intercept,
            outcome,
            predictor,
            weight_column,
        ) in specifications:
            fit = fit_log_response(
                sample,
                include_intercept=include_intercept,
                outcome=outcome,
                predictor=predictor,
                weight_column=weight_column,
            )
            rows.append(
                {
                    "model_key": spec.key,
                    "model": spec.display_name,
                    "specification": label,
                    **fit,
                }
            )
    return pd.DataFrame(rows)
