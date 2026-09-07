# Appendix: why the capped laboratory estimates are withheld

An earlier project draft attempted to reproduce the laboratory tax experiment
of @PfeilEtAl2024. It is separate from the archived taxable-income prompts
analyzed above. We withhold that draft's structural notch-elasticity estimates
and asserted numerical bounds. This appendix explains our identification
argument and audits the retained lab inputs; it does not report a new
experimental replication.

## A cap does not locate the marginal buncher

The source instrument permits zero choices and assigns a maximum of
$E\in\{14,16,20,21,22,24,25,30\}$ tasks, with gross income $z=20q$ cents.
The progressive schedule leaves 75 percent of gross income through 400 cents
and 50 percent of the entire income above that threshold. The flat schedules
leave 75 or 50 percent throughout. These menus come from the source design and
instrument [@PfeilEtAl2024, Table 2 and Appendix B]. Our reference harness uses
integer choices $q\in\{0,\ldots,E\}$; enforcement of an integer step in the
original human input screen is not established by the recovered screenshots.
The following dominance argument also holds for fractional choices.

At 20 tasks, progressive disposable earnings are 300 cents. Every feasible
choice strictly between 20 and 30 tasks gives less consumption for more work;
30 tasks gives the same consumption for more work. Under utility increasing
in consumption and strictly decreasing in work, all these choices are
dominated by 20. With only weak work aversion the endpoint can tie, but supplies
no interior tangency. When $E=20$, a choice at the notch is also a cap choice
under either flat schedule.

The 200-cent dominated width is budget geometry, not an observed displacement
of a marginal buncher. The structural and reduced-form formulas of
@KlevenWaseem2013 [equations 5--6 and 11--12] require the appropriate behavioral
displacement and maintained model; their equation 12 is an upper-bound
approximation, not a mechanical lower bound. @Kleven2018 gives distinct
approximations in equations 4--5. Substituting the experimental cap or the
dominated width does not supply the missing behavioral input.

A constructive counterexample makes the limitation precise. For any positive
elasticity parameter $e$, use quasi-linear utility $c-V_e(q)$, where
$V_e(q)=600( q/60)^{1+1/e}/(1+1/e)$. Its marginal effort cost is
$10(q/60)^{1/e}$. Over the capped menus, every such parameter produces flat-tax
choices $q=E$ and progressive choices $q=\min(E,20)$. A sufficiently large
participation cost additionally produces zero choices for any of these
parameters. Identical capped choices can therefore accompany arbitrarily
small or large positive uncapped elasticities. This establishes lack of global
identification under the stated model, not that every possible dataset has
the same identified set under all added restrictions. Observing dominated
choices can instead reject maintained preferences or decision assumptions;
it does not select a unique structural elasticity. We report neither a point
estimate nor numerical structural bounds from these archives.

## Named alternatives and their acceptance conditions

With a verified design and complete selected grid, define an outcome
$g(q,E)$ as tasks, gross cents, utilization $q/E$, participation, cap choice,
exact-notch choice or above-notch choice. All level outcomes retain valid
zeros. Notch-choice outcomes use caps above 20 so that the notch is not the
cap. Average within each subject, phase and cap, then apply declared fixed
cap weights, then give each subject equal weight. These are
**endowment-standardized outcomes**, not inferred human assignment probabilities.
The reference defaults to equal weight over the source cap menu; it never
reweights surviving cells or drops incomplete subjects to fabricate a panel.

Under random assignment, consistency, no interference, exogenous cap assignment
and appropriate completion handling, a post-period contrast against the
progressive-to-progressive control describes the total effect of assignment
to a sequence, including its history. For progressive-to-flat arms, a change
contrast against that control can describe a reform effect under the additional
common-prehistory and no-anticipation assumptions. For flat-to-progressive
arms it remains a change in sequence-assignment effects: the experiment lacks
the corresponding flat-to-flat controls needed to isolate introducing the
notch without further history/trend assumptions.

A utilization-level contrast is a proportion or percentage-point effect,
not a log-income coefficient. A mean-log outcome is undefined on a zero;
we do not delete zero choices or add a constant. The log of a standardized
mean instead retains zeros in the mean, provided every required mean is
positive, and combines participation with positive-income responses.
Normalizing an appropriate log contrast by a common log net-of-tax change
requires a fixed target and justified comparison. It yields a named finite
response under the experimental caps, not automatically a structural or human
policy ETI. A normalized contrast across the notch is especially sensitive to
changes in the whole choice menu, which a single branch rate does not summarize.

Inference additionally requires verified independent units. The reference
resamples whole subject vectors within assigned arm, preserving all repeated
rounds, signed effects, zeros and undefined draws. It reports every attempted
draw and withholds its percentile interval if the point or any draw is
undefined. More rows do not establish more independent subjects. Completion
ranges for bounded missing outcomes require the full planned inventory,
including wholly absent subjects; such finite-sample ranges are neither
confidence intervals nor elasticity bounds. The deterministic regressions
exercise these rules using explicitly synthetic data only.

## What the retained observations can support

{{< include generated/legacy_lab_audit.md >}}

The pickle preserves free-text answers and provider response objects; every
stored answer matches its retained response payload. Its stored rate pairs
also agree with the same-revision historical collection code, but no run-bound
delivered instrument or complete planned/attempt inventory was retained.
That code describes stateless prompts and a different cap menu, not verified
independent human-style subjects. We do not convert ambiguous answer text into
a task choice. The Gemini CSV contains recorded numeric choices but no raw
provider answers, and contains only the progressive-to-flat-25 sequence.
Neither archive satisfies the reviewed endowment-grid and provenance contract.
Accordingly, standardized outcomes, causal contrasts, subject-bootstrap
intervals and missing-outcome completion ranges are all withheld. The raw
archives, exact hashes and machine-readable reasons accompany the code;
they do not alter the taxable-income responses analyzed in the main paper.

The recovered human instrument and the public registration are source evidence,
not participant microdata. As checked on September 7, 2026, trial 8410 reports
that study data are not publicly available [@PKNFRegistry]. The later article's
institutional archive supplies the paper and instrument appendix and states
that data are available on request [@PfeilEtAl2025]. Human Table 6 has therefore
not been reproduced. An instrument screenshot, a printed regression coefficient
or a synthetic recovery check cannot substitute for the subject-level data,
assignment inventory and analysis code needed for that comparison.
