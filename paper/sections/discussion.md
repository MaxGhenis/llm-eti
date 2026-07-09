# Discussion

## What the archive shows

The four models do not produce a common taxable-income response distribution.
Claude usually returns a positive and comparatively smooth response. DeepSeek
often returns the baseline but generally moves in the economically predicted
direction when it changes income. Gemma and GPT-4o mini usually preserve the
baseline, yet a minority of answers produce large or zero-dollar adjustments.
A single average ratio obscures these differences.

Broad income also matters. Claude changes both broad and taxable income,
whereas the other models' average taxable-income responses come mostly through
the difference between the two measures. That pattern is compatible with the
adjustment channels named in the prompt, but it does not establish that people
use those channels to the same degree.

## Why these are not ETI estimates

An empirical ETI estimate requires a design that identifies human responses to
tax incentives. This exercise elicits numeric completions from language models
under hypothetical scenarios. No taxpayer chooses, no reform is observed, and
no counterfactual trend is identified. Similarity between a model-implied slope
and a published ETI estimate would therefore be descriptive, not validation.

Training-data exposure adds ambiguity: a model may reproduce phrases, numbers,
or qualitative claims from the tax literature. It may also respond to surface
cues or copy the supplied baseline. The same-rate check, baseline mass, and
sensitivity to tail responses show why a plausible average cannot distinguish
learned economic structure from prompt-conditioned generation.

## Appropriate uses

LLM elicitation can still help researchers generate hypotheses about adjustment
channels, expose prompt assumptions that deserve tests, compare how model
families encode a stylized policy question, and stress-test structured-output
contracts before human data collection. The present evidence does not support
using an LLM response slope to score a tax proposal, replace administrative-data
analysis, or forecast a person or population.

## Limitations

1. **Incomplete run provenance.** The outputs and prompt implementation are
   archived, but failed attempts, response IDs, decoding parameters, retry
   numbers, and cache hits are not.
2. **Model-specific formatting.** Claude and DeepSeek received a non-null,
   whole-dollar suffix, preventing a perfectly identical prompt comparison.
3. **Differential coverage and year imbalance.** The source sample is weighted
   toward 2023 because of order-dependent trimming, and DeepSeek's missing
   coverage is concentrated in 2024. Year-stratified estimates expose but do
   not eliminate this selection.
4. **Cross-model outcome selection.** The common comparison panel requires
   positive answers from every model. Model-specific clean-pair sensitivities
   address but do not remove that design tradeoff.
5. **Delivered-value rounding.** More than one fifth of source scenarios display
   no integer rate change. A prospective design should use prespecified,
   meaningful changes.
6. **Boundary and tail behavior.** Zero-dollar and extreme responses make mean
   slopes transformation- and trimming-sensitive.
7. **No human benchmark.** The archive cannot establish whether any model
   resembles a matched human sample.
8. **Moving aliases.** Several identifiers are provider aliases rather than
   immutable weight or API snapshots.

## A prospective design

A confirmatory follow-up should preregister a common prompt, balanced and
economically meaningful tax-rate changes, and immutable model snapshots where
available. It should store a row for every attempt, including code commit,
prompt hash, scenario ID, provider and model revision, decoding parameters,
cache status, retry number, raw response, parsed response, and failure reason.

Repeated calls should be explicitly uncached and analyzed as within-prompt
variation. Structured distributions over response bins would reveal more than
a single point completion. Prompt variants, alternative mappings from answers
to outcomes, exclusion rules, and any human comparison should be specified
before outcomes are viewed.

## Conclusion

The archived models encode sharply different responses to the same stylized tax
question. Those responses can be studied as model outputs, but they do not
recover a human elasticity of taxable income. Exact prompt rendering, immutable
provenance, failure accounting, balanced treatments, and distribution-aware
summaries are prerequisites for credible economic research with language
models.
