#!/usr/bin/env python3
"""Fail a release build on stale, missing, or placeholder publication assets."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from render_publication import PAPER_URL, REQUIRED_QUARTO_VERSION, SITEMAP_NAMESPACE

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
SITE = ROOT / "_site"
SOCIAL_IMAGE_URL = "https://maxghenis.github.io/llm-eti/assets/social-card.png"


class _LocalReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attribute = (
            "href"
            if tag in {"a", "link"}
            else (
                "src"
                if tag
                in {
                    "img",
                    "script",
                    "iframe",
                }
                else None
            )
        )
        if attribute is None:
            return
        values = dict(attrs)
        if values.get(attribute):
            self.references.append(values[attribute] or "")


class _DocumentMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.main_landmarks = 0
        self.skip_targets: list[str] = []
        self.canonical_urls: list[str] = []
        self.metadata: defaultdict[str, list[str]] = defaultdict(list)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "main" or values.get("role") == "main":
            self.main_landmarks += 1
        if tag == "a" and "skip-link" in (values.get("class") or "").split():
            if values.get("href"):
                self.skip_targets.append(values["href"] or "")
        if tag == "link" and "canonical" in (values.get("rel") or "").split():
            if values.get("href"):
                self.canonical_urls.append(values["href"] or "")
        if tag == "meta" and values.get("content"):
            key = values.get("property") or values.get("name")
            if key:
                self.metadata[key].append(values["content"] or "")


def _missing_local_references(html_path: Path) -> list[str]:
    parser = _LocalReferenceParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    missing = []
    for reference in parser.references:
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or reference.startswith(("#", "mailto:")):
            continue
        path_text = unquote(parsed.path)
        if not path_text:
            continue
        if path_text.startswith("/"):
            candidate = SITE / path_text.lstrip("/")
        else:
            candidate = html_path.parent / path_text
        if path_text.endswith("/"):
            candidate /= "index.html"
        if not candidate.exists():
            missing.append(reference)
    return sorted(set(missing))


def main() -> None:
    required = [
        PAPER / "generated" / "analysis_summary.json",
        PAPER / "generated" / "abstract.md",
        PAPER / "generated" / "boundary_by_direction.md",
        PAPER / "generated" / "positivity_selection_balance.md",
        PAPER / "generated" / "positivity_selection_narrative.md",
        PAPER / "generated" / "main_narrative.md",
        PAPER / "generated" / "primary_panel.md",
        PAPER / "generated" / "regression_details.md",
        PAPER / "generated" / "slope_results.md",
        PAPER / "generated" / "sensitivity.md",
        PAPER / "generated" / "year_coverage.md",
        PAPER / "generated" / "completion_figure.md",
        PAPER / "generated" / "slopes_figure.md",
        PAPER / "generated" / "patterns_figure.md",
        PAPER / "generated" / "feature_figure.html",
        PAPER / "_variables.yml",
        PAPER / "figures" / "completion_by_model.png",
        PAPER / "figures" / "completion_by_model.svg",
        PAPER / "figures" / "completion_by_model.pdf",
        PAPER / "figures" / "model_response_slopes.png",
        PAPER / "figures" / "response_patterns.png",
        ROOT / "assets" / "social-card.png",
        SITE / "index.html",
        SITE / "reproduce.html",
        SITE / "paper" / "index.html",
        SITE / "paper" / "llm-eti.pdf",
        SITE / "paper" / "llm-eti.tex",
        SITE / "paper" / "llm-eti-source.zip",
        SITE / "sitemap.xml",
        SITE / "downloads" / "publication_manifest.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing publication artifacts: {missing}")

    pdf = SITE / "paper" / "llm-eti.pdf"
    if pdf.stat().st_size < 50_000 or not pdf.read_bytes().startswith(b"%PDF-"):
        raise SystemExit("The publication PDF is empty or has an invalid signature")

    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo is None:
        if os.environ.get("ALLOW_MISSING_PDFINFO") != "1":
            raise SystemExit(
                "pdfinfo (poppler-utils) is required to verify PDF accessibility "
                "tagging; install it or set ALLOW_MISSING_PDFINFO=1 to skip "
                "explicitly."
            )
        print("Warning: pdfinfo is unavailable; skipping the PDF tagging check.")
    else:
        pdf_metadata = subprocess.run(
            [pdfinfo, os.fspath(pdf)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        tagged_value = next(
            (
                line.partition(":")[2].strip().lower()
                for line in pdf_metadata.splitlines()
                if line.partition(":")[0].strip().lower() == "tagged"
            ),
            None,
        )
        if tagged_value != "yes":
            raise SystemExit("The publication PDF is not tagged for accessibility")

    tex = SITE / "paper" / "llm-eti.tex"
    tex_text = tex.read_text(encoding="utf-8")
    if tex.stat().st_size < 10_000 or "\\documentclass" not in tex_text:
        raise SystemExit("The retained TeX source is missing or invalid")

    with zipfile.ZipFile(SITE / "paper" / "llm-eti-source.zip") as source_bundle:
        bundled = set(source_bundle.namelist())
    required_bundle_files = {
        "llm-eti.tex",
        "references.bib",
        "figures/completion_by_model.png",
        "figures/model_response_slopes.png",
        "figures/response_patterns.png",
    }
    if not required_bundle_files.issubset(bundled):
        raise SystemExit(
            "The TeX source bundle is incomplete: "
            f"{sorted(required_bundle_files - bundled)}"
        )

    forbidden = [
        "Placeholder for:",
        "No ETI data available",
        "Run full simulations to generate",
        "?var:",
    ]
    searchable = [
        *(PAPER / "generated").glob("*"),
        *SITE.rglob("*.html"),
    ]
    for path in searchable:
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        for phrase in forbidden:
            if phrase in text:
                raise SystemExit(f"Forbidden placeholder text in {path}: {phrase}")

    summary = json.loads((PAPER / "generated" / "analysis_summary.json").read_text())
    expected_counts = {
        "scenario_count": 1000,
        "archived_response_row_count": 8095,
        "deduplicated_analysis_row_count": 8087,
        "balanced_primary_scenario_count": 821,
        "identified_balanced_scenario_count": 632,
        "primary_analysis_scenario_count": 603,
    }
    for key, expected_count in expected_counts.items():
        if summary.get(key) != expected_count:
            raise SystemExit(
                f"Unexpected {key}: {summary.get(key)!r}; expected {expected_count}"
            )

    expected_results = {
        "claude_haiku_4_5": {
            "slope": 0.712642,
            "slope_ci_lower": 0.654093,
            "slope_ci_upper": 0.771190,
            "broad_slope": 0.424497,
            "broad_slope_ci_lower": 0.398850,
            "broad_slope_ci_upper": 0.450144,
        },
        "deepseek_v3": {
            "slope": 0.410232,
            "slope_ci_lower": 0.347147,
            "slope_ci_upper": 0.473317,
            "broad_slope": 0.000146,
            "broad_slope_ci_lower": -0.000109,
            "broad_slope_ci_upper": 0.000402,
        },
        "gemma_4_26b": {
            "slope": 0.261423,
            "slope_ci_lower": -0.013805,
            "slope_ci_upper": 0.536651,
            "broad_slope": 0.017850,
            "broad_slope_ci_lower": 0.003442,
            "broad_slope_ci_upper": 0.032258,
        },
        "gpt_4o_mini": {
            "slope": 0.356886,
            "slope_ci_lower": 0.266829,
            "slope_ci_upper": 0.446942,
            "broad_slope": 0.051619,
            "broad_slope_ci_lower": 0.026664,
            "broad_slope_ci_upper": 0.076574,
        },
    }
    observed_results = {row["model_key"]: row for row in summary["main_results"]}
    for model, fields in expected_results.items():
        for field, expected_value in fields.items():
            observed_value = observed_results[model][field]
            if abs(observed_value - expected_value) > 1e-6:
                raise SystemExit(
                    f"Unexpected {field} for {model}: {observed_value:.9f}; "
                    f"expected {expected_value:.6f}"
                )

    publication_manifest = json.loads(
        (SITE / "downloads" / "publication_manifest.json").read_text()
    )
    if publication_manifest.get("quarto_version") != REQUIRED_QUARTO_VERSION:
        raise SystemExit(
            f"Publication manifest must record Quarto {REQUIRED_QUARTO_VERSION}; "
            f"found {publication_manifest.get('quarto_version')!r}"
        )

    paper_html = (SITE / "paper" / "index.html").read_text(encoding="utf-8")
    for link in ["llm-eti.pdf", "llm-eti.tex", "llm-eti-source.zip"]:
        if link not in paper_html:
            raise SystemExit(f"Web paper does not link to {link}")

    core_pages = [
        SITE / "index.html",
        SITE / "reproduce.html",
        SITE / "paper" / "index.html",
    ]
    parsed_pages: dict[Path, _DocumentMetadataParser] = {}
    for html_path in core_pages:
        parser = _DocumentMetadataParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
        parsed_pages[html_path] = parser
        duplicate_ids = sorted(
            identifier for identifier, count in Counter(parser.ids).items() if count > 1
        )
        if duplicate_ids:
            raise SystemExit(
                f"Duplicate HTML ids in {html_path.relative_to(SITE)}: {duplicate_ids}"
            )
        if parser.main_landmarks != 1:
            raise SystemExit(
                f"Expected one main landmark in {html_path.relative_to(SITE)}, "
                f"found {parser.main_landmarks}"
            )

    for html_path in [SITE / "index.html", SITE / "reproduce.html"]:
        parser = parsed_pages[html_path]
        if parser.skip_targets != ["#main-content"] or "main-content" not in parser.ids:
            raise SystemExit(
                f"Missing skip-to-main target in {html_path.relative_to(SITE)}"
            )

    paper_metadata = parsed_pages[SITE / "paper" / "index.html"]
    if paper_metadata.canonical_urls != [PAPER_URL]:
        raise SystemExit(
            f"Unexpected paper canonical URL: {paper_metadata.canonical_urls}"
        )
    expected_social_metadata = {
        "og:type": "article",
        "og:url": PAPER_URL,
        "og:title": "What do language models imply about taxable-income responses?",
        "og:image": SOCIAL_IMAGE_URL,
        "twitter:card": "summary_large_image",
        "twitter:title": "What do language models imply about taxable-income responses?",
        "twitter:image": SOCIAL_IMAGE_URL,
    }
    for key, expected_content in expected_social_metadata.items():
        if paper_metadata.metadata.get(key) != [expected_content]:
            raise SystemExit(
                f"Unexpected {key} metadata: {paper_metadata.metadata.get(key, [])}"
            )

    sitemap_root = ET.parse(SITE / "sitemap.xml").getroot()
    sitemap_urls = [
        element.text
        for element in sitemap_root.findall(
            f"{{{SITEMAP_NAMESPACE}}}url/{{{SITEMAP_NAMESPACE}}}loc"
        )
    ]
    if sitemap_urls.count(PAPER_URL) != 1:
        raise SystemExit(
            f"Sitemap must contain the paper URL exactly once: {sitemap_urls}"
        )

    broken: dict[str, list[str]] = {}
    for html_path in SITE.rglob("*.html"):
        missing_references = _missing_local_references(html_path)
        if missing_references:
            broken[os.fspath(html_path.relative_to(SITE))] = missing_references
    if broken:
        raise SystemExit(f"Broken local publication references: {broken}")

    generated_paths = [
        *sorted(path for path in (PAPER / "generated").glob("*") if path.is_file()),
        *sorted(path for path in (PAPER / "figures").glob("*") if path.is_file()),
        PAPER / "_variables.yml",
        ROOT / "assets" / "social-card.png",
    ]
    relative_generated_paths = [
        os.fspath(path.relative_to(ROOT)) for path in generated_paths
    ]
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", *relative_generated_paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if tracked.returncode:
        raise SystemExit(
            "Generated publication assets must be tracked by git:\n"
            f"{tracked.stderr.strip()}"
        )
    generated_status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            "paper/generated",
            "paper/figures",
            "paper/_variables.yml",
            "assets/social-card.png",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    untracked_generated = [line for line in generated_status if line.startswith("??")]
    if untracked_generated:
        raise SystemExit(
            f"Untracked generated publication assets: {untracked_generated}"
        )

    # Numeric and prose artifacts must be byte-stable. Matplotlib's font
    # rasterization and PDF/SVG geometry vary across operating systems, so the
    # figures are rebuilt above and validated structurally instead of compared
    # byte-for-byte with artifacts committed from another platform.
    subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            "--",
            "paper/generated",
            "paper/_variables.yml",
        ],
        cwd=ROOT,
        check=True,
    )
    print("Publication integrity checks passed.")


if __name__ == "__main__":
    main()
