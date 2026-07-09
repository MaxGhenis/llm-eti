from pathlib import Path

import pytest

from llm_eti.study2 import load_study2_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def study_data():
    return load_study2_data(
        ROOT / "data" / "scenarios.csv",
        ROOT / "data" / "responses",
    )
