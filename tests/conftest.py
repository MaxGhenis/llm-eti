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


@pytest.fixture
def git_source(tmp_path):
    """Small real Git repo: provenance tests work from a dirty developer checkout."""
    import subprocess

    root = tmp_path / "source"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, content in {
        "paper/sections/discussion.md": b"Committed manuscript\n",
        "paper/generated/abstract.md": b"Committed generated text\n",
        "paper/_variables.yml": b"count: 8095\n",
        "paper/figures/model_response_slopes.png": b"figure",
        "pyproject.toml": b"[project]\n",
        "uv.lock": b"version = 1\n",
    }.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "Publication fixture",
        ],
        cwd=root,
        check=True,
    )
    return root
