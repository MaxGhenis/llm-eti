"""Semantic PDF regressions; TeX probes run when a local LuaLaTeX exists."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.check_publication import verify_pdf_text

ROOT = Path(__file__).resolve().parents[1]
LUALATEX = os.environ.get("LUALATEX_BIN") or shutil.which("lualatex")


@pytest.mark.parametrize("broken", [False, True])
@pytest.mark.skipif(not LUALATEX, reason="LuaLaTeX is unavailable")
def test_template_rejects_color_selection_that_typesets_text(tmp_path, broken):
    injection = (
        r"\ExplSyntaxOn\cs_set_protected:Npn\color_select:n#1{0.0~0.0~1.0}\ExplSyntaxOff"
        if broken
        else ""
    )
    source = (
        r"\DocumentMetadata{lang=en,tagging=on}\documentclass{article}"
        + injection
        + (ROOT / "paper/pdf-compatibility.tex").read_text()
        + r"\begin{document}A reference.\end{document}"
    )
    (tmp_path / "probe.tex").write_text(source)
    result = subprocess.run(
        [str(LUALATEX), "-interaction=nonstopmode", "-halt-on-error", "probe.tex"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if broken:
        assert result.returncode != 0
        assert "Incompatible TeX color backend" in result.stdout
    else:
        assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("broken", [False, True])
@pytest.mark.skipif(
    not LUALATEX or not shutil.which("pdftotext"), reason="PDF tools are unavailable"
)
def test_pdf_gate_detects_visible_rgb_operands(tmp_path, broken):
    # This reproduces the actual extracted-text failure, independently of TeX
    # package versions and the preamble guard, and also proves normal text passes.
    text = "0.0 0.0 1.0Reference" if broken else "Reference (2026)"
    (tmp_path / "probe.tex").write_text(
        r"\documentclass{article}\begin{document}" + text + r"\end{document}"
    )
    subprocess.run(
        [str(LUALATEX), "-interaction=nonstopmode", "-halt-on-error", "probe.tex"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        timeout=60,
    )
    if broken:
        with pytest.raises(SystemExit, match="RGB color operands"):
            verify_pdf_text(tmp_path / "probe.pdf")
    else:
        verify_pdf_text(tmp_path / "probe.pdf")
