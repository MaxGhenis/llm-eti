#!/usr/bin/env python3
"""Render the Quarto microsite, web paper, PDF, and retained TeX source."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = ROOT / "_site"
PAPER_DIR = ROOT / "paper"
PUBLIC_PAPER_DIR = SITE_DIR / "paper"
DOWNLOADS_DIR = SITE_DIR / "downloads"
PAPER_URL = "https://maxghenis.github.io/llm-eti/paper/"
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
REQUIRED_QUARTO_VERSION = "1.9.38"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(command: list[str], *, cwd: Path) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True, env=os.environ.copy())


def _find_quarto() -> str:
    configured = os.environ.get("QUARTO_BIN")
    if configured:
        path = Path(configured).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"QUARTO_BIN does not exist: {path}")
        return str(path)
    quarto = shutil.which("quarto")
    if quarto is None:
        raise SystemExit(
            f"Quarto is required; expected version {REQUIRED_QUARTO_VERSION}."
        )
    return quarto


def _copy_named_artifact(source_candidates: list[Path], destination: Path) -> Path:
    source = next((path for path in source_candidates if path.is_file()), None)
    if source is None:
        candidates = ", ".join(
            str(path.relative_to(ROOT)) for path in source_candidates
        )
        raise SystemExit(f"Missing rendered artifact; checked {candidates}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def _write_source_bundle(tex: Path, destination: Path) -> None:
    """Create a deterministic, directly compilable TeX source bundle."""

    files = [
        (tex, Path("llm-eti.tex")),
        (PAPER_DIR / "references.bib", Path("references.bib")),
        *[
            (figure, Path("figures") / figure.name)
            for figure in sorted((PUBLIC_PAPER_DIR / "figures").glob("*.png"))
        ],
    ]
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, archive_path in files:
            info = zipfile.ZipInfo(os.fspath(archive_path), (2026, 7, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())


def _add_paper_to_sitemap() -> None:
    """Add the separately rendered manuscript to Quarto's root sitemap."""

    sitemap = SITE_DIR / "sitemap.xml"
    if not sitemap.is_file():
        raise SystemExit("Quarto did not produce _site/sitemap.xml")

    ET.register_namespace("", SITEMAP_NAMESPACE)
    tree = ET.parse(sitemap)
    root = tree.getroot()
    url_tag = f"{{{SITEMAP_NAMESPACE}}}url"
    loc_tag = f"{{{SITEMAP_NAMESPACE}}}loc"
    entries = list(root.findall(url_tag))
    paper_entries = [entry for entry in entries if entry.findtext(loc_tag) == PAPER_URL]
    if not paper_entries:
        paper_entry = ET.Element(url_tag)
        ET.SubElement(paper_entry, loc_tag).text = PAPER_URL
        entries.append(paper_entry)
    elif len(paper_entries) > 1:
        first_paper_entry = paper_entries[0]
        entries = [
            entry
            for entry in entries
            if entry.findtext(loc_tag) != PAPER_URL or entry is first_paper_entry
        ]

    for entry in list(root):
        root.remove(entry)
    root.extend(sorted(entries, key=lambda entry: entry.findtext(loc_tag) or ""))
    ET.indent(tree, space="  ")
    tree.write(sitemap, encoding="utf-8", xml_declaration=True)


def main() -> None:
    quarto = _find_quarto()
    quarto_version = subprocess.run(
        [quarto, "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if quarto_version != REQUIRED_QUARTO_VERSION:
        if os.environ.get("ALLOW_QUARTO_VERSION_MISMATCH") != "1":
            raise SystemExit(
                f"Publication rendering requires Quarto {REQUIRED_QUARTO_VERSION}, "
                f"found {quarto_version}. Set ALLOW_QUARTO_VERSION_MISMATCH=1 to "
                "explicitly opt out."
            )
        print(f"Warning: rendering with opted-out Quarto {quarto_version}.")

    _run([sys.executable, "scripts/generate_artifacts.py"], cwd=ROOT)

    shutil.rmtree(SITE_DIR, ignore_errors=True)
    _run([quarto, "render"], cwd=ROOT)
    _run([quarto, "render"], cwd=PAPER_DIR)
    (PAPER_DIR / "index-luamml-mathml.html").unlink(missing_ok=True)
    _add_paper_to_sitemap()

    if not (PUBLIC_PAPER_DIR / "index.html").is_file():
        raise SystemExit("Quarto did not produce _site/paper/index.html")

    pdf = _copy_named_artifact(
        [PUBLIC_PAPER_DIR / "index.pdf", PAPER_DIR / "index.pdf"],
        PUBLIC_PAPER_DIR / "llm-eti.pdf",
    )
    tex = _copy_named_artifact(
        [
            PUBLIC_PAPER_DIR / "index.tex",
            PUBLIC_PAPER_DIR / "_tex" / "index.tex",
            PAPER_DIR / "index.tex",
        ],
        PUBLIC_PAPER_DIR / "llm-eti.tex",
    )
    source_bundle = PUBLIC_PAPER_DIR / "llm-eti-source.zip"
    _write_source_bundle(tex, source_bundle)

    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        PAPER_DIR / "generated" / "analysis_summary.json",
        DOWNLOADS_DIR / "analysis_summary.json",
    )
    shutil.copy2(
        ROOT / "data" / "run_manifest.json",
        DOWNLOADS_DIR / "run_manifest.json",
    )
    (SITE_DIR / ".nojekyll").touch()

    build_manifest = {
        "quarto_version": quarto_version,
        "outputs": {
            "paper/index.html": _sha256(PUBLIC_PAPER_DIR / "index.html"),
            "paper/llm-eti.pdf": _sha256(pdf),
            "paper/llm-eti.tex": _sha256(tex),
            "paper/llm-eti-source.zip": _sha256(source_bundle),
            "downloads/analysis_summary.json": _sha256(
                DOWNLOADS_DIR / "analysis_summary.json"
            ),
            "downloads/run_manifest.json": _sha256(DOWNLOADS_DIR / "run_manifest.json"),
        },
    }
    (DOWNLOADS_DIR / "publication_manifest.json").write_text(
        json.dumps(build_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Rendered publication with Quarto {quarto_version} into {SITE_DIR}")


if __name__ == "__main__":
    main()
