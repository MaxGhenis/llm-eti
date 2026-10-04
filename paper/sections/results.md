# Results

## Archived parseable-response coverage

The archived runs did not cover the source scenarios uniformly. A missing row
cannot be separated into a model failure, parser failure, exhausted retry, or
stopped run because unsuccessful attempts were not retained. We therefore
describe these counts as archive coverage rather than success rates.

{{< include generated/completion.md >}}

: Archived scenario and unique parseable-response coverage by model, relative to the 1,000-scenario source archive. {#tbl-completion}

{{< include generated/completion_figure.md >}}

{{< include generated/partial_run_note.md >}}

{{< include generated/design_diagnostics.md >}}

```{=latex}
\clearpage
```

## Main response slopes conditional on positive outputs

{{< include generated/slope_results.md >}}

: Model-specific taxable- and broad-income slopes conditional on positive broad- and taxable-income outputs in all eight model-by-repetition cells. {#tbl-slope-results}

{{< include generated/slopes_figure.md >}}

{{< include generated/main_narrative.md >}}

## Distribution diagnostics

{{< include generated/response_diagnostics.md >}}

: Distribution diagnostics for individual taxable-income responses. {#tbl-response-diagnostics}

{{< include generated/key_findings.md >}}

{{< include generated/patterns_figure.md >}}

```{=latex}
\clearpage
```

{{< include generated/response_friction.md >}}

: Frequency with which individual outputs change either income measure in the primary log panel. {#tbl-response-friction}

The paired outputs often agree exactly, especially for models that usually copy
the displayed baseline. They are repeated requested outputs conditional on one
prompt, not independent observations of behavior.

## Same-rate and boundary checks

Prompts whose continuous rates rendered as the same integer rate provide a
descriptive check. A model following the delivered scenario should often return
the supplied baseline.

{{< include generated/same_rate_check.md >}}

: Response-level and scenario-pair taxable-income stability among same-rate scenarios in the clean four-model panel. Pair-level stability requires both requested responses to equal the displayed baseline to the nearest dollar. {#tbl-same-rate-check}

```{=latex}
\clearpage
```

Some models returned zero taxable income. Those are valid outputs of the
free-text prompt, but ordinary logarithms are undefined at zero. The primary
panel excludes every scenario containing a nonpositive broad- or
taxable-income output and reports the exclusions explicitly.

{{< include generated/boundary_outputs.md >}}

: Nonpositive outputs in the rate-identified clean panel before the primary positivity restriction. {#tbl-boundary-outputs}

{{< include generated/boundary_by_direction.md >}}

: Zero and nonpositive-output incidence by model and treatment direction in the 632-scenario rate-identified balanced panel. {#tbl-boundary-by-direction}

{{< include generated/positivity_selection_narrative.md >}}

{{< include generated/positivity_selection_balance.md >}}

: Scenario covariates retained and omitted by the 632-to-603 all-positive selection step. {#tbl-positivity-selection-balance}

## Sensitivity

{{< include generated/sensitivity.md >}}

: Taxable-income slope sensitivity across alternative specifications. {#tbl-sensitivity}

{{< include generated/sensitivity_narrative.md >}}
