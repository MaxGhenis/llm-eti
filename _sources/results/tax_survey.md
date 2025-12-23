---
kernelspec:
  name: python3
  display_name: Python 3
---

# Study 2: Tax Response Survey

```{code-cell} python
:tags: [remove-cell]

# Setup: Import paper results (single source of truth)
from llm_eti.paper_results import r
```

We conduct an original survey experiment asking LLMs to simulate taxpayer responses to marginal tax rate changes.

## Experimental Design

Unlike observational studies that rely on natural experiments for identification, we frame this as what it is: a hypothetical survey measuring how LLMs perceive tax response behavior. This allows us to systematically vary dimensions of interest.

### Factorial Design

We vary four factors:

```{code-cell} python
:tags: [remove-input]

from IPython.display import Markdown
Markdown(r.table_factorial_design())
```

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

```{code-cell} python
:tags: [remove-input]

from IPython.display import Markdown
Markdown(r.table_response_dist())
```

### Key Finding: GPT-4o Exhibits Realistic Frictions

The most striking result is GPT-4o's high "about same" response rate ({eval}`r.gpt4o.non_response_rate`). This aligns with empirical findings on optimization frictions:

- {cite}`Chetty2012` shows that adjustment costs prevent many taxpayers from responding to tax changes
- {cite}`KlevenWaseem2013` find substantial bunching below notches, indicating incomplete optimization

GPT-4o-mini, by contrast, shows only {eval}`r.gpt4o_mini.non_response_rate` non-response—suggesting it over-optimizes and misses real-world frictions.

### Implied ETI Estimates

Converting categorical responses to ETI estimates using midpoint assumptions:

```{code-cell} python
:tags: [remove-input]

from IPython.display import Markdown
Markdown(r.table_mean_eti())
```

### Heterogeneity by Income

```{code-cell} python
:tags: [remove-input]

from IPython.display import Markdown
Markdown(r.table_eti_by_income())
```

Both models correctly predict that higher-income taxpayers are more responsive—a robust finding in the empirical literature ({cite}`GruberSaez2002`; {cite}`SaezEtAl2012`).

### Heterogeneity by Employment Type

Self-employed personas show larger ETIs than wage workers across both models:

- **GPT-4o**: {eval}`r.gpt4o.eti_self_employed` (self-employed) vs. {eval}`r.gpt4o.eti_wage_worker` (wage worker)
- **GPT-4o-mini**: {eval}`r.gpt4o_mini.eti_self_employed` vs. {eval}`r.gpt4o_mini.eti_wage_worker`

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

1. Produces mean ETI close to empirical estimates ({eval}`r.gpt4o.eti` vs. {eval}`r.empirical_range`)
2. Exhibits realistic optimization frictions ({eval}`r.gpt4o.non_response_rate` non-response)
3. Correctly predicts income heterogeneity (higher income → larger ETI)
4. Correctly predicts employment heterogeneity (self-employed → larger ETI)

Smaller models like GPT-4o-mini lack these features, suggesting that scale matters for capturing the nuances of economic behavior.

```{admonition} Limitations
:class: warning

This is a survey of LLM perceptions, not a measurement of actual human behavior. Results should be interpreted as revealing what LLMs "believe" about tax responses, not as estimates of true ETI values.
```
