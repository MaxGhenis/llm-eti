# What can LLMs tell us about the ETI?

**Jason DeBacker** (University of South Carolina) and **Max Ghenis** (PolicyEngine)

```{admonition} Abstract
:class: abstract

In this study, we employ large language models (LLMs) to investigate how these AI systems perceive and simulate behavioral responses to changes in tax policies. By leveraging the economic reasoning capabilities of state-of-the-art LLMs, such as Anthropic's Claude or OpenAI's GPT models, we simulate various tax filer scenarios and analyze the LLMs' responses to policy changes, such as modifications to statutory marginal tax rates or the Earned Income Tax Credit (EITC) phase-in range.

We begin by examining how LLMs perceive and simulate behavioral responses across different tax filer situations, including primary and secondary earners, capital gains income, and single filers with children. For each scenario, we vary household income levels to test for heterogeneity across the income distribution. By comparing the LLMs' simulated responses to empirical estimates from the literature, we assess the alignment between the AI-generated perceptions and real-world observations, highlighting similarities, differences, and potential insights beyond the available literature.

Furthermore, we delve into the "reasoning" behind the LLMs' simulated responses, exploring factors such as income and substitution effects, optimization frictions, and incomplete information. By analyzing the LLMs' explanations, we gain a deeper understanding of how these AI systems perceive and model complex economic decision-making processes.

This study contributes to the growing field of AI-assisted economic research by demonstrating the potential of LLMs to provide novel insights into behavioral responses to tax policy changes, complementing and extending the existing empirical literature. Our findings have implications for policymakers, researchers, and practitioners seeking to leverage AI technologies to inform economic policy decisions and advance our understanding of taxpayer behavior.
```

**Keywords:** AI, elasticity of taxable income

**JEL classification:** H21, H31

## Introduction

Large language models (LLMs) have been found to replicate human behavior in economic contexts. {cite}`BIN2023` estimate demand functions implied from an LLM and find that they match very closely those estimated from human preferences. {cite}`BrookinsDeBacker2024` show that LLMs elicit cooperation similar to humans in strategic games. {cite}`AHGW2024` use LLMs to replicate results from a number of social science experiments that used human subjects.

This paper extends the research on LLM responses in an economic context to explore an important parameter in public finance economics: the elasticity of taxable income (ETI). If LLMs are insightful regarding the ETI, there is potential for new research methods and questions and for the application of LLMs to tax policy and administration. For example, LLMs may allow one to explore heterogeneity one can't identify in observational data. For example, religion is not measured in administrative tax data, but there may be interesting differences in the elasticity of taxable income through differences in charitable giving across religiosity. LLMs also allow researchers to simulate tax policies that have not existed and approximate human responses. Even when laboratory or field experiments can be employed to measure taxpayer behavior, LLMs are orders of magnitude cheaper and may act as a substitute (or complement) to such experiments.

Furthermore, if LLMs prove insightful in this context, tax practitioners can use these to quickly explore how taxpayers might respond to changes in tax law or regulation, or to simulate hypothetical scenarios. Practitioners may also use LLMs to decompose different margins of responses (e.g., reporting versus real responses) that may not be directly observable in the data.

We take two approaches to elicit ETI estimates from LLMs. First, we replicate the controlled lab experiment of {cite}`PKNF2024`, but prompt LLMs rather than humans. Next, we replicate a seminal study of the ETI that uses observational data, {cite}`GruberSaez2002`. This provides a test of whether a (more) real-world context through which to evaluate the implied ETI from LLMs.

Our findings suggest that LLMs are broadly consistent with empirical estimates of the ETI. However, in several cases LLMs elicit ETIs towards the top end of empirical estimates, suggesting that LLMs may not take into consideration certain frictions that real taxpayers face.

The remainder of this paper is organized as follows. {doc}`results/pknf_replication` presents the replication of {cite}`PKNF2024`. {doc}`results/gruber_saez_replication` describes the use of LLMs in simulating the study of {cite}`GruberSaez2002`. {doc}`discussion` offers concluding thoughts.

```{note}
This is a reproducible research paper. All code and data are available on [GitHub](https://github.com/MaxGhenis/llm-eti). You can regenerate all results using the provided Makefile.
```