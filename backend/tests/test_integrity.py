"""Tests verifying Agentic Integrity state logic and inconsistency prevention.

Regression tests for:
1. Rejection override: If governor / scorecard finds blocking prior art or direct anticipation, candidate status cannot be 'survived'.
2. Prior art consolidation: Supporting evidence citations from scorecard are included in challenging prior art.
"""

def is_candidate_survived(verdict: dict | None, scorecard: dict | None) -> bool:
    if not verdict:
        return False
    v_str = (verdict.get("verdict") or "").lower()
    if v_str != "survives":
        return False
    summary = (scorecard.get("summary") or "").lower() if scorecard else ""
    if (
        "directly anticipated" in summary
        or "no room for novelty" in summary
        or "cannot be recommended" in summary
    ):
        return False
    return True


def consolidate_prior_art(verdict: dict | None, scorecard: dict | None) -> list[str]:
    cited = verdict.get("cited_patents", []) if verdict else []
    evidence = scorecard.get("supporting_evidence", []) if scorecard else []
    
    extracted = []
    import re
    for item in evidence:
        match = re.search(r"\b(US-[A-Za-z0-9-]+)\b", item)
        if match:
            extracted.append(match.group(1))
        elif item.strip().startswith("US-"):
            extracted.append(item.strip())
            
    res = []
    for pat in list(cited) + extracted:
        if pat not in res:
            res.append(pat)
    return res


def test_rejection_overrides_survives_verdict_when_governor_cites_anticipation():
    verdict = {"candidate_id": "c1", "verdict": "survives", "rationale": "Clear functional differentiation"}
    scorecard = {
        "candidate_id": "c1",
        "summary": "Proposed claims directly anticipated by pre-existing patents leaving virtually no room for novelty or patentability.",
        "supporting_evidence": ["US-10145381-B2-0"],
    }
    
    assert is_candidate_survived(verdict, scorecard) is False


def test_clean_survives_candidate_passes_integrity_check():
    verdict = {"candidate_id": "c2", "verdict": "survives", "rationale": "Overcomes US-10045067-B2"}
    scorecard = {
        "candidate_id": "c2",
        "summary": "Novel active polymer matrix demonstrates strong differentiation.",
        "supporting_evidence": [],
    }
    
    assert is_candidate_survived(verdict, scorecard) is True


def test_prior_art_consolidation_includes_scorecard_evidence():
    verdict = {"candidate_id": "c3", "verdict": "rejected", "cited_patents": []}
    scorecard = {
        "candidate_id": "c3",
        "summary": "Anticipated by US-10145381-B2-0",
        "supporting_evidence": ["US-10145381-B2-0", "US-11113260-B2-1"],
    }
    
    patents = consolidate_prior_art(verdict, scorecard)
    assert "US-10145381-B2-0" in patents
    assert "US-11113260-B2-1" in patents
    assert len(patents) == 2


def test_reconcile_candidate_verdicts_backend_authoritative():
    from main import reconcile_candidate_verdicts

    verdicts = [
        {"candidate_id": "c1", "verdict": "survives", "rationale": "Differentiation claimed"},
        {"candidate_id": "c2", "verdict": "survives", "rationale": "Novel structure"},
    ]
    scorecards = [
        {
            "candidate_id": "c1",
            "summary": "Proposed claims directly anticipated by pre-existing patents leaving virtually no room for novelty.",
        },
        {
            "candidate_id": "c2",
            "summary": "Clear novelty and high differentiation.",
        },
    ]

    reconciled = reconcile_candidate_verdicts(verdicts, scorecards)
    assert len(reconciled) == 2
    assert reconciled[0]["candidate_id"] == "c1"
    assert reconciled[0]["verdict"] == "rejected"
    assert reconciled[1]["candidate_id"] == "c2"
    assert reconciled[1]["verdict"] == "survives"

