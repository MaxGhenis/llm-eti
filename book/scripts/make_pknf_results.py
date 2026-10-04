#!/usr/bin/env python3
"""
Generate tables and figures for PKNF (2024) lab experiment replication results.

Loops over all pknf_results_*.csv files in book/data/ and generates:
- Table 5: Fraction choosing labor <= 20 by treatment and pre/post period
- Table 6: DiD regression of labor supply share on post, treated, post*treated
- Income regression table: DiD regression with log income as dependent variable
- Figure 2: Bar chart of mean labor by max_labor endowment, by treatment
- Figure 4: Line plot of mean labor supply share by round and treatment
- Bunching figure: Income histogram by pre/post for Prog,Flat25 treatment
- ETI estimates derived from income regression DiD coefficients

Expected filename format: pknf_results_{model}_{flat_rate}pct_{top_rate}pct.csv
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

# Directories
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"
FIGURES_DIR = SCRIPT_DIR.parent / "figures"
TABLES_DIR = SCRIPT_DIR.parent / "tables"

FIGURES_DIR.mkdir(exist_ok=True)
TABLES_DIR.mkdir(exist_ok=True)

# Matplotlib style (consistent with PKNF_results.py)
plt.rcParams["figure.figsize"] = (8, 5)
plt.rcParams["figure.facecolor"] = "#ffffff"
plt.rcParams["axes.facecolor"] = "#ffffff"
plt.rcParams["axes.edgecolor"] = "#d0d0d0"
plt.rcParams["grid.color"] = "#d0d0d0"
plt.rcParams["grid.linestyle"] = ":"
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.grid"] = True
plt.rcParams["axes.grid.axis"] = "y"

# PKNF paper Table 6, Column 1 (Prog->Flat25, 50pct top rate) for comparison
PKNF_TABLE6_COL1 = [
    "-0.007",
    "(0.006)",
    "-0.052",
    "(0.022)",
    "0.083",
    "(0.009)",
    "0.947",
    "(0.055)",
    "3344",
    "0.035",
]

REG_INDEX = [
    "Post",
    "",
    "Treated",
    "",
    "Post*Treated",
    "",
    "Constant",
    "",
    "N",
    "R-squared",
]

# Labor threshold used in Table 5 (corresponds to income bracket kink at $400 = 20 units * $20/unit)
LABOR_THRESHOLD = 20

# PKNF (2024) paper Table 5 values: fraction choosing labor <= threshold, by treatment and pre/post
PKNF_TABLE5 = {
    "Prog,Prog": {"Pre": 0.78, "Post": 0.81},
    "Prog,Flat25": {"Pre": 0.88, "Post": 0.46},
    "Prog,Flat50": {"Pre": 0.83, "Post": 0.54},
    "Flat25,Prog": {"Pre": 0.53, "Post": 0.79},
    "Flat50,Prog": {"Pre": 0.54, "Post": 0.79},
}

# Display names and column order for the cross-model comparison table
MODEL_DISPLAY_NAMES = {
    "gpt-4o": "GPT-4o",
    "gpt-4o-mini": "GPT-4o-mini",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "deepseek-ai_DeepSeek-V3": "DeepSeek V3",
    "google_gemma-4-26B-A4B-it": "Gemma 4",
}
MODEL_COLUMN_ORDER = [
    "GPT-4o",
    "GPT-4o-mini",
    "Claude Haiku 4.5",
    "DeepSeek V3",
    "Gemma 4",
]

# Bar colors for cross-model figures: PKNF gets gray, each LLM gets a distinct color
BAR_COLORS = {
    "PKNF": "#555555",
    "GPT-4o": "#4472C4",
    "GPT-4o-mini": "#70B0E0",
    "Claude Haiku 4.5": "#ED7D31",
    "DeepSeek V3": "#70AD47",
    "Gemma 4": "#9B59B6",
}

# Preferred legend order matching PKNF Figure 4
TREATMENT_ORDER = [
    "Prog,Prog",
    "Prog,Flat25",
    "Prog,Flat40",
    "Prog,Flat50",
    "Flat25,Prog",
    "Flat40,Prog",
    "Flat50,Prog",
]

# Treatment colors matched to PKNF Figure 4
TREATMENT_COLORS = {
    "Prog,Prog": "#4472C4",  # blue
    "Prog,Flat25": "#ED7D31",  # orange
    "Prog,Flat40": "#BF9000",  # gold (40pct analog of Flat50)
    "Prog,Flat50": "#BF9000",  # gold/tan
    "Flat25,Prog": "#9BBB59",  # yellow-green
    "Flat40,Prog": "#70AD47",  # green (40pct analog of Flat50)
    "Flat50,Prog": "#70AD47",  # green
}


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean PKNF simulation data for analysis.

    Maps new CSV column names to the analysis variables used throughout:
      labor_supply    -> labor (chosen labor units)
      labor_endowment -> max_labor (maximum labor units available)
      post_reform     -> Post (0/1 indicator)
    """
    df = df.copy()
    df["Post"] = df["post_reform"].astype(int)
    df["labor"] = df["labor_supply"]
    df["max_labor"] = df["labor_endowment"]
    df = df.dropna(subset=["income", "labor"])
    df = df[df["labor"] >= 1]
    df["lab_supply"] = df["labor"] / df["max_labor"]
    df = df[df["lab_supply"] <= 1]
    df["labor_20"] = (df["labor"] <= LABOR_THRESHOLD).astype(int)
    df["log_income"] = np.log(df["income"])
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["log_income"])
    return df


