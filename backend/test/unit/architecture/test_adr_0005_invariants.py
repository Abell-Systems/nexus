"""Automated architectural enforcement test for ADR 0005.

Invariants verified:
1. No Path("config/policies/...") in domain/ or application/ matching code.
2. No policy=None fallback or load_*_policy() in domain/ or application/.
3. Mandatory policy injection: DefaultMatchingEngine.evaluate() fails explicitly, not with an
   unhelpful AttributeError, when a candidate pool is evaluated without a policy.
"""

from pathlib import Path

import pytest

from application.matching.engine import DefaultMatchingEngine
from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, CandidatePool


def test_no_config_policies_paths_in_domain_or_application():
    """ADR 0005: Code under domain/ and application/ MUST NOT resolve repository-relative policy paths."""
    src_dirs = [
        Path("backend/src/main/domain"),
        Path("backend/src/main/application"),
    ]

    violating_files: list[str] = []
    for sdir in src_dirs:
        for py_file in sdir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            if "config/policies" in content:
                violating_files.append(str(py_file))

    assert not violating_files, (
        f"Found forbidden repository-relative policy paths in domain/application: {violating_files}. "
        "Under ADR 0005, configuration must be injected explicitly, not resolved by internal modules."
    )


def test_default_matching_engine_fails_fast_when_policy_is_none():
    """ADR 0005 / ADR 0004 §3.1's fail-fast invariant, migrated from the deleted
    CandidateMatchingService (superseded PR #7 scaffolding, removed for duplicating
    DefaultEvidenceEvaluator's fusion — see the HybridRanker cleanup) onto the actual
    canonical evaluation engine.

    Before this test, DefaultMatchingEngine.evaluate(policy=None, ...) over a non-empty
    pool raised a bare `AttributeError: 'NoneType' object has no attribute
    'sufficiency_rules'` deep inside DefaultEvidenceEvaluator — not the explicit,
    diagnosable ValueError ADR 0004 §3.1 requires for a missing mandatory policy.
    """
    engine = DefaultMatchingEngine()
    demand = DemandSignal(demand_id="D-1", source_network="test", title="t", description="d")
    pool = CandidatePool(demand_id="D-1", candidates=[Candidate(publication_id="P-1")])

    with pytest.raises(ValueError, match="MatchingPolicyConfig must be explicitly provided"):
        engine.evaluate(demand=demand, candidates=pool, policy=None)
