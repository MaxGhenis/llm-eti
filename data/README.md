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

## Column dictionary

### Scenario file

| Column | Type or units | Scope and meaning |
|---|---|---|
| `year` | Calendar year | PolicyEngine source year. It forms part of the source-record and regression-cluster scope. |
| `tax_unit_id` | Integer identifier | Identifier inherited from the source file. It is scoped to `year`, is not a publication scenario ID, and can recur because the generator sampled with replacement. |
| `household_weight` | Source survey weight | Estimated households represented by the source household. The generator used it as a sampling probability; the sampled analysis rows themselves receive equal weight. |
| `broad_income` | Annual US dollars | Unrounded source tax-unit broad income before the hypothetical rate change. |
| `taxable_income` | Annual US dollars | Unrounded source tax-unit taxable income before the hypothetical rate change. |
| `mtr` | Rate as a decimal fraction | Unrounded initial combined tax-only marginal rate; `0.25` denotes 25%. |
| `mtr_prime` | Rate as a decimal fraction | Unrounded hypothetical marginal rate supplied to the prompt renderer; `0.25` denotes 25%. |

### Response files

| Column | Type or units | Scope and meaning |
|---|---|---|
| `timestamp` | `YYYY-MM-DD HH:MM:SS` | Timezone-naive collection string. The direct runner used host-local `datetime.now()` without recording the host timezone; the DeepSeek recovery script rendered file times in `America/New_York`. The archive therefore does not support a common timezone conversion. |
| `tax_unit_id` | Numeric source identifier | Source identifier serialized as a number. It is not unique by itself; the analysis recovers `year` by joining the full scenario key to `scenarios.csv`. |
| `filing_status` | Empty field | Blank in all 8,095 archived response rows; it carries no filing-status information. |
| `broad_income` | Annual US dollars | Unrounded source broad income copied into the response row; a raw scenario input, not a model output. |
| `taxable_income` | Annual US dollars | Unrounded source taxable income copied into the response row; a raw scenario input, not a model output. |
| `mtr` | Rate as a decimal fraction | Unrounded initial source marginal rate copied into the response row. |
| `mtr_prime` | Rate as a decimal fraction | Unrounded hypothetical source marginal rate copied into the response row. |
| `response_number` | Integer index | Requested response 1 or 2 within a model–scenario cell. It is not a globally unique response ID. |
| `taxable_income_this` | Annual US dollars | Parsed taxable-income model output recovered from `income_response_raw`; zero-dollar values occur. |
| `broad_income_this` | Annual US dollars | Parsed broad-income model output recovered from `income_response_raw`; zero-dollar values occur. |
| `implied_eti_taxable` | Dimensionless ratio | Deprecated legacy derivative computed from unrounded source values. The publication never analyzes this column. |
| `implied_eti_broad` | Dimensionless ratio | Deprecated legacy derivative computed from unrounded source values. The publication never analyzes this column. |
| `model` | String identifier | Model identifier stored by the runner. Some values are provider aliases rather than immutable model revisions. |
| `income_response_raw` | Raw text | Archived model answer before local field extraction. It can contain exact JSON, Python-style objects, Markdown fences, prose, quoted newlines, or other recoverable formatting. |

`income_response_raw` is the archived raw answer, whereas the two `*_this`
columns are its parsed numeric fields. Unsuccessful attempts were not retained,
so the response files cannot be used to estimate an overall parser-attempt
success rate. The analysis reconstructs the whole-dollar incomes and integer
rates delivered to the models rather than treating the copied, higher-precision
scenario fields as prompt text.

## Float-encoding caveat

`scenarios.csv` stores the scenario key columns with up to 17 significant
digits, while the response CSVs store the same values with 16; the two
encodings are one unit in the last place apart as exact IEEE doubles.
`llm_eti.study2` pins pandas' default `float_precision="high"` parser, under
which both files parse to identical float64 keys, and validates the join.
Reading either file with `float_precision="round_trip"` or another
correctly-rounding parser leaves roughly half of the response rows unmatched
and aborts the merge with a validation error.

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
