# Identification decision

Withhold the PKNF notch-based structural ETI point estimate and both asserted numerical bounds. A randomized experiment can identify effects of its assigned tax schedules without identifying the derivative of uncapped earnings with respect to a smooth marginal net wage. In this experiment, the entire feasible above-notch range is dominated under standard preferences. The marginal buncher required by the cited estimator cannot be recovered by treating the cap as its location. This is our identification argument, not a conclusion attributed to the human paper.

The offline code accompanying this note is a specification and a synthetic falsification/recovery harness. It is not an estimator applied to human or LLM observations. Source locations and retrieval limits are in [SOURCES.md](SOURCES.md).

# Budget set and support

Let q be integer tasks, E the assigned task maximum, z=20q gross cents, and K=20E. Choices satisfy q∈{0,...,E}. For the original eight E values, K never exceeds 600 cents. Write disposable task earnings as

```
c_P(z) = 0.75 z   if 0 <= z <= 400,
         0.50 z   if 400 < z <= K;
c_25(z) = 0.75 z;    c_50(z) = 0.50 z.
```

The fixed show-up payment does not alter the following dominance comparison. See [PKNF design and Table 2, PDF pp. 10-12](https://www.ifo.de/DocDL/cesifo1_wp11350.pdf#page=10).

At z*=400, c_P=300. For 400<z<600, consumption is strictly smaller and work strictly greater. At z=600 consumption is equal but work greater. Thus, if utility increases with consumption and strictly decreases with work, every feasible q>20 is strictly inferior to q=20. With only weak aversion to work, q=30 can tie q=20; it still provides no interior tangency. For E<=20 the notch is inaccessible; E=20 makes the notch location a cap even under flat taxes. For E>20, the nondominated progressive menu ends at 20 tasks. With positive marginal effort cost, the optimum is no higher than 20 regardless of how small or large a smooth unconstrained elasticity is. Intrinsic enjoyment of tasks, mistakes, social preferences, and dynamics can violate these utility assumptions; observing dominated choices does not uniquely identify which mechanism operates.

The mechanical dominated width is

```
D = Δt z* / (1-t-Δt) = 0.25*400/0.50 = 200 cents.
```

It is a property of the budget set. It is not a measured Δz* or a lower bound on elasticity. [KW equation 6, printed pp. 676-677](https://www.mazharwaseem.com/static/uploads/Kleven_Waseem_2013.pdf#page=8) explicitly permits this limiting response with elasticity tending to zero. The frictionless marginal buncher's unconstrained baseline earnings lie beyond z*+D for positive elasticity, outside PKNF support. Even perfect recovery of the observed flat-tax distribution does not recover the latent earnings distribution above each cap.

# What the cited equations say

Let Δz* denote the estimated counterfactual earnings displacement of the marginal buncher, r=Δz*/z*, t the lower proportional rate, and Δt its upward jump. [KW equations 11-12, printed p. 687](https://www.mazharwaseem.com/static/uploads/Kleven_Waseem_2013.pdf#page=19) give

```
t_implicit = t + Δt (1+r)/r,
e_KW12 approximately r² / [Δt/(1-t)].
```

The paper labels this an upper-bound approximation. Its numerator is behavioral, its net-of-tax scaling uses the lower rate, and its approximation does not become exact by using the upper net-of-tax rate. The separate friction-adjusted bunching-hole lower-bound discussion is a different argument with density/friction assumptions.

[Kleven's August 2018 clarification, PDF pp. 2-3](https://www.henrikkleven.com/research/published/notchelasticity_kleven_2018.pdf#page=2), supplies

```
equation 4: e_R approximately r² / {2 [Δt/(1-t)]},
equation 5: e_R approximately r² / {(2+r) [Δt/(1-t)]}.
```

The second formula underlies the original paper's reported reduced-form tables. These are approximations conditional on an identified response and suitable interior geometry; neither is a rescue for PKNF. For a mechanical r=D/z*=0.5, the three displayed expressions yield 0.75, 0.375, and 0.30, respectively. These are **invalid plug-in demonstrations**, not estimates or bounds for this experiment. Using the upper-rate denominator instead produces the reviewed 0.5. No-response data leave that mechanical number unchanged. The sizable 25-point rate jump also undermines a small-notch approximation. At r=0.5, the exact implicit marginal tax rate is 1; shorter hypothetical segments imply rates above 1, so a smooth positive net-wage interpretation already fails geometrically.

# Constructive nonidentification

An additional executable check in `kw_reference.py` solves the exact continuous, uncapped [KW equation 5](https://www.mazharwaseem.com/static/uploads/Kleven_Waseem_2013.pdf#page=8) for the marginal buncher's response given a known elasticity, then recovers that elasticity by inversion. A separately evaluated utility-indifference equality verifies the transcription. For e∈{0.05,0.2,0.5,1,2}, both the counterfactual marginal buncher and the post-notch interior alternative exceed 600 cents. Setting r mechanically to 0.5 instead supplies no positive-elasticity solution in the tested bracket. This reference exercise illustrates the identifying geometry in a model that has the required support; it does not estimate PKNF responses.

Consider the following explicitly synthetic quasi-linear preferences, for any finite e>0:

```
U_e(q;s) = c_s(20q) - V_e(q) - F 1{q>0},
V_e(q) = 600/(1+1/e) * (q/60)^(1+1/e).
V'_e(q) = 10 (q/60)^(1/e).
```

Under an uncapped flat schedule with net task wage w, q*(w)=60(w/10)^e, so d log q*/d log w=e. For every PKNF cap, V'_e(q)<10 on positive feasible q; flat25 and flat50 therefore choose E when F=0. Prog chooses min(E,20) by the same monotonicity below 20 and dominance above it. Every e>0 yields the **same complete vector of choices across all three schedules and all eight caps**. A subgroup with F=1000 chooses zero in every menu, and its mixture share can be held identical across models. In particular, e=0.2 and e=2 produce identical choices even including nonparticipation. As e can be arbitrarily close to zero or arbitrarily large, these observations support neither a positive universal elasticity floor nor a finite universal ceiling.

This counterexample establishes failure of global point identification from the experimental design under an already restrictive structural family. It does not assert that every possible observed dataset is compatible with every e. Additional parametric restrictions, known heterogeneity, repeated individual preferences, and uncapped interior flat choices can restrict a model-specific identified set. Discrete observations then give utility inequalities U(q_observed)>=U(q) for every feasible alternative, with weak inequalities at ties. They do not automatically give the continuous first-order or marginal-buncher equality. A structural estimate would require stating those assumptions, solving that discrete capped choice model including F, and showing its identified set/sensitivity; a point number forced by a likelihood is not an identification proof.

Pooling cap distributions compounds the problem: cap masses and the 20-cent grid invalidate a smooth density interpolation around 400. Restricting to E>20 removes the cap-at-notch cases but does not restore the missing support above 600. A randomized flat25 comparator can identify excess **probability at 400** on matched support; it cannot identify the latent marginal buncher's uncapped income. With entry/exit or moves below 400, missing mass above the notch need not equal excess mass at 400. The local continuous participation argument in [KW Section II.A.4, printed pp. 685-687](https://www.mazharwaseem.com/static/uploads/Kleven_Waseem_2013.pdf#page=17) cannot simply be imposed on the ten above-notch discrete choices.

# Deliverable estimands

The implementable definitions, exposure table, correct log normalization, zero policy, subject-resampling contract, and causal assumptions are in [SPECIFICATION.md](SPECIFICATION.md). Primary targets are zero-inclusive, endowment-standardized effects of assigned treatment sequences and common-prehistory reforms, together with cap and exact-notch choice probabilities. Smooth-price log normalization is restricted to a named population and labeled separately from structural notch ETI. `estimands.py` implements these summaries for complete selected subject/endowment panels; `synthetic.py` supplies only artificial data-generating processes; `test_estimands.py` verifies the claims offline.
