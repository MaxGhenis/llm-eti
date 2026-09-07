"""Deterministic offline tests of substantive identification/estimation claims."""

import csv
import io
import itertools
import math
import statistics
import unittest
from dataclasses import replace
from typing import Any, cast

from llm_eti.lab_methods.design_tools import completion_bounds, reference_exposure
from llm_eti.lab_methods.estimands import (
    ARMS,
    ENDOWMENTS,
    DesignError,
    Estimate,
    Observation,
    SubjectSummary,
    cluster_bootstrap,
    estimate,
    kw_formula_demonstration,
    net_of_tax_log_change,
    normalize_log_effect,
    notch_identification,
    summarize,
    target_weights,
    validate_observations,
)
from llm_eti.lab_methods.kw_reference import (
    eq5_residual,
    marginal_buncher,
    recover_synthetic_elasticity,
)
from llm_eti.lab_methods.replay import FIELDS, read_synthetic_panels
from llm_eti.lab_methods.synthetic import (
    continuous_flat_choice,
    discrete_choice,
    dominance_table,
    equivalence_panel,
    known_response_panel,
    net_pay,
    no_response_panel,
    participation_panel,
    utility,
)
from llm_eti.lab_methods.uncertainty_design import (
    coverage_audit,
    exact_subject_percentile_interval,
)


def _defined(value: float | None) -> float:
    assert value is not None, "Expected a defined synthetic result"
    return value


class BudgetAndIdentificationTests(unittest.TestCase):
    def test_exact_kw_known_elasticity_recovery_requires_outside_support(self):
        for e in (0.05, 0.2, 0.5, 1, 2):
            reference = marginal_buncher(e)
            self.assertLess(abs(reference["eq5_residual"]), 1e-14)
            self.assertTrue(reference["both_relevant_points_outside_pknf_support"])
            self.assertAlmostEqual(
                recover_synthetic_elasticity(reference["relative_response"]),
                e,
                places=10,
            )

    def test_kw_root_satisfies_independent_utility_indifference(self):
        # Direct utility calculation in cents, independently of the normalized
        # equation residual, checks formula signs and scale normalization.
        for e in (0.05, 0.2, 0.5, 1, 2):
            result = marginal_buncher(e)
            z0 = result["counterfactual_marginal_buncher_cents"]
            zi = result["post_notch_interior_cents"]
            ability = z0 / 0.75**e

            def cost(z, ability=ability, e=e):
                return ability / (1 + 1 / e) * (z / ability) ** (1 + 1 / e)

            self.assertAlmostEqual(
                0.75 * 400 - cost(400), 0.5 * zi - cost(zi), places=10
            )

    def test_mechanical_width_has_no_positive_exact_kw_root(self):
        for e in (0.01, 0.05, 0.2, 1, 5):
            self.assertGreater(eq5_residual(0.5, e), 0)
        with self.assertRaises(DesignError):
            recover_synthetic_elasticity(0.5)

    def test_source_table_payoffs_and_threshold_convention(self):
        expected_prog = (210, 240, 300, 210, 220, 240, 250, 300)
        self.assertEqual(tuple(net_pay(e, "Prog") for e in ENDOWMENTS), expected_prog)
        self.assertEqual(net_pay(0, "Prog"), 0)
        self.assertEqual(net_pay(20, "Prog"), 300)
        self.assertEqual(net_pay(21, "Prog"), 210)
        self.assertEqual(net_pay(30, "Flat25"), 450)

    def test_all_feasible_above_notch_choices_are_dominated(self):
        for row in dominance_table():
            self.assertFalse(row["strictly_higher_consumption_than_q20"])
            for q in row["above_notch_tasks"]:
                self.assertLessEqual(net_pay(q, "Prog"), net_pay(20, "Prog"))
                for e in (0.2, 2):
                    self.assertLess(
                        utility(q, "Prog", e, 60), utility(20, "Prog", e, 60)
                    )

    def test_different_structural_elasticities_identical_complete_panels(self):
        low, high = equivalence_panel(0.2), equivalence_panel(2)
        self.assertEqual(low, high)
        self.assertTrue(any(r.tasks == 0 for r in low))
        for r in low:
            if r.tasks:
                schedule = ARMS[r.arm][r.phase]
                self.assertEqual(
                    r.tasks, min(r.endowment, 20) if schedule == "Prog" else r.endowment
                )

    def test_equivalence_extends_beyond_two_selected_values(self):
        reference = equivalence_panel(1)
        for e in (0.1, 0.5, 5, 20):
            self.assertEqual(reference, equivalence_panel(e))

    def test_no_point_or_bounds_returned_for_pknf(self):
        result = notch_identification()
        self.assertFalse(result["identified"])
        for field in ("estimate", "lower_bound", "upper_bound"):
            self.assertIsNone(result[field])

    def test_equation_transcription_not_a_claimed_bound(self):
        result = kw_formula_demonstration(0.5)
        self.assertAlmostEqual(result["kw_equation12_rhs"], 0.75)
        self.assertAlmostEqual(result["kleven2018_equation4_rhs"], 0.375)
        self.assertAlmostEqual(result["kleven2018_equation5_rhs"], 0.3)
        self.assertFalse(result["valid_estimate_for_pknf"])

    def test_finite_discrete_choices_can_mask_continuous_response(self):
        e = 0.1
        q0 = discrete_choice(14, "Flat50", e, 6)
        q1 = discrete_choice(14, "Flat25", e, 6)
        self.assertEqual((q0, q1), (6, 6))
        self.assertGreater(continuous_flat_choice(0.75, e, 6), 6)

    def test_caps_mask_known_smooth_elasticity(self):
        for cap in ENDOWMENTS:
            self.assertEqual(discrete_choice(cap, "Flat50", 1, 60), cap)
            self.assertEqual(discrete_choice(cap, "Flat25", 1, 60), cap)
        self.assertEqual(continuous_flat_choice(0.75, 1, 60), 90)


