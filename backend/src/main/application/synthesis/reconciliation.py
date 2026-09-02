"""Candidate verdict and score reconciliation logic."""

from typing import Any


def reconcile_candidate_verdicts(
    verdicts: list[dict[str, Any]], scorecards: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Ensures backend produces authoritative verdict: if governor scorecard finds
    direct anticipation or blocking prior art, force verdict to 'rejected'."""
    reconciled = []
    for v in verdicts:
        v_copy = dict(v)
        cand_id = v_copy.get("candidate_id")
        sc = next((s for s in scorecards if isinstance(s, dict) and s.get("candidate_id") == cand_id), None)
        if sc:
            summary = (sc.get("summary") or "").lower()
            if (
                "directly anticipated" in summary
                or "no room for novelty" in summary
                or "cannot be recommended" in summary
            ):
                v_copy["verdict"] = "rejected"
        reconciled.append(v_copy)
    return reconciled
