# LLM × ETI

Reproducible research for **“What do language models imply about taxable-income
responses?”** by Jason DeBacker and Max Ghenis.

This project compares archived responses from Claude Haiku 4.5, DeepSeek V3,
Gemma 4 26B, and GPT-4o mini on a common set of hypothetical tax scenarios. It
studies model-output distributions; it does **not** treat an LLM completion as
an estimate of human behavior.

The publication has three outputs from one Quarto manuscript source:

- a small project microsite;
- a native web version of the paper; and
- a compiled PDF with its generated TeX retained for audit, plus a compilable
  source bundle containing the figures.

## Reproduce everything

Prerequisites are [uv](https://docs.astral.sh/uv/), Quarto 1.9.38, and a LaTeX
distribution.

```bash
git clone https://github.com/MaxGhenis/llm-eti.git
cd llm-eti
uv sync --python 3.13 --group dev --frozen
make publication
```

The build validates the frozen inputs, regenerates every number and figure,
runs tests and static checks, renders the site and web paper, compiles the PDF,
retains the TeX, checks internal links and file signatures, and fails if tracked
generated artifacts drift. No model API key is required.

Publication rendering requires a Git checkout with source committed to `HEAD`.
Both the index and working tree are checked, including manuscript sections,
analysis code, generated text, and numeric summaries. Untracked non-ignored
files also fail the release gate. Run `make artifacts`, review changes, and
commit them before rendering an edited publication. Tests use isolated Git
fixtures and can still run while developing with uncommitted changes.

`_site/downloads/publication_manifest.json` records the exact commit, a clean
source attestation, SHA-256 hashes of every tracked source file, dependency and
rendering versions, and output hashes. Source identity is checked before and
after rendering and again by `make check`. Only modifications to the nine named
generated figures (PNG/SVG/PDF) and `assets/social-card.png` are exempt from
byte equality with `HEAD`: font rasterization and geometry can vary by platform.
Their actual bytes are separately hashed in `platform_generated_sha256` and
the figures remain subject to structural checks. This exception does not allow
new, deleted, renamed, or type-changed figure files. There is no dirty-source
release override; preview edited prose after committing it on a local branch.

Useful narrower targets:

```bash
make artifacts   # Regenerate tables, figures, and analysis_summary.json
make test        # Run offline integrity and regression tests
make lint        # Run Black, Ruff, and mypy checks
make site        # Render the microsite plus HTML/PDF/TeX paper
make serve       # Preview _site at http://localhost:8000
```

## Reproducibility boundary

The analysis starts from `data/scenarios.csv` and five archived response files
under `data/responses/`. The original runner did not retain the exact
PolicyEngine-US or upstream dataset revisions used to create the scenario
sample, nor every provider setting, failed attempt, or cache hit. Those unknowns
are disclosed rather than reconstructed.

The analysis rebuild is deterministic from the archived CSVs. A future call to
a moving model endpoint is not expected to reproduce the same text.

The Python source distribution is a minimal library artifact containing
`llm_eti` and the required package, readme, license, and notice files. It omits
the research data, tests, paper and site sources, assets, protocols, automation,
and CI configuration. Clone the repository or use its publication/release
archive when reproducing the paper; the Python sdist alone is not the
research-data archive.

## Repository map

```text
index.qmd                    editorial project landing page
reproduce.qmd                public provenance and build guide
paper/index.qmd              canonical web/PDF/TeX manuscript
paper/sections/              manuscript sections
paper/generated/             derived tables, text, and machine summary
paper/figures/               derived PNG, SVG, and PDF figures
data/                        frozen scenario and response inputs
llm_eti/study2.py            validated analysis library
scripts/generate_artifacts.py single presentation-artifact generator
scripts/render_publication.py Quarto build orchestrator
tests/                       offline integrity and regression tests
```

See [`data/README.md`](data/README.md),
[`data/run_manifest.json`](data/run_manifest.json), and
[`NOTICE.md`](NOTICE.md) for provenance and third-party boundaries.

## Citation and license

Citation metadata are in [`CITATION.cff`](CITATION.cff). Its `license` field
and the [Unlicense](LICENSE) cover original code and text contributed to this
repository. See [`NOTICE.md`](NOTICE.md) for the archived response corpus's
provenance, current redistribution status, and third-party terms that require
separate review.
