# Study 2: Tax Response Survey

We conduct an original survey experiment asking LLMs to simulate taxpayer responses to marginal tax rate changes.

## Experimental Design

Unlike observational studies that rely on natural experiments for identification, we frame this as what it is: a hypothetical survey measuring how LLMs perceive tax response behavior. This allows us to systematically vary dimensions of interest.

### Factorial Design

We vary four factors:

```{include} ../generated/factorial_design.md
```

This yields 16 scenarios per model, or 32 total model-scenario combinations, with 50 repetitions per scenario.

### Survey Prompt

Each LLM receives a prompt describing a taxpayer persona and asking how their taxable income would change:

```
You are [persona description].

Your current tax situation:
- Filing status: [status]
- Annual wage income: $[income]
- Current federal marginal tax rate: [rate]%

A tax law change will [increase/decrease] your marginal rate to [new_rate]%.

What would your taxable income be next year?
- MUCH_LOWER: decrease 10%+
- SOMEWHAT_LOWER: decrease 2-10%
- ABOUT_SAME: within 2%
- SOMEWHAT_HIGHER: increase 2-10%
- MUCH_HIGHER: increase 10%+
```

## Results

### Response Distribution by Model

```{include} ../generated/response_distribution.md
```

### Key Finding: GPT-4o Exhibits Realistic Frictions

The most striking result is GPT-4o's high "about same" response rate (80.5%). This aligns with empirical findings on optimization frictions:

- {cite}`Chetty2012` shows that adjustment costs prevent many taxpayers from responding to tax changes
- {cite}`KlevenWaseem2013` find substantial bunching below notches, indicating incomplete optimization

GPT-4o-mini, by contrast, shows only 3.1% non-response, suggesting it over-optimizes and misses real-world frictions.

### Implied ETI Estimates

Converting categorical responses to ETI estimates using midpoint assumptions:

```{include} ../generated/mean_eti.md
```

### Heterogeneity by Income

```{include} ../generated/eti_by_income.md
```

Both models correctly predict that higher-income taxpayers are more responsive—a robust finding in the empirical literature ({cite}`GruberSaez2002`; {cite}`SaezEtAl2012`).

### Heterogeneity by Employment Type

Self-employed personas show larger ETIs than wage workers across both models:

- **GPT-4o**: 0.48 (self-employed) vs. 0.31 (wage worker)
- **GPT-4o-mini**: 1.42 vs. 1.15

This pattern is economically sensible: self-employed individuals have more flexibility in reporting and timing of income.

## Comparison to Prior "Replications"

Our original survey design differs fundamentally from attempts to "replicate" observational studies like {cite}`GruberSaez2002`:

| Aspect | G-S "Replication" | Our Survey |
|--------|------------------|------------|
| **Framing** | Claims to replicate empirical study | Acknowledges hypothetical nature |
| **Identification** | None (asks "what if" questions) | Factorial design with controls |
| **Personas** | None (just income levels) | Detailed demographic profiles |
| **Response format** | Continuous (invites hallucination) | Categorical (structured) |
| **Tax system** | Arbitrary rates (15-35%) | Actual 2024 US brackets |

The key insight is that LLMs cannot replicate observational studies because they lack the identification strategies (tax reforms, instrumental variables) that make empirical estimates credible. What LLMs *can* do is reveal their priors about tax response behavior—which, as we show, are surprisingly close to empirical estimates.

## Discussion

These results suggest GPT-4o has internalized economically sensible priors about tax responses from its training data. The model:

1. Produces mean ETI close to empirical estimates (0.36 vs. 0.25-0.40)
2. Exhibits realistic optimization frictions (80.5% non-response)
3. Correctly predicts income heterogeneity (higher income → larger ETI)
4. Correctly predicts employment heterogeneity (self-employed → larger ETI)

Smaller models like GPT-4o-mini lack these features, suggesting that scale matters for capturing the nuances of economic behavior.

```{admonition} Limitations
:class: warning

This is a survey of LLM perceptions, not a measurement of actual human behavior. Results should be interpreted as revealing what LLMs "believe" about tax responses, not as estimates of true ETI values.
```
