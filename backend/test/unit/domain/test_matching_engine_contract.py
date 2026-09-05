"""Tests for the MatchingEngine interface and single-source-of-truth CPC similarity under ADR 0004.

Invariants verified:
1. Interface compliance: MatchingEngine.evaluate(demand, candidates, policy) -> list[MatchAssessment].
2. Single source of truth for CPC: CPC similarity levels come strictly from policy (cpc_concordance_levels).
3. Determinism: identical inputs + identical policy -> bit-exact identical MatchAssessment list.
4. Explainability: each MatchAssessment carries observed facts, derived features, and policy hash.
5. Ineligible candidates: evaluated and marked with appropriate sufficiency.
"""



from pathlib import Path

import pytest

from domain.models.demand import DemandRecord, SpanishOriginLevel
from domain.models.matching import (
    Candidate,
    CandidatePool,
    EvidenceSufficiency,
    MatchAssessment,
    MatchConfidence,
    MatchingPolicyConfig,
    RetrievalMethod,
    compute_cpc_symbol_similarity_from_levels,
)
from domain.protocols.matching import MatchingEngine

# Anchored to repo root so this resolves regardless of pytest's invocation cwd
# (e.g. `pytest` from repo root vs `cd backend && pytest`).
DEFAULT_MATCHING_POLICY_PATH = (
    Path(__file__).resolve().parents[4] / "config" / "policies" / "matching" / "default_matching_policy.json"
)


def _make_demand() -> DemandRecord:
    return DemandRecord(
        demand_id="DEMAND-001",
        title="High-performance solid-state battery with sulfide electrolyte",
        description="Seeking all-solid-state lithium secondary battery technology with sulfide inorganic solid electrolyte.",
        requesting_organization="EnergyTech S.L.",
        origin_country="Spain",
        spanish_origin_level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
        is_spanish_demand=True,
        cpc_prefix="H01M",
        posted_date="2024-01-15",
        url="https://example.com/calls/001",
    )


def test_matching_engine_protocol_is_runtime_checkable():
    class DummyEngine:
        def evaluate(
            self,
            demand: DemandRecord,
            candidates: CandidatePool,
            policy: MatchingPolicyConfig,
        ) -> list[MatchAssessment]:
            return []

    assert isinstance(DummyEngine(), MatchingEngine)


def test_cpc_similarity_uses_policy_levels_as_single_source_of_truth():
    policy = MatchingPolicyConfig.load_from_json(DEFAULT_MATCHING_POLICY_PATH)
    levels = policy.cpc_concordance_levels

    # 1. Exact subgroup match uses levels.subgroup (1.0)
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "H01M10/0562", levels) == levels.subgroup

    # 2. Main group match uses levels.main_group (0.75)
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "H01M10/0525", levels) == levels.main_group

    # 3. Subclass match uses levels.subclass (0.50)
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "H01M4/13", levels) == levels.subclass

    # 4. Section match uses levels.section (0.25)
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "H02J7/00", levels) == levels.section

    # 5. Non-match uses levels.none (0.0)
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "C11D1/02", levels) == levels.none


def test_custom_policy_levels_dynamically_alter_cpc_similarity():
    """Modifying policy levels must change similarity values without touching Python code."""
    from domain.models.matching import CPCConcordanceLevels

    custom_levels = CPCConcordanceLevels(
        subgroup=0.99,
        main_group=0.66,
        subclass=0.33,
        section=0.11,
        none=0.01,
    )

    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "H01M10/0562", custom_levels) == 0.99
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "H01M10/0525", custom_levels) == 0.66
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "H01M4/13", custom_levels) == 0.33
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "H02J7/00", custom_levels) == 0.11
    assert compute_cpc_symbol_similarity_from_levels("H01M10/0562", "C11D1/02", custom_levels) == 0.01


def test_default_matching_engine_full_evaluation_and_determinism():
    from application.matching.engine import DefaultMatchingEngine

    engine = DefaultMatchingEngine()
    policy = MatchingPolicyConfig.load_from_json(DEFAULT_MATCHING_POLICY_PATH)
    demand = _make_demand()

    # Candidate 1: strong prior art with semantic and lexical overlap
    cand1 = Candidate(
        publication_id="ES-2849102-B2",
        retrieval_scores={RetrievalMethod.LEXICAL: 0.80, RetrievalMethod.SEMANTIC: 0.85},
    )
    # Candidate 2: incompatible temporal candidate (published after demand)
    cand2 = Candidate(
        publication_id="ES-2999999-B2",
        retrieval_scores={RetrievalMethod.LEXICAL: 0.90, RetrievalMethod.SEMANTIC: 0.95},
    )
    # Candidate 3: zero active signals
    cand3 = Candidate(
        publication_id="ES-1111111-B2",
        retrieval_scores={},
    )

    pool = CandidatePool(
        demand_id=demand.demand_id,
        candidates=[cand1, cand2, cand3],
    )

    metadata = {
        "ES-2849102-B2": {
            "publication_date": "2022-05-10",
            "classifications_cpc": ["H01M10/0562"],
            "shared_terms": ["solid-state", "electrolyte"],
        },
        "ES-2999999-B2": {
            "publication_date": "2024-12-01",  # After demand date 2024-01-15
            "classifications_cpc": ["H01M10/0562"],
        },
        "ES-1111111-B2": {
            "publication_date": "2020-01-01",
        },
    }

    assessments = engine.evaluate(demand, pool, policy, patent_metadata=metadata)
    assert len(assessments) == 3

    # Check top candidate
    top = assessments[0]
    assert top.publication_id == "ES-2849102-B2"
    assert top.confidence in (MatchConfidence.STRONG, MatchConfidence.MODERATE)
    assert top.sufficiency == EvidenceSufficiency.SUFFICIENT
    assert top.features.temporal_valid is True
    assert top.features.delta_days is not None and top.features.delta_days > 0
    assert "solid-state" in top.features.shared_terms
    assert top.policy_sha256 == policy.policy_sha256

    # Check temporally ineligible candidate
    ineligible = next(a for a in assessments if a.publication_id == "ES-2999999-B2")
    assert ineligible.sufficiency == EvidenceSufficiency.INELIGIBLE_TEMPORAL
    assert ineligible.overall_score == 0.0
    assert ineligible.confidence == MatchConfidence.NONE
    assert ineligible.features.temporal_valid is False

    # Check insufficient candidate
    insufficient = next(a for a in assessments if a.publication_id == "ES-1111111-B2")
    assert insufficient.sufficiency == EvidenceSufficiency.INSUFFICIENT_EVIDENCE
    assert insufficient.overall_score == 0.0
    assert insufficient.confidence == MatchConfidence.NONE

    # Verify bit-exact determinism across duplicate run
    assessments_second_run = engine.evaluate(demand, pool, policy, patent_metadata=metadata)
    assert assessments == assessments_second_run


