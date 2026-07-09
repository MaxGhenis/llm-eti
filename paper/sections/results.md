# Results

## Archived parseable-response coverage

The archived runs did not cover the source scenarios uniformly. A missing row
cannot be separated into a model failure, parser failure, exhausted retry, or
stopped run because unsuccessful attempts were not retained. We therefore
describe these counts as archive coverage rather than success rates.

{{< include generated/completion.md >}}

: Archived scenario and unique parseable-response coverage by model, relative to the 1,000-scenario source archive. {#tbl-completion}

![Archived parseable-response coverage by model. The gray GPT-4o bar denotes the partial run, which is excluded from outcome comparisons.](figures/completion_by_model.png){#fig-completion fig-alt="Horizontal bars show scenario coverage: Claude 100 percent, GPT-4o mini and Gemma near 100 percent, DeepSeek 83.5 percent, and the partial GPT-4o run 24.5 percent."}

{{< include generated/partial_run_note.md >}}

{{< include generated/design_diagnostics.md >}}

```{=latex}
\clearpage
```

## Main response slopes

{{< include generated/slope_results.md >}}

: Model-specific taxable- and broad-income slopes on the primary panel. {#tbl-slope-results}

![Taxable- and broad-income log-response slopes with cluster-robust 95 percent confidence intervals on the primary panel.](figures/model_response_slopes.png){#fig-response-slopes fig-alt="A horizontal dot and interval plot shows Claude with the largest taxable-income slope, followed by DeepSeek, GPT-4o mini, and Gemma. Claude also has the largest broad-income slope; the others are much closer to zero."}

{{< include generated/main_narrative.md >}}

## Distribution diagnostics

{{< include generated/response_diagnostics.md >}}

: Distribution diagnostics for individual taxable-income responses. {#tbl-response-diagnostics}

{{< include generated/key_findings.md >}}

![Distribution of unchanged, directionally consistent, and opposite-direction individual responses in the primary panel.](figures/response_patterns.png){#fig-response-patterns fig-alt="Stacked horizontal bars show that Claude changes income in most responses, DeepSeek does so about half the time, and Gemma and GPT-4o mini usually copy the baseline."}

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

: Taxable-income stability among same-rate scenarios in the clean four-model panel. {#tbl-same-rate-check}

```{=latex}
\clearpage
```

Some models returned zero taxable income. Those are valid outputs of the
free-text prompt, but ordinary logarithms are undefined at zero. The primary
panel excludes every scenario containing a nonpositive broad- or
taxable-income output and reports the exclusions explicitly.

{{< include generated/boundary_outputs.md >}}

: Nonpositive outputs in the rate-identified clean panel before the primary positivity restriction. {#tbl-boundary-outputs}

## Sensitivity

{{< include generated/sensitivity.md >}}

: Taxable-income slope sensitivity across alternative specifications. {#tbl-sensitivity}

{{< include generated/sensitivity_narrative.md >}}
