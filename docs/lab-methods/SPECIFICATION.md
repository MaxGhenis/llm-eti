# Analysis contract

Use the treatment sequence as the assignment, the subject as the independent experimental unit, and a declared distribution over endowments as the target. Do not label the resulting finite contrasts structural notch ETI. This reference implementation is offline, Python standard-library only, and intentionally rejects unsupported panels. Its synthetic reference schedule presents every original endowment once per half, with reversed order in the second half. That permutation is an implementation fixture, not a verified transcription of the human archive.

An input observation has `subject`, `arm`, `round` (1-16), `endowment` (one of the eight original task caps), and `tasks` (integer 0 through endowment). `None`, fractional, nonfinite, negative, and out-of-cap responses are invalid; none become zero or a clipped answer. Subject IDs must be globally unique and assigned to a single arm; subject-round keys cannot repeat. The upstream analysis owner must additionally supply the full planned-row inventory, immutable run/instrument version, actual independent draw/cache provenance, and missing-attempt inventory before using these functions on real data. A panel with a missing *entire subject* cannot be diagnosed from completed observations alone.

For metric g, within subject i and phase p, form

```
S_ip(g;π) = Σ_e π(e) [1/n_ipe Σ_{r in (i,p,e)} g(q_ir,e)].
μ_ap = 1/N_a Σ_{i:A_i=a} S_ip.
```

The weights π are prespecified, strictly positive on the named target support, and sum to one. The default is uniform across all eight caps; the notch-choice default is uniform across the five caps above 20. These are declared standardized targets, not inferred human assignment probabilities. Every included subject must have at least one observation for every selected phase/endowment cell. Within-cell repetitions receive equal weight, then endowments receive π, then subjects equal weight. Missing selected cells abort with a named error; the implementation never reweights the remaining cells. If the human design is not a complete grid, use its verified assignment probabilities or an explicitly specified cell-standardization/regression estimator; do not drop incomplete subjects and call that an ITT. The executable reference is not a general attrition estimator or a reproduction of Table 6's controlled regression.

| Outcome g | Target and interpretation | Zero handling |
| --- | --- | --- |
| q; 20q | Mean tasks; mean gross cents under assigned sequence | Retained |
| q/E | Mean labor utilization on [0,1]; multiply effects by 100 for percentage points | Retained |
| 1{q>0} | Participation probability, separately from changing any positive decision | Retained as zero |
| 1{q=E} | Cap-choice probability; flags constraints without selecting on cap outcomes | Retained as zero |
| 1{q=20}, E>20 | Exact-notch probability on an opportunity-to-cross population | Retained in denominator |
| 1{q>20}, E>20 | Above-notch choice probability; under Prog a dominance diagnostic under stated utility assumptions | Retained in denominator |
| log(20q) | Mean log gross income on an ex ante fixed positive-outcome population, if all outcomes are actually positive | Undefined on any zero; no automatic deletion |

The level difference in exact-notch probabilities across comparable schedules is a signed excess-probability statistic. For example, π-standardized pre-period Prog versus Flat25 under randomized assignment can estimate a difference between early schedule exposures (averaged over the declared rounds). It is neither B/h0 nor a structural elasticity. An excess probability can be negative or zero and remains reportable as such. The API provides post and change contrasts; constructing a first-half-only contrast requires passing a separately named first-half statistic, not silently mixing phase histories.

For causal effects, define potential outcomes under full sequences a. Under random assignment, consistency, no interference, and appropriate handling of completion/attrition, the primary post contrast is

```
τ_post(a,PP;g,π) = μ_a,post(g;π) - μ_PP,post(g;π).
```

This identifies a total effect of assignment to the sequence, including learning, history, framing and the final schedule. Randomized endowments must be exogenous; holding their target mix fixed removes composition differences. For Prog→Flat25 and Prog→Flat50, the control and reform arms have the same pre schedule. Assuming no anticipation of the future arm, the corresponding change contrast

```
δ(g;π) = [μ_a,post - μ_a,pre] - [μ_PP,post - μ_PP,pre]
```

can estimate the reform effect using the common-prehistory comparison. Pre outcomes can also be used in a prespecified baseline-adjusted post regression. No significance test on pre differences proves no anticipation. For Flat25→Prog and Flat50→Prog, comparison with PP identifies a **sequence effect** in the post period, while δ is a change in assignment effects; it does not isolate introducing a notch after a flat history. The design lacks Flat25→Flat25 and Flat50→Flat50 controls. Calling those change contrasts isolated reform effects requires an additional untreated-trend/history assumption. A difference between the two reversal arms is also a sequence contrast, not automatic evidence of a structural asymmetric elasticity.

# Affected populations and denominators

Two different exposure concepts are needed.