class EstimandTests(unittest.TestCase):
    def test_no_response_all_zero_inclusive_level_outcomes(self):
        rows = no_response_panel()
        for metric in (
            "tasks",
            "gross_cents",
            "utilization",
            "participation",
            "at_cap",
            "at_notch",
            "above_notch",
        ):
            summaries, audit = summarize(rows, metric)
            self.assertGreater(audit["zero_rows_in_target"], 0)
            for arm in ARMS:
                if arm != "Prog,Prog":
                    self.assertEqual(estimate(summaries, arm).value, 0)

    def test_known_discrete_interior_response_recovers_e_one(self):
        weights = target_weights((14, 16, 20))
        summaries, audit = summarize(known_response_panel(), "log_gross", weights)
        effect = estimate(summaries, "Prog,Flat50")
        d = net_of_tax_log_change(0.25, 0.50)
        self.assertEqual(audit["cap_rows_in_target"], 0)
        self.assertEqual(audit["zero_rows_in_target"], 0)
        self.assertAlmostEqual(
            _defined(normalize_log_effect(effect, d).value), 1, places=12
        )

    def test_continuous_uncapped_control_recovers_multiple_elasticities(self):
        for e in (0.05, 0.2, 0.8, 1, 2, 4):
            q0 = continuous_flat_choice(0.5, e, 6)
            q1 = continuous_flat_choice(0.75, e, 6)
            result = math.log(q1 / q0) / net_of_tax_log_change(0.5, 0.25)
            self.assertAlmostEqual(result, e, places=12)

    def test_log_denominator_sign_and_magnitude(self):
        self.assertAlmostEqual(net_of_tax_log_change(0.5, 0.25), 0.4054651081081644)
        self.assertAlmostEqual(net_of_tax_log_change(0.25, 0.5), -0.4054651081081644)
        self.assertAlmostEqual(
            net_of_tax_log_change(0.5, 0.25) / 0.25, 1.6218604324326575
        )

    def test_zero_denominator_is_undefined_not_zero_elasticity(self):
        result = normalize_log_effect(Estimate(0), net_of_tax_log_change(0.25, 0.25))
        self.assertIsNone(result.value)
        self.assertEqual(result.reason, "zero_log_net_of_tax_change")

    def test_participation_changes_survive_level_analysis(self):
        rows = participation_panel()
        weights = target_weights((14, 16, 20))
        qs, audit = summarize(rows, "tasks", weights)
        ps, _ = summarize(rows, "participation", weights)
        self.assertAlmostEqual(_defined(estimate(qs, "Prog,Flat50").value), -3.75)
        self.assertAlmostEqual(_defined(estimate(ps, "Prog,Flat50").value), -0.25)
        self.assertGreater(audit["zero_rows_in_target"], 0)

    def test_log_outcome_refuses_zero_selection(self):
        summaries, audit = summarize(participation_panel(), "log_gross")
        result = estimate(summaries, "Prog,Flat50")
        self.assertIsNone(result.value)
        self.assertEqual(result.reason, "undefined_outcome_zero_in_log_sample")
        self.assertGreater(audit["undefined_log_cells"], 0)

    def test_log_mean_response_contains_participation_and_intensive_changes(self):
        rows = participation_panel()
        weights = target_weights((14, 16, 20))
        summaries, _ = summarize(rows, "gross_cents", weights)
        effect = estimate(summaries, "Prog,Flat50", scale="log_of_mean")
        d = net_of_tax_log_change(0.25, 0.5)
        self.assertAlmostEqual(_defined(normalize_log_effect(effect, d).value), 2)
        # DGP intensive e=1; the other unit comes from log(.5/.75) participation.
        self.assertAlmostEqual(math.log(0.5 / 0.75) / d, 1)
        self.assertAlmostEqual(math.log(6 / 9) / d, 1)

    def test_gross_unit_change_does_not_change_log_mean_effect(self):
        qs, _ = summarize(participation_panel(), "tasks")
        zs, _ = summarize(participation_panel(), "gross_cents")
        qeffect = estimate(qs, "Prog,Flat50", scale="log_of_mean")
        zeffect = estimate(zs, "Prog,Flat50", scale="log_of_mean")
        self.assertAlmostEqual(_defined(qeffect.value), _defined(zeffect.value))

    def test_cap_standardization_uses_fixed_weights(self):
        weights = {14: 0.25, 30: 0.75}
        summaries, _ = summarize(equivalence_panel(1), "tasks", weights)
        # 75% active; only E=30 changes, by 10 tasks, with target mass .75.
        self.assertAlmostEqual(
            _defined(estimate(summaries, "Prog,Flat25").value), 0.75 * 0.75 * 10
        )

    def test_notch_share_excludes_cap_at_notch(self):
        summaries, audit = summarize(equivalence_panel(1), "at_notch")
        self.assertEqual(set(audit["target_weights"]), {21, 22, 24, 25, 30})
        self.assertAlmostEqual(
            _defined(estimate(summaries, "Prog,Flat25").value), -0.75
        )
        with self.assertRaises(DesignError):
            summarize(equivalence_panel(1), "at_notch", target_weights())

    def test_post_sequence_contrast_distinct_from_change_contrast(self):
        summaries = [
            SubjectSummary("t", "Flat25,Prog", 10, 8),
            SubjectSummary("c", "Prog,Prog", 8, 8),
        ]
        self.assertEqual(estimate(summaries, "Flat25,Prog", contrast="post").value, 0)
        self.assertEqual(estimate(summaries, "Flat25,Prog", contrast="did").value, -2)


