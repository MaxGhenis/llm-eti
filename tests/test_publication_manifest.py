import hashlib
import json
import platform
import subprocess
from pathlib import Path

import pytest

from scripts.check_publication import _verify_publication_manifest
from scripts.render_publication import (
    MANIFEST_OUTPUT_PATHS,
    REQUIRED_QUARTO_VERSION,
    ROOT,
    _build_manifest,
)


def test_build_manifest_records_source_and_environment_attestations():
    outputs = {"paper/example.pdf": "a" * 64}
    manifest = _build_manifest(REQUIRED_QUARTO_VERSION, outputs)
    git_commit_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert manifest == {
        "git_commit_sha": git_commit_sha,
        "operating_system": platform.platform(),
        "outputs": outputs,
        "pyproject_toml_sha256": hashlib.sha256(
            (ROOT / "pyproject.toml").read_bytes()
        ).hexdigest(),
        "python_version": platform.python_version(),
        "quarto_version": REQUIRED_QUARTO_VERSION,
        "uv_lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
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