def parse_filename(csv_path: Path) -> tuple[str, float, float]:
    """
    Parse model name, flat rate, and top rate from filename.

    Expected format: pknf_results_{model}_{flat_rate}pct_{top_rate}pct.csv
    Uses rsplit to handle model names that contain underscores (e.g., google_gemma-...).
    """
    stem = csv_path.stem  # e.g., "pknf_results_gpt-4o-mini_25pct_50pct"
    rest = stem[len("pknf_results_") :]  # e.g., "gpt-4o-mini_25pct_50pct"
    parts = rest.rsplit("_", 2)  # ["gpt-4o-mini", "25pct", "50pct"]
    model = parts[0]
    flat_rate = float(parts[1].replace("pct", "")) / 100
    top_rate = float(parts[2].replace("pct", "")) / 100
    return model, flat_rate, top_rate


def get_eti_divisor(treatment: str, top_rate: float) -> float | None:
    """
    Compute the ETI divisor (change in net-of-tax rate) for a treatment.

    For Prog->FlatX:  divisor =  top_rate - flat_rate  (positive if flat < top)
    For FlatX->Prog:  divisor =  flat_rate - top_rate  (negative if flat < top)
    Returns None for the control (Prog,Prog) or when divisor = 0.
    """
    pre, post = [s.strip() for s in treatment.split(",", 1)]
    if pre == post:
        return None
    if post.startswith("Flat"):
        flat_rate = float(post[4:]) / 100
        divisor = top_rate - flat_rate
    elif pre.startswith("Flat"):
        flat_rate = float(pre[4:]) / 100
        divisor = flat_rate - top_rate
    else:
        return None
    return divisor if divisor != 0.0 else None


def make_table5(df: pd.DataFrame, out_prefix: str, treatments: list[str]) -> None:
    """Table 5: fraction choosing labor <= threshold by treatment and pre/post period."""
    table5 = (
        df[["treatment", "Post", "labor_20"]]
        .groupby(["treatment", "Post"])
        .mean()
        .reset_index()
    )
    table5 = table5.pivot(
        index="treatment", columns="Post", values="labor_20"
    ).reset_index()
    table5 = table5.rename(
        columns={"treatment": "Treatment", 0: "Pre-Reform", 1: "Post-Reform"}
    )

    # Preserve treatment order and filter to what's in the data
    ordered = [t for t in treatments if t in table5["Treatment"].values]
    table5 = table5.set_index("Treatment").loc[ordered].reset_index()

    table5.to_markdown(
        TABLES_DIR / f"{out_prefix}_table5.md", floatfmt=".2f", index=False
    )
    table5.to_latex(
        TABLES_DIR / f"{out_prefix}_table5.tex", float_format="%.2f", index=False
    )
    print(f"  Saved Table 5 -> {out_prefix}_table5.{{md,tex}}")


def make_figure2(df: pd.DataFrame, out_prefix: str, treatments: list[str]) -> None:
    """
    Figure 2: Grouped bar chart of mean labor by max_labor endowment, pre vs post.
    One panel per non-control treatment.
    """
    df_bar = (
        df[["treatment", "Post", "labor", "max_labor"]]
        .groupby(["treatment", "Post", "max_labor"])
        .mean()
        .reset_index()
    )
    max_labor_values = sorted(df_bar["max_labor"].unique())
    post_values = sorted(df_bar["Post"].unique())
    colors = ["#f8953a", "#4c72b0"]
    bar_width = 0.35
    gap = 0.05

    panel = 0
    for treat in [t for t in treatments if t != "Prog,Prog"]:
        panel += 1
        fig, ax = plt.subplots()
        for j, max_lab in enumerate(max_labor_values):
            group_center = j
            for k, post in enumerate(post_values):
                pos = group_center - (bar_width + gap) / 2 + k * (bar_width + gap)
                df_cell = df_bar[
                    (df_bar["max_labor"] == max_lab)
                    & (df_bar["Post"] == post)
                    & (df_bar["treatment"] == treat)
                ]
                if not df_cell.empty:
                    label = ("Post" if post == 1 else "Pre") if j == 0 else ""
                    ax.bar(
                        pos,
                        df_cell["labor"].values[0],
                        width=bar_width,
                        color=colors[k],
                        alpha=0.9 if post == 0 else 1.0,
                        label=label,
                        edgecolor="black",
                        linewidth=0.5,
                    )
        mean_val = df_bar[df_bar["treatment"] == treat]["labor"].mean()
        max_val = df_bar[df_bar["treatment"] == treat]["labor"].max()
        ax.axhline(
            y=mean_val, color="#808080", linestyle="--", linewidth=1.5, alpha=0.8
        )
        ax.set_xlabel("Maximum Labor")
        ax.set_ylabel("Labor Supply, in Units")
        ax.set_title(treat)
        ax.set_ylim(0, max_val + 0.5)
        ax.set_xticks(np.arange(len(max_labor_values)))
        ax.set_xticklabels(max_labor_values)
        ax.legend()
        fig.savefig(
            FIGURES_DIR / f"{out_prefix}_fig2_{panel}.png", bbox_inches="tight", dpi=300
        )
        plt.close(fig)
    print(f"  Saved Figure 2 ({panel} panels) -> {out_prefix}_fig2_*.png")


