import math

import pytest

from domain.models.annotation import AnnotationJudgment
from domain.models.evaluation import RelevanceGrade
from application.evaluation.iaa import compute_iaa


def _judgment(demand_id, pub_id, annotator, grade) -> AnnotationJudgment:
    return AnnotationJudgment(
        demand_id=demand_id, publication_id=pub_id, annotator_id=annotator, grade=RelevanceGrade(grade)
    )


class IaaTest:
    def test_should_return_kappa_one_for_perfect_agreement(self):
        judgments_a = [_judgment("D1", "P1", "valentin", 2), _judgment("D1", "P2", "valentin", 0)]
        judgments_b = [_judgment("D1", "P1", "lydia", 2), _judgment("D1", "P2", "lydia", 0)]
        report = compute_iaa(judgments_a, judgments_b)
        assert report.weighted_kappa == pytest.approx(1.0)
        assert report.binary_kappa == pytest.approx(1.0)
        assert report.disagreements == []

    def test_should_penalize_distant_disagreement_more_than_adjacent(self):
        # Pair 1: adjacent disagreement (2 vs 3). Pair 2: distant disagreement (0 vs 3).
        judgments_a_adjacent = [_judgment("D1", "P1", "valentin", 2)]
        judgments_b_adjacent = [_judgment("D1", "P1", "lydia", 3)]
        judgments_a_distant = [_judgment("D1", "P1", "valentin", 0)]
        judgments_b_distant = [_judgment("D1", "P1", "lydia", 3)]

        # Need >1 pair with variance for kappa to be defined; pad with an agreeing pair.
        pad_a = _judgment("D1", "P2", "valentin", 1)
        pad_b = _judgment("D1", "P2", "lydia", 1)

        report_adjacent = compute_iaa(judgments_a_adjacent + [pad_a], judgments_b_adjacent + [pad_b])
        report_distant = compute_iaa(judgments_a_distant + [pad_a], judgments_b_distant + [pad_b])

        assert report_distant.weighted_kappa < report_adjacent.weighted_kappa

    def test_should_report_disagreements_explicitly_without_resolving_them(self):
        judgments_a = [_judgment("D1", "P1", "valentin", 3), _judgment("D1", "P2", "valentin", 1)]
        judgments_b = [_judgment("D1", "P1", "lydia", 1), _judgment("D1", "P2", "lydia", 1)]
        report = compute_iaa(judgments_a, judgments_b)
        assert len(report.disagreements) == 1
        assert report.disagreements[0].publication_id == "P1"
        assert report.disagreements[0].grade_a == 3
        assert report.disagreements[0].grade_b == 1

    def test_should_compute_binary_kappa_on_grade_gte_2_view(self):
        # A: [2,1] -> binary [True, False]. B: [3,0] -> binary [True, False]. Agree both.
        judgments_a = [_judgment("D1", "P1", "valentin", 2), _judgment("D1", "P2", "valentin", 1)]
        judgments_b = [_judgment("D1", "P1", "lydia", 3), _judgment("D1", "P2", "lydia", 0)]
        report = compute_iaa(judgments_a, judgments_b)
        assert report.binary_kappa == pytest.approx(1.0)

    def test_should_produce_4x4_confusion_matrix(self):
        judgments_a = [_judgment("D1", "P1", "valentin", 2), _judgment("D1", "P2", "valentin", 0)]
        judgments_b = [_judgment("D1", "P1", "lydia", 2), _judgment("D1", "P2", "lydia", 1)]
        report = compute_iaa(judgments_a, judgments_b)
        assert len(report.confusion_matrix) == 4
        assert all(len(row) == 4 for row in report.confusion_matrix)
        assert sum(sum(row) for row in report.confusion_matrix) == 2

    def test_should_raise_on_mismatched_publication_id_sets(self):
        judgments_a = [_judgment("D1", "P1", "valentin", 2)]
        judgments_b = [_judgment("D1", "P2", "lydia", 2)]
        with pytest.raises(ValueError, match="same set"):
            compute_iaa(judgments_a, judgments_b)

    def test_should_raise_when_both_inputs_are_the_same_annotator(self):
        judgments = [_judgment("D1", "P1", "valentin", 2), _judgment("D1", "P2", "valentin", 0)]
        with pytest.raises(ValueError, match="same single annotator"):
            compute_iaa(judgments, judgments)

    def test_should_raise_when_either_input_is_empty(self):
        judgments = [_judgment("D1", "P1", "valentin", 2)]
        with pytest.raises(ValueError, match="non-empty"):
            compute_iaa([], judgments)
        with pytest.raises(ValueError, match="non-empty"):
            compute_iaa(judgments, [])
        with pytest.raises(ValueError, match="non-empty"):
            compute_iaa([], [])

    def test_should_report_nan_kappa_for_zero_variance_input_not_perfect_agreement(self):
        # Both annotators grade everything 0 -> no expected variance, kappa is
        # 0/0 (undefined), not perfect agreement.
        judgments_a = [_judgment("D1", "P1", "valentin", 0), _judgment("D1", "P2", "valentin", 0)]
        judgments_b = [_judgment("D1", "P1", "lydia", 0), _judgment("D1", "P2", "lydia", 0)]
        report = compute_iaa(judgments_a, judgments_b)
        assert math.isnan(report.weighted_kappa)
        assert math.isnan(report.binary_kappa)
