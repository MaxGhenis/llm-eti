# Model Comparisons

This section provides additional analysis comparing different LLM models and exploring robustness of our results.

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

## Response Patterns by Income Level

Using the enhanced regression analysis from your branch:

```{table} ETI Regression with Multiple Specifications
:name: tab-enhanced-reg

| | (1) | (2) | (3) | (4) |
|---|-----|-----|-----|-----|
| Constant | 0.439*** | 0.217*** | 0.292*** | 0.171** |
| | (0.056) | (0.031) | (0.050) | (0.070) |
| Income ($100k) | -0.060* | | -0.060* | 0.036 |
| | (0.034) | | (0.034) | (0.045) |
| \|ΔMTR\| | | 2.455*** | 2.455*** | 4.473*** |
| | | (0.481) | (0.481) | (1.456) |
| Income × \|ΔMTR\| | | | | -1.614* |
| | | | | (0.887) |
| Observations | 15,985 | 15,985 | 15,985 | 15,985 |
| R² | 0.000 | 0.001 | 0.001 | 0.001 |
```

Note: This uses GPT-4o data. 80.5% of responses show zero ETI.

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

## Robustness Checks

### Alternative Prompt Specifications

We tested variations in prompt wording:
1. **Baseline**: As shown in methods
2. **Detailed**: Including information about deductions
3. **Simplified**: Only mentioning tax rate change

Results are robust across specifications for GPT-4o but vary for GPT-4o-mini.

### Sample Restrictions

Excluding extreme responses (ETI > 10 or < -10):
- GPT-4o: Mean ETI changes from 0.364 to 0.358
- GPT-4o-mini: Mean ETI changes from 1.280 to 1.195

## Implications for Using LLMs in Tax Research

1. **Model Selection Matters**: GPT-4o produces more realistic responses
2. **Non-Response is Informative**: Models that always respond may miss important frictions
3. **Heterogeneity Analysis**: LLMs can explore dimensions not available in admin data
4. **Cost-Effectiveness**: LLM simulations cost <$100 vs. $100,000s for lab experiments