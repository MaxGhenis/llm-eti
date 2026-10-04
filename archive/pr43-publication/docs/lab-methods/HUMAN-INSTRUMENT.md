# Verified instrument and assignment evidence

The assigned source is the [2024 official PDF](https://www.ifo.de/DocDL/cesifo1_wp11350.pdf). PDF page numbers below are one-based; printed page numbers are two lower. [visual-audit.json](visual-audit.json) records 29 directly inspected page renderings with image hashes and page-specific notes. The instrument images are evidence about the displayed design, not recovered observations or executed experimental software.

## Decision and payment sequence

The study uses a pre-decision demographic survey, instructions, a practice transcription, control questions, 16 income decisions, a paid working stage for one selected decision, then a follow-up survey. Subjects see their applicable tax schedule and assigned income cap when choosing gross income. They see a summary after each choice. The general instructions tell them tax rates can vary; that screen does not disclose their whole treatment sequence in advance (Figure 14, PDF p. 57).

Figure 18 (PDF p. 61) shows a gross-income input, with a 480-cent cap in the example. Task count and tax payment are displayed automatically. The progressive schedule applies 25% to all income at or below 400 cents and 50% to all income above 400 cents. This is not a marginal-bracket display. Figure 19 (PDF p. 62) confirms the 400 gross / 100 tax / 300 net / 20 tasks example.

After all 16 decisions, one round is randomly selected for actual transcription and bonus payment. Figures 20 and 28 (PDF pp. 62, 70) explicitly illustrate a selected round with **zero income, zero required tasks, and a $1 completion payment**. The working screen permits continuation in that example. Thus zero is an allowed choice; the example supplies no estimate of the number of real zero outcomes. Nonselected decisions are still chosen-labor observations, not missing observations or 15 additional performed-work rounds.

## Caps, phases, and randomization

[cap-menu.csv](cap-menu.csv) transcribes the eight Table 2 cap/payoff rows. [treatment-sequences.csv](treatment-sequences.csv) transcribes Table 1's five sequences and reported subject counts. Rounds 1-8 are phase 0; rounds 9-16 are phase 1. The CSVs are design lookup tables, **not a planned or realized subject-round inventory**.

The paper reports randomly assigning a cap in each period. Footnote 7 (PDF p. 32) says restricting to caps above 20 leaves ten observations per subject. This suggests controlled cap exposure, but does not specify a shuffle, replacement rule, one occurrence per cap in each phase, a common order across phases, or an exact matching algorithm. No subject identifiers, cap-assignment logs, or implementation code were recovered. All those fields remain unknown in [design-manifest.json](design-manifest.json). Do not create a complete subject-by-cap grid from these tables and call it the human design.

The public [2022 registry](https://www.socialscienceregistry.org/trials/8410) specifies individual randomization by LIONESS Lab using JavaScript `Math.random()` and no clustered treatment assignment. That identifies a reported random-number source, not the assignment algorithm. Allocation probabilities, seed/state, blocking, cap permutation, and payment-round probabilities remain unverified. The same registration plans four interventions, 480 observations, and 120 per arm; it is not an exact plan for the five-arm 2024 reported sample.

The screenshot's numeric input does not reveal its validation step or rounding behavior. The paper's task interpretation alone is insufficient to certify that the runtime accepted only integer tasks or multiples of 20 cents. Preserve original income and task fields if data later become available; do not silently round them.

## Sample, controls, and boundaries

Figure 8 (PDF p. 44) and Section 4.1/footnote 5 (PDF p. 17) report 879 link entrants, 344 exclusions/dropouts before the main experiment, 13 during the main experiment, and 522 complete subjects with 8,352 decisions. The five pre-main counts are 16 captcha failures, 104 attention failures, 137 control-question failures, 30 leaving instructions, and 57 leaving the practice task. Their sum is 344. Footnote 4 (PDF p. 8) identifies two working-stage departures; the remaining eleven are an arithmetic inference if decision/working stages exhaust those thirteen. Actual partial-row counts, randomized roster, and all zero-outcome counts remain unavailable.

The six socioeconomic controls in Table 6 are age, female, at least a bachelor's degree, full-time employment, below-median household income, and MTurk experience. Figures 12-13 (PDF pp. 55-56) show the source questions. Experience is weekly hours on MTurk or similar platforms; household income asks about **2021 before-tax income**. The paper's below-median description refers to a 2022 benchmark, but the actual cutoff, dropdown categories, recodes, and missing-value handling are not available. The screenshot does not resolve those coding choices.

Figures 21-27 are post-decision questions. In particular, Figure 22 (PDF p. 64) includes a separate hypothetical **40-cent** wage task question with a **50%** tax. Do not mix that response into the 16 main decisions, which pay **20 cents per task**. Additional post-treatment controls in Appendix Table 10 are not interchangeable with the six controls of the narrow Table 6 target.

The paper's Section 4.4 uses “extensive” for increase/decrease/no-change response categories. It is not the zero-versus-positive participation outcome. Defining such response categories requires the unrecovered pre/post matching rule. The methods lane remains responsible for identification and new estimands; this artifact adds primary-source evidence only.
