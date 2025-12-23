---
kernelspec:
  name: python3
  display_name: Python 3
---

# What can LLMs tell us about the ETI?

**Jason DeBacker** (University of South Carolina) and **Max Ghenis** (PolicyEngine)

```{code-cell} python
:tags: [remove-cell]

# Setup: Import paper results (single source of truth)
from llm_eti.paper_results import r
```

```{admonition} Abstract
:class: abstract

We investigate whether large language models (LLMs) can produce economically meaningful estimates of the elasticity of taxable income (ETI). Building on the emerging literature using LLMs as simulated economic agents ({cite}`Horton2023`), we conduct two complementary studies. First, we replicate the controlled laboratory experiment of {cite}`PKNF2024`, finding that LLMs exhibit bunching behavior at tax notches similar to human subjects, with implied ETI ≥ {eval}`r.pknf_gpt4o.eti`. Second, we conduct an original survey experiment asking LLMs to simulate taxpayer responses to hypothetical tax changes across varied personas and tax scenarios. GPT-4o produces mean ETI estimates ({eval}`r.gpt4o.eti`) remarkably close to canonical empirical estimates ({eval}`r.empirical_range`), while exhibiting realistic optimization frictions absent in smaller models. Our findings suggest LLMs have internalized economically sensible tax response behavior from training data, opening possibilities for rapid policy prototyping and exploring heterogeneity along dimensions unmeasured in administrative data.
```

**Keywords:** AI, elasticity of taxable income, behavioral simulation, large language models

**JEL classification:** H21, H31, C90

## Introduction

Large language models (LLMs) have emerged as promising tools for simulating human behavior in economic contexts. {cite}`Horton2023` introduced the concept of "homo silicus"—using LLMs as computational stand-ins for human economic agents—and demonstrated that GPT-3 could replicate classic behavioral economics findings. Subsequent work has confirmed that LLMs can simulate demand functions matching human preferences ({cite}`BIN2023`), exhibit cooperation patterns similar to humans in strategic games ({cite}`BrookinsDeBacker2024`), and predict outcomes of social science experiments ({cite}`AHGW2024`).

However, this nascent literature has also identified important limitations. {cite}`RossKimLo2024` find that LLM economic behavior is "neither entirely human-like nor entirely economicus-like," with models struggling to maintain consistent behavior across settings. {cite}`ChoiEtAl2025` show that while LLMs demonstrate reasonable group-level behavioral tendencies, they struggle with individual-level predictions using real human personas. These findings suggest LLMs may be useful for understanding aggregate patterns rather than predicting specific individual responses.

This paper extends the LLM-as-economic-agent research program to a critical parameter in public finance: the elasticity of taxable income (ETI). The ETI measures how taxable income responds to changes in marginal tax rates, synthesizing real behavioral responses (labor supply, savings) and reporting responses (timing, avoidance). Canonical estimates place the ETI in the range of {eval}`r.empirical_range` ({cite}`GruberSaez2002`; {cite}`SaezEtAl2012`), with significant heterogeneity by income level and response margin.

If LLMs can produce sensible ETI estimates, they offer several advantages for tax research:

1. **Cost efficiency**: LLM simulations cost orders of magnitude less than laboratory experiments or survey data collection
2. **Heterogeneity exploration**: LLMs can simulate responses along dimensions not measured in administrative data (e.g., religiosity, risk preferences, tax knowledge)
3. **Counterfactual analysis**: LLMs can evaluate tax policies that have never existed
4. **Mechanism decomposition**: With appropriate prompting, LLMs may distinguish real from reporting responses

We take two complementary approaches. First, we replicate the controlled laboratory experiment of {cite}`PKNF2024`, which measures labor supply responses to tax schedule changes including a progressive notch. This provides a clean benchmark where we can compare LLM behavior to human subjects under identical conditions.

Second, we conduct an original tax response survey asking LLMs to simulate how taxpayers with various demographic profiles would respond to marginal tax rate changes. Unlike prior "replications" of observational studies (which lack the identification strategies that make empirical estimates credible), we frame this as what it is: a survey experiment measuring LLM perceptions of tax response behavior.

Our findings suggest that LLMs—particularly larger models like GPT-4o—have internalized economically sensible priors about tax responses. GPT-4o produces mean ETI estimates close to empirical benchmarks and exhibits realistic optimization frictions ({eval}`r.gpt4o.non_response_rate` non-response rate), while GPT-4o-mini shows mechanical over-responsiveness. Both models correctly predict that higher-income taxpayers are more responsive to tax changes.

The remainder of this paper is organized as follows. {doc}`methods` describes our experimental designs. {doc}`results/pknf_replication` presents the lab experiment replication. {doc}`results/tax_survey` reports results from our original tax response survey. {doc}`discussion` discusses implications and limitations.

```{note}
This is a reproducible research paper. All code and data are available on [GitHub](https://github.com/MaxGhenis/llm-eti).
```