def test_matching_engine_sufficiency_rule_governed_strictly_by_policy():
    """ADR 0004 & ADR 0005: min_signals_for_sufficient must come from policy, not in-code literals."""
    from application.matching.engine import DefaultMatchingEngine

    engine = DefaultMatchingEngine()
    policy = MatchingPolicyConfig.load_from_json(DEFAULT_MATCHING_POLICY_PATH)
    demand = _make_demand()

    # Candidate with exactly 1 active signal (e.g. lexical only)
    cand = Candidate(
        publication_id="ES-1234567-B2",
        retrieval_scores={RetrievalMethod.LEXICAL: 0.80},
    )
    pool = CandidatePool(demand_id=demand.demand_id, candidates=[cand])
    metadata = {
        "ES-1234567-B2": {"publication_date": "2020-01-01"},
    }

    # Under standard policy, min_signals_for_sufficient is 2, so 1 active signal -> PARTIAL
    assessments = engine.evaluate(demand, pool, policy, patent_metadata=metadata)
    assert assessments[0].sufficiency == EvidenceSufficiency.PARTIAL

    # Alter policy dynamically so that 1 signal is sufficient
    altered_policy = policy.model_copy(deep=True)
    altered_policy.sufficiency_rules.min_signals_for_sufficient = 1
    altered_assessments = engine.evaluate(demand, pool, altered_policy, patent_metadata=metadata)
    assert altered_assessments[0].sufficiency == EvidenceSufficiency.SUFFICIENT


def test_matching_engine_rejects_incompatible_demand_type():
    """MatchingEngine should reject arbitrary non-demand objects instead of duck-typing blindly."""
    from application.matching.engine import DefaultMatchingEngine

    engine = DefaultMatchingEngine()
    policy = MatchingPolicyConfig.load_from_json(DEFAULT_MATCHING_POLICY_PATH)
    pool = CandidatePool(demand_id="D-1", candidates=[])

    with pytest.raises(TypeError, match="Expected DemandRecord or DemandSignal"):
        engine.evaluate("not-a-demand", pool, policy)


def test_matching_engine_with_canonical_patent_candidate_evidence_objects():
    """Verifies that MatchingEngine seamlessly consumes canonical PatentCandidateEvidence objects."""
    from application.matching.engine import DefaultMatchingEngine
    from domain.models.matching import PatentCandidateEvidence

    engine = DefaultMatchingEngine()
    policy = MatchingPolicyConfig.load_from_json(DEFAULT_MATCHING_POLICY_PATH)
    demand = _make_demand()

    # Demand with target CPC symbol H01M10/0562
    demand = _make_demand().model_copy(update={"cpc_prefix": "H01M10/0562"})

    cand = Candidate(
        publication_id="ES-2849102-B2",
        retrieval_scores={RetrievalMethod.LEXICAL: 0.70, RetrievalMethod.SEMANTIC: 0.80},
    )
    pool = CandidatePool(demand_id=demand.demand_id, candidates=[cand])

    # Strongly typed canonical evidence list
    evidence_list = [
        PatentCandidateEvidence(
            publication_id="ES-2849102-B2",
            publication_date="2022-05-10",
            classifications_cpc=["H01M10/0562"],
            shared_terms=("solid-state", "electrolyte"),
            title="Electrolito sólido para baterías",
            abstract="Composición de electrolito inorgánico.",
        )
    ]

    assessments = engine.evaluate(demand, pool, policy, patent_metadata=evidence_list)
    assert len(assessments) == 1
    top = assessments[0]
    assert top.publication_id == "ES-2849102-B2"
    assert top.sufficiency == EvidenceSufficiency.SUFFICIENT
    assert top.features.shared_terms == ("solid-state", "electrolyte")
    assert top.features.cpc_concordance == 1.0  # Exact subgroup match
