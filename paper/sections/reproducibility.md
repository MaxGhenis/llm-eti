# Reproducibility and data provenance

The complete publication rebuild is offline after dependencies are installed:

```bash
uv sync --python 3.13 --group dev --frozen
make publication
```

The command validates and analyzes the frozen CSVs, regenerates every reported
fragment and figure, runs tests and static checks, renders the project site and
web paper, compiles the PDF while retaining its TeX source, and verifies that
the generated source artifacts have no git drift. No model API credential is
used.

The machine-readable `paper/generated/analysis_summary.json` records the source
SHA-256 digests, sample counts, cluster count, model estimates, archive
coverage, and sensitivities. `data/run_manifest.json` separately records known
run settings and fields that the legacy runner did not retain.

The six immutable inputs are `data/scenarios.csv` and the five CSVs under
`data/responses/`. Quoted raw model text can contain newlines, so record counts
are validated with a CSV parser. The loader checks schemas, exact scenario
joins, response numbers, duplicate delivered prompts, and ambiguous recovery
groups before estimation.

The published build exposes the web paper at `/paper/`, with `llm-eti.pdf`,
`llm-eti.tex`, and a directly compilable `llm-eti-source.zip` generated from
this same Quarto source.
