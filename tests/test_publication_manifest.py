import hashlib
import json
import platform
import subprocess
from pathlib import Path

import pytest

from scripts import check_publication, render_publication
from scripts.check_publication import _verify_publication_manifest
from scripts.render_publication import (
    MANIFEST_OUTPUT_PATHS,
    REQUIRED_QUARTO_VERSION,
    _build_manifest,
)


@pytest.fixture(autouse=True)
def isolated_source(git_source, monkeypatch):
    monkeypatch.setattr(render_publication, "ROOT", git_source)
    monkeypatch.setattr(check_publication, "ROOT", git_source)
    return git_source


def test_build_manifest_records_source_and_environment_attestations(isolated_source):
    root = isolated_source
    outputs = {"paper/example.pdf": "a" * 64}
    manifest = _build_manifest(REQUIRED_QUARTO_VERSION, outputs)
    git_commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert manifest == {
        "git_commit_sha": git_commit_sha,
        "git_source_state": "clean",
        "source_sha256": {
            path.relative_to(root)
            .as_posix(): hashlib.sha256(path.read_bytes())
            .hexdigest()
            for path in root.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and path.relative_to(root).as_posix()
            != "paper/figures/model_response_slopes.png"
        },
        "platform_generated_sha256": {
            "paper/figures/model_response_slopes.png": hashlib.sha256(
                b"figure"
            ).hexdigest()
        },
        "operating_system": platform.platform(),
        "outputs": outputs,
        "pyproject_toml_sha256": hashlib.sha256(
            (root / "pyproject.toml").read_bytes()
        ).hexdigest(),
        "python_version": platform.python_version(),
        "quarto_version": REQUIRED_QUARTO_VERSION,
        "uv_lock_sha256": hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest(),
    }


def _write_site_and_manifest(site_dir: Path) -> tuple[Path, dict[str, object]]:
    outputs = {}
    for index, relative_path in enumerate(MANIFEST_OUTPUT_PATHS):
        output_path = site_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(f"output-{index}".encode())
        outputs[relative_path] = hashlib.sha256(output_path.read_bytes()).hexdigest()
    manifest = _build_manifest(REQUIRED_QUARTO_VERSION, outputs)
    manifest_path = site_dir / "downloads" / "publication_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, manifest


def test_publication_manifest_verifies_every_output_hash(tmp_path: Path):
    manifest_path, _ = _write_site_and_manifest(tmp_path)
    _verify_publication_manifest(manifest_path, tmp_path)

    changed_output = tmp_path / MANIFEST_OUTPUT_PATHS[0]
    changed_output.write_bytes(b"changed")
    with pytest.raises(SystemExit, match="Publication output hash mismatch"):
        _verify_publication_manifest(manifest_path, tmp_path)


def test_publication_manifest_requires_every_attestation(tmp_path: Path):
    manifest_path, manifest = _write_site_and_manifest(tmp_path)
    del manifest["operating_system"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SystemExit, match="lacks attestations"):
        _verify_publication_manifest(manifest_path, tmp_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("git_commit_sha", "0" * 40),
        ("git_source_state", "dirty"),
        ("source_sha256", {}),
        ("platform_generated_sha256", {}),
    ],
)
def test_manifest_is_bound_to_current_head_and_source(tmp_path, field, value):
    manifest_path, manifest = _write_site_and_manifest(tmp_path)
    manifest[field] = value
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(SystemExit, match=f"{field} does not match the build source"):
        _verify_publication_manifest(manifest_path, tmp_path)


def test_committed_manuscript_change_invalidates_old_manifest(
    tmp_path, isolated_source
):
    manifest_path, _ = _write_site_and_manifest(tmp_path)
    (isolated_source / "paper/sections/discussion.md").write_text("New source\n")
    subprocess.run(["git", "add", "."], cwd=isolated_source, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "Change manuscript",
        ],
        cwd=isolated_source,
        check=True,
    )
    with pytest.raises(
        SystemExit, match="git_commit_sha does not match the build source"
    ):
        _verify_publication_manifest(manifest_path, tmp_path)