def make_figure4(df: pd.DataFrame, out_prefix: str, treatments: list[str]) -> None:
    """Figure 4: Line plot of mean labor supply share by round and treatment."""
    df_line = (
        df[["treatment", "lab_supply", "round"]]
        .groupby(["treatment", "round"])
        .mean()
        .reset_index()
    )
    # Place vertical dashed line at the pre/post boundary
    max_pre_round = df[df["Post"] == 0]["round"].max()
    split_point = max_pre_round + 0.5

    # Sort treatments into PKNF legend order, preserving only those present in data
    ordered = [t for t in TREATMENT_ORDER if t in treatments]
    ordered += [t for t in treatments if t not in TREATMENT_ORDER]

    fig, ax = plt.subplots()
    for treat in ordered:
        df_treat = df_line[df_line["treatment"] == treat]
        ax.plot(
            df_treat["round"],
            df_treat["lab_supply"],
            marker="o",
            label=treat,
            color=TREATMENT_COLORS.get(treat),
            alpha=0.9,
        )
    ax.set_ylim(0.7, 1.02)
    ax.axvline(x=split_point, color="gray", linestyle="--", linewidth=1.5, alpha=0.8)
    ax.set_xlabel("Period")
    ax.set_ylabel("Labor Supply (%)")
    ax.legend()
    fig.savefig(FIGURES_DIR / f"{out_prefix}_fig4.png", bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"  Saved Figure 4 -> {out_prefix}_fig4.png")


def calculate_bunching_eti(
    df: pd.DataFrame,
    top_rate: float,
    notch_income: float = 400.0,
    low_rate: float = 0.25,
    wage_rate: float = 20.0,
    counterfactual_window: float | None = None,
) -> dict:
    """
    Estimate ETI using a bunching estimator at the all-or-nothing income notch.

    The progressive schedule taxes ALL income at the lower rate up to z* and at
    the higher rate above z*, creating a dominated region [z*, z* + Δz*] where
    after-tax income is strictly lower than at z*. Rational agents should bunch
    at z* rather than earn inside the dominated region.

    Eligible observations are restricted to rounds where the agent's labor
    endowment strictly exceeds notch_labor (= notch_income / wage_rate), so
    the agent has a genuine choice between bunching at z* and earning above it.

    Robust to the 50pct top-rate case where the dominated region's upper bound
    (z* + Δz* = 600) equals the maximum achievable income — in that case the
    function skips any analysis that requires observing income above the
    dominated region.

    ETI lower bound formula (Kleven & Waseem 2013):
        e_min = (Δz* / z*) / log[(1 - low_rate) / (1 - top_rate)]

    Data-driven ETI point estimate:
        Infer implied income adjustment Δz̃ from excess bunching at z*
        relative to the counterfactual (flat schedule) density, capped at Δz*.
        e = (Δz̃ / z*) / log[(1 - low_rate) / (1 - top_rate)]

        The counterfactual density at z* is estimated in one of two ways:
        - counterfactual_window=None : use the fraction of flat observations at
          exactly z* (may be zero when no subjects naturally choose z* under
          the flat schedule, yielding eti_estimate=nan).
        - counterfactual_window=W   : use the average fraction per income bin
          in the flat schedule over [z*-W, z*+W].  W is in income units; the
          number of bins in the window is 2W/wage_rate + 1.  This is more
          robust when the point density at z* is zero.

    Parameters
    ----------
    df                    : cleaned DataFrame with columns income, tax_schedule, max_labor
    top_rate              : top marginal tax rate in the progressive schedule (e.g. 0.40 or 0.50)
    notch_income          : income at the notch point (default 400 ECU)
    low_rate              : lower bracket tax rate in the progressive schedule (default 0.25)
    wage_rate             : ECU per labor unit, used to convert labor endowment to max income
    counterfactual_window : half-width in income units for window density estimation (default None)

    Returns
    -------
    dict with estimation results and supporting statistics
    """
    notch_labor = notch_income / wage_rate  # labor units at the notch (20 units)

    # --- Structural parameters ---
    # Dominated region boundary: (1 - top_rate)(z* + Δz*) = (1 - low_rate)z*
    delta_z_star = notch_income * (top_rate - low_rate) / (1 - top_rate)
    dominated_top = notch_income + delta_z_star

    # Can we observe income strictly above the dominated region?
    # Use a one-unit wage buffer for floating-point safety.
    max_observable = df["max_labor"].max() * wage_rate
    can_observe_above = max_observable > dominated_top + wage_rate

    # --- Eligible observations ---
    # Only rounds where the agent's endowment strictly exceeds notch_labor,
    # so bunching is a genuine behavioral choice rather than a ceiling effect.
    df_elig = df[df["max_labor"] > notch_labor].copy()

    prog_inc = df_elig[df_elig["tax_schedule"] == "progressive"]["income"]
    flat_inc = df_elig[df_elig["tax_schedule"] != "progressive"]["income"]
    n_prog, n_flat = len(prog_inc), len(flat_inc)

    # --- Bunching mass at z* ---
    prog_at_z = (prog_inc == notch_income).mean() if n_prog > 0 else np.nan
    flat_at_z = (flat_inc == notch_income).mean() if n_flat > 0 else np.nan
    excess_bunching = (prog_at_z - flat_at_z) if (n_prog > 0 and n_flat > 0) else np.nan

    # --- Mass inside the dominated region ---
    # Rational agents should never be here; any mass indicates irrational / noisy behavior.
    prog_in_dom = (
        ((prog_inc > notch_income) & (prog_inc < dominated_top)).mean()
        if n_prog > 0
        else np.nan
    )

    # --- Mass above the dominated region (only when observable) ---
    if can_observe_above:
        prog_above = (prog_inc >= dominated_top).mean() if n_prog > 0 else np.nan
        flat_above = (flat_inc >= dominated_top).mean() if n_flat > 0 else np.nan
        missing_mass = (flat_above - prog_above) if n_flat > 0 else np.nan
    else:
        prog_above = flat_above = missing_mass = np.nan

    # --- ETI lower bound (structural) ---
    # Kleven & Waseem (2013, QJE) equation 12:
    # e = (Δz*/z*)² / ((τ_H - τ_L) / (1 - τ_H))
    kw_denominator = (top_rate - low_rate) / (1 - top_rate)
    eti_lower_bound = (delta_z_star / notch_income) ** 2 / kw_denominator

    # --- Counterfactual density at z* from flat schedule ---
    # Point estimate: fraction at exactly z* (may be zero).
    # Window estimate: average fraction per income bin in [z*-W, z*+W].
    if counterfactual_window is not None and n_flat > 0:
        in_window = (flat_inc >= notch_income - counterfactual_window) & (
            flat_inc <= notch_income + counterfactual_window
        )
        n_bins_in_window = 2 * counterfactual_window / wage_rate + 1
        flat_counterfactual_density = in_window.mean() / n_bins_in_window
    else:
        flat_counterfactual_density = flat_at_z  # fraction at exactly z*

    # --- Data-driven ETI point estimate ---
    # Δz̃ = (excess_bunching / flat_density_per_bin) × bin_width, capped at Δz*.
    # Uses whichever counterfactual density was selected above.
    if (
        flat_counterfactual_density > 0
        and not np.isnan(excess_bunching)
        and excess_bunching > 0
    ):
        implied_delta_z = min(
            (excess_bunching / flat_counterfactual_density) * wage_rate, delta_z_star
        )
        eti_estimate = (implied_delta_z / notch_income) ** 2 / kw_denominator
    else:
        eti_estimate = np.nan

    return {
        "notch_income": notch_income,
        "delta_z_star": delta_z_star,
        "dominated_top": dominated_top,
        "can_observe_above_dominated": can_observe_above,
        "counterfactual_window": counterfactual_window,
        "n_prog": n_prog,
        "n_flat": n_flat,
        "prog_frac_at_notch": prog_at_z,
        "flat_frac_at_notch": flat_at_z,
        "flat_counterfactual_density": flat_counterfactual_density,
        "excess_bunching": excess_bunching,
        "prog_frac_in_dominated": prog_in_dom,
        "prog_frac_above_dominated": prog_above,
        "flat_frac_above_dominated": flat_above,
        "missing_mass": missing_mass,
        "eti_lower_bound": eti_lower_bound,
        "eti_estimate": eti_estimate,
    }