1. **Menu exposure**, determined without conditioning on a response. Prog↔Flat25 changes the menu only for E>20; this population includes q=20 bunchers and q=0 nonparticipants. For E<=20 the monetary menus coincide, so observed changes there can still reflect history/framing/spillovers. Prog↔Flat50 changes positive low-effort alternatives at every E. For E<=20 the entire positive menu has a common proportional net-wage change; this is the strongest existing design region for a price-normalized contrast.
2. **Fixed-reference tax exposure**, defined with a prespecified pre-reform reference q_i0(e) at the *same endowment*. For example use the mean of that subject's pre observations at e, selected before examining post outcomes; save the rule and q_i0. Evaluate both statutory tax schedules at the fixed positive reference earnings; do not classify using post income or realized tax rates. This describes mechanical exposure at the reference, not all effects on the choice menu. Under reversal arms, the pre choice already depends on the initially randomized schedule; such selected groups are not comparable random subgroups across arms. Even in common-prehistory arms, selecting pre outcomes requires no anticipation and a fixed comparison rule, and can produce regression-to-the-mean patterns.

| Reform | Menu-exposed support | Positive fixed-reference choices with a branch-rate change | d = log[(1-t_after)/(1-t_before)] on that branch |
| --- | --- | --- | --- |
| Prog→Flat25 | E>20 | q_i0>20 | +log(1.5) = +0.4054651081081644 |
| Prog→Flat50 | Every E | 0<q_i0<=20 | log(2/3) = -0.4054651081081644 |
| Flat25→Prog | E>20 | q_i0>20 | -log(1.5) = -0.4054651081081644 |
| Flat50→Prog | Every E | 0<q_i0<=20 | +log(1.5) = +0.4054651081081644 |

Other positive reference choices have d=0; q_i0=0 has zero tax liability under both schedules and no defined average tax rate. Keep zero choices in menu-exposed populations and analyze participation separately. At q=20 this table describes the proportional rate on the reference income, not a smooth two-sided marginal incentive: the next task under Prog lowers disposable earnings by 90 cents. Never call the table a continuous marginal tax rate at the notch.

The log normalization of a mean-log change contrast is

```
ε_finite,G = δ_G(log z) / log[(1-t_after)/(1-t_before)].
```

This requires a fixed target G with a common, meaningful price change, positive log outcomes, and a valid comparison. A log-income contrast divided by 0.25 for the 50%→25% change is inflated by log(1.5)/0.25=1.6218604324 relative to this definition. Retain full floating-point coefficients; format after inference. A utilization coefficient such as Table 6's 0.083 is a proportion/percentage-point effect, not log income and not an elasticity numerator.

For E<=20 in Prog→Flat50 versus PP, the menu is linear and d=log(2/3), including the same direction for all positive choices. Report the zero-inclusive level and participation effects first. If the fixed sample has positive outcomes, a normalized log contrast can be reported as a **finite labor-supply response under the experimental caps**. Interpreting it as a structural compensated elasticity additionally needs stable isoelastic preferences, no income effects, no fixed-cost selection, no meaningful discretization/cap effects, and no nonprice treatment pathways. These conditions hold by construction only in the known-response synthetic fixture. Dropping observed cap hitters or zero choosers to enforce them selects on outcomes; it does not establish them.

For E>20, both notch removal and introduction change global alternatives and discrete tax liability. At q_i0=20, Prog→Flat25 can induce a large increase despite d=0 at the reference. Dividing the whole exposed population's response by log(1.5) is at most a **policy-shock-normalized contrast** using a named arbitrary scale; it is not an identified ETI. A denominator averaged over endogenous realized rates is not a cure. Instrumenting a single local rate with assignment would require exclusion of all the other menu/income/history channels, which this notch treatment does not supply.

# Zero-inclusive log summaries

When all four standardized mean-income cells are strictly positive, define

```
δ_logmean = [log μ_a,post(z) - log μ_a,pre(z)]
            - [log μ_PP,post(z) - log μ_PP,pre(z)].
```

This includes valid zeros in μ and is invariant to changing cents to dollars. It differs from δ(log z). For each target population/time cell, μ(z)=p*m_plus, where p=Pr(z>0) and m_plus=E[z|z>0] under that same standardized distribution; hence log μ=log p+log m_plus. Its normalized response combines participation and positive-income composition/intensity. The synthetic entry-cost fixture has structural intensive e=1 but a log-mean normalized contrast of 2; the decomposition explains the difference. If a cell has zero mean, this log contrast is undefined; do not add one, epsilon, or an asinh transform and retain the elasticity label.

Separately reporting E[log z|z>0,A=a,p] is possible with cell-by-cell counts, but it compares selected populations and is descriptive. A causal intensive-margin target among subjects positive under both potential regimes is a principal-stratum estimand; positivity in observed rounds or pre participation alone does not identify that stratum. If a transformation such as asinh is wanted, preregister its units and interpret it as a transformed-outcome treatment effect, not an ETI.

# Independent-subject uncertainty

The implementation averages within subjects and resamples whole subject pre/post/endowment vectors with replacement **within assigned arm**, preserving arm size and pairing. Each occurrence of a resampled subject counts, even if its source ID repeats; there is no regrouping that erases multiplicity. The equivalent two-period level estimator is a difference of mean subject changes. Under independent subjects a standard error is sqrt(s²_Δ,a/N_a+s²_Δ,PP/N_PP); an adjusted regression must cluster at that same unit. If assignment used blocks or clusters above subjects, reproduce those in inference instead. A common control reused across many contrasts creates correlated estimates; joint comparisons need a shared bootstrap control draw and prespecified multiplicity/equivalence procedures, not independent per-contrast intervals.

