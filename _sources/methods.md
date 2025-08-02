# Methods

This study employs two complementary approaches to elicit elasticity of taxable income (ETI) estimates from large language models:

## Experimental Approach: Replicating PKNF (2024)

We replicate the controlled laboratory experiment of {cite}`PKNF2024`, which measures labor supply responses to changes in tax schedules. The experiment consists of:

- **16 rounds** of decision-making
- **Three tax schedules**: 
  - Flat tax at 25%
  - Flat tax at 50%
  - Progressive tax with a notch (25% up to 20 units, 50% above)
- **Tax reform** after round 8 (either adding or removing the notch)
- **Randomized labor endowments** (14-30 units per round)

### Key Modifications for LLM Implementation

1. We prompt LLMs with the same instructions given to human subjects
2. We do not implement the "real effort" task (typing characters)
3. We use OpenAI's GPT models (`gpt-4o` and `gpt-4o-mini`)

## Observational Approach: Replicating Gruber & Saez (2002)

To simulate observational data with plausibly exogenous variation in marginal tax rates, we prompt LLMs with taxpayer scenarios:

```{admonition} LLM Prompt Template
You are a taxpayer with the following tax profile:
- Your broad income last year was [$X]
- Your taxable income last year was [$0.75 × X$]
- Your marginal tax rate last year was [$r\%$]

This year, if you had the same broad income, your marginal tax rate will change to [$r'\%$]. Given this change, estimate your taxable income for this year.
```

### Parameter Space

- **Broad income**: $50,000 to $200,000 (in $10,000 increments)
- **Tax rates**: 15% to 35% (in 2% increments)
- **Simulations**: 100 responses per scenario
- **Total observations**: 35,200 (2 models × 16 incomes × 11 rates × 100 reps)

## ETI Calculation

For each simulation, we compute the elasticity of taxable income using:

$$e = \frac{\% \Delta \text{Income}}{\% \Delta (1 - \text{MTR})}$$

Where:
- $\% \Delta \text{Income} = \frac{\text{New Income} - \text{Initial Income}}{\text{Initial Income}}$
- $\% \Delta (1 - \text{MTR}) = \frac{(1 - \text{New Rate}) - (1 - \text{Initial Rate})}{1 - \text{Initial Rate}}$

## Implementation Details

All simulations are implemented in Python using:
- OpenAI API for LLM interactions
- Pandas for data management
- Statsmodels for regression analysis
- Matplotlib/Seaborn for visualizations

Code is available at [github.com/MaxGhenis/llm-eti](https://github.com/MaxGhenis/llm-eti).