def bootstrap_bunching_eti(
    df: pd.DataFrame,
    top_rate: float,
    notch_income: float = 400.0,
    low_rate: float = 0.25,
    wage_rate: float = 20.0,
    counterfactual_window: float | None = 40.0,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> dict:
    """
    Bootstrap standard errors and 95% CIs for the data-driven bunching ETI estimate.

    Resamples progressive and flat eligible observations independently with
    replacement, recomputes the ETI estimate for each draw, and summarises
    the resulting distribution.  Fully vectorised — no Python loop over
    bootstrap iterations.

    The structural lower bound (eti_lower_bound) is a fixed function of the
    tax parameters and carries no sampling uncertainty, so no SE is returned
    for it.

    Parameters
    ----------
    n_bootstrap : number of bootstrap draws (default 1000)
    seed        : random seed for reproducibility
    All other parameters match calculate_bunching_eti.

    Returns
    -------
    dict with eti_estimate_se, eti_estimate_ci_low, eti_estimate_ci_high,
    n_bootstrap, and n_valid_bootstrap (draws that produced a non-nan estimate).
    """
    notch_labor = notch_income / wage_rate
    delta_z_star = notch_income * (top_rate - low_rate) / (1 - top_rate)
    kw_denominator = (top_rate - low_rate) / (1 - top_rate)

    df_elig = df[df["max_labor"] > notch_labor]
    prog_inc = df_elig[df_elig["tax_schedule"] == "progressive"]["income"].to_numpy()
    flat_inc = df_elig[df_elig["tax_schedule"] != "progressive"]["income"].to_numpy()

    nan_result = {
        "eti_estimate_se": np.nan,
        "eti_estimate_ci_low": np.nan,
        "eti_estimate_ci_high": np.nan,
        "n_bootstrap": n_bootstrap,
        "n_valid_bootstrap": 0,
    }
    if len(prog_inc) == 0 or len(flat_inc) == 0:
        return nan_result

    rng = np.random.default_rng(seed)

    # Draw all bootstrap samples at once: shape (n_bootstrap, n_obs)
    prog_boot = rng.choice(prog_inc, size=(n_bootstrap, len(prog_inc)), replace=True)
    flat_boot = rng.choice(flat_inc, size=(n_bootstrap, len(flat_inc)), replace=True)

    # Bunching fraction at z* for each draw
    prog_at_z = (prog_boot == notch_income).mean(axis=1)
    flat_at_z = (flat_boot == notch_income).mean(axis=1)
    excess = prog_at_z - flat_at_z

    # Counterfactual density
    if counterfactual_window is not None:
        in_win = (flat_boot >= notch_income - counterfactual_window) & (
            flat_boot <= notch_income + counterfactual_window
        )
        n_bins = 2 * counterfactual_window / wage_rate + 1
        flat_density = in_win.mean(axis=1) / n_bins
    else:
        flat_density = flat_at_z

    # ETI estimate for each draw (nan when excess ≤ 0 or density = 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        implied_dz = np.where(
            (flat_density > 0) & (excess > 0),
            np.minimum((excess / flat_density) * wage_rate, delta_z_star),
            np.nan,
        )
    eti_boot = (implied_dz / notch_income) ** 2 / kw_denominator

    valid = eti_boot[~np.isnan(eti_boot)]
    if len(valid) == 0:
        return nan_result

    return {
        "eti_estimate_se": float(np.std(valid, ddof=1)),
        "eti_estimate_ci_low": float(np.percentile(valid, 2.5)),
        "eti_estimate_ci_high": float(np.percentile(valid, 97.5)),
        "n_bootstrap": n_bootstrap,
        "n_valid_bootstrap": int(len(valid)),
    }


