"""Offline reference estimands for complete subject/endowment panels.

No data collection, model calls, density extrapolation, or structural notch ETI.
All uncertainty is conditional on independently generated/assigned subjects.
See SPECIFICATION.md for the estimand, restrictions, and nonidentification rules.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, TypeGuard, cast

ENDOWMENTS = (14, 16, 20, 21, 22, 24, 25, 30)
ARMS = {
    "Prog,Prog": ("Prog", "Prog"),
    "Prog,Flat25": ("Prog", "Flat25"),
    "Prog,Flat50": ("Prog", "Flat50"),
    "Flat25,Prog": ("Flat25", "Prog"),
    "Flat50,Prog": ("Flat50", "Prog"),
}
METRICS = {
    "tasks",
    "gross_cents",
    "utilization",
    "participation",
    "at_cap",
    "at_notch",
    "above_notch",
    "log_gross",
}


class DesignError(ValueError):
    """Invalid or unsupported data/design; never silently remove observations."""


@dataclass(frozen=True)
class Observation:
    subject: str
    arm: str
    round: int
    endowment: int
    tasks: int | None

    @property
    def phase(self) -> int:
        return int(self.round > 8)


@dataclass(frozen=True)
class SubjectSummary:
    subject: str
    arm: str
    pre: float | None
    post: float | None


@dataclass(frozen=True)
class Estimate:
    value: float | None
    reason: str | None = None


def _integer(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_observations(rows: Sequence[Observation]) -> None:
    if not rows:
        raise DesignError("No observations")
    keys: set[tuple[str, int]] = set()
    subject_arms: dict[str, str] = {}
    for row in rows:
        if not isinstance(row.subject, str) or not row.subject:
            raise DesignError("Subject must be a nonempty globally unique string")
        if row.arm not in ARMS:
            raise DesignError(f"Unknown arm: {row.arm}")
        if not _integer(row.round) or not 1 <= row.round <= 16:
            raise DesignError("Round must be an integer from 1 to 16")
        if not _integer(row.endowment) or row.endowment not in ENDOWMENTS:
            raise DesignError("Endowment must be in the original eight-value support")
        if not _integer(row.tasks) or not 0 <= row.tasks <= row.endowment:
            raise DesignError(
                "Missing/invalid tasks are not zero: require integer 0..E"
            )
        key = (row.subject, row.round)
        if key in keys:
            raise DesignError(f"Duplicate subject-round: {key}")
        keys.add(key)
        if row.subject in subject_arms and subject_arms[row.subject] != row.arm:
            raise DesignError("One independent subject cannot have two assigned arms")
        subject_arms[row.subject] = row.arm


def target_weights(endowments: Iterable[int] = ENDOWMENTS) -> dict[int, float]:
    support = tuple(endowments)
    if not support or len(support) != len(set(support)):
        raise DesignError("Target support must be nonempty and unique")
    if any(not _integer(e) or e not in ENDOWMENTS for e in support):
        raise DesignError("Unknown target endowment")
    return {e: 1 / len(support) for e in support}


def _check_weights(weights: Mapping[int, float]) -> None:
    if not weights or any(
        not _integer(e)
        or e not in ENDOWMENTS
        or not isinstance(w, int | float)
        or isinstance(w, bool)
        or not math.isfinite(w)
        or w <= 0
        for e, w in weights.items()
    ):
        raise DesignError("Weights require known endowments and finite positive mass")
    if not math.isclose(math.fsum(weights.values()), 1, abs_tol=1e-12, rel_tol=0):
        raise DesignError("Prespecified target weights must sum to one")


def outcome(row: Observation, metric: str) -> float | None:
    q, e = row.tasks, row.endowment
    if not _integer(q):
        raise DesignError("Missing/invalid tasks cannot be an outcome")
    if metric == "log_gross":
        return math.log(20 * q) if q > 0 else None
    return {
        "tasks": q,
        "gross_cents": 20 * q,
        "utilization": q / e,
        "participation": float(q > 0),
        "at_cap": float(q == e),
        "at_notch": float(q == 20),
        "above_notch": float(q > 20),
    }[metric]


def summarize(
    rows: Sequence[Observation],
    metric: str,
    weights: Mapping[int, float] | None = None,
) -> tuple[list[SubjectSummary], dict]:
    """Equal subjects, fixed cap weights, equal rounds within subject/phase/cap.

    A complete selected subject x phase x cap grid is required. We do not
    reweight surviving cells or invent the original randomization algorithm.
    `at_notch` and `above_notch` require E>20 to separate notch choice from caps.
    """
    validate_observations(rows)
    if metric not in METRICS:
        raise DesignError(f"Unknown outcome: {metric}")
    if weights is None:
        weights = (
            target_weights(e for e in ENDOWMENTS if e > 20)
            if metric in {"at_notch", "above_notch"}
            else target_weights()
        )
    _check_weights(weights)
    if metric in {"at_notch", "above_notch"} and any(e <= 20 for e in weights):
        raise DesignError("Notch-choice outcomes require target endowments E>20")
    groups: dict[str, list[Observation]] = defaultdict(list)
    for row in rows:
        groups[row.subject].append(row)
    summaries = []
    audit: dict[str, Any] = {
        "metric": metric,
        "target_weights": dict(weights),
        "rows_total": len(rows),
        "rows_in_target": 0,
        "zero_rows_in_target": 0,
        "cap_rows_in_target": 0,
        "subjects": len(groups),
        "subjects_by_arm": dict(Counter(group[0].arm for group in groups.values())),
        "undefined_log_cells": 0,
        "complete_selected_grid_required": True,
    }
    for subject, group in sorted(groups.items()):
        phase_values: list[float | None] = []
        for phase in (0, 1):
            terms = []
            undefined = False
            for cap, weight in sorted(weights.items()):
                cell = [r for r in group if r.phase == phase and r.endowment == cap]
                if not cell:
                    raise DesignError(
                        f"Incomplete selected grid: subject={subject}, phase={phase}, E={cap}"
                    )
                audit["rows_in_target"] += len(cell)
                audit["zero_rows_in_target"] += sum(r.tasks == 0 for r in cell)
                audit["cap_rows_in_target"] += sum(r.tasks == cap for r in cell)
                values = [outcome(r, metric) for r in cell]
                if any(v is None for v in values):
                    undefined = True
                    audit["undefined_log_cells"] += 1
                else:
                    terms.append(weight * statistics.fmean(cast(list[float], values)))
            phase_values.append(None if undefined else math.fsum(terms))
        summaries.append(SubjectSummary(subject, group[0].arm, *phase_values))
    return summaries, audit


def _arm_values(
    summaries: Sequence[SubjectSummary],
    arm: str,
) -> list[SubjectSummary]:
    return [s for s in summaries if s.arm == arm]


def _contrast_groups(
    treated: Sequence[SubjectSummary],
    control: Sequence[SubjectSummary],
    contrast: str,
    scale: str,
) -> Estimate:
    if contrast not in {"did", "post"} or scale not in {"level", "log_of_mean"}:
        raise DesignError("Use contrast did/post and scale level/log_of_mean")
    if not treated or not control:
        return Estimate(None, "missing_arm")
    phases = ("pre", "post") if contrast == "did" else ("post",)
    cells = {}
    for label, group in (("treated", treated), ("control", control)):
        for phase in phases:
            values = [getattr(s, phase) for s in group]
            if any(v is None for v in values):
                return Estimate(None, "undefined_outcome_zero_in_log_sample")
            if any(not math.isfinite(v) for v in values):
                raise DesignError("Nonfinite subject outcome")
            value = statistics.fmean(values)
            if scale == "log_of_mean":
                if value <= 0:
                    return Estimate(None, "nonpositive_cell_mean")
                value = math.log(value)
            cells[label, phase] = value
    if contrast == "post":
        return Estimate(cells["treated", "post"] - cells["control", "post"])
    return Estimate(
        (cells["treated", "post"] - cells["treated", "pre"])
        - (cells["control", "post"] - cells["control", "pre"])
    )


def estimate(
    summaries: Sequence[SubjectSummary],
    treated: str,
    control: str = "Prog,Prog",
    contrast: str = "did",
    scale: str = "level",
) -> Estimate:
    if treated == control or treated not in ARMS or control not in ARMS:
        raise DesignError("Specify two distinct, known treatment arms")
    if len({s.subject for s in summaries}) != len(summaries):
        raise DesignError("Subject summaries must be unique before resampling")
    return _contrast_groups(
        _arm_values(summaries, treated),
        _arm_values(summaries, control),
        contrast,
        scale,
    )


def net_of_tax_log_change(tax_before: float, tax_after: float) -> float:
    for rate in (tax_before, tax_after):
        if isinstance(rate, bool) or not math.isfinite(rate) or not 0 <= rate < 1:
            raise DesignError("Tax rates must be finite fractions in [0,1)")
    return math.log((1 - tax_after) / (1 - tax_before))


def normalize_log_effect(effect: Estimate, denominator: float) -> Estimate:
    """Algebra only: caller must establish a common price shock and population.

    Never interpret a utilization-level coefficient as a log-income coefficient.
    A defined result is a normalized finite contrast, not an automatic ETI claim.
    """
    if not math.isfinite(denominator):
        raise DesignError("Nonfinite log net-of-tax denominator")
    if denominator == 0:
        return Estimate(None, "zero_log_net_of_tax_change")
    if effect.value is None:
        return effect
    return Estimate(effect.value / denominator)


def quantile(values: Sequence[float], probability: float) -> float:
    if not values or not 0 <= probability <= 1:
        raise DesignError("Quantile requires values and probability in [0,1]")
    values = sorted(values)
    position = (len(values) - 1) * probability
    lo, hi = math.floor(position), math.ceil(position)
    return values[lo] + (position - lo) * (values[hi] - values[lo])


def cluster_bootstrap(
    summaries: Sequence[SubjectSummary],
    treated: str,
    control: str = "Prog,Prog",
    contrast: str = "did",
    scale: str = "level",
    *,
    draws: int = 999,
    seed: int = 20260907,
    independent_subjects_confirmed: bool = False,
    denominator: float | None = None,
) -> dict:
    """Stratify by arm, resample whole subject vectors, preserve paired phases.

    Duplicate draws retain multiplicity: never regroup them under source IDs.
    Any undefined replicate suppresses the interval rather than conditioning
    it on successful/positive replicates. All attempted draws are returned.
    """
    if independent_subjects_confirmed is not True:
        raise DesignError("Establish independent subject units before inference")
    if not _integer(draws) or draws < 2 or not _integer(seed):
        raise DesignError("At least two draws and an integer seed are required")
    point = estimate(summaries, treated, control, contrast, scale)
    arms = [_arm_values(summaries, a) for a in (treated, control)]
    if any(len(group) < 2 for group in arms):
        raise DesignError("At least two independent subjects per arm are required")
    if denominator is not None:
        point = normalize_log_effect(point, denominator)
    rng = random.Random(seed)
    attempted: list[float | None] = []
    reasons: Counter = Counter()
    for _ in range(draws):
        resampled = [
            [group[rng.randrange(len(group))] for _ in range(len(group))]
            for group in arms
        ]
        value = _contrast_groups(resampled[0], resampled[1], contrast, scale)
        if denominator is not None:
            value = normalize_log_effect(value, denominator)
        attempted.append(value.value)
        if value.value is None:
            reasons[value.reason] += 1
    defined = [v for v in attempted if v is not None]
    interval_available = point.value is not None and not reasons
    return {
        "point": asdict(point),
        "seed": seed,
        "draws_requested": draws,
        "unit": "independent_subject",
        "stratification": "arm",
        "subjects_per_arm": {
            a: len(g) for a, g in zip((treated, control), arms, strict=False)
        },
        "contrast": contrast,
        "scale": scale,
        "log_net_denominator": denominator,
        "draws": attempted,
        "defined_draws": len(defined),
        "undefined_draws": draws - len(defined),
        "undefined_reasons": dict(reasons),
        "negative_draws": sum(v < 0 for v in defined),
        "zero_draws": sum(v == 0 for v in defined),
        "positive_draws": sum(v > 0 for v in defined),
        "ci_percentile_95": (
            [quantile(defined, 0.025), quantile(defined, 0.975)]
            if interval_available
            else None
        ),
        "bootstrap_se": statistics.stdev(defined) if interval_available else None,
        "interval_status": (
            "available"
            if interval_available
            else "withheld_undefined_point_or_draws_no_conditioning"
        ),
        "structural_eti_identified": False,
    }


def notch_identification() -> dict:
    """Design-level decision. This intentionally does not take bunching data."""
    return {
        "identified": False,
        "estimate": None,
        "lower_bound": None,
        "upper_bound": None,
        "threshold_cents": 400,
        "dominated_width_cents": 200,
        "maximum_cap_cents": 600,
        "above_dominated_support": False,
        "reason": "No observed interior marginal buncher; discrete capped support; see METHODS.md",
    }


def kw_formula_demonstration(relative_response: float) -> dict:
    """Display source algebra, never estimate an elasticity from observations."""
    if not math.isfinite(relative_response) or relative_response < 0:
        raise DesignError("Demonstration response must be finite and nonnegative")
    scaled_square = relative_response**2 / (0.25 / 0.75)
    return {
        "relative_response_input": relative_response,
        "kw_equation12_rhs": scaled_square,
        "kleven2018_equation4_rhs": scaled_square / 2,
        "kleven2018_equation5_rhs": scaled_square / (2 + relative_response),
        "valid_estimate_for_pknf": False,
    }
