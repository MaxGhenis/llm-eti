"""Read the committed synthetic CSV and replay summaries without DGP generation.

This fixture loader intentionally requires synthetic=true. It is not a human
or LLM data adapter and never guesses the experimental identity of real rows.
"""

import csv
from collections import defaultdict
from typing import TextIO

from .estimands import DesignError, Observation, validate_observations

FIELDS = ["synthetic", "dgp", "subject", "arm", "round", "endowment", "tasks"]


def read_synthetic_panels(stream: TextIO) -> dict[str, list[Observation]]:
    reader = csv.DictReader(stream)
    if reader.fieldnames != FIELDS:
        raise DesignError("Expected exact synthetic fixture CSV header")
    panels: dict[str, list[Observation]] = defaultdict(list)
    for line, raw in enumerate(reader, start=2):
        if None in raw or any(v is None for v in raw.values()):
            raise DesignError(f"Malformed CSV row {line}")
        if raw["synthetic"] != "true" or not raw["dgp"].startswith("synthetic_"):
            raise DesignError(f"Row {line} is not explicitly synthetic")
        try:
            row = Observation(
                raw["subject"],
                raw["arm"],
                int(raw["round"]),
                int(raw["endowment"]),
                int(raw["tasks"]),
            )
        except ValueError as exc:
            raise DesignError(f"Invalid integer field on row {line}") from exc
        panels[raw["dgp"]].append(row)
    if not panels:
        raise DesignError("Empty fixture CSV")
    for rows in panels.values():
        validate_observations(rows)
    return dict(panels)
