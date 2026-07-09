# Archived June 2026 tax-response protocol

This file records the prompt used to create the archived corpus. It is preserved
for provenance and should not be treated as a preregistered future protocol.

## Common prompt

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

## Formatting suffix

DeepSeek V3 and Claude Haiku 4.5 additionally received:

```text
Do not use null. Return your best numeric estimates even if approximate. Use
whole-dollar amounts.
```

## Known orchestration settings

- EDSL: 1.0.7
- Responses requested per scenario: 2
- First attempt: universal cache enabled
- Parser retries: cache disabled
- Maximum parser attempts: 3

Provider decoding parameters, failed attempt rows, provider response IDs, and
per-response cache-hit status were not archived.