class UncertaintyTests(unittest.TestCase):
    def test_exact_subject_bootstrap_boundary_distribution(self):
        self.assertEqual(exact_subject_percentile_interval(2, 1, 1), (-4, 4))
        self.assertEqual(exact_subject_percentile_interval(2, 0, 0), (0, 0))
        self.assertEqual(exact_subject_percentile_interval(2, 2, 0), (4, 4))

    def test_exact_coverage_audit_detects_false_precision_from_repeated_rows(self):
        audit = coverage_audit(20, 8)
        self.assertAlmostEqual(audit["true_sampling_variance"], 8 / 20)
        self.assertLess(audit["coverage"]["naive_row_wald"], 0.7)
        self.assertGreater(audit["coverage"]["subject_wald"], 0.9)
        self.assertGreater(audit["coverage"]["subject_percentile_limit"], 0.9)
        self.assertAlmostEqual(
            audit["naive_to_subject_se_ratio_when_variance_positive"],
            math.sqrt(19 / 159),
        )

    def test_inference_equal_without_pseudoreplicated_rounds(self):
        once, repeated = coverage_audit(6, 1), coverage_audit(6, 8)
        self.assertEqual(
            once["coverage"]["subject_wald"], once["coverage"]["naive_row_wald"]
        )
        self.assertEqual(
            once["coverage"]["subject_percentile_limit"],
            repeated["coverage"]["subject_percentile_limit"],
        )

    def test_no_response_bootstrap_retains_all_zero_mass(self):
        summaries, _ = summarize(no_response_panel(), "tasks")
        result = cluster_bootstrap(
            summaries, "Prog,Flat25", draws=199, independent_subjects_confirmed=True
        )
        self.assertEqual(result["zero_draws"], 199)
        self.assertEqual(result["undefined_draws"], 0)
        self.assertEqual(result["ci_percentile_95"], [0, 0])

    def test_signed_bunching_contrasts_do_not_condition_on_positive_draws(self):
        summaries = [
            SubjectSummary("t1", "Prog,Flat25", 0, 1),
            SubjectSummary("t2", "Prog,Flat25", 1, 0),
            SubjectSummary("c1", "Prog,Prog", 0, 0),
            SubjectSummary("c2", "Prog,Prog", 0, 0),
        ]
        result = cluster_bootstrap(
            summaries, "Prog,Flat25", draws=399, independent_subjects_confirmed=True
        )
        self.assertEqual(result["point"]["value"], 0)
        for field in ("negative_draws", "zero_draws", "positive_draws"):
            self.assertGreater(result[field], 0)
        self.assertEqual(result["ci_percentile_95"], [-1, 1])

    def test_undefined_zero_mean_draws_are_recorded_and_interval_withheld(self):
        summaries = [
            SubjectSummary("t0", "Prog,Flat25", 0, 0),
            SubjectSummary("t1", "Prog,Flat25", 10, 10),
            SubjectSummary("c0", "Prog,Prog", 0, 0),
            SubjectSummary("c1", "Prog,Prog", 10, 10),
        ]
        result = cluster_bootstrap(
            summaries,
            "Prog,Flat25",
            scale="log_of_mean",
            draws=199,
            independent_subjects_confirmed=True,
        )
        self.assertEqual(result["point"]["value"], 0)
        self.assertGreater(result["undefined_draws"], 0)
        self.assertGreater(result["defined_draws"], 0)
        self.assertEqual(result["defined_draws"] + result["undefined_draws"], 199)
        self.assertIsNone(result["ci_percentile_95"])
        self.assertEqual(
            sum(v is None for v in result["draws"]), result["undefined_draws"]
        )

    def test_independent_unit_must_be_established(self):
        summaries, _ = summarize(no_response_panel(), "tasks")
        with self.assertRaises(DesignError):
            cluster_bootstrap(summaries, "Prog,Flat25")

    def test_seed_is_reproducible_without_python_hash(self):
        summaries, _ = summarize(participation_panel(), "tasks")
        args: dict[str, Any] = {
            "draws": 99,
            "seed": 44,
            "independent_subjects_confirmed": True,
        }
        a = cluster_bootstrap(summaries, "Prog,Flat50", **args)
        b = cluster_bootstrap(summaries, "Prog,Flat50", **args)
        self.assertEqual(a, b)
        self.assertNotEqual(
            a["draws"],
            cluster_bootstrap(summaries, "Prog,Flat50", **{**args, "seed": 45})[
                "draws"
            ],
        )

    def test_repeated_rounds_do_not_create_independent_subjects(self):
        def make_rows(repeats):
            rows = []
            for arm in ("Prog,Prog", "Prog,Flat25"):
                for i in range(4):
                    for phase in (0, 1):
                        for r in range(repeats):
                            q = 4 + i + (i * phase if arm == "Prog,Flat25" else 0)
                            rows.append(
                                Observation(f"{arm}:{i}", arm, 8 * phase + r + 1, 14, q)
                            )
            return rows

        small, _ = summarize(make_rows(1), "tasks", {14: 1})
        large, _ = summarize(make_rows(8), "tasks", {14: 1})
        self.assertEqual(small, large)
        args: dict[str, Any] = {"draws": 199, "independent_subjects_confirmed": True}
        self.assertEqual(
            cluster_bootstrap(small, "Prog,Flat25", **args),
            cluster_bootstrap(large, "Prog,Flat25", **args),
        )

    def test_exact_cluster_resampling_variance_preserves_pairing(self):
        # Enumerate all resamples of two subjects in each arm. Each subject's
        # pre/post pair remains intact; large individual intercepts cancel.
        treated = [(100, 101), (200, 203)]
        control = [(300, 300), (400, 402)]
        draws = []
        for ts in itertools.product(range(2), repeat=2):
            for cs in itertools.product(range(2), repeat=2):
                dt = statistics.fmean(treated[i][1] - treated[i][0] for i in ts)
                dc = statistics.fmean(control[i][1] - control[i][0] for i in cs)
                draws.append(dt - dc)
        self.assertEqual(statistics.fmean(draws), 1)
        self.assertEqual(statistics.pvariance(draws), 1)

    def test_negative_denominator_ci_orders_transformed_draws(self):
        summaries, _ = summarize(participation_panel(), "gross_cents")
        args: dict[str, Any] = {
            "scale": "log_of_mean",
            "draws": 199,
            "independent_subjects_confirmed": True,
        }
        raw = cluster_bootstrap(summaries, "Prog,Flat50", **args)
        d = net_of_tax_log_change(0.25, 0.5)
        transformed = cluster_bootstrap(summaries, "Prog,Flat50", denominator=d, **args)
        self.assertEqual(transformed["draws"], [v / d for v in raw["draws"]])
        self.assertLessEqual(*transformed["ci_percentile_95"])


