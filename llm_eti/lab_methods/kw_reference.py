"""Continuous UNCAPPED synthetic reference for KW equation 5.

This numerical exercise supplies a known elasticity and solves for its marginal
buncher. It is NOT an estimator that accepts PKNF observations. Its purpose is
to show the missing support and distinguish structural equality from equation
12/2018 approximations. Source: METHODS.md and SOURCES.md.
"""

import math

from .estimands import DesignError, kw_formula_demonstration


def eq5_residual(
    relative_response: float,
    elasticity: float,
    lower_rate: float = 0.25,
    upper_rate: float = 0.50,
) -> float:
    """KW equation 5 with no pure level notch (ΔT=0), proportional notch Δt>0."""
    if not all(
        math.isfinite(x)
        for x in (relative_response, elasticity, lower_rate, upper_rate)
    ):
        raise DesignError("Finite reference parameters required")
    if relative_response < 0 or elasticity <= 0 or not 0 <= lower_rate < upper_rate < 1:
        raise DesignError("Require r>=0, e>0, and 0<=lower<upper<1")
    inverse_x = 1 / (1 + relative_response)
    net_ratio = (1 - upper_rate) / (1 - lower_rate)
    return float(
        inverse_x
        - elasticity / (1 + elasticity) * inverse_x ** (1 + 1 / elasticity)
        - net_ratio ** (1 + elasticity) / (1 + elasticity)
    )


def marginal_buncher(elasticity: float, threshold: float = 400) -> dict:
    """Bisection in r: equation 5 is strictly decreasing for r>0 at fixed e."""
    if not math.isfinite(threshold) or threshold <= 0:
        raise DesignError("Positive finite threshold required")
    lo, hi = 0.0, 1.0
    eq5_residual(lo, elasticity)  # validate before solving
    for _ in range(100):
        if eq5_residual(hi, elasticity) <= 0:
            break
        hi *= 2
    else:
        raise DesignError("Could not bracket the synthetic marginal buncher")
    for _ in range(160):
        mid = (lo + hi) / 2
        if eq5_residual(mid, elasticity) > 0:
            lo = mid
        else:
            hi = mid
    response = (lo + hi) / 2
    baseline = threshold * (1 + response)
    interior = baseline * (0.5 / 0.75) ** elasticity
    return {
        "synthetic": True,
        "model": "uncapped_continuous_KW_eq5",
        "known_structural_elasticity": elasticity,
        "relative_response": response,
        "counterfactual_marginal_buncher_cents": baseline,
        "post_notch_interior_cents": interior,
        "eq5_residual": eq5_residual(response, elasticity),
        "pknf_maximum_cents": 600,
        "both_relevant_points_outside_pknf_support": min(baseline, interior) > 600,
        "approximation_demonstrations": kw_formula_demonstration(response),
    }


def recover_synthetic_elasticity(
    relative_response: float,
    bracket: tuple[float, float] = (0.01, 5),
) -> float:
    """Invert equation 5 only for the uncapped known-DGP recovery check.

    Bracket is explicit. No cap substitution, empirical bunching input, or
    asserted uniqueness over arbitrary preference/heterogeneity models.
    """
    lo, hi = bracket
    f_lo, f_hi = (
        eq5_residual(relative_response, lo),
        eq5_residual(relative_response, hi),
    )
    if f_lo == 0:
        return lo
    if f_hi == 0:
        return hi
    if f_lo * f_hi > 0:
        raise DesignError("No structural solution in the supplied synthetic bracket")
    for _ in range(160):
        mid = (lo + hi) / 2
        f_mid = eq5_residual(relative_response, mid)
        if f_mid * f_lo > 0:
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return (lo + hi) / 2
