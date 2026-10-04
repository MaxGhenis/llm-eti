"""Gruber-Saez ETI tables and figures (all models).

Produces, from the stacked per-model simulation results in book/data:
  * summary_statistics.tex                       -- mean/median ETI per model
  * gs_eti_regression_taxable_spline.tex         -- ETI regression, taxable income
  * gs_eti_regression_broad_spline.tex           -- ETI regression, broad income
  * gs_table9_income_group_all_models_cpi2026.tex -- GS 2002 Table 9 analogue
  * eti_by_mtr_model.png                         -- ETI vs MTR change scatter
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
import statsmodels.api as sm  # noqa: E402
from patsy import dmatrix  # noqa: E402

# --------------------------------------------------
# Paths
# --------------------------------------------------
# Overridable so the paper can be rebuilt from its frozen inputs:
#   LLM_ETI_GS_DATA_DIR=paper_inputs/gs LLM_ETI_GS_OUT_DIR=paper/images_tables
DATA_DIR = Path(
    os.environ.get("LLM_ETI_GS_DATA_DIR", Path(__file__).parents[1] / "data")
)
OUTPUT_DIR = Path(
    os.environ.get(
        "LLM_ETI_GS_OUT_DIR",
        Path(__file__).parents[2] / "results" / "combined_analysis_20260617",
    )
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Clean display names + column ordering for every model file in book/data
DISPLAY_NAMES = {
    "gpt-4o": "GPT-4o",
    "gpt-4o-mini": "GPT-4o-mini",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "deepseek-ai/DeepSeek-V3": "DeepSeek-V3",
    "google/gemma-4-26B-A4B-it": "Gemma 4",
}
MODEL_ORDER = [
    "GPT-4o",
    "GPT-4o-mini",
    "Claude Haiku 4.5",
    "DeepSeek-V3",
    "Gemma 4",
]

# Longer headers are wrapped onto two lines to keep the tables narrow.
HEADER_TWO_LINE = {
    "GPT-4o-mini": ("GPT-4o", "mini"),
    "Claude Haiku 4.5": ("Claude", "Haiku 4.5"),
    "DeepSeek-V3": ("DeepSeek", "V3"),
    "All Models": ("All", "Models"),
}


def header_cell(name):
    if name in HEADER_TWO_LINE:
        top, bottom = HEADER_TWO_LINE[name]
        return rf"\shortstack{{{top} \\ {bottom}}}"
    return name


def header_row(headers):
    return "  & " + " & ".join(header_cell(h) for h in headers) + r" \\"


print("--------------------------------------------------")
print("Gruber-Saez ETI tables and figures (all models)")
print("--------------------------------------------------")

# --------------------------------------------------
# Load every model file and stack
# --------------------------------------------------
files = sorted(DATA_DIR.glob("gruber_saez_results_*.csv"))
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
df["model_display"] = df["model"].map(DISPLAY_NAMES).fillna(df["model"])
for f in files:
    print(f"Loaded {f.name}")
print(f"Total observations: {len(df):,}")

# --------------------------------------------------
# Construct log changes (Gruber-Saez specification)
# --------------------------------------------------
df["log_rate_change"] = np.log((1 - df["mtr_prime"]) / (1 - df["mtr"]))
df["log_taxable_income_change"] = np.log(
    df["taxable_income_this"] / df["taxable_income"]
)
df["log_broad_income_change"] = np.log(df["broad_income_this"] / df["broad_income"])
df["mtr_change"] = df["mtr_prime"] - df["mtr"]


# --------------------------------------------------
# Shared formatting helpers
# --------------------------------------------------
def stars(p):
    if p < 0.01:
        return "***"
    elif p < 0.05:
        return "**"
    elif p < 0.1:
        return "*"
    return ""


def fmt_coef(coef, p):
    if coef is None or np.isnan(coef):
        return "--"
    s = stars(p)
    return f"${coef:.3f}^{{{s}}}$" if s else f"${coef:.3f}$"


def columns():
    """(label, sample) for each model plus a combined 'All Models' column."""
    cols = [(m, df[df["model_display"] == m]) for m in MODEL_ORDER]
    cols.append(("All Models", df))
    return cols


# --------------------------------------------------
# Gruber-Saez ETI regression: log income change on log net-of-tax rate.
# The coefficient on the log net-of-tax rate IS the ETI. Base-year income is
# controlled for with a natural cubic spline (df=5) -- GS's mean-reversion
# adjustment.
# --------------------------------------------------
OUTCOMES = [
    ("log_taxable_income_change", "taxable_income", "Taxable Income", "taxable"),
    ("log_broad_income_change", "broad_income", "Broad Income", "broad"),
]


def fit_eti(sample, ycol, base_col):
    """OLS of log income change on log net-of-tax rate + base-year spline."""
    s = sample.replace([np.inf, -np.inf], np.nan).dropna(
        subset=["log_rate_change", ycol, base_col]
    )
    s = s[s[base_col] > 0]
    log_base = np.log(s[base_col].to_numpy())
    spline = dmatrix(
        "cr(log_base, df=5)", {"log_base": log_base}, return_type="dataframe"
    )
    spline.index = s.index
    X = pd.concat([s[["log_rate_change"]], spline], axis=1)
    reg = sm.OLS(s[ycol], X).fit(cov_type="HC1")
    # The five natural-cubic-spline basis terms in log base-year income.
    spline_cols = [c for c in spline.columns if c != "Intercept"]
    return {
        "coef": reg.params["log_rate_change"],
        "se": reg.bse["log_rate_change"],
        "p": reg.pvalues["log_rate_change"],
        "const": reg.params["Intercept"],
        "const_se": reg.bse["Intercept"],
        "const_p": reg.pvalues["Intercept"],
        "spline_coefs": [reg.params[c] for c in spline_cols],
        "spline_ses": [reg.bse[c] for c in spline_cols],
        "spline_ps": [reg.pvalues[c] for c in spline_cols],
        "r2": reg.rsquared,
        "n": int(reg.nobs),
    }


def build_reg_table(ycol, base_col, measure):
    res = [fit_eti(sample, ycol, base_col) for _, sample in columns()]
    consts = [fmt_coef(r["const"], r["const_p"]) for r in res]
    const_ses = [f"({r['const_se']:.3f})" for r in res]
    slopes = [fmt_coef(r["coef"], r["p"]) for r in res]
    slope_ses = [f"({r['se']:.3f})" for r in res]
    r2s = [f"{r['r2']:.3f}" for r in res]
    ns = [f"{r['n']:,}" for r in res]

    # One coef/SE row-pair per natural-cubic-spline basis term in log base-year
    # income (df=5 -> 5 terms). All columns share the same number of terms.
    n_spline = len(res[0]["spline_coefs"])
    spline_lines = []
    for k in range(n_spline):
        coefs = [fmt_coef(r["spline_coefs"][k], r["spline_ps"][k]) for r in res]
        ses = [f"({r['spline_ses'][k]:.3f})" for r in res]
        spline_lines.append(
            f"  Base income spline {k + 1} & " + " & ".join(coefs) + r" \\"
        )
        spline_lines.append("  & " + " & ".join(ses) + r" \\")

    headers = [c[0] for c in columns()]
    ncol = len(headers)

    lines = [
        r"\begin{table}[!htbp] \centering",
        rf"  \caption{{Model Comparison: Elasticity Results ({measure})}}",
        r"  \begin{tabular}{l" + "c" * ncol + "}",
        r"  \toprule",
        header_row(headers),
        r"  \midrule",
        "  Constant & " + " & ".join(consts) + r" \\",
        "  & " + " & ".join(const_ses) + r" \\",
        "  Net-of-tax elasticity & " + " & ".join(slopes) + r" \\",
        "  & " + " & ".join(slope_ses) + r" \\",
        *spline_lines,
        r"  \midrule",
        r"  $R^2$ & " + " & ".join(r2s) + r" \\",
        r"  \midrule",
        "  N & " + " & ".join(ns) + r" \\",
        r"  \bottomrule",
        r"  \end{tabular}",
        r"  \begin{flushleft}\footnotesize",
        r"  Heteroskedasticity-robust SEs in parentheses. Specifications include "
        r"a natural cubic spline (df\,$=$5) in log base-year income; its five "
        r"basis-term coefficients are reported as ``Base income spline 1--5''.\\",
        r"  $^{*}p<0.1$, $^{**}p<0.05$, $^{***}p<0.01$",
        r"  \end{flushleft}",
        r"\end{table}",
    ]
    return "\n".join(lines)


for ycol, base_col, measure, key in OUTCOMES:
    fname = f"gs_eti_regression_{key}_spline.tex"
    (OUTPUT_DIR / fname).write_text(build_reg_table(ycol, base_col, measure))
    print(f"Wrote {fname}")


# --------------------------------------------------
# Summary statistics table
# --------------------------------------------------
def build_summary_table():
    headers = [c[0] for c in columns()]
    ncol = len(headers)
    mean_eti, median_eti, same_inc, obs = [], [], [], []
    for _, sample in columns():
        eti = sample["implied_eti_taxable"].replace([np.inf, -np.inf], np.nan).dropna()
        same = (sample["taxable_income_this"] == sample["taxable_income"]).mean() * 100
        mean_eti.append(f"{eti.mean():.3f}")
        median_eti.append(f"{eti.median():.3f}")
        same_inc.append(f"{same:.1f}\\%")
        obs.append(f"{len(sample):,}")

    lines = [
        r"\begin{table}[!htbp] \centering",
        r"  \caption{Model Comparison: Summary Statistics}",
        r"  \label{tab:obs_summ_stats}",
        r"  \begin{tabular}{l" + "c" * ncol + "}",
        r"  \toprule",
        header_row(headers),
        r"  \midrule",
        "  Mean ETI & " + " & ".join(mean_eti) + r" \\",
        "  Median ETI & " + " & ".join(median_eti) + r" \\",
        "  \\% Same Income & " + " & ".join(same_inc) + r" \\",
        r"  \midrule",
        "  Observations & " + " & ".join(obs) + r" \\",
        r"  \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


(OUTPUT_DIR / "summary_statistics.tex").write_text(build_summary_table())
print("Wrote summary_statistics.tex")

# --------------------------------------------------
# ETI vs MTR change scatter (taxable-income ETI; trimmed to 1st-99th pct)
# --------------------------------------------------
eti = df["implied_eti_taxable"].replace([np.inf, -np.inf], np.nan)
lo, hi = eti.quantile(0.01), eti.quantile(0.99)
viz = df[(eti >= lo) & (eti <= hi)].copy()
present = [m for m in MODEL_ORDER if m in viz["model_display"].unique()]

fig, ax = plt.subplots(figsize=(14, 7))
ax.set_axisbelow(True)  # gridlines behind the points
ax.grid(True, color="lightgrey", linewidth=0.5)
sns.scatterplot(
    data=viz,
    x="mtr_change",
    y="implied_eti_taxable",
    hue="model_display",
    hue_order=present,
    alpha=0.4,
    s=30,
    edgecolor="none",
    ax=ax,
)
# Gruber & Saez (2002) headline ETI estimate.
ax.axhline(0.4, color="firebrick", linestyle="--", linewidth=1.2)
ax.text(
    ax.get_xlim()[0],
    0.4,
    " GS 2002 (0.40)",
    color="firebrick",
    va="bottom",
    ha="left",
    fontsize=14,
)
ax.set_title("ETI vs Tax Rate Change by Model", fontsize=20)
ax.set_xlabel("Change in Marginal Tax Rate", fontsize=16)
ax.set_ylabel("Implied ETI", fontsize=16)
ax.tick_params(axis="both", labelsize=14)
legend = ax.legend(
    title="Model",
    bbox_to_anchor=(1.01, 1),
    loc="upper left",
    fontsize=14,
    markerscale=1.6,
)
legend.get_title().set_fontsize(15)
fig.tight_layout()
fig.savefig(OUTPUT_DIR / "eti_by_mtr_model.png", dpi=150)
plt.close(fig)
print("Wrote eti_by_mtr_model.png")


# ==================================================
# Gruber & Saez (2002) Table 9 analogue: ETI by base-year income group.
# Reproduces GS Table 9, Panel A (one pooled "All Models" table). The three
# GS income-concept columns are:
#   (1) Elasticity of BROAD income,   sample split by BROAD income
#   (2) Elasticity of TAXABLE income, sample split by BROAD income
#   (3) Elasticity of TAXABLE income, sample split by TAXABLE income
# GS's 1992-dollar cutoffs are inflated to 2026 dollars (CPI-U) so the brackets
# line up with our simulated incomes (PolicyEngine microdata, 2026 dollars).
# Regressions are income-weighted (WLS), OLS not 2SLS (the net-of-tax rate
# change is imposed by the simulation), with a base-year income spline.
# ==================================================

# Below this many usable observations in a group, fall back from the df=5
# spline to a single linear base-year income control to keep the fit stable.
SPLINE_MIN_N = 150

# CPI inflation: GS express all dollar figures in 1992 dollars (GS pp. 7-8);
# our simulated incomes are in contemporary (2026) dollars.
# Source: BLS CPI-U, all items, U.S. city average (1982-84 = 100).
CPI_BASE_YEAR = 1992
CPI_TARGET_YEAR = 2026
CPI_U = {1992: 140.3, 2026: 330.0}  # 1992 published; 2026 estimated
CPI_FACTOR = CPI_U[CPI_TARGET_YEAR] / CPI_U[CPI_BASE_YEAR]

# GS Table 9 income groups (1992 dollars). cols (1)&(2) use broad-income cuts;
# col (3) uses taxable-income cuts.
GS_BROAD_CUTS = [(10_000, 50_000), (50_000, 100_000), (100_000, np.inf)]
GS_TAXABLE_CUTS = [(10_000, 32_000), (32_000, 75_000), (75_000, np.inf)]


def inflate(cuts):
    """Inflate (lo, hi) cutoffs to TARGET_YEAR dollars, rounded to $1,000."""
    out = []
    for lo, hi in cuts:
        lo2 = round(lo * CPI_FACTOR, -3)
        hi2 = hi if np.isinf(hi) else round(hi * CPI_FACTOR, -3)
        out.append((lo2, hi2))
    return out


def fmt_k(v):
    return f"{v / 1000:.0f}K"


def row_label(broad_pair, tax_pair):
    """LaTeX row label: broad range with the taxable-cut range in parentheses."""

    def part(lo, hi):
        if np.isinf(hi):
            return rf"\${fmt_k(lo)}+"
        return rf"\${fmt_k(lo)}--\${fmt_k(hi)}"

    return f"{part(*broad_pair)} ({part(*tax_pair)})"


BROAD_CUTS = inflate(GS_BROAD_CUTS)
TAXABLE_CUTS = inflate(GS_TAXABLE_CUTS)
CUTSET_LABEL = rf"CPI-adjusted to {CPI_TARGET_YEAR}\$"
CUTSET_NOTE = (
    rf"Income ranges are GS's 1992-dollar cutoffs inflated to "
    rf"{CPI_TARGET_YEAR} dollars with CPI-U (factor {CPI_FACTOR:.2f}); the "
    rf"{CPI_TARGET_YEAR} CPI value is an estimate."
)

COL_HEADERS = [
    (r"Broad", r"income (1)"),
    (r"Taxable", r"income (2)"),
    (r"Taxable inc.", r"(tax. cuts) (3)"),
]


def fit_eti_group(sample, ycol, base_col, group_col, lo, hi):
    """Income-weighted OLS of log income change on log net-of-tax rate within
    one base-year income group, with a base-year income control (spline, or a
    linear fallback for thin groups). Returns coef/SE/p and N, or NaNs if the
    group is too small to estimate."""
    needed = ["log_rate_change", ycol, base_col, group_col]
    s = sample.replace([np.inf, -np.inf], np.nan).dropna(subset=needed)
    s = s[(s[base_col] > 0) & (s[group_col] >= lo) & (s[group_col] < hi)]
    n = len(s)
    if n < 10:
        return {"coef": np.nan, "se": np.nan, "p": np.nan, "n": n}

    log_base = np.log(s[base_col].to_numpy())
    if n >= SPLINE_MIN_N:
        ctrl = dmatrix(
            "cr(log_base, df=5)", {"log_base": log_base}, return_type="dataframe"
        )
        ctrl.index = s.index
        X = pd.concat([s[["log_rate_change"]], ctrl], axis=1)
    else:  # linear fallback
        X = sm.add_constant(
            pd.DataFrame(
                {
                    "log_rate_change": s["log_rate_change"].to_numpy(),
                    "log_base_income": log_base,
                },
                index=s.index,
            )
        )

    weights = s[base_col].to_numpy()  # GS: regressions weighted by income
    reg = sm.WLS(s[ycol], X, weights=weights).fit(cov_type="HC1")
    return {
        "coef": reg.params["log_rate_change"],
        "se": reg.bse["log_rate_change"],
        "p": reg.pvalues["log_rate_change"],
        "n": int(reg.nobs),
    }


def build_table9(label, sample):
    """One GS Table-9-style table for a single sample (model or pooled)."""
    # The three GS columns: (outcome change, base income col, grouping col, cuts).
    cols = [
        ("log_broad_income_change", "broad_income", "broad_income", BROAD_CUTS),
        ("log_taxable_income_change", "taxable_income", "broad_income", BROAD_CUTS),
        ("log_taxable_income_change", "taxable_income", "taxable_income", TAXABLE_CUTS),
    ]
    row_labels = [
        row_label(BROAD_CUTS[i], TAXABLE_CUTS[i]) for i in range(len(BROAD_CUTS))
    ]

    # res[row][col] -> fit dict
    res = [
        [
            fit_eti_group(sample, ycol, base_col, group_col, *cuts[i])
            for (ycol, base_col, group_col, cuts) in cols
        ]
        for i in range(len(row_labels))
    ]

    body = []
    for i, rlabel in enumerate(row_labels):
        coefs = " & ".join(
            fmt_coef(res[i][j]["coef"], res[i][j]["p"]) for j in range(3)
        )
        ses = " & ".join(
            ("--" if np.isnan(res[i][j]["se"]) else f"({res[i][j]['se']:.3f})")
            for j in range(3)
        )
        ns = " & ".join(f"{res[i][j]['n']:,}" for j in range(3))
        body += [
            f"  {rlabel} & {coefs} " + r"\\",
            f"  & {ses} " + r"\\",
            f"  N. Obs & {ns} " + r"\\[2pt]",
        ]

    top = " & ".join(rf"\shortstack{{{a} \\ {b}}}" for a, b in COL_HEADERS)
    lines = [
        r"\begin{table}[!htbp] \centering",
        rf"  \caption{{Elasticity Results by Income Group, \textit{{{label}}} "
        rf"({CUTSET_LABEL}; Gruber \& Saez 2002, Table 9)}}",
        r"  \begin{tabular}{lccc}",
        r"  \toprule",
        "  Income range & " + top + r" \\",
        r"  \midrule",
        *body,
        r"  \bottomrule",
        r"  \end{tabular}",
        r"  \begin{flushleft}\footnotesize",
        r"  Each cell: income-weighted OLS elasticity of income with respect to "
        r"the net-of-tax rate, estimated within the base-year income group. "
        r"Heteroskedasticity-robust SEs in parentheses. Columns (1)--(2) split "
        r"the sample by base-year broad income; column (3) by base-year taxable "
        r"income. Groups control for base-year income via a natural cubic spline "
        rf"(df\,$=$5), or a single linear term when N\,$<${SPLINE_MIN_N}. "
        r"OLS rather than 2SLS because the net-of-tax rate change is imposed by "
        r"the simulation. " + CUTSET_NOTE + r"\\",
        r"  $^{*}p<0.1$, $^{**}p<0.05$, $^{***}p<0.01$",
        r"  \end{flushleft}",
        r"\end{table}",
    ]
    return "\n".join(lines)


(OUTPUT_DIR / "gs_table9_income_group_all_models_cpi2026.tex").write_text(
    build_table9("All Models", df)
)
print("Wrote gs_table9_income_group_all_models_cpi2026.tex")

print("--------------------------------------------------")
print(f"All outputs written to {OUTPUT_DIR}")
print("--------------------------------------------------")
