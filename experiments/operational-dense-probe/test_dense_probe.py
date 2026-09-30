import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dense_probe as dp  # noqa: E402


def _labels(demand: str, grades: dict[str, int | None]) -> dict[dp.Pair, dp.Label]:
    return {(demand, pub): grade for pub, grade in grades.items()}


class PairsAndSampleTest:
    def test_should_dedupe_pair_when_both_methods_return_same_patent(self):
        pairs = dp.union_pairs({"D1": ["P1", "P2"]}, {"D1": ["P2", "P3"]})
        assert pairs == [("D1", "P1"), ("D1", "P2"), ("D1", "P3")]

    def test_should_return_same_blind_order_when_seed_is_fixed(self):
        pairs = [("D1", f"P{i}") for i in range(20)]
        assert dp.blind_order(pairs) == dp.blind_order(list(reversed(pairs)))

    def test_should_not_keep_sorted_order_when_blind_shuffling_many_pairs(self):
        pairs = [("D1", f"P{i:02d}") for i in range(20)]
        assert dp.blind_order(pairs) != sorted(pairs)

    def test_should_draw_ceil_of_twenty_percent_when_sampling_common_pairs(self):
        ordered = dp.blind_order([("D1", f"P{i}") for i in range(23)])
        assert len(dp.draw_common_sample(ordered)) == 5

    def test_should_draw_exactly_twenty_percent_when_float_product_overshoots(self):
        ordered = dp.blind_order([("D1", f"P{i}") for i in range(15)])
        assert len(dp.draw_common_sample(ordered)) == 3

    def test_should_draw_same_common_sample_when_called_twice_with_seed_42(self):
        ordered = dp.blind_order([("D1", f"P{i}") for i in range(40)])
        assert dp.draw_common_sample(ordered) == dp.draw_common_sample(ordered)


class FinalLabelsTest:
    def test_should_use_adjudicated_grade_when_pair_is_in_common_sample(self):
        a = {("D1", "P1"): 1, ("D1", "P2"): 3}
        adjudicated = {("D1", "P1"): 2}
        result = dp.final_labels(a, adjudicated, common={("D1", "P1")})
        assert result == {("D1", "P1"): 2, ("D1", "P2"): 3}

    def test_should_exclude_pair_when_evaluator_a_marked_uncertain_outside_common_sample(self):
        result = dp.final_labels({("D1", "P1"): None}, {}, common=set())
        assert result == {("D1", "P1"): None}

    def test_should_raise_when_common_pair_has_no_adjudication(self):
        with pytest.raises(KeyError):
            dp.final_labels({("D1", "P1"): 2}, {}, common={("D1", "P1")})


class PrecisionAtFiveTest:
    def test_should_divide_relevant_by_five_when_all_five_judged(self):
        labels = _labels("D1", {"P1": 3, "P2": 2, "P3": 1, "P4": 0, "P5": 2})
        assert dp.precision_at_5("D1", ["P1", "P2", "P3", "P4", "P5"], labels) == pytest.approx(0.6)

    def test_should_keep_empty_slots_in_denominator_when_list_is_short(self):
        labels = _labels("D1", {"P1": 3, "P2": 2})
        assert dp.precision_at_5("D1", ["P1", "P2"], labels) == pytest.approx(0.4)

    def test_should_leave_denominator_when_pair_is_excluded(self):
        labels = _labels("D1", {"P1": 3, "P2": None, "P3": 0, "P4": 0, "P5": 0})
        assert dp.precision_at_5("D1", ["P1", "P2", "P3", "P4", "P5"], labels) == pytest.approx(0.25)

    def test_should_return_none_when_all_five_pairs_are_excluded(self):
        labels = _labels("D1", {f"P{i}": None for i in range(1, 6)})
        assert dp.precision_at_5("D1", [f"P{i}" for i in range(1, 6)], labels) is None

    def test_should_return_zero_when_list_is_empty(self):
        assert dp.precision_at_5("D1", [], {}) == 0.0

    def test_should_raise_when_a_listed_pair_has_no_judgment(self):
        with pytest.raises(KeyError, match="Unjudged"):
            dp.precision_at_5("D1", ["P1"], {})

    def test_should_reject_list_longer_than_five(self):
        with pytest.raises(ValueError):
            dp.precision_at_5("D1", [f"P{i}" for i in range(6)], {})


