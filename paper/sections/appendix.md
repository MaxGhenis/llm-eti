# Appendix: Archived prompt instrument {.unnumbered}

The following is the exact common template preserved with the June 2026
archive. Braced fields were populated for each scenario using the formatting
shown.

```text
You are a taxpayer with the following profile:
- Last year, your broad income was ${broad_income:,.0f}
- Last year, your taxable income was ${taxable_income:,.0f}
- Last year, your marginal tax rate was {int(mtr_last * 100)}%

Due to a change in tax law, your marginal tax rate this year will be
{int(mtr_this * 100)}%.
Your broad income before any adjustments or changes in behavior would be
approximately the same as last year.

Given this change in tax rates, you may adjust your behavior -- for example,
how much you work, your charitable contributions, retirement savings, or the
timing of income realizations like capital gains. What would your broad
income be this year? And what would your taxable income be?

Respond with exactly one JSON object and nothing else:
{"broad_income": <number or null>, "taxable_income": <number or null>}
```

Claude Haiku 4.5 and DeepSeek V3 additionally received this suffix:

```text
Do not use null. Return your best numeric estimates even if approximate. Use
whole-dollar amounts.
```

Two responses were requested per scenario. The first request used EDSL 1.0.7's
universal cache; parser retries disabled that cache and allowed up to three
attempts. Provider decoding parameters, failed-attempt rows, response IDs, and
per-response cache-hit status were not retained.

## Full primary regression results

{{< include generated/regression_details.md >}}

: Primary taxable- and broad-income regressions. Standard errors and 95% confidence intervals use the stated one-way cluster-robust covariance estimator; clusters are source year by tax-unit identifier. {#tbl-regression-details}
