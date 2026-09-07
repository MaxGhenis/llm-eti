# Archived June 2026 tax-response protocol

This file records the prompt used to create the archived corpus. It is preserved
for provenance and should not be treated as a preregistered future protocol.

## Common prompt template

The template text from the first `Y` through the closing `}` below is encoded as
UTF-8 with LF line endings and no trailing LF. Its SHA-256 is
`52754080153c4982d9a43349560a853a9fac791d8d84abcc3adb6ba3ffe4973d`.
The line break immediately before the closing Markdown fence is not part of the
digest.

```text
You are a taxpayer with the following profile:
- Last year, your broad income was ${broad_income:,.0f}
- Last year, your taxable income was ${taxable_income:,.0f}
- Last year, your marginal tax rate was {int(mtr_last * 100)}%

Due to a change in tax law, your marginal tax rate this year will be {int(mtr_this * 100)}%.
Your broad income before any adjustments or changes in behavior would be
approximately the same as last year.

Given this change in tax rates, you may adjust your behavior -- for example,
how much you work, your charitable contributions, retirement savings, or the
timing of income realizations like capital gains. What would your broad
income be this year? And what would your taxable income be?

Respond with exactly one JSON object and nothing else:
{"broad_income": <number or null>, "taxable_income": <number or null>}
```

## Suffixed prompt template

DeepSeek V3 and Claude Haiku 4.5 received the common template followed by
exactly two LF bytes and the one-line suffix shown in the complete template
below. The complete UTF-8 template has no trailing LF and has SHA-256
`3d9029a7e0f0d559f5bf87eef621541588792c5a4649fe95de109277670d4011`.

```text
You are a taxpayer with the following profile:
- Last year, your broad income was ${broad_income:,.0f}
- Last year, your taxable income was ${taxable_income:,.0f}
- Last year, your marginal tax rate was {int(mtr_last * 100)}%

Due to a change in tax law, your marginal tax rate this year will be {int(mtr_this * 100)}%.
Your broad income before any adjustments or changes in behavior would be
approximately the same as last year.

Given this change in tax rates, you may adjust your behavior -- for example,
how much you work, your charitable contributions, retirement savings, or the
timing of income realizations like capital gains. What would your broad
income be this year? And what would your taxable income be?

Respond with exactly one JSON object and nothing else:
{"broad_income": <number or null>, "taxable_income": <number or null>}

Do not use null. Return your best numeric estimates even if approximate. Use whole-dollar amounts.
```

The parser used for these responses is archived verbatim in
`protocols/legacy_income_parser.md`.

## Known orchestration settings

- EDSL: 1.0.7
- Responses requested per scenario: 2
- First attempt: universal cache enabled
- Parser retries: cache disabled
- Maximum parser attempts: 3

Provider decoding parameters, failed attempt rows, provider response IDs, and
per-response cache-hit status were not archived.
