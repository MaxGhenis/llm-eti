# Frozen publication inputs

This directory is the reproducibility boundary for the paper. The scenario
sample and archived response CSVs are immutable inputs; rebuilding the
publication does not call a model API or download a contemporary dataset.

## Contents

| Path | Contents | Records |
|---|---|---:|
| `scenarios.csv` | PolicyEngine-derived tax-unit scenarios | 1,000 |
| `responses/gruber_saez_results_claude-haiku-4-5-20251001.csv` | Claude Haiku 4.5 responses | 2,000 |
| `responses/gruber_saez_results_deepseek-ai_DeepSeek-V3.csv` | DeepSeek V3 responses | 1,678 |
| `responses/gruber_saez_results_google_gemma-4-26B-A4B-it.csv` | Gemma 4 26B responses | 1,974 |
| `responses/gruber_saez_results_gpt-4o-mini.csv` | GPT-4o mini responses | 1,997 |
| `responses/gruber_saez_results_gpt-4o.csv` | Partial GPT-4o responses | 446 |

The `income_response_raw` field may contain quoted newlines. Use an RFC
4180-compatible CSV parser; physical line counts are not record counts.

## Analysis rules

`llm_eti.study2` joins each response to its source scenario and reconstructs the
whole-dollar incomes and integer marginal rates that the model actually saw.
The primary analysis excludes:

- all ten source rows belonging to five duplicated delivered prompts;
- ambiguous DeepSeek recovery reruns;
- prompts whose displayed before-and-after rates are identical; and
- every scenario with a nonpositive broad- or taxable-income output from any
  primary model or requested repetition.

Zero-dollar responses remain visible in boundary diagnostics and the `log1p`
sensitivity. The checked-in `run_manifest.json` records known settings, unknown
fields, source locations, record counts, and SHA-256 digests.

## Provenance boundary

The response files were generated from June 4 through June 8, 2026 and entered
the repository in commit `b23f2cb` through pull request 42. The exact
PolicyEngine-US package and upstream dataset revisions used to create
`scenarios.csv` were not recorded. That CSV—not a fresh simulation—is therefore
the input reproduced by this release.
