"""Unit tests for candidate verdict reconciliation."""

from application.synthesis.reconciliation import reconcile_candidate_verdicts


def test_reconcile_candidate_verdicts_preserves_survives():
    verdicts = [{"candidate_id": "c1", "verdict": "survives"}]
    scorecards = [{"candidate_id": "c1", "summary": "High commercial novelty"}]
    reconciled = reconcile_candidate_verdicts(verdicts, scorecards)
    assert len(reconciled) == 1
    assert reconciled[0]["verdict"] == "survives"


def test_reconcile_candidate_verdicts_forces_rejected_when_anticipated():
    verdicts = [{"candidate_id": "c1", "verdict": "survives"}]
    scorecards = [{"candidate_id": "c1", "summary": "Directly anticipated by prior art"}]
    reconciled = reconcile_candidate_verdicts(verdicts, scorecards)
    assert len(reconciled) == 1
    assert reconciled[0]["verdict"] == "rejected"


def test_reconcile_candidate_verdicts_handles_empty_inputs():
    assert reconcile_candidate_verdicts([], []) == []
