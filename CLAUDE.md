# CLAUDE.md

Guidance for agents working in this repository.

## Research boundary

This repository analyzes a frozen June 2026 language-model response archive.
It does not estimate human behavior and does not call model APIs during the
publication build.

The six canonical inputs are `data/scenarios.csv` and the five CSVs under
`data/responses/`. Do not mutate them, replace them with fresh downloads, or use
the legacy `implied_eti_*` columns. `data/run_manifest.json` records their hashes
and the limits of the historical provenance.

The unsupported PKNF replication and the legacy scenario generator were
removed. Do not reintroduce either result into the paper without a new,
prospectively validated design.

## Build

Use uv and Python 3.13:

```bash
make install
make publication
```

`make publication` regenerates the analysis artifacts, runs tests and static
checks, renders the Quarto microsite and web paper, compiles the PDF, retains
the TeX source, checks local links, and verifies generated-file drift.

Useful targets:

```bash
make artifacts
make test
make lint
make site
make serve
```

Quarto 1.9.38 is the pinned publication version. CI installs it with TinyTeX.

## Architecture

- `llm_eti/study2.py` is the validated analysis library.
- `scripts/generate_artifacts.py` is the only presentation-artifact generator.
- `paper/generated/` and `paper/figures/` are generated, tracked, and checked
  for drift.
- `paper/index.qmd` is the canonical manuscript source for HTML, PDF, and TeX.
- `index.qmd` and `reproduce.qmd` form the small project microsite.
- `scripts/render_publication.py` orchestrates both Quarto projects.
- `scripts/check_publication.py` enforces release integrity.

Do not hand-edit a generated table, headline number, plot, or
`analysis_summary.json`. Change the analysis/generator and regenerate instead.

## Methodological invariants

- Reconstruct the whole-dollar incomes and integer rates delivered in the
  prompt.
- Exclude all duplicated delivered-prompt rows and ambiguous recovery reruns.
- The primary four-model panel contains 821 clean paired scenarios, 632 with a
  displayed rate change, and 603 with positive outputs in all eight responses.
- Average response-level log changes within model-scenario cells.
- Fit model-specific OLS slopes with an intercept and cluster by
  `year × tax_unit_id` (600 clusters in the primary panel).
- Treat `log1p` as a unit-dependent boundary stress test, not an elasticity.
- Describe results as model-implied responses, never human ETI estimates.

Tests lock the primary counts, slopes, hashes, and major sensitivity results.
Update them only when an intentional methodological change is documented.

## CI and deployment

The publication workflow has read-only permissions during build and uses a
separate GitHub Pages deploy job on `main`. It must not receive an API key or
fabricate placeholder data. PDF or TeX build failures are release failures.
