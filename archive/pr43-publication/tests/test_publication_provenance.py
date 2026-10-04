import hashlib
import subprocess

import pytest

from scripts import render_publication
from scripts.publication_provenance import source_attestation, verify_generated_text


@pytest.mark.parametrize("staged", [False, True])
def test_dirty_manuscript_cannot_claim_clean_head(git_source, monkeypatch, staged):
    manuscript = git_source / "paper/sections/discussion.md"
    manuscript.write_text("Uncommitted manuscript revision\n")
    if staged:
        subprocess.run(["git", "add", str(manuscript)], cwd=git_source, check=True)
    monkeypatch.setattr(render_publication, "ROOT", git_source)
    with pytest.raises(SystemExit, match="clean source against HEAD.*discussion.md"):
        render_publication._build_manifest("1.9.38", {})


def test_renderer_rejects_dirty_source_before_invoking_quarto(git_source, monkeypatch):
    (git_source / "paper/sections/discussion.md").write_text("Dirty\n")
    monkeypatch.setattr(render_publication, "ROOT", git_source)
    monkeypatch.setattr(
        render_publication,
        "_find_quarto",
        lambda: pytest.fail("Must fail before Quarto"),
    )
    with pytest.raises(SystemExit, match="clean source against HEAD"):
        render_publication.main()


@pytest.mark.parametrize("filename", ["generated/abstract.md", "_variables.yml"])
@pytest.mark.parametrize("state", ["unstaged", "staged", "staged_then_reverted"])
def test_generated_text_drift_in_index_or_worktree_is_rejected(
    git_source, filename, state
):
    generated = git_source / "paper" / filename
    original = generated.read_bytes()
    generated.write_text("Changed generated content\n")
    if state != "unstaged":
        subprocess.run(["git", "add", str(generated)], cwd=git_source, check=True)
    if state == "staged_then_reverted":
        generated.write_bytes(original)
    with pytest.raises(
        SystemExit, match="Generated publication text differs from HEAD"
    ):
        verify_generated_text(git_source)
    with pytest.raises(SystemExit, match="clean source against HEAD"):
        source_attestation(git_source)


def test_untracked_manuscript_is_not_attributed_to_head(git_source):
    (git_source / "paper/sections/new section.md").write_text("Uncommitted\n")
    with pytest.raises(SystemExit, match="new section.md"):
        source_attestation(git_source)


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_git_index_optimizations_cannot_hide_dirty_manuscript(git_source, flag):
    manuscript = git_source / "paper/sections/discussion.md"
    subprocess.run(
        ["git", "update-index", flag, str(manuscript)], cwd=git_source, check=True
    )
    manuscript.write_text("Hidden manuscript revision\n")
    with pytest.raises(SystemExit, match="does not match HEAD.*discussion.md"):
        source_attestation(git_source)


def test_untracked_generated_text_is_rejected(git_source):
    (git_source / "paper/generated/new.md").write_text("Uncommitted\n")
    with pytest.raises(SystemExit, match="Untracked generated publication text"):
        verify_generated_text(git_source)


@pytest.mark.parametrize("staged", [False, True])
def test_platform_figure_changes_are_explicitly_hashed(git_source, staged):
    figure = git_source / "paper/figures/model_response_slopes.png"
    figure.write_bytes(b"Platform-specific rasterization")
    if staged:
        subprocess.run(["git", "add", str(figure)], cwd=git_source, check=True)
    attestation = source_attestation(git_source)
    assert attestation["git_source_state"] == "clean"
    assert attestation["platform_generated_sha256"] == {
        "paper/figures/model_response_slopes.png": hashlib.sha256(
            figure.read_bytes()
        ).hexdigest()
    }
    verify_generated_text(git_source)


@pytest.mark.parametrize("change", ["new", "delete", "rename", "symlink"])
def test_figure_exception_does_not_allow_arbitrary_source_changes(git_source, change):
    figure = git_source / "paper/figures/model_response_slopes.png"
    if change == "new":
        (figure.parent / "extra.png").write_bytes(b"untracked")
    elif change == "delete":
        figure.unlink()
    elif change == "rename":
        subprocess.run(
            ["git", "mv", str(figure), str(figure.with_suffix(".svg"))],
            cwd=git_source,
            check=True,
        )
    else:
        figure.unlink()
        figure.symlink_to("../sections/discussion.md")
    with pytest.raises(SystemExit, match="clean source against HEAD"):
        source_attestation(git_source)