class ExposureAndCompletionTests(unittest.TestCase):
    def test_baseline_buncher_has_menu_exposure_but_zero_reference_rate_change(self):
        result = reference_exposure("Prog,Flat25", 30, 20)
        self.assertTrue(result["menu_exposed"])
        self.assertEqual(result["reference_branch_log_net_change"], 0)
        self.assertTrue(result["reference_at_nonsmooth_notch"])
        self.assertIsNone(result["whole_positive_menu_log_scale_change"])

    def test_low_caps_have_identical_prog_and_flat25_menus(self):
        for cap in (14, 16, 20):
            result = reference_exposure("Prog,Flat25", cap, cap)
            self.assertFalse(result["menu_exposed"])
            self.assertEqual(result["whole_positive_menu_log_scale_change"], 0)

    def test_low_cap_prog_flat50_has_common_menu_scale_change(self):
        for cap in (14, 16, 20):
            result = reference_exposure("Prog,Flat50", cap, 0)
            self.assertTrue(result["menu_exposed"])
            self.assertIsNone(result["reference_branch_log_net_change"])
            self.assertEqual(result["reference_tax_change_cents"], 0)
            self.assertAlmostEqual(
                result["whole_positive_menu_log_scale_change"], math.log(2 / 3)
            )

    def test_reference_rates_have_all_four_correct_signs(self):
        for arm, q, sign in (
            ("Prog,Flat25", 21, 1),
            ("Prog,Flat50", 10, -1),
            ("Flat25,Prog", 21, -1),
            ("Flat50,Prog", 10, 1),
        ):
            result = reference_exposure(arm, 30, q)
            self.assertAlmostEqual(
                result["reference_branch_log_net_change"], sign * math.log(1.5)
            )

    def test_reference_outside_cap_rejected(self):
        with self.assertRaises(DesignError):
            reference_exposure("Prog,Flat25", 14, 20)

    def test_no_missing_bounds_collapse_to_point_for_all_level_metrics(self):
        rows = participation_panel()
        for metric in (
            "tasks",
            "gross_cents",
            "utilization",
            "participation",
            "at_cap",
            "at_notch",
            "above_notch",
        ):
            for contrast in ("did", "post"):
                summaries, _ = summarize(rows, metric)
                point = estimate(summaries, "Prog,Flat50", contrast=contrast).value
                result = completion_bounds(
                    rows, metric, "Prog,Flat50", contrast=contrast
                )
                self.assertAlmostEqual(result["lower"], point)
                self.assertAlmostEqual(result["upper"], point)
                self.assertEqual(result["missing_rows_in_contrast"], 0)

    def test_missing_completion_bounds_match_exhaustive_discrete_choices(self):
        rows = [
            Observation("t", "Prog,Flat25", 1, 14, None),
            Observation("t", "Prog,Flat25", 9, 14, 9),
            Observation("c", "Prog,Prog", 1, 14, 6),
            Observation("c", "Prog,Prog", 9, 14, None),
        ]
        result = completion_bounds(rows, "tasks", "Prog,Flat25", weights={14: 1})
        possible = []
        for q0, q3 in itertools.product(range(15), repeat=2):
            completed = [
                replace(rows[0], tasks=q0),
                rows[1],
                rows[2],
                replace(rows[3], tasks=q3),
            ]
            subjects, _ = summarize(completed, "tasks", {14: 1})
            possible.append(_defined(estimate(subjects, "Prog,Flat25").value))
        self.assertEqual(
            (result["lower"], result["upper"]), (min(possible), max(possible))
        )
        self.assertEqual((result["lower"], result["upper"]), (-13, 15))
        self.assertEqual(result["missing_rows_in_contrast"], 2)
        self.assertEqual(result["observed_zero_rows_in_contrast"], 0)
        self.assertFalse(result["confidence_interval"])
        self.assertFalse(result["elasticity_bound"])

    def test_positive_did_coefficients_complete_in_opposite_direction(self):
        rows = [
            Observation("t", "Prog,Flat25", 1, 14, 9),
            Observation("t", "Prog,Flat25", 9, 14, None),
            Observation("c", "Prog,Prog", 1, 14, None),
            Observation("c", "Prog,Prog", 9, 14, 6),
        ]
        result = completion_bounds(rows, "tasks", "Prog,Flat25", weights={14: 1})
        self.assertEqual((result["lower"], result["upper"]), (-15, 13))

    def test_notch_bounds_use_q20_as_upper_not_the_cap(self):
        rows = [
            Observation("t", "Prog,Flat25", 1, 21, 20),
            Observation("t", "Prog,Flat25", 9, 21, None),
            Observation("c", "Prog,Prog", 1, 21, 20),
            Observation("c", "Prog,Prog", 9, 21, 0),
        ]
        result = completion_bounds(rows, "at_notch", "Prog,Flat25", weights={21: 1})
        self.assertEqual((result["lower"], result["upper"]), (0, 1))
        self.assertEqual(result["observed_zero_rows_in_contrast"], 1)

    def test_missingness_bounds_cannot_be_requested_for_logs(self):
        with self.assertRaises(DesignError):
            completion_bounds(known_response_panel(), "log_gross", "Prog,Flat50")


