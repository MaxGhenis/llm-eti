# Introduction

The elasticity of taxable income (ETI) summarizes how reported taxable income
changes when the marginal net-of-tax rate changes. Empirical ETI estimates do
not come from asking taxpayers what they might do. They depend on observed tax
reforms, comparison groups, and assumptions that separate behavioral responses
from income trends and other confounders [@GruberSaez2002; @SaezEtAl2012].

Large language models (LLMs) create a different object. A model can be shown a
hypothetical taxpayer and tax-rate change and asked to predict the taxpayer's
next income. Transforming that answer by the change in the net-of-tax rate
produces a *model-implied response ratio*. It does not identify a human
behavioral elasticity: no taxpayer makes a choice, no reform is observed, and
no comparison group identifies a counterfactual.

That distinction matters as researchers use LLMs to simulate economic agents
and human samples [@HortonEtAl2026; @ArgyleEtAl2023; @AherEtAl2023]. Selected
aggregate patterns may be reproducible, but model behavior can vary across
models, prompts, and elicitation settings [@RossKimLo2024]. A plausible-looking
numeric answer may reflect training-data exposure, the supplied baseline,
rounding, or a small number of tail responses rather than a stable behavioral
relationship.

We examine these concerns in an archived multi-model tax-response corpus. The
scenarios pair prior-year broad and taxable income with a marginal tax rate and
a hypothetical post-reform rate. Four primary models—Claude Haiku 4.5,
DeepSeek V3, Gemma 4 26B, and GPT-4o mini—each supplied up to two requested
responses per scenario. A fifth GPT-4o run stopped early and is retained only
for archive-coverage diagnostics.

Our contribution is methodological. We:

1. reconstruct the incomes and integer tax rates that the prompt displayed,
   rather than analyzing higher-precision values the models never saw;
2. compare four models on a common, conservatively cleaned scenario panel;
3. report baseline copying, directional consistency, medians, tails, broad- and
   taxable-income slopes, and exploratory sensitivities instead of relying on
   one average ratio; and
4. provide a deterministic pipeline from frozen CSVs to every number, table,
   figure, web page, TeX source, and PDF.

The models produce sharply different response distributions and substantial
scenario-ratio mean–median divergence. We interpret that instability as
evidence about the measurement properties of LLM elicitation—not as evidence
about taxpayer behavior.
