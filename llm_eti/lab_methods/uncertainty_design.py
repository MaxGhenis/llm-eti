"""Exact finite-DGP coverage audit of independent-subject inference.

SYNTHETIC: each independent subject chooses 8 tasks pre and either 6 or 10
post, with equal probability, repeated at every endowment in that phase.
The two randomized arms have the same distribution: true mean DiD is zero.
Enumerate binomial counts, not new human/model responses or paid compute.
"""

import math
from fractions import Fraction
from statistics import NormalDist

from .estimands import DesignError


def _binomial_numerators(n: int, successes: int) -> list[int]:
    """Conditional bootstrap probabilities have common denominator n**n."""
    return [
        math.comb(n, k) * successes**k * (n - successes) ** (n - k)
        for k in range(n + 1)
    ]


def exact_subject_percentile_interval(
    n: int, k_t: int, k_c: int
) -> tuple[float, float]:
    """Infinite-resample percentile limit, with discrete inverse-CDF quantiles.

    This is distinct from the finite-999-draw, interpolated quantiles used by
    estimands.py. Its purpose is to examine the method without Monte Carlo error.
    """
    if (
        any(not isinstance(v, int) or isinstance(v, bool) for v in (n, k_t, k_c))
        or n < 1
        or not 0 <= k_t <= n
        or not 0 <= k_c <= n
    ):
        raise DesignError("Integer n>=1 and success counts within 0..n required")
    p_t, p_c = _binomial_numerators(n, k_t), _binomial_numerators(n, k_c)
    probabilities = [0] * (2 * n + 1)
    for j, probability_t in enumerate(p_t):
        for k, probability_c in enumerate(p_c):
            probabilities[j - k + n] += probability_t * probability_c
    quantiles = []
    denominator = n ** (2 * n)
    for target_numerator in (1, 39):  # 1/40 = .025; 39/40 = .975 exactly
        cumulative = 0
        for index, probability in enumerate(probabilities):
            cumulative += probability
            if cumulative * 40 >= target_numerator * denominator:
                quantiles.append(4 * (index - n) / n)
                break
        else:
            raise ArithmeticError("Conditional bootstrap PMF did not sum to one")
    return quantiles[0], quantiles[1]


def coverage_audit(
    subjects_per_arm: int = 40, repeated_rounds_per_phase: int = 8
) -> dict:
    n, repeats = subjects_per_arm, repeated_rounds_per_phase
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        raise DesignError("At least two independent subjects per arm required")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise DesignError("At least one repeated observation per phase required")
    zcrit = NormalDist().inv_cdf(0.975)
    counts = {"subject_wald": 0, "naive_row_wald": 0, "subject_percentile_limit": 0}
    variance_total = 0
    probability_denominator = 2 ** (2 * n)
    for k_t in range(n + 1):
        for k_c in range(n + 1):
            ways = math.comb(n, k_t) * math.comb(n, k_c)
            effect = 4 * (k_t - k_c) / n
            variance_numerator = 16 * (k_t * (n - k_t) + k_c * (n - k_c))
            subject_variance = variance_numerator / (n**2 * (n - 1))
            naive_variance = variance_numerator / (n**2 * (repeats * n - 1))
            variance_total += ways * (k_t - k_c) ** 2
            if abs(effect) <= zcrit * math.sqrt(subject_variance):
                counts["subject_wald"] += ways
            if abs(effect) <= zcrit * math.sqrt(naive_variance):
                counts["naive_row_wald"] += ways
            low, high = exact_subject_percentile_interval(n, k_t, k_c)
            if low <= 0 <= high:
                counts["subject_percentile_limit"] += ways
    exact_variance = Fraction(16 * variance_total, n**2 * probability_denominator)
    return {
        "synthetic": True,
        "human_or_llm_validation": False,
        "dgp": "independent_subject_phase_shocks_plus_or_minus_two_tasks",
        "subjects_per_arm": n,
        "rounds_per_phase": repeats,
        "pre_tasks": 8,
        "post_tasks_support": [6, 10],
        "post_probabilities": [0.5, 0.5],
        "true_treatment_effect": 0,
        "true_sampling_variance": float(exact_variance),
        "true_sampling_se": math.sqrt(float(exact_variance)),
        "naive_to_subject_se_ratio_when_variance_positive": math.sqrt(
            (n - 1) / (repeats * n - 1)
        ),
        "nominal_confidence": 0.95,
        "coverage": {
            name: float(Fraction(count, probability_denominator))
            for name, count in counts.items()
        },
        "exact_coverage_fractions": {
            name: str(Fraction(count, probability_denominator))
            for name, count in counts.items()
        },
        "probability_enumeration": "all (n+1)^2 pairs of binomial subject counts; no Monte Carlo sampling",
        "bootstrap_quantile_definition": "inverse discrete CDF using integer probability numerators and exact 1/40,39/40 cutoffs",
        "limitations": "Coverage is DGP-specific; exact percentile limit differs from a finite B=999 bootstrap; Wald intervals use normal critical values. No general coverage guarantee.",
    }