Use a persisted deterministic seed, report number of independent subjects, and retain every signed finite draw, including exactly zero. `cluster_bootstrap` returns all draws, sign counts, and reasons for undefined draws. Percentile intervals and the bootstrap SE are withheld if the point or any replicate is undefined; no inference conditional on positive effects, positive counterfactual density, or successful log draws is presented. The proportion undefined is itself an output. This conservative rule is an explicit choice of the reference implementation, not a claim that no alternative valid boundary inference exists. Negative denominators are applied to each draw before sorting the interval. A zero denominator returns an undefined estimate even if the numerator is also zero.

Percentile intervals are an illustrative subject-resampling procedure, not guaranteed finite-sample coverage. Small subject counts, boundary participation, and weak first stages need design-based randomization inference or other justified inference. More rounds do not increase the number of independent subjects. A synthetic no-effect fixture whose per-subject changes are exactly zero naturally gives a degenerate interval; that is an implementation check, not a power study or evidence of equivalence.

`uncertainty_design.py` additionally enumerates the exact sampling distribution for an independent-subject DGP with q_pre=8 and q_post∈{6,10}, each with probability 1/2, repeated within phase. At N subjects per arm the true contrast variance is 8/N. Treating R repeated rows as independent shrinks the estimated standard error by sqrt[(N-1)/(RN-1)] wherever the variance is positive. The audit compares normal-critical-value subject and naive-row Wald intervals and the exact conditional subject-bootstrap percentile limit. It evaluates every pair of binomial subject counts and records exact probability fractions; it is not a Monte Carlo coverage estimate. The report gives actual DGP-specific coverage, including departures from nominal 95%. Its inverse-discrete-CDF bootstrap quantiles differ from the finite-draw interpolated quantiles in `estimands.py`, so it is a method audit, not an exact coverage certification for that finite-B implementation.

For LLM data, a subject label by itself does not establish independence: cached repeats may be identical draws; independent stateless prompts do not create a persistent human-style subject. Confirm independent draws, state/history and any shared generation dependence before setting `independent_subjects_confirmed=True`. The code cannot authenticate those facts. Human-subject uncertainty, LLM sampling variability, model sensitivity, and human/LLM external validity are distinct. These synthetic tests support none of the latter claims.

# Missing bounded outcomes and executable exposure

`design_tools.reference_exposure` enumerates both finite menus and separately evaluates a fixed reference. It reports menu exposure, the reference tax-liability change, the branch-rate log change (undefined at a zero reference), and whether a common proportional scale change applies over the whole positive menu. It flags the nonsmooth reference at q=20 with E>20. This makes the key distinction executable: a Prog→Flat25 reference buncher at q=20 has zero branch-rate change while its E=30 menu changes. The function cannot verify that a reference was constructed before treatment outcomes; save that provenance separately.

`design_tools.completion_bounds` provides a different kind of bound that *is* defensible when the full planned inventory is known: the range of the finite-sample level contrast over every feasible completion of missing choices. It retains `tasks=None` as missing and observed `tasks=0` as nonparticipation. For each missing row, tasks lie in [0,E], gross cents in [0,20E], and utilization/indicator outcomes in [0,1]. Apply the same subject/cap/phase averaging and substitute lower/upper endpoints according to the contrast coefficient's sign. For a change contrast, treated-post and control-pre enter positively; treated-pre and control-post negatively. Indicators use feasible maximizing choices (q=20 for exact-notch probability), not mechanically the cap. The endpoints are attainable under these support-only assumptions; the set of possible interior values can be discrete.

These are **sharp finite-sample completion ranges**, not confidence intervals, bounds on a population causal effect, or bounds on structural elasticity. They impose no stable-preference or cross-round restriction. The full subject roster and all planned selected cells are required, including subjects with no completed responses. The main point-estimation API continues to reject missing observations. With no missing values these ranges collapse to the observed contrast. With missing values, do not present the midpoint as a point estimate or bootstrap only the completed records. To infer a population partially identified effect, add a justified design-based confidence procedure for the bounds; that procedure is outside this reference implementation. Log outcomes and elasticities are explicitly rejected by the completion-bound API.

# Handoff acceptance criteria

1. Suppress structural notch ETI and numerical bound claims in the owner's analysis; retain signed descriptive bunching probabilities.
2. Preserve planned rows, zero choices, failure counts, original cap labels, and independent-unit provenance. Abort rather than silently pool incompatible runs.
3. Declare sequence versus reform estimand, comparison arm, target cap weights, affectedness rule, units, and missingness policy before computing outputs.
4. Use utilization levels to compare with the 2024 human Table 6, with its controls and subject uncertainty once archive code/data are available. Do not normalize that coefficient as log income.
5. Apply log normalization only to a named log estimand/population; separately report zeros, caps, participation, and log-mean versus mean-log differences.
6. Run this offline harness, then reproduce matched human outcomes from the actual archive. Synthetic recovery alone never passes a human/LLM validation gate.
