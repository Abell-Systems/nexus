import pytest

from application.corpus.validation_gate import evaluate_validation_gate
from domain.models.corpus_expansion import TechnicalProblemClassification as C


def test_gate_passes_when_recall_specificity_and_boundary_all_clean():
    reference = {
        "a": C.TECHNICAL_PROBLEM, "b": C.TECHNICAL_PROBLEM,
        "c": C.GENERIC_PROCUREMENT, "d": C.GENERIC_PROCUREMENT,
    }
    llm = dict(reference)
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset({"c"}))
    assert result.passed is True
    assert result.recall_technical_problem == 1.0
    assert result.specificity_generic_procurement == 1.0
    assert result.boundary_false_positives == ()


def test_gate_fails_on_low_recall():
    reference = {"a": C.TECHNICAL_PROBLEM, "b": C.TECHNICAL_PROBLEM}
    llm = {"a": C.GENERIC_PROCUREMENT, "b": C.TECHNICAL_PROBLEM}
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset())
    assert result.passed is False
    assert result.recall_technical_problem == 0.5


def test_gate_a_passes_while_gate_b_independently_fails_on_boundary_case():
    reference = {
        "tp1": C.TECHNICAL_PROBLEM, "tp2": C.TECHNICAL_PROBLEM,
        **{f"gp{i}": C.GENERIC_PROCUREMENT for i in range(10)},
    }
    llm = dict(reference)
    llm["gp0"] = C.TECHNICAL_PROBLEM  # the one boundary misclassification
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset({"gp0"}))
    assert result.recall_technical_problem == 1.0
    assert result.specificity_generic_procurement == 0.9  # 9/10, meets the 0.90 threshold -> Gate A passes
    assert result.boundary_false_positives == ("gp0",)  # Gate B fails independently
    assert result.passed is False


def test_non_boundary_false_positive_hurts_specificity_but_not_boundary_gate():
    reference = {"a": C.TECHNICAL_PROBLEM, "b": C.GENERIC_PROCUREMENT}
    llm = {"a": C.TECHNICAL_PROBLEM, "b": C.TECHNICAL_PROBLEM}
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset())
    assert result.boundary_false_positives == ()
    assert result.specificity_generic_procurement == 0.0
    assert result.passed is False


def test_gate_pass_carries_warning_when_generic_procurement_reference_class_is_empty():
    reference = {"a": C.TECHNICAL_PROBLEM, "b": C.TECHNICAL_PROBLEM}
    llm = dict(reference)
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset())
    assert result.passed is True
    assert result.specificity_generic_procurement == 1.0
    assert "0 GENERIC_PROCUREMENT reference cases" in result.reason


def test_evaluate_validation_gate_raises_on_mismatched_keys():
    reference = {"a": C.TECHNICAL_PROBLEM}
    llm = {"b": C.TECHNICAL_PROBLEM}
    with pytest.raises(ValueError):
        evaluate_validation_gate(reference, llm, boundary_ids=frozenset())
