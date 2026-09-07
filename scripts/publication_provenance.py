"""Bind a release to clean Git source and explicitly hashed generated figures."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# These are the generator's platform-dependent outputs, not a directory-wide
# exemption for arbitrary source or new files. Text and numeric artifacts must
# still match HEAD. Figure bytes are attested separately and checked structurally.
PLATFORM_GENERATED_PATHS = frozenset(
    f"paper/figures/{stem}.{extension}"
    for stem in ("completion_by_model", "model_response_slopes", "response_patterns")
    for extension in ("png", "svg", "pdf")
) | {"assets/social-card.png"}
GENERATED_TEXT_PATHS = ("paper/generated", "paper/_variables.yml")


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True
    ).stdout


def _paths(output: bytes) -> set[str]:
    return {os.fsdecode(path) for path in output.split(b"\0") if path}


def verify_generated_text(root: Path) -> None:
    """Reject both index and worktree drift, including staged-then-reverted edits."""
    for comparison in ((), ("--cached",)):
        changed = _paths(
            _git(
                root,
                "diff",
                *comparison,
                "--name-only",
                "-z",
                "HEAD",
                "--",
                *GENERATED_TEXT_PATHS,
            )
        )
        if changed:
            raise SystemExit(
                "Generated publication text differs from HEAD "
                f"({'index' if comparison else 'worktree'}): {sorted(changed)}"
            )
    untracked = _paths(
        _git(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            *GENERATED_TEXT_PATHS,
        )
    )
    if untracked:
        raise SystemExit(f"Untracked generated publication text: {sorted(untracked)}")


def source_attestation(root: Path) -> dict[str, object]:
    """Require clean tracked source before claiming that HEAD reproduces a build.

    Only modifications to the ten named, committed generated images are allowed.
    New, deleted, renamed, or type-changed images are source changes too. Checking
    the index independently catches staged edits even if the worktree equals HEAD.
    """
    commit = _git(root, "rev-parse", "HEAD").decode().strip()
    tracked = _paths(_git(root, "ls-tree", "-r", "--name-only", "-z", "HEAD"))
    dirty = _paths(_git(root, "ls-files", "--others", "--exclude-standard", "-z"))
    for comparison in ((), ("--cached",)):
        changed = _paths(
            _git(root, "diff", *comparison, "--name-only", "-z", "HEAD", "--")
        )
        non_modifications = _paths(
            _git(
                root,
                "diff",
                *comparison,
                "--name-only",
                "-z",
                "--diff-filter=ACDRTUXB",
                "HEAD",
                "--",
            )
        )
        dirty.update(changed - PLATFORM_GENERATED_PATHS)
        dirty.update(non_modifications)
    if dirty:
        raise SystemExit(
            "Publication requires clean source against HEAD (index and worktree). "
            f"Commit or restore these paths before rendering: {sorted(dirty)}"
        )
    source_hashes: dict[str, str] = {}
    figure_hashes: dict[str, str] = {}
    for relative_path in sorted(tracked):
        path = root / relative_path
        if path.is_symlink() or not path.is_file():
            raise SystemExit(
                f"Publication source must be a regular file: {relative_path}"
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        destination = (
            figure_hashes
            if relative_path in PLATFORM_GENERATED_PATHS
            else source_hashes
        )
        destination[relative_path] = digest
    return {
        "git_commit_sha": commit,
        "git_source_state": "clean",
        "source_sha256": source_hashes,
        "platform_generated_sha256": figure_hashes,
    }


if __name__ == "__main__":
    source_attestation(ROOT)
    print("Publication source is clean against HEAD.")
