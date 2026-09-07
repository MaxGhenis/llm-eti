"""Exact menu exposure and bounded-outcome completion ranges; no ETI bounds."""

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import replace

from .estimands import (
    ARMS,
    ENDOWMENTS,
    METRICS,
    DesignError,
    Observation,
    net_of_tax_log_change,
    summarize,
    target_weights,
    validate_observations,
)


def branch_rate(schedule: str, reference_tasks: float) -> float:
    if not math.isfinite(reference_tasks) or reference_tasks < 0:
        raise DesignError("Finite nonnegative reference tasks required")
    if schedule == "Prog":
        return 0.25 if reference_tasks <= 20 else 0.5
    if schedule in {"Flat25", "Flat50"}:
        return 0.25 if schedule == "Flat25" else 0.5
    raise DesignError("Unknown tax schedule")


def reference_exposure(arm: str, endowment: int, reference_tasks: float) -> dict:
    """Evaluate both menus at a FIXED pre reference; do not select on post choice.

    The caller must save how the reference was constructed and establish
    comparability. Fractional references may be pre means, not actual choices.
    """
    if arm not in ARMS or endowment not in ENDOWMENTS:
        raise DesignError("Known arm and endowment required")
    if (
        isinstance(reference_tasks, bool)
        or not math.isfinite(reference_tasks)
        or not 0 <= reference_tasks <= endowment
    ):
        raise DesignError("Fixed reference must be finite and within the assigned cap")
    before, after = ARMS[arm]
    ratios, changed = [], False
    for q in range(1, endowment + 1):
        c0, c1 = (20 * q * (1 - branch_rate(s, q)) for s in (before, after))
        ratios.append(c1 / c0)
        changed |= c0 != c1
    common = all(math.isclose(r, ratios[0], abs_tol=1e-12, rel_tol=0) for r in ratios)
    t0, t1 = (branch_rate(s, reference_tasks) for s in (before, after))
    return {
        "arm": arm,
        "endowment": endowment,
        "reference_tasks": reference_tasks,
        "menu_exposed": changed,
        "reference_tax_before_cents": 20 * reference_tasks * t0,
        "reference_tax_after_cents": 20 * reference_tasks * t1,
        "reference_tax_change_cents": 20 * reference_tasks * (t1 - t0),
        "reference_branch_log_net_change": (
            net_of_tax_log_change(t0, t1) if reference_tasks > 0 else None
        ),
        "reference_zero": reference_tasks == 0,
        "reference_at_nonsmooth_notch": reference_tasks == 20
        and endowment > 20
        and "Prog" in (before, after),
        "whole_positive_menu_log_scale_change": math.log(ratios[0]) if common else None,
        "structural_eti_identified": False,
    }


def completion_bounds(
    planned_rows: Sequence[Observation],
    metric: str,
    treated: str,
    control: str = "Prog,Prog",
    contrast: str = "did",
    weights: Mapping[int, float] | None = None,
) -> dict:
    """Sharp finite-sample ranges over all feasible missing-task completions.

    Every planned subject/round must be present. tasks=None means unobserved,
    never nonparticipation. No assumptions connect an unknown choice to other
    rounds or impose utility optimization. These are not confidence intervals,
    causal-population intervals, or elasticity bounds. Logs are unsupported.
    """
    if metric not in METRICS - {"log_gross"}:
        raise DesignError("Completion bounds support bounded level outcomes only")
    if contrast not in {"did", "post"}:
        raise DesignError("Use did or post contrast")
    if treated == control or treated not in ARMS or control not in ARMS:
        raise DesignError("Two distinct known arms required")
    if weights is None:
        weights = (
            target_weights(e for e in ENDOWMENTS if e > 20)
            if metric in {"at_notch", "above_notch"}
            else target_weights()
        )
    # Validate design and all OBSERVED q without dropping the unknown records.
    # q=0 below is an extremal completion, not an imputation/analysis response.
    low_rows = [replace(r, tasks=0) if r.tasks is None else r for r in planned_rows]
    validate_observations(low_rows)
    high_rows = []
    for row in planned_rows:
        if row.tasks is None:
            q = (
                20
                if metric == "at_notch"
                else 21 if metric == "above_notch" else row.endowment
            )
            # Rows outside selected caps play no role in the bound, but still
            # must be valid to pass the shared design validator.
            high_rows.append(replace(row, tasks=min(q, row.endowment)))
        else:
            high_rows.append(row)
    low_summaries, _ = summarize(low_rows, metric, weights)
    high_summaries, _ = summarize(high_rows, metric, weights)
    groups = {}
    for bound, summaries in (("low", low_summaries), ("high", high_summaries)):
        for arm in (treated, control):
            group = [s for s in summaries if s.arm == arm]
            if not group:
                raise DesignError(
                    "Both arms must occur in the complete planned inventory"
                )
            for phase in ("pre", "post"):
                groups[bound, arm, phase] = statistics.fmean(
                    getattr(s, phase) for s in group
                )
    coefficients = [(treated, "post", 1), (control, "post", -1)]
    if contrast == "did":
        coefficients += [(treated, "pre", -1), (control, "pre", 1)]
    lower = math.fsum(
        sign * groups["low" if sign > 0 else "high", arm, phase]
        for arm, phase, sign in coefficients
    )
    upper = math.fsum(
        sign * groups["high" if sign > 0 else "low", arm, phase]
        for arm, phase, sign in coefficients
    )
    relevant = [
        r
        for r in planned_rows
        if r.arm in {treated, control}
        and r.endowment in weights
        and (contrast == "did" or r.phase == 1)
    ]
    return {
        "metric": metric,
        "contrast": contrast,
        "treated": treated,
        "control": control,
        "target_weights": dict(weights),
        "lower": lower,
        "upper": upper,
        "planned_rows_in_contrast": len(relevant),
        "missing_rows_in_contrast": sum(r.tasks is None for r in relevant),
        "observed_zero_rows_in_contrast": sum(r.tasks == 0 for r in relevant),
        "interpretation": "sharp_finite_sample_completion_range_given_caps_and_inventory",
        "confidence_interval": False,
        "elasticity_bound": False,
    }
