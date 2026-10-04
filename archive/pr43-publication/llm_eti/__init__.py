"""Reproducible analysis for archived LLM taxable-income responses."""

from .study2 import (
    MODEL_SPECS,
    completion_summary,
    load_study2_data,
    model_summary,
    primary_analysis_scenario_ids,
    primary_balanced_scenario_ids,
    sensitivity_summary,
)

__version__ = "0.2.0"

__all__ = [
    "MODEL_SPECS",
    "__version__",
    "completion_summary",
    "load_study2_data",
    "model_summary",
    "primary_analysis_scenario_ids",
    "primary_balanced_scenario_ids",
    "sensitivity_summary",
]