def make_bunching_eti_table(
    model_dfs: list[tuple[str, pd.DataFrame]],
    flat_rate: float,
    top_rate: float,
    counterfactual_window: float | None = 40.0,
    n_bootstrap: int = 1000,
) -> None:
    """
    Cross-model table of bunching ETI estimates for a given rate combination,
    including bootstrap standard errors and 95% CIs for the data-driven estimate.

    Rows = LLM models (in standard column order).
    Columns = key bunching statistics, ETI estimates, and bootstrap SEs/CIs.

    Parameters
    ----------
    counterfactual_window : half-width in income units for the flat-schedule
        density window used in the data-driven ETI estimate.  Default 40 ECU
        (±2 labor units around z*).  Pass None to use only the point density
        at exactly z*.
    n_bootstrap : number of bootstrap draws for standard errors (default 1000).
    """
    flat_str = f"{int(flat_rate * 100)}pct"
    top_str = f"{int(top_rate * 100)}pct"
    out_prefix = f"pknf_all_models_{flat_str}_{top_str}"

    model_lookup = {
        MODEL_DISPLAY_NAMES.get(label, label): df for label, df in model_dfs
    }
    rows = {}
    for display_name in MODEL_COLUMN_ORDER:
        if display_name not in model_lookup:
            continue
        df = model_lookup[display_name]
        point = calculate_bunching_eti(
            df,
            top_rate,
            low_rate=flat_rate,
            counterfactual_window=counterfactual_window,
        )
        boot = bootstrap_bunching_eti(
            df,
            top_rate,
            low_rate=flat_rate,
            counterfactual_window=counterfactual_window,
            n_bootstrap=n_bootstrap,
        )
        rows[display_name] = {**point, **boot}

    if not rows:
        return

    table = pd.DataFrame(rows).T
    table.index.name = "Model"
    key_cols = [
        "n_prog",
        "n_flat",
        "prog_frac_at_notch",
        "flat_counterfactual_density",
        "excess_bunching",
        "prog_frac_in_dominated",
        "missing_mass",
        "eti_lower_bound",
        "eti_estimate",
        "eti_estimate_se",
        "eti_estimate_ci_low",
        "eti_estimate_ci_high",
    ]
    # Drop columns that are all NaN (e.g. missing_mass for 50pct case)
    key_cols = [c for c in key_cols if not table[c].isna().all()]

    table = table[key_cols]
    table.to_markdown(TABLES_DIR / f"{out_prefix}_bunching_eti.md", floatfmt=".3f")
    table.to_latex(TABLES_DIR / f"{out_prefix}_bunching_eti.tex", float_format="%.3f")
    print(f"  Saved bunching ETI table -> {out_prefix}_bunching_eti.{{md,tex}}")


def make_eti_summary_table(
    model_dfs: list[tuple[str, pd.DataFrame]],
    flat_rate: float,
    top_rate: float,
    counterfactual_window: float | None = 40.0,
    n_bootstrap: int = 1000,
) -> None:
    """
    Formatted ETI summary table with two columns and 95% CIs below point estimates.

    Columns
    -------
    Structural LB    : lower bound implied by the dominated region geometry
                       (fixed by tax parameters, no sampling uncertainty).
    Data-Driven ETI  : estimate inferred from excess bunching relative to the
                       flat-schedule counterfactual density; 95% bootstrap CI
                       shown in brackets on the row below each model.

    Parameters
    ----------
    model_dfs             : list of (model_label, cleaned_df) pairs
    flat_rate             : flat marginal tax rate (e.g. 0.25)
    top_rate              : top progressive marginal tax rate (0.40 or 0.50)
    counterfactual_window : half-width in income units for window density estimate
                           (default 40 ECU = ±2 labor units around z*)
    n_bootstrap           : bootstrap draws used for CI computation (default 1000)
    """
    flat_str = f"{int(flat_rate * 100)}pct"
    top_str = f"{int(top_rate * 100)}pct"
    out_prefix = f"pknf_all_models_{flat_str}_{top_str}"

    model_lookup = {
        MODEL_DISPLAY_NAMES.get(label, label): df for label, df in model_dfs
    }

    # Gather point estimates and bootstrap CIs for each model
    results = {}
    for display_name in MODEL_COLUMN_ORDER:
        if display_name not in model_lookup:
            continue
        df = model_lookup[display_name]
        point = calculate_bunching_eti(
            df,
            top_rate,
            low_rate=flat_rate,
            counterfactual_window=counterfactual_window,
        )
        boot = bootstrap_bunching_eti(
            df,
            top_rate,
            low_rate=flat_rate,
            counterfactual_window=counterfactual_window,
            n_bootstrap=n_bootstrap,
        )
        results[display_name] = {**point, **boot}

    if not results:
        return

    # Build alternating point-estimate / CI rows (economics table convention)
    col_lb = "Structural LB"
    col_dd = "Data-Driven ETI"
    model_col, lb_col, dd_col = [], [], []

    for model, r in results.items():
        lb = r["eti_lower_bound"]
        est = r["eti_estimate"]
        ci_low = r["eti_estimate_ci_low"]
        ci_high = r["eti_estimate_ci_high"]

        # Point estimate row
        model_col.append(model)
        lb_col.append(f"{lb:.3f}")
        dd_col.append(f"{est:.3f}" if not np.isnan(est) else "—")

        # CI row (blank model name, dashes for structural since it has no CI)
        model_col.append("")
        lb_col.append("")
        dd_col.append(f"[{ci_low:.3f}, {ci_high:.3f}]" if not np.isnan(ci_low) else "")

    table = pd.DataFrame(
        {"Model": model_col, col_lb: lb_col, col_dd: dd_col}
    ).set_index("Model")

    table.to_markdown(TABLES_DIR / f"{out_prefix}_eti_summary.md", index=True)
    table.to_latex(TABLES_DIR / f"{out_prefix}_eti_summary.tex", index=True)
    print(f"  Saved ETI summary table -> {out_prefix}_eti_summary.{{md,tex}}")


