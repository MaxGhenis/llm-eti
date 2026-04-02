# Model Comparisons

This section compares the two survey models and the lab benchmark using the analyses reported in the paper.

## Cross-Model ETI Comparison

```{figure} ../figures/model_eti_comparison.png
:name: fig-model-compare
:width: 100%

Comparison of ETI estimates across different LLM models and empirical benchmarks.
```

## Key Findings Across Models

```{table} Summary of ETI Estimates
:name: tab-eti-summary

| Source | Mean ETI | Context |
|--------|----------|---------|
| Gruber & Saez (2002) | 0.40 | US tax reforms 1979-1981 |
| Saez et al. (2012) | 0.25 | Meta-analysis |
| **GPT-4o** | **0.364** | **Simulated responses** |
| **GPT-4o-mini** | **1.280** | **Simulated responses** |
| GPT-4o (lab) | ≥0.53 | Bunching estimator |
```

GPT-4o is the only survey model whose mean ETI falls inside the canonical empirical range. GPT-4o-mini responds too aggressively across nearly every slice of the survey, which is why its overall mean ETI is more than three times the benchmark range.

## Income Heterogeneity

Higher-income personas are more tax-responsive in both models, but GPT-4o-mini produces implausibly large elasticities throughout:

| Income | Bracket | GPT-4o ETI | GPT-4o-mini ETI |
|--------|---------|------------|-----------------|
| $40,000 | 12% | 0.28 | 0.95 |
| $95,000 | 22% | 0.32 | 1.12 |
| $180,000 | 24% | 0.41 | 1.38 |
| $400,000 | 35% | 0.52 | 1.67 |

## Non-Response Analysis

```{figure} ../figures/response_rate.png
:name: fig-response-rate
:width: 100%

Percentage of taxpayers adjusting income by model and income level.
```

The high non-response rate in GPT-4o (80.5%) aligns with empirical findings:
- Chetty (2012): Substantial optimization frictions in practice
- Kleven & Waseem (2013): Many taxpayers don't respond to tax changes
- GPT-4o-mini's low non-response (3.1%) suggests over-optimization

## Implications for Using LLMs in Tax Research

1. **Model Selection Matters**: GPT-4o produces more realistic responses
2. **Non-Response is Informative**: Models that always respond may miss important frictions
3. **Heterogeneity Analysis**: LLMs can explore dimensions not available in admin data
4. **Cost-Effectiveness**: LLM simulations cost <$100 vs. $100,000s for lab experiments
