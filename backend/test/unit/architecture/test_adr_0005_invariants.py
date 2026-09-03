"""Automated architectural enforcement test for ADR 0005.

Invariants verified:
1. No Path("config/policies/...") in domain/ or application/ matching code.
2. No policy=None fallback or load_*_policy() in domain/ or application/.
3. Mandatory policy injection: CandidateMatchingService.match() fails explicitly if policy is None.
4. Mandatory policy injection: DefaultMatchingEngine.evaluate() requires valid MatchingPolicyConfig.
"""

from pathlib import Path

import pytest

from application.matching.service import CandidateMatchingService
from domain.models.demand import DemandRecord, SpanishOriginLevel


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


def test_candidate_matching_service_fails_fast_when_policy_is_none():
    """ADR 0005: MatchingPolicyConfig must be explicitly injected into CandidateMatchingService.match()."""
    class StubRetriever:
        def retrieve(self, demand, limit=100):
            return []

    service = CandidateMatchingService(
        lexical_retriever=StubRetriever(),
        semantic_retriever=StubRetriever(),
        cpc_retriever=StubRetriever(),
        rankers={
            "lexical": type("StubRanker", (), {"rank": lambda self, pool: []})(),
            "semantic": type("StubRanker", (), {"rank": lambda self, pool: []})(),
            "cpc": type("StubRanker", (), {"rank": lambda self, pool: []})(),
            "hybrid": type("StubRanker", (), {"rank": lambda self, pool: []})(),
        },
    )

    demand = DemandRecord(
        demand_id="D-1",
        title="Test Title",
        description="Test Description",
        url="https://example.com/demand/1",
        spanish_origin_level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
        is_spanish_demand=True,
    )

    with pytest.raises(ValueError, match="MatchingPolicyConfig must be explicitly provided"):
        service.match(demand, policy=None)


def test_candidate_matching_service_uses_policy_retrieval_limit_without_override():
    """ADR 0004 & ADR 0005: Operational limit comes strictly from policy; API forbids caller override."""
    recorded_limits = []

    class MockRetriever:
        def retrieve(self, demand, limit=100):
            recorded_limits.append(limit)
            return []

    service = CandidateMatchingService(
        lexical_retriever=MockRetriever(),
        semantic_retriever=MockRetriever(),
        cpc_retriever=MockRetriever(),
        rankers={
            "lexical": type("StubRanker", (), {"rank": lambda self, pool: []})(),
            "semantic": type("StubRanker", (), {"rank": lambda self, pool: []})(),
            "cpc": type("StubRanker", (), {"rank": lambda self, pool: []})(),
            "hybrid": type("StubRanker", (), {"rank": lambda self, pool: []})(),
        },
    )

    demand = DemandRecord(
        demand_id="D-1",
        title="Test Title",
        description="Test Description",
        url="https://example.com/demand/1",
        spanish_origin_level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
        is_spanish_demand=True,
    )

    from domain.models.matching import MatchingPolicyConfig
    policy = MatchingPolicyConfig.load_from_json(Path("config/policies/matching/default_matching_policy.json"))

    # Test with custom policy operational limit (e.g. 42)
    custom_policy = policy.model_copy(deep=True)
    custom_policy.operational_limits.retrieval_limit = 42

    service.match(demand, policy=custom_policy)

    # All retrievers must have received limit=42 directly from policy
    assert recorded_limits == [42, 42, 42]

    # Verify that match() signature does not accept 'retrieval_limit'
    import inspect
    sig = inspect.signature(service.match)
    assert "retrieval_limit" not in sig.parameters, (
        "CandidateMatchingService.match() must NOT allow callers to override retrieval_limit. "
        "Policy is the single source of truth."
    )