def _run_did_regression(df: pd.DataFrame, treat: str, dep_var: str):
    """Run DiD regression for one treatment vs Prog,Prog control."""
    df_reg = df[(df["treatment"] == treat) | (df["treatment"] == "Prog,Prog")].copy()
    df_reg["treated"] = (df_reg["treatment"] == treat).astype(int)
    df_reg["post_treat"] = df_reg["Post"] * df_reg["treated"]
    return smf.ols(f"{dep_var} ~ Post + treated + post_treat", data=df_reg).fit()


def _format_reg_col(res) -> list[str]:
    """Format regression results into alternating estimate/SE rows."""
    return [
        f"{res.params['Post']:.3f}",
        f"({res.bse['Post']:.3f})",
        f"{res.params['treated']:.3f}",
        f"({res.bse['treated']:.3f})",
        f"{res.params['post_treat']:.3f}",
        f"({res.bse['post_treat']:.3f})",
        f"{res.params['Intercept']:.3f}",
        f"({res.bse['Intercept']:.3f})",
        f"{res.nobs:.0f}",
        f"{res.rsquared:.3f}",
    ]


def make_regression_tables(
    df: pd.DataFrame, out_prefix: str, treatments: list[str], top_rate: float
) -> None:
    """
    Table 6: DiD regressions for labor supply share and log income.
    Also saves:
      - comparison table vs PKNF paper (50pct, Prog,Flat25 only)
      - ETI estimates derived from post_treat coefficient / change in net-of-tax rate
    """
    treated = [t for t in treatments if t != "Prog,Prog"]
    lab_results = {}
    inc_results = {}

    for treat in treated:
        lab_results[treat] = _format_reg_col(
            _run_did_regression(df, treat, "lab_supply")
        )
        inc_results[treat] = _format_reg_col(
            _run_did_regression(df, treat, "log_income")
        )

    # Table 6 (labor supply share)
    reg_df = pd.DataFrame(lab_results, index=REG_INDEX)
    reg_df.to_markdown(TABLES_DIR / f"{out_prefix}_table6.md", index=True)
    reg_df.to_latex(TABLES_DIR / f"{out_prefix}_table6.tex", index=True)
    print(f"  Saved Table 6 -> {out_prefix}_table6.{{md,tex}}")

    # Comparison with PKNF paper (only for 50pct top rate, Prog,Flat25 treatment)
    if "Prog,Flat25" in lab_results and abs(top_rate - 0.50) < 0.01:
        compare_df = pd.DataFrame(
            {"PKNF": PKNF_TABLE6_COL1, "LLM": reg_df["Prog,Flat25"]},
            index=REG_INDEX,
        )
        compare_df.to_markdown(
            TABLES_DIR / f"{out_prefix}_table6_compare.md", index=True
        )
        compare_df.to_latex(TABLES_DIR / f"{out_prefix}_table6_compare.tex", index=True)
        print(f"  Saved Table 6 comparison -> {out_prefix}_table6_compare.{{md,tex}}")

    # Income regression table
    inc_df = pd.DataFrame(inc_results, index=REG_INDEX)
    inc_df.to_markdown(TABLES_DIR / f"{out_prefix}_income_reg.md", index=True)
    inc_df.to_latex(TABLES_DIR / f"{out_prefix}_income_reg.tex", index=True)
    print(f"  Saved income regression table -> {out_prefix}_income_reg.{{md,tex}}")

    # ETI estimates: post_treat coef / change in net-of-tax rate
    eti = {}
    for treat in treated:
        divisor = get_eti_divisor(treat, top_rate)
        if divisor is not None:
            post_treat_coef = float(
                inc_results[treat][4]
            )  # index 4 = Post*Treated estimate
            eti[treat] = post_treat_coef / divisor

    if eti:
        eti_df = pd.Series(eti, name="ETI").to_frame()
        eti_df.to_markdown(TABLES_DIR / f"{out_prefix}_eti.md")
        eti_df.to_latex(TABLES_DIR / f"{out_prefix}_eti.tex")
        print(f"  ETI estimates: {eti}")
        print(f"  Saved ETI table -> {out_prefix}_eti.{{md,tex}}")


def make_bunching_figure(df: pd.DataFrame, out_prefix: str) -> None:
    """Bunching figure: income histogram pre vs post for the Prog,Flat25 treatment."""
    if "Prog,Flat25" not in df["treatment"].values:
        return
    df_treat = df[df["treatment"] == "Prog,Flat25"]
    fig, ax = plt.subplots()
    ax.hist(
        df_treat[df_treat["Post"] == 0]["income"],
        bins=20,
        alpha=0.5,
        density=True,
        label="Prog (Pre)",
        color="#f8953a",
    )
    ax.hist(
        df_treat[df_treat["Post"] == 1]["income"],
        bins=20,
        alpha=0.5,
        density=True,
        label="Flat25 (Post)",
        color="#4c72b0",
    )
    ax.set_xlabel("Pre-tax Income")
    ax.set_ylabel("Density")
    ax.legend()
    fig.savefig(
        FIGURES_DIR / f"{out_prefix}_bunching.png", bbox_inches="tight", dpi=300
    )
    plt.close(fig)
    print(f"  Saved bunching figure -> {out_prefix}_bunching.png")