class InputContractTests(unittest.TestCase):
    def test_saved_fixture_parser_preserves_zero_and_panel_identity(self):
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerow(["true", "synthetic_a", "s", "Prog,Prog", 1, 14, 0])
        writer.writerow(["true", "synthetic_b", "s", "Prog,Prog", 1, 14, 9])
        stream.seek(0)
        panels = read_synthetic_panels(stream)
        self.assertEqual(panels["synthetic_a"][0].tasks, 0)
        self.assertEqual(panels["synthetic_b"][0].tasks, 9)

    def test_fixture_reader_does_not_silently_accept_unlabeled_real_data(self):
        text = ",".join(FIELDS) + "\nfalse,synthetic_a,s,Prog,1,14,0\n"
        with self.assertRaisesRegex(DesignError, "not explicitly synthetic"):
            read_synthetic_panels(io.StringIO(text))

    def test_fixture_reader_rejects_blank_responses(self):
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(FIELDS)
        writer.writerow(["true", "synthetic_a", "s", "Prog,Prog", 1, 14, ""])
        stream.seek(0)
        with self.assertRaisesRegex(DesignError, "Invalid integer"):
            read_synthetic_panels(stream)

    def setUp(self):
        self.rows = known_response_panel()

    def test_missing_is_not_zero(self):
        with self.assertRaises(DesignError):
            summarize([replace(self.rows[0], tasks=None)] + self.rows[1:], "tasks")

    def test_invalid_values_are_not_clipped_or_rounded(self):
        for q in (-1, 15, 1.5, math.nan, math.inf, True):
            with self.subTest(q=q), self.assertRaises(DesignError):
                validate_observations([replace(self.rows[0], tasks=cast(Any, q))])

    def test_duplicate_round_rejected(self):
        with self.assertRaises(DesignError):
            summarize(self.rows + [self.rows[0]], "tasks")

    def test_subject_reassignment_rejected(self):
        with self.assertRaises(DesignError):
            summarize(
                [replace(self.rows[0], arm="Prog,Flat50")] + self.rows[1:], "tasks"
            )

    def test_unobserved_selected_cap_cell_not_reweighted_away(self):
        with self.assertRaisesRegex(DesignError, "Incomplete selected grid"):
            summarize(self.rows[1:], "tasks")

    def test_bad_weights_rejected(self):
        for weights in ({14: 0.2}, {14: 1, 16: 0}, {15: 1}, {14: math.nan}, {14: True}):
            with self.subTest(weights=weights), self.assertRaises(DesignError):
                summarize(self.rows, "tasks", weights)

    def test_bad_rates_rejected(self):
        for rate in (math.nan, math.inf, -1, 1, True):
            with self.subTest(rate=rate), self.assertRaises(DesignError):
                net_of_tax_log_change(rate, 0.25)


if __name__ == "__main__":
    unittest.main()