class PairedMacroTest:
    def test_should_average_demands_available_for_both_methods_when_one_is_dropped(self):
        result = dp.paired_macro({"D1": 0.2, "D2": None, "D3": 0.4}, {"D1": 0.6, "D2": 0.8, "D3": 0.4})
        assert result.n_used == 2 and result.n_dropped == 1
        assert result.p5_bm25 == pytest.approx(0.3)
        assert result.p5_dense == pytest.approx(0.5)
        assert result.delta == pytest.approx(0.2)

    def test_should_raise_when_no_demand_is_usable_for_both_methods(self):
        with pytest.raises(ValueError):
            dp.paired_macro({"D1": None}, {"D1": 0.5})


class OutcomeTest:
    def test_should_be_yes_when_both_thresholds_met_and_kappa_ok(self):
        assert dp.classify_outcome(0.50, 0.30, 0.80) == dp.Outcome.RESOLVED_YES

    def test_should_be_yes_when_delta_is_exactly_threshold_despite_float_fuzz(self):
        # 0.41 - 0.26 == 0.14999999999999997 in IEEE-754
        assert dp.classify_outcome(0.41, 0.26, 0.70) == dp.Outcome.RESOLVED_YES

    def test_should_be_no_when_dense_below_absolute_threshold(self):
        assert dp.classify_outcome(0.39, 0.10, 0.90) == dp.Outcome.RESOLVED_NO

    def test_should_be_no_when_improvement_below_threshold(self):
        assert dp.classify_outcome(0.60, 0.50, 0.90) == dp.Outcome.RESOLVED_NO

    def test_should_be_unresolved_when_kappa_below_threshold_even_if_thresholds_met(self):
        assert dp.classify_outcome(0.90, 0.10, 0.69) == dp.Outcome.UNRESOLVED

    def test_should_be_unresolved_when_kappa_below_threshold_even_if_thresholds_failed(self):
        assert dp.classify_outcome(0.10, 0.50, 0.30) == dp.Outcome.UNRESOLVED


class BootstrapSummaryTest:
    def test_should_report_paired_intervals_when_enough_demands(self):
        bm25 = {f"D{i}": 0.2 for i in range(10)}
        dense = {f"D{i}": 0.6 for i in range(10)}
        summary = dp.bootstrap_summary(bm25, dense)
        assert summary["delta"]["estimate"] == pytest.approx(0.4)
        assert summary["delta"]["ci_lower"] <= summary["delta"]["estimate"] <= summary["delta"]["ci_upper"]
        assert summary["dense"]["estimate"] == pytest.approx(0.6)

    def test_should_return_none_when_fewer_than_two_paired_demands(self):
        assert dp.bootstrap_summary({"D1": 0.2}, {"D1": 0.6}) is None


class KappaTest:
    def test_should_compute_kappa_over_common_pairs_graded_by_both_evaluators(self):
        common = {("D1", f"P{i}") for i in range(8)}
        a = {("D1", "P0"): 0, ("D1", "P1"): 1, ("D1", "P2"): 2, ("D1", "P3"): 3,
             ("D1", "P4"): 0, ("D1", "P5"): 1, ("D1", "P6"): 2, ("D1", "P7"): 3}
        b = dict(a)
        result = dp.common_sample_kappa(a, b, common)
        assert result.weighted_kappa == pytest.approx(1.0)
        assert result.n_used == 8 and result.n_excluded == 0

    def test_should_exclude_pair_from_kappa_when_either_evaluator_marked_uncertain(self):
        common = {("D1", "P0"), ("D1", "P1"), ("D1", "P2")}
        a = {("D1", "P0"): 0, ("D1", "P1"): 3, ("D1", "P2"): None}
        b = {("D1", "P0"): 0, ("D1", "P1"): 3, ("D1", "P2"): 1}
        result = dp.common_sample_kappa(a, b, common)
        assert result.n_used == 2 and result.n_excluded == 1


class LanguageTest:
    def test_should_guess_english_when_english_stopwords_dominate(self):
        assert dp.guess_language("Seeking the best materials for the vehicles and with low weight") == "en"

    def test_should_guess_spanish_when_spanish_stopwords_dominate(self):
        assert dp.guess_language("Buscamos los mejores materiales para el peso de los vehiculos que con una") == "es"