def make_cross_model_table5(
    model_dfs: list[tuple[str, pd.DataFrame]],
    flat_rate: float,
    top_rate: float,
) -> None:
    """
    Cross-model Table 5 comparison: fraction choosing labor <= threshold,
    pre and post reform, for each treatment and LLM model.

    For the 50pct top-rate case the first two columns are the PKNF paper values.
    Column pairs are ordered: PKNF | GPT-4o | GPT-4o-mini | Claude Haiku 4.5 | DeepSeek V3 | Gemma 4
    """
    flat_str = f"{int(flat_rate * 100)}pct"
    top_str = f"{int(top_rate * 100)}pct"
    out_prefix = f"pknf_all_models_{flat_str}_{top_str}"

    # Determine which treatments appear in the data
    all_treatments: set[str] = set()
    for _, df in model_dfs:
        all_treatments.update(df["treatment"].unique())
    ordered_treatments = [t for t in TREATMENT_ORDER if t in all_treatments]
    ordered_treatments += sorted(t for t in all_treatments if t not in TREATMENT_ORDER)

    # Build a dict of {column_name: Series(treatment -> value)} for each Pre/Post pair
    col_data: dict[str, dict[str, float]] = {}

    # PKNF paper columns (50pct only)
    if abs(top_rate - 0.50) < 0.01:
        col_data["PKNF Pre"] = {
            t: PKNF_TABLE5.get(t, {}).get("Pre", float("nan"))
            for t in ordered_treatments
        }
        col_data["PKNF Post"] = {
            t: PKNF_TABLE5.get(t, {}).get("Post", float("nan"))
            for t in ordered_treatments
        }

    # LLM model columns in preferred order
    model_lookup = {
        MODEL_DISPLAY_NAMES.get(label, label): df for label, df in model_dfs
    }
    for display_name in MODEL_COLUMN_ORDER:
        if display_name not in model_lookup:
            continue
        df = model_lookup[display_name]
        means = df.groupby(["treatment", "Post"])["labor_20"].mean()
        col_data[f"{display_name} Pre"] = {
            t: means.get((t, 0), float("nan")) for t in ordered_treatments
        }
        col_data[f"{display_name} Post"] = {
            t: means.get((t, 1), float("nan")) for t in ordered_treatments
        }

    table = pd.DataFrame(col_data, index=ordered_treatments)
    table.index.name = "Treatment"
    table.to_markdown(TABLES_DIR / f"{out_prefix}_table5_compare.md", floatfmt=".2f")
    table.to_latex(TABLES_DIR / f"{out_prefix}_table5_compare.tex", float_format="%.2f")
    print(f"  Saved cross-model Table 5 -> {out_prefix}_table5_compare.{{md,tex}}")


def make_cross_model_bar_figure(
    model_dfs: list[tuple[str, pd.DataFrame]],
    flat_rate: float,
    top_rate: float,
) -> None:
    """
    Two-panel grouped bar chart of Table 5 results across models.

    Left panel: Pre-reform fractions. Right panel: Post-reform fractions.
    Groups on x-axis: tax treatments (in PKNF order).
    Bars within each group: PKNF paper result (50pct only) then each LLM in
    the same order used in the cross-model tables.
    """
    flat_str = f"{int(flat_rate * 100)}pct"
    top_str = f"{int(top_rate * 100)}pct"
    out_prefix = f"pknf_all_models_{flat_str}_{top_str}"

    # Determine which treatments appear in the data, in PKNF legend order
    all_treatments: set[str] = set()
    for _, df in model_dfs:
        all_treatments.update(df["treatment"].unique())
    ordered_treatments = [t for t in TREATMENT_ORDER if t in all_treatments]
    ordered_treatments += sorted(t for t in all_treatments if t not in TREATMENT_ORDER)

    # Build {source_label: {treatment: pre_value}} and post equivalent
    sources_pre: dict[str, dict[str, float]] = {}
    sources_post: dict[str, dict[str, float]] = {}

    # PKNF paper values (50pct top rate only)
    if abs(top_rate - 0.50) < 0.01:
        sources_pre["PKNF"] = {
            t: PKNF_TABLE5.get(t, {}).get("Pre", float("nan"))
            for t in ordered_treatments
        }
        sources_post["PKNF"] = {
            t: PKNF_TABLE5.get(t, {}).get("Post", float("nan"))
            for t in ordered_treatments
        }

    # LLM models in the table column order
    model_lookup = {
        MODEL_DISPLAY_NAMES.get(label, label): df for label, df in model_dfs
    }
    for display_name in MODEL_COLUMN_ORDER:
        if display_name not in model_lookup:
            continue
        means = (
            model_lookup[display_name].groupby(["treatment", "Post"])["labor_20"].mean()
        )
        sources_pre[display_name] = {
            t: means.get((t, 0), float("nan")) for t in ordered_treatments
        }
        sources_post[display_name] = {
            t: means.get((t, 1), float("nan")) for t in ordered_treatments
        }

    all_sources = list(
        sources_pre.keys()
    )  # PKNF first (if present), then LLMs in order
    n_groups = len(ordered_treatments)
    n_bars = len(all_sources)
    bar_width = 0.8 / n_bars
    x = np.arange(n_groups)

    for data, period in [(sources_pre, "pre"), (sources_post, "post")]:
        fig, ax = plt.subplots(figsize=(9, 5))
        for i, source in enumerate(all_sources):
            offsets = x + bar_width * (i - (n_bars - 1) / 2)
            vals = [data[source].get(t, float("nan")) for t in ordered_treatments]
            ax.bar(
                offsets,
                vals,
                width=bar_width,
                label=source,
                color=BAR_COLORS.get(source, f"C{i}"),
                edgecolor="white",
                linewidth=0.5,
            )
        ax.set_xticks(x)
        ax.set_xticklabels(ordered_treatments, rotation=20, ha="right")
        ax.set_ylim(0, 1.1)
        ax.set_ylabel(f"Fraction with Labor Supply \u2264 {LABOR_THRESHOLD}")
        ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", borderaxespad=0)
        fig.tight_layout()
        fname = f"{out_prefix}_table5_bar_{period}.png"
        fig.savefig(FIGURES_DIR / fname, bbox_inches="tight", dpi=300)
        plt.close(fig)
        print(f"  Saved cross-model bar figure -> {fname}")


