# Methods

This study employs two complementary approaches to investigate LLM perceptions of tax response behavior:

## Study 1: Lab Experiment Replication (PKNF 2024)

We replicate the controlled laboratory experiment of {cite}`PKNF2024`, which measures labor supply responses to changes in tax schedules. This is a true replication: we use the same experimental design but substitute LLM responses for human subjects.

### Experimental Design

The experiment consists of:

- **16 rounds** of decision-making
- **Three tax schedules**:
  - Flat tax at 25%
  - Flat tax at 50%
  - Progressive tax with a notch (25% up to 20 units, 50% above)
- **Tax reform** after round 8 (either adding or removing the notch)
- **Randomized labor endowments** (14-30 units per round)

### LLM Implementation

We prompt LLMs with instructions mirroring those given to human subjects:

```
LABOR DECISION - Round [N]

You have [X] hours available to work this round.
Each hour of work earns $20.

TAX SYSTEM:
[Description of current tax schedule]

How many hours will you work? (0 to [X])
```

We run 100 simulated subjects per treatment group using OpenAI's GPT models.

## Study 2: Tax Response Survey

Unlike Study 1, this is an *original* survey experiment—not a replication of any observational study.

### Motivation

Prior work has attempted to "replicate" observational studies like {cite}`GruberSaez2002` by asking LLMs hypothetical questions about tax responses. This framing is problematic:

1. **No identification strategy**: Observational studies derive their credibility from natural experiments (tax reforms, instrument variables). Asking LLMs "what would you do if taxes changed" has no analog.
2. **Missing context**: Real taxpayers have histories, constraints, and information that cannot be captured in a brief prompt.
3. **Hallucination risk**: Open-ended numerical responses invite fabrication.

We instead design a clean survey experiment that acknowledges its hypothetical nature while maximizing signal.

### Factorial Design

We systematically vary:

| Factor | Levels | Rationale |
|--------|--------|-----------|
| Income | $40k, $95k, $180k, $400k | Spans tax brackets |
| Rate change | +5pp, -5pp | Tests direction effects |
| Persona type | Wage worker, Self-employed | Tests margin heterogeneity |
| Model | GPT-4o, GPT-4o-mini, Claude, Gemini | Tests model differences |

Total: 4 × 2 × 2 × 4 = 64 scenarios per model, with 50 repetitions each.

### Prompt Design

Each prompt includes:

1. **Persona description**: Demographics, occupation, filing status
2. **Current tax situation**: Income, filing status, marginal rate
3. **Policy change**: Direction and magnitude of rate change
4. **Categorical response options**: Avoids open-ended hallucination

```
You are a 35-year-old software engineer, single with no dependents.

Your current tax situation:
- Filing status: single
- Annual wage income: $95,000
- Current federal marginal tax rate: 22%

A tax law change will increase your marginal rate by 5 percentage points, from 22% to 27%.

What would your taxable income be next year?
- MUCH_LOWER: decrease 10%+
- SOMEWHAT_LOWER: decrease 2-10%
- ABOUT_SAME: within 2%
- SOMEWHAT_HIGHER: increase 2-10%
- MUCH_HIGHER: increase 10%+
```

### ETI Calculation

For each categorical response, we compute implied ETI using:

$$e = \frac{\% \Delta \text{Income}}{\% \Delta (1 - \text{MTR})}$$

Using midpoint assumptions:
- MUCH_LOWER → -15%
- SOMEWHAT_LOWER → -6%
- ABOUT_SAME → 0%
- SOMEWHAT_HIGHER → +6%
- MUCH_HIGHER → +15%

## Implementation

All simulations use:
- **EDSL** (Expected Parrot's Domain-Specific Language) for survey orchestration
- **OpenAI API** for GPT models
- **Universal caching** to reduce costs on repeated runs
- **Python 3.12** with pandas, statsmodels, matplotlib

Code is available at [github.com/MaxGhenis/llm-eti](https://github.com/MaxGhenis/llm-eti).
