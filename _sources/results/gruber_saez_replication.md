# Replicating an Observational Study

We replicate the seminal empirical study of {cite}`GruberSaez2002` by simulating taxpayer responses to marginal tax rate changes using LLMs.

## Summary Statistics

```{table} Model Comparison: Summary Statistics
:name: tab-summ-stats

| Metric | GPT-4o | GPT-4o-mini |
|--------|--------|-------------|
| Mean ETI | 0.364 | 1.280 |
| Median ETI | 0.000 | 1.140 |
| % Same Income | 80.5% | 3.1% |
| Observations | 15,985 | 15,999 |
```

Key observations:
- **GPT-4o**: Mean ETI (0.364) very close to Gruber & Saez (0.40)
- **GPT-4o-mini**: Shows much higher responsiveness (ETI = 1.28)
- **Non-response**: GPT-4o exhibits realistic "stickiness" with 80.5% reporting unchanged income

## Distribution of Responses

```{figure} ../images/eti_by_income.png
:name: fig-eti-income
:width: 100%

Average ETI by income level. The figure shows heterogeneity in tax responsiveness across the income distribution.
```

## ETI Heterogeneity Analysis

To understand variation across income levels and tax changes, we estimate:

$$\text{ETI}_i = \beta_0 + \beta_1 \cdot \text{Income}_i + \beta_2 \cdot |\Delta\text{MTR}|_i + \beta_3 \cdot \text{Income}_i \times |\Delta\text{MTR}|_i + \epsilon_i$$

```{table} Regression Results
:name: tab-obs-regs

| Variable | GPT-4o | GPT-4o-mini |
|----------|--------|-------------|
| Constant | 0.440*** | 1.224*** |
| | (0.057) | (0.017) |
| \|ΔMTR\| | -6.797*** | 0.671*** |
| | (0.865) | (0.257) |
| Income × \|ΔMTR\| | 1.123* | 0.934*** |
| | (0.649) | (0.193) |
| R² | 0.020 | 0.028 |

Note: Income measured in $100,000s. Heteroskedasticity-robust standard errors in parentheses.
*p<0.1; **p<0.05; ***p<0.01
```


## Model Interpretation

The regression results reveal important differences between models:

1. **GPT-4o**: 
   - Larger tax changes → smaller ETIs (negative coefficient on |ΔMTR|)
   - Suggests diminishing marginal responses or optimization frictions
   - Pattern consistent with empirical literature on adjustment costs

2. **GPT-4o-mini**:
   - Larger tax changes → larger ETIs (positive coefficient on |ΔMTR|)
   - More mechanical/linear response pattern
   - Less incorporation of real-world frictions

3. **Both models**:
   - Higher-income taxpayers more responsive (positive interaction term)
   - Consistent with empirical findings on income heterogeneity