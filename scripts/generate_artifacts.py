#!/usr/bin/env python3
"""Generate every reported number, table, figure, and site datum.

This is the only presentation-layer analysis entry point.  It reads the frozen
CSV corpus through :mod:`llm_eti.study2`; the Quarto sources never recompute a
statistic or carry a hand-entered headline result.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from llm_eti.study2 import (
    MODEL_SPECS,
    completion_summary,
    load_study2_data,
    model_summary,
    primary_analysis_scenario_ids,
    primary_balanced_scenario_ids,
    sensitivity_summary,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "responses"
SCENARIO_PATH = ROOT / "data" / "scenarios.csv"
GENERATED_DIR = ROOT / "paper" / "generated"
FIGURES_DIR = ROOT / "paper" / "figures"
ASSETS_DIR = ROOT / "assets"

INK = "#17231f"
TEAL = "#176b63"
TEAL_LIGHT = "#75b9ae"
RUST = "#c86b4a"
STONE = "#a7aaa3"
PAPER = "#f4f0e6"
MODEL_COLORS = {
    "Claude Haiku 4.5": "#176b63",
    "DeepSeek V3": "#4d8e86",
    "Gemma 4 26B": "#c86b4a",
    "GPT-4o mini": "#795b8f",
    "GPT-4o (partial run)": "#a7aaa3",
}
FIGURE_TIMESTAMP = datetime(2026, 7, 9, tzinfo=UTC)
plt.rcParams["svg.hashsalt"] = "llm-eti-0.2.0"


def _write(name: str, content: str) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    if name.endswith(".html"):
        content = "\n".join(line.lstrip() for line in content.splitlines())
    (GENERATED_DIR / name).write_text(f"{content.rstrip()}\n", encoding="utf-8")


def _canonicalize_json(value: Any) -> Any:
    """Remove immaterial cross-platform floating-point noise from JSON output."""

    if isinstance(value, dict):
        return {key: _canonicalize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonicalize_json(item) for item in value]
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError("Publication JSON cannot contain non-finite numbers")
        return float(f"{value:.12g}")
    return value


def _fmt_number(value: float, precision: int) -> str:
    """Format a result without producing a misleading negative zero."""

    threshold = 0.5 * 10**-precision
    clean = 0.0 if abs(value) < threshold else value
    return f"{clean:.{precision}f}"


def _fmt_ci(row: pd.Series, prefix: str = "") -> str:
    slope = float(row[f"{prefix}slope"])
    lower = float(row[f"{prefix}slope_ci_lower"])
    upper = float(row[f"{prefix}slope_ci_upper"])
    precision = 4 if min(abs(slope), abs(lower), abs(upper)) < 0.01 else 2
    return (
        f"{_fmt_number(slope, precision)} "
        f"[{_fmt_number(lower, precision)}, {_fmt_number(upper, precision)}]"
    )


def _fmt_iqr(row: pd.Series) -> str:
    values = [row["median_implied_eti"], row["eti_q25"], row["eti_q75"]]
    values = [0.0 if abs(value) < 0.005 else value for value in values]
    return f"{values[0]:.2f} [{values[1]:.2f}, {values[2]:.2f}]"


def _completion_table(completion: pd.DataFrame) -> str:
    table = completion.copy()
    table["Scenario coverage"] = table["scenario_completion_rate"].map(
        lambda value: f"{value:.1%}"
    )
    table["Unique-response coverage"] = table["response_completion_rate"].map(
        lambda value: f"{value:.1%}"
    )
    table = table.rename(
        columns={
            "model": "Model",
            "completed_scenarios": "Scenarios represented",
            "source_records": "Archived records",
            "valid_responses": "Unique parseable responses",
            "complete_pairs": "Complete response pairs",
        }
    )
    return str(
        table[
            [
                "Model",
                "Scenarios represented",
                "Scenario coverage",
                "Archived records",
                "Unique parseable responses",
                "Complete response pairs",
                "Unique-response coverage",
            ]
        ].to_markdown(index=False)
    )


def _main_results_tables(summary: pd.DataFrame) -> tuple[str, str]:
    table = summary.copy()
    table["Taxable slope (95% CI)"] = table.apply(_fmt_ci, axis=1)
    table["Broad slope (95% CI)"] = table.apply(
        lambda row: _fmt_ci(row, "broad_"), axis=1
    )
    table["Median ratio [IQR]"] = table.apply(_fmt_iqr, axis=1)
    table["Unchanged"] = table["unchanged_share"].map(lambda value: f"{value:.1%}")
    table["Directional among changes"] = table["directional_consistency_nonzero"].map(
        lambda value: f"{value:.1%}"
    )
    table = table.rename(columns={"model": "Model", "n_scenarios": "Scenarios"})
    slopes = table[
        [
            "Model",
            "Scenarios",
            "Taxable slope (95% CI)",
            "Broad slope (95% CI)",
        ]
    ].to_markdown(index=False)
    diagnostics = table[
        [
            "Model",
            "Median ratio [IQR]",
            "Unchanged",
            "Directional among changes",
        ]
    ].to_markdown(index=False)
    return slopes, diagnostics


def _sensitivity_table(sensitivity: pd.DataFrame) -> str:
    table = sensitivity.copy()
    table["Slope (95% CI)"] = table.apply(_fmt_ci, axis=1)
    table = table.rename(
        columns={
            "model": "Model",
            "specification": "Specification",
            "n_scenarios": "Scenarios",
        }
    )
    return str(
        table[["Model", "Specification", "Scenarios", "Slope (95% CI)"]].to_markdown(
            index=False
        )
    )


def _source_hashes() -> dict[str, str]:
    paths = [SCENARIO_PATH, *(DATA_DIR / spec.filename for spec in MODEL_SPECS)]
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _provenance_table(results: pd.DataFrame) -> str:
    table = (
        results.groupby(["model_display", "model"], as_index=False)
        .agg(
            first_archived=("timestamp", "min"),
            last_archived=("timestamp", "max"),
            parsed_records=("source_record_count", "max"),
        )
        .rename(
            columns={
                "model_display": "Display name",
                "model": "Archived model identifier",
                "first_archived": "First timestamp",
                "last_archived": "Last timestamp",
                "parsed_records": "Archived records",
            }
        )
    )
    order = [spec.display_name for spec in MODEL_SPECS]
    table["Display name"] = pd.Categorical(
        table["Display name"], categories=order, ordered=True
    )
    table = table.sort_values("Display name")
    for column in ["First timestamp", "Last timestamp"]:
        table[column] = pd.to_datetime(table[column]).dt.strftime("%Y-%m-%d %H:%M")
    return str(table.to_markdown(index=False))


def _year_coverage_table(
    scenarios: pd.DataFrame,
    results: pd.DataFrame,
    balanced_ids: set[str],
    analysis_ids: set[str],
) -> str:
    """Show source and analysis coverage by year and model."""

    rows: list[dict[str, int]] = []
    primary_specs = [spec for spec in MODEL_SPECS if spec.primary]
    for year in sorted(scenarios["year"].unique()):
        source = scenarios[scenarios["year"].eq(year)]
        row: dict[str, int] = {
            "Year": int(year),
            "Source scenarios": int(len(source)),
        }
        for spec in primary_specs:
            model = results[
                results["model_key"].eq(spec.key)
                & results["year"].eq(year)
                & results["valid_income_response"]
            ]
            row[spec.display_name] = int(model["scenario_id"].nunique())
        row["Clean four-model panel"] = int(
            source["scenario_id"].isin(balanced_ids).sum()
        )
        row["Primary log panel"] = int(source["scenario_id"].isin(analysis_ids).sum())
        rows.append(row)
    return str(pd.DataFrame(rows).to_markdown(index=False))


def _sample_characteristics_table(
    scenarios: pd.DataFrame, analysis_ids: set[str]
) -> str:
    """Summarize the frozen source sample and selected primary panel."""

    rows = []
    for label, sample in [
        ("Frozen source", scenarios),
        ("Primary log panel", scenarios[scenarios["scenario_id"].isin(analysis_ids)]),
    ]:
        rows.append(
            {
                "Sample": label,
                "Scenarios": len(sample),
                "2023": int(sample["year"].eq(2023).sum()),
                "2024": int(sample["year"].eq(2024).sum()),
                "Median broad income": f"${sample['prompt_broad_income'].median():,.0f}",
                "Median taxable income": f"${sample['prompt_taxable_income'].median():,.0f}",
                "Median initial MTR": f"{sample['prompt_mtr'].median():.0%}",
                "Median absolute rate change": (
                    f"{(sample['prompt_mtr_prime'] - sample['prompt_mtr']).abs().median():.0%}"
                ),
            }
        )
    return str(pd.DataFrame(rows).to_markdown(index=False))


def _style_axes(ax: plt.Axes) -> None:
    ax.set_facecolor("white")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0, colors=INK)
    ax.tick_params(axis="x", colors="#5d665f")
    ax.xaxis.label.set_color("#5d665f")
    ax.yaxis.label.set_color("#5d665f")
    ax.title.set_color(INK)


def _save_figure(fig: plt.Figure, name: str, *, transparent: bool = False) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(name).stem
    for suffix in [".png", ".svg", ".pdf"]:
        output = FIGURES_DIR / f"{stem}{suffix}"
        creator = "llm-eti deterministic publication pipeline"
        if suffix == ".png":
            fig.savefig(
                output,
                dpi=200,
                bbox_inches="tight",
                facecolor="none" if transparent else "white",
                transparent=transparent,
                metadata={"Creator": creator},
            )
        elif suffix == ".svg":
            fig.savefig(
                output,
                bbox_inches="tight",
                facecolor="none" if transparent else "white",
                transparent=transparent,
                metadata={"Creator": creator, "Date": "2026-07-09"},
            )
            svg = output.read_text(encoding="utf-8")
            output.write_text(
                "\n".join(line.rstrip() for line in svg.splitlines()) + "\n",
                encoding="utf-8",
            )
        else:
            fig.savefig(
                output,
                bbox_inches="tight",
                facecolor="none" if transparent else "white",
                transparent=transparent,
                metadata={
                    "Creator": creator,
                    "CreationDate": FIGURE_TIMESTAMP,
                    "ModDate": FIGURE_TIMESTAMP,
                },
            )
    plt.close(fig)


def _plot_completion(completion: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    values = completion["scenario_completion_rate"] * 100
    colors = [MODEL_COLORS[model] for model in completion["model"]]
    bars = ax.barh(completion["model"], values, color=colors, height=0.58)
    ax.bar_label(
        bars,
        labels=[f"{value:.1f}%" for value in values],
        padding=5,
        color=INK,
        fontsize=10,
    )
    ax.invert_yaxis()
    ax.set_xlim(0, 106)
    ax.set_xlabel("Share of 1,000 scenarios with an archived response")
    ax.set_title("Archived coverage differed across models", loc="left", weight="bold")
    _style_axes(ax)
    fig.tight_layout()
    _save_figure(fig, "completion_by_model.png")


def _plot_slopes(summary: pd.DataFrame) -> None:
    order = summary.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(9.4, 5.3))

    for offset, outcome, prefix, color, marker in [
        (-0.13, "Taxable income", "", TEAL, "o"),
        (0.13, "Broad income", "broad_", RUST, "s"),
    ]:
        estimate = order[f"{prefix}slope"].to_numpy()
        lower = estimate - order[f"{prefix}slope_ci_lower"].to_numpy()
        upper = order[f"{prefix}slope_ci_upper"].to_numpy() - estimate
        ax.errorbar(
            estimate,
            y + offset,
            xerr=np.vstack([lower, upper]),
            fmt=marker,
            markersize=7,
            capsize=4,
            color=color,
            ecolor=color,
            linewidth=1.8,
            label=outcome,
        )

    ax.axvline(0, color=STONE, linewidth=1, zorder=0)
    ax.set_yticks(y, order["model"])
    ax.set_xlabel("Slope of log income response on the log net-of-tax-rate change")
    ax.set_title(
        "The models imply different response patterns", loc="left", weight="bold"
    )
    ax.legend(frameon=False, ncol=2, loc="lower right")
    _style_axes(ax)
    fig.tight_layout()
    _save_figure(fig, "model_response_slopes.png")


def _plot_response_patterns(results: pd.DataFrame, analysis_ids: set[str]) -> None:
    sample = results[
        results["primary_model"]
        & results["scenario_id"].isin(analysis_ids)
        & results["valid_income_response"]
    ].copy()
    sample["pattern"] = np.select(
        [sample["taxable_income_unchanged"], sample["directionally_consistent"]],
        ["Unchanged", "Directionally consistent"],
        default="Opposite direction",
    )
    shares = (
        sample.groupby(["model_display", "pattern"]).size()
        / sample.groupby("model_display").size()
    ).unstack(fill_value=0)
    order = [spec.display_name for spec in MODEL_SPECS if spec.primary]
    shares = shares.reindex(order).iloc[::-1]
    categories = ["Unchanged", "Directionally consistent", "Opposite direction"]
    colors = ["#c7cbc4", TEAL, RUST]

    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    left = np.zeros(len(shares))
    for category, color in zip(categories, colors, strict=False):
        values = shares.get(category, pd.Series(0, index=shares.index)).to_numpy()
        ax.barh(
            shares.index,
            values * 100,
            left=left * 100,
            label=category,
            color=color,
            height=0.58,
        )
        left += values
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of individual responses in the primary panel")
    ax.set_title(
        "Baseline copying and directional changes vary sharply",
        loc="left",
        weight="bold",
    )
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.28))
    _style_axes(ax)
    fig.tight_layout()
    _save_figure(fig, "response_patterns.png")


def _plot_social_card(summary: pd.DataFrame) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(12, 6.3), facecolor=PAPER)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_axis_off()
    fig.text(0.07, 0.82, "LLM × ETI", color=TEAL, fontsize=17, weight="bold")
    fig.text(
        0.07,
        0.62,
        "What do language models imply\nabout taxable-income responses?",
        color=INK,
        fontsize=32,
        weight="bold",
        linespacing=1.05,
    )
    fig.text(
        0.07,
        0.40,
        "Four models. One common scenario panel.\nNo common response pattern.",
        color="#526159",
        fontsize=16,
        linespacing=1.4,
    )

    inset = fig.add_axes((0.63, 0.17, 0.30, 0.66), facecolor=PAPER)
    plot = summary.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(plot))
    inset.hlines(y, 0, plot["slope"], color="#b8cec9", linewidth=4)
    inset.scatter(plot["slope"], y, s=85, color=TEAL, zorder=3)
    inset.set_yticks(y, [name.replace(" ", "\n", 1) for name in plot["model"]])
    inset.set_xlim(0, 0.8)
    inset.set_xlabel("Taxable-income slope", color="#526159")
    inset.spines[["top", "right", "left"]].set_visible(False)
    inset.tick_params(axis="y", length=0, labelsize=10, colors=INK)
    inset.tick_params(axis="x", colors="#526159")
    fig.savefig(
        ASSETS_DIR / "social-card.png",
        dpi=100,
        facecolor=PAPER,
        metadata={"Creator": "llm-eti deterministic publication pipeline"},
    )
    plt.close(fig)


def _hero_metrics(summary: pd.DataFrame, analysis_count: int) -> str:
    rows = []
    maximum = max(0.8, float(summary["slope"].max()))
    for row in summary.itertuples(index=False):
        width = max(2.5, 100 * float(row.slope) / maximum)
        rows.append(
            "\n".join(
                [
                    '<div class="slope-row">',
                    f'  <div class="slope-model"><span>{row.model}</span><strong>{row.slope:.2f}</strong></div>',
                    '  <div class="slope-track" aria-hidden="true">',
                    f'    <span style="width: {width:.1f}%"></span>',
                    "  </div>",
                    f'  <div class="slope-ci">95% CI {row.slope_ci_lower:.2f} to {row.slope_ci_upper:.2f}</div>',
                    "</div>",
                ]
            )
        )
    return "\n".join(
        [
            '<div class="hero-result" aria-label="Primary taxable-income response slopes by model">',
            '  <div class="hero-result-heading">',
            "    <span>Model-implied taxable-income slope</span>",
            f"    <span>{analysis_count:,} common scenarios</span>",
            "  </div>",
            *rows,
            '  <p class="hero-result-note">Ordinary-log OLS with an intercept; 95% intervals cluster by year and source tax unit.</p>',
            "</div>",
        ]
    )


def _sample_flow(total: int, balanced: int, identified: int, primary: int) -> str:
    steps = [
        (total, "Archived scenarios", "Frozen PolicyEngine-derived input"),
        (balanced, "Clean four-model panel", "Two responses per model"),
        (identified, "Displayed rate change", "Integer rates differ"),
        (primary, "Primary log panel", "Every output is positive"),
    ]
    items = []
    for number, label, note in steps:
        items.append(
            "\n".join(
                [
                    '<li class="flow-step" data-reveal>',
                    f"  <strong>{number:,}</strong>",
                    f"  <span>{label}</span>",
                    f"  <small>{note}</small>",
                    "</li>",
                ]
            )
        )
    return (
        '<ol class="sample-flow" aria-label="Primary sample construction">\n'
        + "\n".join(items)
        + "\n</ol>"
    )


def main() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    scenarios, results = load_study2_data(SCENARIO_PATH, DATA_DIR)
    balanced_ids = primary_balanced_scenario_ids(results)
    analysis_ids = primary_analysis_scenario_ids(results)
    scenario_index = scenarios.set_index("scenario_id")
    identified_ids = {
        scenario_id
        for scenario_id in balanced_ids
        if bool(scenario_index.loc[scenario_id, "displayed_rate_change"])
    }
    completion = completion_summary(scenarios, results)
    summary = model_summary(results, scenario_ids=analysis_ids)
    sensitivity = sensitivity_summary(results, analysis_ids, identified_ids)

    same_rate_count = int((~scenarios["displayed_rate_change"]).sum())
    negative_rate_count = int(scenarios["prompt_mtr"].lt(0).sum())
    source_record_count = int(completion["source_records"].sum())
    duplicate_cells = int(results["ambiguous_rerun"].sum())
    duplicate_scenarios = int(
        results.loc[results["ambiguous_rerun"], "scenario_id"].nunique()
    )

    _write("completion.md", _completion_table(completion))
    _write("model_provenance.md", _provenance_table(results))
    _write(
        "year_coverage.md",
        _year_coverage_table(scenarios, results, balanced_ids, analysis_ids),
    )
    _write(
        "sample_characteristics.md",
        _sample_characteristics_table(scenarios, analysis_ids),
    )
    slope_results, response_diagnostics = _main_results_tables(summary)
    _write("slope_results.md", slope_results)
    _write("response_diagnostics.md", response_diagnostics)
    _write("sensitivity.md", _sensitivity_table(sensitivity))
    year_counts = scenarios.groupby("year").size().to_dict()
    _write(
        "scenario_sample.md",
        (
            "The legacy script first drew 550 tax units with replacement from each "
            "year, concatenated 2023 before 2024, removed perturbed rates outside "
            "the observed initial-rate range, and retained the first 1,000 rows. "
            f"The frozen result consequently contains **{year_counts[2023]:,} "
            f"scenarios from 2023** and **{year_counts[2024]:,} from 2024**, rather "
            "than equal year counts. This order-dependent construction and the "
            "positive-income source eligibility restriction define the scope of the "
            "archive."
        ),
    )
    _write(
        "treatment_diagnostics.md",
        (
            f"In **{same_rate_count:,} of {len(scenarios):,}** source scenarios, "
            "distinct continuous rates rendered as the same integer percentage, so "
            "the delivered prompt communicated no rate change. The initial displayed "
            f"marginal rate is negative in **{negative_rate_count:,}** scenarios. "
            "Five pairs of source rows rendered as identical delivered prompts; all "
            "ten are excluded from clean analyses."
        ),
    )
    _write(
        "recovery_diagnostics.md",
        (
            f"The five response files contain **{source_record_count:,} archived "
            f"rows**. Deduplication leaves **{len(results):,} unique analysis rows**. "
            f"In DeepSeek, **{duplicate_scenarios} scenarios** contain "
            f"**{duplicate_cells} duplicated scenario–response cells** "
            f"(**{duplicate_cells * 2} raw rows**); the first timestamped row in each "
            "cell is retained and flagged, and every affected scenario is excluded "
            "from common-panel analysis."
        ),
    )
    _write(
        "primary_panel.md",
        (
            f"The clean four-model intersection contains **{len(balanced_ids):,} "
            f"scenarios**. Of those, **{len(identified_ids):,}** display a nonzero "
            "integer rate change. Requiring positive broad- and taxable-income "
            "outputs from all four models and both requested responses leaves "
            f"**{len(analysis_ids):,} scenarios** in "
            f"**{int(summary['n_clusters'].min()):,} year–tax-unit clusters**."
        ),
    )
    _write(
        "design_diagnostics.md",
        (
            f"The archive contains **{len(scenarios):,} scenarios**. The clean "
            f"four-model intersection contains **{len(balanced_ids):,}**, of which "
            f"**{len(identified_ids):,}** displayed different integer marginal tax "
            f"rates. In **{same_rate_count:,}** source scenarios, distinct continuous "
            "rates rendered as the same integer percentage, so the delivered prompt "
            "identified no tax response. The initial displayed marginal rate is "
            f"negative in **{negative_rate_count:,}** source scenarios. Requiring "
            "positive broad- and taxable-income outputs in both repetitions for all "
            f"four models leaves the **{len(analysis_ids):,}-scenario** primary panel."
        ),
    )

    placebo = results[
        results["primary_model"]
        & results["scenario_id"].isin(balanced_ids)
        & ~results["displayed_rate_change"]
        & results["valid_income_response"]
    ]
    placebo_table = (
        placebo.groupby("model_display", as_index=False)
        .agg(
            scenarios=("scenario_id", "nunique"),
            unchanged_share=("taxable_income_unchanged", "mean"),
        )
        .rename(
            columns={
                "model_display": "Model",
                "scenarios": "Same-rate scenarios",
                "unchanged_share": "Taxable income unchanged",
            }
        )
    )
    placebo_table["Taxable income unchanged"] = placebo_table[
        "Taxable income unchanged"
    ].map(lambda value: f"{value:.1%}")
    _write("same_rate_check.md", placebo_table.to_markdown(index=False))

    partial = (
        results[results["model_key"].eq("gpt_4o")]
        .sort_values("response_number")
        .drop_duplicates("scenario_id")
    )
    _write(
        "partial_run_note.md",
        (
            f"The partial GPT-4o archive represents {partial['scenario_id'].nunique():,} "
            f"scenarios. Of those, {(~partial['displayed_rate_change']).mean():.1%} "
            "display the same before-and-after integer rate, compared with "
            f"{(~scenarios['displayed_rate_change']).mean():.1%} of the full source "
            "sample. Its mean absolute delivered log net-of-tax-rate change is "
            f"{partial['log_net_of_tax_change'].abs().mean():.4f}, versus "
            f"{scenarios['log_net_of_tax_change'].abs().mean():.4f} overall. The "
            "stopped run is therefore not a representative smaller sample and is "
            "excluded from outcome comparisons."
        ),
    )

    primary_responses = results[
        results["primary_model"]
        & results["scenario_id"].isin(analysis_ids)
        & results["valid_income_response"]
    ].copy()
    primary_responses["either_income_changes"] = ~(
        primary_responses["taxable_income_unchanged"]
        & np.isclose(
            primary_responses["broad_income_this"],
            primary_responses["prompt_broad_income"],
            atol=0.5,
            rtol=0,
        )
    )
    response_cells = (
        primary_responses.groupby(["model_display", "scenario_id"])[
            "either_income_changes"
        ]
        .agg(["sum", "size"])
        .reset_index()
    )
    response_cells["any_repeat_changes"] = response_cells["sum"].gt(0)
    response_cells["both_repeats_change"] = response_cells["sum"].eq(
        response_cells["size"]
    )
    friction = (
        primary_responses.groupby("model_display")["either_income_changes"]
        .mean()
        .rename("Either income changes")
        .to_frame()
        .join(
            response_cells.groupby("model_display")[
                ["any_repeat_changes", "both_repeats_change"]
            ]
            .mean()
            .rename(
                columns={
                    "any_repeat_changes": "At least one repeat changes",
                    "both_repeats_change": "Both repeats change",
                }
            )
        )
        .reset_index()
        .rename(columns={"model_display": "Model"})
    )
    for column in [
        "Either income changes",
        "At least one repeat changes",
        "Both repeats change",
    ]:
        friction[column] = friction[column].map(lambda value: f"{value:.1%}")
    _write("response_friction.md", friction.to_markdown(index=False))

    boundary = results[
        results["primary_model"]
        & results["scenario_id"].isin(identified_ids)
        & results["valid_income_response"]
    ].copy()
    boundary["nonpositive_output"] = boundary["taxable_income_this"].le(0) | boundary[
        "broad_income_this"
    ].le(0)
    boundary_table = (
        boundary.groupby("model_display", as_index=False)
        .agg(
            zero_taxable_records=(
                "taxable_income_this",
                lambda values: int(values.eq(0).sum()),
            ),
            affected_scenarios=(
                "scenario_id",
                lambda values: int(
                    boundary.loc[values.index]
                    .groupby("scenario_id")["nonpositive_output"]
                    .any()
                    .sum()
                ),
            ),
        )
        .rename(
            columns={
                "model_display": "Model",
                "zero_taxable_records": "Zero taxable-income records",
                "affected_scenarios": "Scenarios with any nonpositive output",
            }
        )
    )
    _write("boundary_outputs.md", boundary_table.to_markdown(index=False))

    by_key = summary.set_index("model_key")
    claude = by_key.loc["claude_haiku_4_5"]
    deepseek = by_key.loc["deepseek_v3"]
    gemma = by_key.loc["gemma_4_26b"]
    mini = by_key.loc["gpt_4o_mini"]
    _write(
        "main_narrative.md",
        (
            "Claude Haiku 4.5 has a taxable-income slope of "
            f"**{claude['slope']:.2f}** (95% CI "
            f"{claude['slope_ci_lower']:.2f} to {claude['slope_ci_upper']:.2f}), "
            "and DeepSeek V3 has a slope of "
            f"**{deepseek['slope']:.2f}** ({deepseek['slope_ci_lower']:.2f} to "
            f"{deepseek['slope_ci_upper']:.2f}). Gemma's taxable-income point "
            f"estimate is **{gemma['slope']:.2f}**, but its interval includes zero "
            f"({gemma['slope_ci_lower']:.2f} to {gemma['slope_ci_upper']:.2f}); "
            f"GPT-4o mini's estimate is **{mini['slope']:.2f}** "
            f"({mini['slope_ci_lower']:.2f} to {mini['slope_ci_upper']:.2f}). "
            f"Claude's broad-income slope is **{claude['broad_slope']:.2f}**. "
            "The other three broad-income estimates are much closer to zero, so "
            "their nonzero taxable-income responses arise primarily through the gap "
            "between broad and taxable income."
        ),
    )
    _write(
        "key_findings.md",
        (
            "The four models do not produce a common response distribution. Claude "
            "Haiku 4.5 has "
            "a median scenario-level implied response ratio of "
            f"**{claude['median_implied_eti']:.2f}**, and DeepSeek V3 has a median "
            f"of **{deepseek['median_implied_eti']:.2f}**. Gemma 4 and GPT-4o mini "
            "both have medians of approximately zero because most responses leave "
            f"taxable income unchanged ({gemma['unchanged_share']:.1%} and "
            f"{mini['unchanged_share']:.1%}). Their occasional large adjustments "
            "nevertheless produce positive least-squares slopes. This mean–median "
            "divergence reflects a large mass at the supplied baseline and sensitivity "
            "to tail responses; it is not evidence that any model recovers a human "
            "behavioral elasticity."
        ),
    )
    sensitivity_index = sensitivity.set_index(["model_key", "specification"])

    def sensitivity_slope(model_key: str, specification: str) -> float:
        return float(sensitivity_index.loc[(model_key, specification), "slope"])

    _write(
        "sensitivity_narrative.md",
        (
            "The model-specific clean-pair samples produce taxable-income slopes of "
            f"**{sensitivity_slope('claude_haiku_4_5', 'All clean completed pairs, intercept'):.2f}** "
            "for Claude, "
            f"**{sensitivity_slope('deepseek_v3', 'All clean completed pairs, intercept'):.2f}** "
            "for DeepSeek, "
            f"**{sensitivity_slope('gemma_4_26b', 'All clean completed pairs, intercept'):.2f}** "
            "for Gemma, and "
            f"**{sensitivity_slope('gpt_4o_mini', 'All clean completed pairs, intercept'):.2f}** "
            "for GPT-4o mini. Year-stratified estimates are reported because the "
            "source composition and DeepSeek coverage differ sharply by year; they "
            "are exploratory selection checks rather than prespecified subgroup "
            "tests. The zero-inclusive log(1 + income) specification is a "
            "unit-dependent boundary stress test and is not interpreted as an "
            "elasticity."
        ),
    )
    _write(
        "abstract.md",
        (
            "We study whether large language models produce stable, coherent answers "
            "about taxable-income responses to marginal tax-rate changes. We analyze "
            "an archived June 2026 corpus in which four primary models were asked for "
            "two responses to one prompt for each of 1,000 PolicyEngine-derived "
            "tax-unit scenarios; archive coverage varied by model and year. A clean "
            f"complete-case intersection contains {len(balanced_ids):,} "
            f"scenarios; {len(identified_ids):,} display a nonzero change in the "
            f"integer marginal tax rate, and {len(analysis_ids):,} also have positive "
            "outputs from every model and repetition. After reconstructing the values "
            "actually shown to each model, model-specific taxable-income response "
            f"slopes range from {summary['slope'].min():.2f} to "
            f"{summary['slope'].max():.2f}, while median scenario ratios range from "
            f"{summary['median_implied_eti'].min():.2f} to "
            f"{summary['median_implied_eti'].max():.2f}. Model distributions differ "
            "sharply: Claude Haiku 4.5 and DeepSeek V3 usually adjust income, whereas "
            "Gemma 4 and GPT-4o mini usually leave taxable income unchanged but "
            "occasionally generate extreme adjustments. These outputs do not identify "
            "human behavior and do not support using an LLM as an ETI estimator. They "
            "instead show that model-implied tax responses are highly model- and "
            "summary-dependent, and that prompt rendering, incomplete archive coverage, and "
            "tail behavior are first-order design choices."
        ),
    )
    _write("hero_metrics.html", _hero_metrics(summary, len(analysis_ids)))
    _write(
        "sample_flow.html",
        _sample_flow(
            len(scenarios), len(balanced_ids), len(identified_ids), len(analysis_ids)
        ),
    )

    manifest = {
        "analysis": "llm_eti.study2",
        "scenario_count": len(scenarios),
        "archived_response_row_count": source_record_count,
        "deduplicated_analysis_row_count": len(results),
        "balanced_primary_scenario_count": len(balanced_ids),
        "identified_balanced_scenario_count": len(identified_ids),
        "primary_analysis_scenario_count": len(analysis_ids),
        "primary_cluster_count": int(summary["n_clusters"].min()),
        "source_sha256": _source_hashes(),
        "completion": completion.to_dict(orient="records"),
        "main_results": summary.to_dict(orient="records"),
        "sensitivity": sensitivity.to_dict(orient="records"),
    }
    (GENERATED_DIR / "analysis_summary.json").write_text(
        json.dumps(_canonicalize_json(manifest), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    _plot_completion(completion)
    _plot_slopes(summary)
    _plot_response_patterns(results, analysis_ids)
    _plot_social_card(summary)
    print(
        f"Generated publication artifacts from {source_record_count:,} archived rows "
        f"({len(results):,} unique analysis rows; "
        f"{len(analysis_ids):,} primary scenarios)."
    )


if __name__ == "__main__":
    main()