def make_cross_model_table6(
    model_dfs: list[tuple[str, pd.DataFrame]],
    flat_rate: float,
    top_rate: float,
    treatment: str = "Prog,Flat25",
) -> None:
    """
    Cross-model Table 6 comparison: DiD regression results (lab_supply) for one
    treatment vs Prog,Prog control, with one column per LLM model.

    For the 50pct top-rate case the first column is the PKNF paper result,
    allowing direct comparison across models and against the human-subject baseline.

    Parameters
    ----------
    model_dfs:  list of (model_label, cleaned_df) pairs for this rate combination
    flat_rate:  flat marginal tax rate (e.g. 0.25)
    top_rate:   top progressive marginal tax rate (e.g. 0.50)
    treatment:  treatment arm to use as the focal comparison column
    """
    flat_str = f"{int(flat_rate * 100)}pct"
    top_str = f"{int(top_rate * 100)}pct"
    out_prefix = f"pknf_all_models_{flat_str}_{top_str}"

    result_cols = {}

    # Include PKNF paper column when comparing the canonical 50pct / Prog,Flat25 case
    if abs(top_rate - 0.50) < 0.01 and treatment == "Prog,Flat25":
        result_cols["PKNF"] = PKNF_TABLE6_COL1

    for model_label, df in model_dfs:
        if treatment not in df["treatment"].values:
            continue
        display_name = MODEL_DISPLAY_NAMES.get(model_label, model_label)
        res = _run_did_regression(df, treatment, "lab_supply")
        result_cols[display_name] = _format_reg_col(res)

    if not result_cols:
        print(
            f"  Skipping cross-model table for {flat_str}/{top_str}: no data for {treatment}"
        )
        return

    # Order columns: PKNF first (if present), then models in preferred order
    ordered_cols = (
        (["PKNF"] if "PKNF" in result_cols else [])
        + [m for m in MODEL_COLUMN_ORDER if m in result_cols]
        + [m for m in result_cols if m not in MODEL_COLUMN_ORDER and m != "PKNF"]
    )
    table = pd.DataFrame({c: result_cols[c] for c in ordered_cols}, index=REG_INDEX)
    table.to_markdown(TABLES_DIR / f"{out_prefix}_table6_compare.md", index=True)
    table.to_latex(TABLES_DIR / f"{out_prefix}_table6_compare.tex", index=True)
    print(f"  Saved cross-model Table 6 -> {out_prefix}_table6_compare.{{md,tex}}")


def process_file(csv_path: Path) -> tuple[str, float, float, pd.DataFrame]:
    """
    Process one PKNF results CSV file, generating all tables and figures.

    Returns (model, flat_rate, top_rate, cleaned_df) so the caller can
    aggregate results across models without re-reading the file.
    """
    print(f"\nProcessing: {csv_path.name}")
    model, flat_rate, top_rate = parse_filename(csv_path)
    print(f"  Model: {model} | Flat rate: {flat_rate:.0%} | Top rate: {top_rate:.0%}")

    df_raw = pd.read_csv(csv_path)
    df = clean_data(df_raw)
    print(f"  Observations after cleaning: {len(df)}")

    treatments = list(df["treatment"].unique())
    # Ensure control group (Prog,Prog) comes first
    if "Prog,Prog" in treatments:
        treatments = ["Prog,Prog"] + sorted(t for t in treatments if t != "Prog,Prog")

    # Build output prefix; sanitize model name (replace / with _)
    model_safe = model.replace("/", "_")
    flat_str = f"{int(flat_rate * 100)}pct"
    top_str = f"{int(top_rate * 100)}pct"
    out_prefix = f"pknf_{model_safe}_{flat_str}_{top_str}"

    make_table5(df, out_prefix, treatments)
    make_figure2(df, out_prefix, treatments)
    make_figure4(df, out_prefix, treatments)
    make_regression_tables(df, out_prefix, treatments, top_rate)
    make_bunching_figure(df, out_prefix)

    return model_safe, flat_rate, top_rate, df


def main() -> None:
    csv_files = sorted(DATA_DIR.glob("pknf_results_*.csv"))
    if not csv_files:
        print(f"No pknf_results_*.csv files found in {DATA_DIR}")
        return
    print(f"Found {len(csv_files)} PKNF results file(s) to process.")

    # Collect cleaned data grouped by (flat_rate, top_rate) for cross-model tables
    rate_groups: dict[tuple[float, float], list[tuple[str, pd.DataFrame]]] = {}
    for csv_path in csv_files:
        model_safe, flat_rate, top_rate, df = process_file(csv_path)
        key = (flat_rate, top_rate)
        rate_groups.setdefault(key, []).append((model_safe, df))

    # Generate one cross-model comparison table per rate combination
    print("\nGenerating cross-model comparison tables...")
    for (flat_rate, top_rate), model_dfs in sorted(rate_groups.items()):
        make_cross_model_table5(model_dfs, flat_rate, top_rate)
        make_cross_model_bar_figure(model_dfs, flat_rate, top_rate)
        make_cross_model_table6(model_dfs, flat_rate, top_rate)
        make_bunching_eti_table(model_dfs, flat_rate, top_rate)
        make_eti_summary_table(model_dfs, flat_rate, top_rate)

    print("\nDone. Outputs written to:")
    print(f"  Figures: {FIGURES_DIR}")
    print(f"  Tables:  {TABLES_DIR}")


if __name__ == "__main__":
    main()
