# Design and methods

## Analysis status

This is a retrospective analysis of a June 2026 model-output archive. The
design, cleaning rules, and estimators were not preregistered. All comparisons
and sensitivity checks are therefore exploratory.

## Scenario sample

The frozen input contains 1,000 tax-unit scenarios. The legacy generator drew
tax units with replacement from PolicyEngine-US files for 2023 and 2024
[@PolicyEngineUS], using household weights as sampling probabilities. The
eligible source universe had
positive household weight and strictly positive tax-unit broad and taxable
income. Broad income is tax-unit market income; taxable income is the
PolicyEngine-US tax-unit measure.

The initial tax-only marginal rate is attached to the highest-market-income
person in each tax unit. It sums that person's federal income-tax, state
income-tax, and FICA marginal rates plus a self-employment-tax component
calculated by increasing self-employment income by one dollar. The hypothetical
new rate multiplies the initial net-of-tax rate by a lognormal shock with log
standard deviation 0.025.

{{< include generated/scenario_sample.md >}}

{{< include generated/sample_characteristics.md >}}

: Source-sample and primary-panel scenario characteristics. {#tbl-sample-characteristics}

Because the scenario generator already sampled with probability proportional
to its survey weight, scenarios receive equal weight in this analysis. The
original run did not record the exact PolicyEngine-US package or upstream
dataset revisions. The frozen `data/scenarios.csv` and its SHA-256 digest—not a
fresh download—are therefore the reproducibility boundary.

## Elicitation and archived runs

The prompt told the model the taxpayer's prior broad income, taxable income,
and marginal tax rate; supplied a new marginal rate; named possible adjustment
channels; and requested one JSON object containing broad and taxable income for
the new year. The full text and the two known formatting variants are archived
in `protocols/legacy_tax_prompt.md`.

DeepSeek V3 and Claude Haiku 4.5 received an additional instruction not to
return `null` and to provide whole-dollar estimates. The suffix was intended to
improve parsing, but it prevents a perfectly identical prompt comparison. Two
responses were requested per scenario. Runs used EDSL 1.0.7 [@EDSL107] with its
universal cache enabled on first attempts and disabled on parser retries. Cache-hit
status, failed attempts, response identifiers, and provider decoding parameters
were not retained.

{{< include generated/model_provenance.md >}}

: Archived model identifiers, collection windows, and record counts. {#tbl-model-provenance}

{{< include generated/recovery_diagnostics.md >}}

Archive coverage is highly structured by year, especially for DeepSeek. The
table reports scenarios with at least one parseable archived response, followed
by the more restrictive common panels.

{{< include generated/year_coverage.md >}}

: Scenario coverage by source year and analysis stage. {#tbl-year-coverage}

The identifiers above are the strings in the archive. Official documentation
describes the named model families [@AnthropicHaiku45; @DeepSeekV3;
@GoogleGemma4; @OpenAIGPT4oMini]. Some archived identifiers are provider aliases
rather than immutable model snapshots, so this release reproduces the analysis
of the stored outputs—not future calls to those endpoints.

## Reconstructing the delivered treatment

The prompt rounded incomes to whole dollars and rendered each marginal rate as
`int(rate * 100)`. The archived `implied_eti_*` columns instead used unrounded
inputs; we never analyze those columns.

For each scenario, we reconstruct the displayed baseline income $z_{i0}$,
initial marginal rate $\tau_{i0}$, and new rate $\tau_{i1}$.

{{< include generated/treatment_diagnostics.md >}}

Same-rate prompts remain a descriptive check but do not identify a response
slope. Excluding both members of each delivered-prompt collision avoids
assigning distinct latent scenarios to textually identical treatments.

## Outcomes and estimators

For each individual response $r$, model $m$, and scenario $i$, the ordinary-log
taxable-income response is

$$
y_{imr} = \log (z_{imr,1} / z_{i0})
$$

and the delivered log net-of-tax-rate change is

$$
x_i = \log ((1 - \tau_{i1}) / (1 - \tau_{i0}))
$$

The primary outcome $\bar y_{im}$ averages the two response-level log changes
within a model-scenario cell. Separately by model, we estimate

$$
\bar y_{im} = \alpha_m + \beta_m x_i + \varepsilon_{im}.
$$

The paper calls $\beta_m$ a *model-implied log-response slope*. OLS includes an
intercept. Confidence intervals cluster by source year and tax-unit identifier,
because a source tax unit can appear more than once. The same specification is
estimated for broad income.

{{< include generated/primary_panel.md >}}

We also report the median scenario-level ratio $\bar y_{im}/x_i$ and its
interquartile range, the share of individual responses equal to the displayed
baseline to the nearest dollar, and directional consistency among nonzero
responses. The paired requested responses are not treated as independent
taxpayers or assumed to be independent model draws.

The confidence intervals quantify cluster-robust sampling uncertainty
conditional on this archived scenario sample and the stated covariance
estimator. They do not incorporate prompt choice, model-version uncertainty,
provider changes, or uncertainty about a population of people.

## Primary panel and exploratory sensitivities

The clean four-model intersection requires two parseable, unambiguous responses
from every primary model and excludes duplicate delivered prompts. Ordinary
logs further require positive broad- and taxable-income outputs from all four
models and both requested responses.

This shared panel makes model comparisons transparent, but it is selected on
all four models' outcomes: whether a Claude or DeepSeek scenario enters can
depend on a nonpositive Gemma or GPT-4o mini answer. We disclose that dependence
and report model-specific clean, positive, two-response samples as a
sensitivity.

Other exploratory specifications use a regression through the origin; exclude
negative initial marginal rates; require at least a two-percentage-point
displayed rate change; use only the first requested response; winsorize the log
outcome at the 1st and 99th percentiles; estimate 2023 and 2024 separately; and
apply $\log(1+z)$ to retain zero-dollar outputs. The last is a unit-dependent
boundary stress test, not an elasticity transformation.
