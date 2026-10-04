"""Explicitly SYNTHETIC DGPs. No human/LLM data, prompts, or external services."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable

from .estimands import ARMS, ENDOWMENTS, DesignError, Observation


def net_pay(tasks: int, schedule: str) -> float:
    if not isinstance(tasks, int) or isinstance(tasks, bool) or tasks < 0:
        raise DesignError("Nonnegative integer tasks required")
    if schedule == "Prog":
        return tasks * (15 if tasks <= 20 else 10)
    if schedule == "Flat25":
        return 15 * tasks
    if schedule == "Flat50":
        return 10 * tasks
    raise DesignError("Unknown schedule")


def effort_cost(q: float, elasticity: float, flat50_optimum: float) -> float:
    """V'(q)=10(q/a)^(1/e), hence uncapped q*(w)=a(w/10)^e."""
    if not math.isfinite(elasticity) or elasticity <= 0:
        raise DesignError("Positive finite structural elasticity required")
    if not math.isfinite(flat50_optimum) or flat50_optimum <= 0:
        raise DesignError("Positive finite productivity scale required")
    if not math.isfinite(q) or q < 0:
        raise DesignError("Finite nonnegative effort required")
    power = 1 + 1 / elasticity
    return float(10 * flat50_optimum / power * (q / flat50_optimum) ** power)


def utility(
    q: int,
    schedule: str,
    elasticity: float,
    flat50_optimum: float,
    fixed_cost: float = 0,
) -> float:
    if not math.isfinite(fixed_cost) or fixed_cost < 0:
        raise DesignError("Nonnegative finite participation cost required")
    return (
        net_pay(q, schedule)
        - effort_cost(q, elasticity, flat50_optimum)
        - (fixed_cost if q > 0 else 0)
    )


def discrete_choice(
    endowment: int,
    schedule: str,
    elasticity: float,
    flat50_optimum: float,
    fixed_cost: float = 0,
) -> int:
    """Enumerate the actual finite menu; exact ties select the lower task count."""
    if endowment not in ENDOWMENTS:
        raise DesignError("Unknown endowment")
    return max(
        range(endowment + 1),
        key=lambda q: utility(q, schedule, elasticity, flat50_optimum, fixed_cost),
    )


def continuous_flat_choice(net_rate: float, elasticity: float, scale: float) -> float:
    """Uncapped, continuous synthetic control experiment, outside PKNF design."""
    if not 0 < net_rate <= 1 or elasticity <= 0 or scale <= 0:
        raise DesignError("Positive DGP inputs required")
    return float(scale * (net_rate / 0.5) ** elasticity)


def panel(
    decision: Callable[[int, str, int, int], int],
    subjects_per_arm: int = 24,
    arms: Iterable[str] = ARMS,
) -> list[Observation]:
    """Synthetic balanced permutation: each E once per phase, reversed post.

    The exact human permutation algorithm was NOT retrieved. This is a named
    reference design for offline validation, not a claim about their archive.
    """
    rows = []
    for arm in arms:
        for subject in range(subjects_per_arm):
            for phase in (0, 1):
                caps = ENDOWMENTS if phase == 0 else ENDOWMENTS[::-1]
                for index, cap in enumerate(caps):
                    schedule = ARMS[arm][phase]
                    rows.append(
                        Observation(
                            f"{arm}:{subject:03d}",
                            arm,
                            8 * phase + index + 1,
                            cap,
                            decision(subject, schedule, phase, cap),
                        )
                    )
    return rows


def no_response_panel() -> list[Observation]:
    """Schedule-blind fixed effort targets, including zero and cap choices."""
    return panel(
        lambda subject, schedule, phase, cap: min(
            cap, (0, 4, 10, 20, 30, 8)[subject % 6]
        )
    )


def known_response_panel() -> list[Observation]:
    """e=1, all active, flat50 q=6 and flat25/progressive q=9, all interior."""
    return panel(
        lambda subject, schedule, phase, cap: discrete_choice(cap, schedule, 1, 6)
    )


def participation_panel() -> list[Observation]:
    """e=1 for everyone; half active, quarter exit at 50%, quarter always zero."""
    return panel(
        lambda subject, schedule, phase, cap: discrete_choice(
            cap, schedule, 1, 6, (0, 0, 45, 1000)[subject % 4]
        )
    )


def equivalence_panel(elasticity: float) -> list[Observation]:
    """Any positive e: flat choices E, Prog choices min(E,20), 25% always zero."""
    return panel(
        lambda subject, schedule, phase, cap: discrete_choice(
            cap, schedule, elasticity, 60, 1000 if subject % 4 == 0 else 0
        )
    )


def dominance_table() -> list[dict]:
    return [
        {
            "endowment_tasks": cap,
            "gross_cap_cents": 20 * cap,
            "above_notch_tasks": list(range(21, cap + 1)),
            "strictly_lower_consumption_than_q20": [
                q for q in range(21, cap + 1) if net_pay(q, "Prog") < 300
            ],
            "equal_consumption_more_work_than_q20": [
                q for q in range(21, cap + 1) if net_pay(q, "Prog") == 300
            ],
            "strictly_higher_consumption_than_q20": [
                q for q in range(21, cap + 1) if net_pay(q, "Prog") > 300
            ],
        }
        for cap in ENDOWMENTS
    ]
