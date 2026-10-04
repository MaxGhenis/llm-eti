"""Analysis functions for PKNF experiment results."""

from typing import Dict, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm


def calculate_bunching_eti(df: pd.DataFrame, notch_location: int = 400) -> float:
    """Calculate ETI using bunching at the notch.

    Uses the Kleven & Waseem (2013) notch estimator, an ETI lower bound. The
    bunching width enters squared because notch responses scale with the square
    root of the elasticity; Saez (2010)'s linear kink formula does not apply.

    Args:
        df: DataFrame with columns 'income' and 'tax_schedule'
        notch_location: Income level where the notch occurs (default: 400 ECU)

    Returns:
        Lower bound estimate of ETI
    """
    # Filter for relevant tax schedules (not used in this simplified calculation)
    # flat_income = df[df["tax_schedule"] == "flat25"]["income"]
    # prog_income = df[df["tax_schedule"] == "progressive"]["income"]

    # Calculate bunching mass
    # Count observations at or just below the notch (380-400 ECU)
    # bunching_window = (380, 400)

    # Calculate bunching mass (not used in this simplified calculation)
    # flat_mass = (
    #     (flat_income >= bunching_window[0]) & (flat_income <= bunching_window[1])
    # ).mean()
    # prog_mass = (
    #     (prog_income >= bunching_window[0]) & (prog_income <= bunching_window[1])
    # ).mean()
    # excess_bunching = prog_mass - flat_mass

    # Parameters for ETI calculation
    # With progressive tax: 25% up to 400, 50% above
    # Dominated region: 400 to 600 (where take-home is lower than at 400)
    delta_z_star = 200  # Size of dominated region
    delta_t = 0.25  # Tax rate increase (from 25% to 50%)
    t = 0.25  # Initial tax rate

    # ETI lower bound (Kleven & Waseem 2013): e >= (Δz*/z*)^2 / (2 * Δt/(1-t))
    z_star = notch_location
    eti_lower_bound = (delta_z_star / z_star) ** 2 / (2 * delta_t / (1 - t))

    return eti_lower_bound


def run_did_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Run difference-in-differences regression for treatment effects.

    Estimates the causal effect of tax reform on labor supply using DiD.

    Args:
        df: DataFrame with experiment results

    Returns:
        DataFrame with regression results
    """
    # Create treatment indicators
    # Treatment: moving from progressive to flat tax (removes notch)
    treated_groups = ["Prog,Flat25", "Prog,Flat50"]
    df["treated"] = df["treatment"].isin(treated_groups).astype(int)

    # Post-reform indicator
    df["post"] = (df["round"] > 8).astype(int)

    # Interaction term
    df["post_treated"] = df["post"] * df["treated"]

    # Normalize labor supply by endowment
    df["labor_utilization"] = df["labor_supply"] / df["labor_endowment"]

    # Run regression
    X = df[["post", "treated", "post_treated"]]
    X = sm.add_constant(X)
    y = df["labor_utilization"]

    model = sm.OLS(y, X).fit()

    # Create results summary
    results_df = pd.DataFrame(
        {
            "Variable": ["Constant", "Post", "Treated", "Post × Treated"],
            "Coefficient": model.params.values,
            "Std Error": model.bse.values,
            "P-value": model.pvalues.values,
        }
    )

    results_df["Significance"] = results_df["P-value"].apply(
        lambda p: "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
    )

    # Add R-squared
    results_df.loc[len(results_df)] = ["R²", model.rsquared, np.nan, np.nan, ""]

    return results_df


def analyze_labor_supply_by_endowment(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze labor supply patterns by endowment level.

    Args:
        df: DataFrame with experiment results

    Returns:
        DataFrame with average labor supply by endowment and tax schedule
    """
    # Group by endowment and tax schedule
    grouped = df.groupby(["labor_endowment", "tax_schedule"])["labor_supply"].agg(
        ["mean", "std", "count"]
    )
    grouped = grouped.reset_index()

    # Add utilization rate
    grouped["utilization_rate"] = grouped["mean"] / grouped["labor_endowment"]

    return grouped


def compare_human_llm_responses(
    llm_df: pd.DataFrame, human_stats: Dict[str, Tuple[float, float]]
) -> pd.DataFrame:
    """Compare LLM responses to human subject data from PKNF (2024).

    Args:
        llm_df: DataFrame with LLM experiment results
        human_stats: Dictionary mapping tax schedules to (mean, std) of fraction with labor < 20

    Returns:
        DataFrame comparing human and LLM responses
    """
    # Calculate fraction with labor supply < 20 for LLMs
    llm_stats = (
        llm_df.groupby("tax_schedule")
        .apply(lambda x: (x["labor_supply"] < 20).mean())
        .to_dict()
    )

    # Create comparison table
    comparison = []
    for schedule, (human_mean, human_range) in human_stats.items():
        llm_fraction = llm_stats.get(schedule, np.nan)
        comparison.append(
            {
                "Tax System": schedule,
                "Human (PKNF 2024)": f"{human_mean:.0%} ({human_range})",
                "LLM": f"{llm_fraction:.0%}",
                "Difference": f"{(llm_fraction - human_mean):.1%}",
            }
        )

    return pd.DataFrame(comparison)
