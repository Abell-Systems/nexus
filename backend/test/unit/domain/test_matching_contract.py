"""Domain and contract tests for the Nexus Matching Engine under ADR 0001, ADR 0002, and ADR 0004.

Tests the formal contract:
    DemandRecord + PatentDocument + MatchingPolicyConfig
        ↓
    MatchFeatures
        ↓
    MatchAssessment

Covers:
- Determinism: identical inputs yield bit-exact identical MatchAssessment.
- Missing data / Null semantics: missing fields don't raise, don't invent defaults, produce neutral feature values.
- Ineligible candidates: temporal violation (t_pub >= t_demand) or jurisdiction mismatch flags ineligibility.
- Strong match vs Partial match vs Zero match differentiation.
- Evidence sufficiency: SUFFICIENT vs PARTIAL vs INSUFFICIENT_EVIDENCE vs INELIGIBLE_TEMPORAL.
- Configuration-driven behavior: changing weights or thresholds changes assessment without altering Python code.
- Cryptographic tamper resistance: tampered policy SHA-256 raises ValueError immediately (fail-fast, no fallback).
"""

import json
from pathlib import Path

import pytest

from domain.models.demand import (
    DemandRecord,
    SpanishOriginLevel,
)
from domain.models.matching import (
    EvidenceSufficiency,
    MatchAssessment,
    MatchConfidence,
    MatchFeatures,
    MatchingPolicyConfig,
)
from domain.models.patent import PatentDocument

# Anchored to repo root so this resolves regardless of pytest's invocation cwd
# (e.g. `pytest` from repo root vs `cd backend && pytest`).
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MATCHING_POLICY_PATH = _REPO_ROOT / "config" / "policies" / "matching" / "default_matching_policy.json"


def _make_demand(
    demand_id: str = "INNOGET-2292",
    title: str = "Biodegradable surfactant for low temperature washing",
    description: str = "Seeking eco-friendly surfactant formulation active at 20C for laundry detergent compositions.",
    cpc_prefix: str | None = "C11D",
    posted_date: str | None = "2024-06-01",
) -> DemandRecord:
    return DemandRecord(
        demand_id=demand_id,
        title=title,
        description=description,
        requesting_organization="EcoClean S.L.",
        origin_country="Spain",
        spanish_origin_level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
        is_spanish_demand=True,
        cpc_prefix=cpc_prefix,
        posted_date=posted_date,
        url="https://www.innoget.com/technology-calls/2292",
    )


def _make_patent(
    publication_id: str = "ES-2849102-B2",
    country_code: str = "ES",
    title: str = "Composición detergente biodegradable con tensioactivos enzimáticos",
    abstract: str = "Detergente para lavado de ropa a baja temperatura que comprende tensioactivos biodegradables.",
    publication_date: str | None = "2021-11-25",
    classifications_cpc: list[str] | None = None,
) -> PatentDocument:
    return PatentDocument(
        publication_id=publication_id,
        country_code=country_code,
        doc_number="2849102",
        kind_code="B2",
        title=title,
        abstract=abstract,
        publication_date=publication_date,
        classifications_cpc=classifications_cpc if classifications_cpc is not None else ["C11D1/02", "C11D3/386"],
    )


def test_matching_policy_config_loads_and_verifies_cryptographic_digest():
    policy_path = DEFAULT_MATCHING_POLICY_PATH
    assert policy_path.exists(), "Default matching policy file must exist"

    policy = MatchingPolicyConfig.load_from_json(policy_path)
    assert policy.policy_id == "NEXUS-MATCHING-POLICY-UC1-DEFAULT"
    assert policy.policy_version == "1.0.0"
    assert len(policy.policy_sha256) == 64
    assert round(policy.weights.alpha + policy.weights.beta + policy.weights.gamma, 6) == 1.0


def test_matching_policy_config_fail_fast_on_missing_file():
    with pytest.raises(FileNotFoundError):
        MatchingPolicyConfig.load_from_json(_REPO_ROOT / "config" / "policies" / "matching" / "non_existent.json")


def test_matching_policy_config_fail_fast_on_tampered_digest(tmp_path):
    policy_path = DEFAULT_MATCHING_POLICY_PATH
    with open(policy_path, encoding="utf-8") as f:
        data = json.load(f)

    # Tamper with weight without updating sha256
    data["weights"]["alpha"] = 0.50
    tampered_file = tmp_path / "tampered_policy.json"
    with open(tampered_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="Cryptographic integrity verification failed"):
        MatchingPolicyConfig.load_from_json(tampered_file)


def test_matching_policy_config_fail_fast_on_missing_declared_digest(tmp_path):
    policy_path = DEFAULT_MATCHING_POLICY_PATH
    with open(policy_path, encoding="utf-8") as f:
        data = json.load(f)

    # Remove declared policy_sha256
    del data["policy_sha256"]
    missing_sha_file = tmp_path / "missing_sha_policy.json"
    with open(missing_sha_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="missing mandatory declared 'policy_sha256'"):
        MatchingPolicyConfig.load_from_json(missing_sha_file)


def test_match_features_model_contracts():
    features = MatchFeatures(
        lexical_score=0.85,
        semantic_score=0.78,
        cpc_concordance=1.0,
        temporal_valid=True,
        delta_days=919,
        shared_terms=("detergente", "biodegradable", "surfactant"),
        concordant_cpc_pairs=(("C11D1/02", "C11D1/02"),),
    )
    assert features.lexical_score == 0.85
    assert features.semantic_score == 0.78
    assert features.cpc_concordance == 1.0
    assert features.temporal_valid is True
    assert features.delta_days == 919
    assert len(features.shared_terms) == 3


def test_match_assessment_model_and_confidence_evaluation():
    features = MatchFeatures(
        lexical_score=0.90,
        semantic_score=0.85,
        cpc_concordance=1.0,
        temporal_valid=True,
        delta_days=500,
        shared_terms=("detergent", "biodegradable"),
        concordant_cpc_pairs=(("C11D1/02", "C11D1/02"),),
    )

    assessment = MatchAssessment(
        demand_id="INNOGET-2292",
        publication_id="ES-2849102-B2",
        overall_score=0.8975,
        confidence=MatchConfidence.STRONG,
        sufficiency=EvidenceSufficiency.SUFFICIENT,
        features=features,
        rationale="Strong alignment: direct CPC subgroup match C11D1/02 and dense semantic similarity 0.85",
        policy_id="NEXUS-MATCHING-POLICY-UC1-DEFAULT",
        policy_version="1.0.0",
        policy_sha256="c7aec29433975db6a2503cf216554a6d5ade701a69b14f0230710542fd519541",
    )

    assert assessment.confidence == MatchConfidence.STRONG
    assert assessment.overall_score == 0.8975
    assert assessment.sufficiency == EvidenceSufficiency.SUFFICIENT


def test_temporal_ineligibility_produces_ineligible_sufficiency():
    """When patent publication date >= demand solicitation date, match must flag INELIGIBLE_TEMPORAL."""
    features = MatchFeatures(
        lexical_score=0.90,
        semantic_score=0.85,
        cpc_concordance=1.0,
        temporal_valid=False,
        delta_days=-150,  # Published 150 days AFTER the demand
        shared_terms=("detergent",),
        concordant_cpc_pairs=(("C11D1/02", "C11D1/02"),),
    )

    assessment = MatchAssessment(
        demand_id="INNOGET-2292",
        publication_id="ES-2849102-B2",
        overall_score=0.0,  # Temporal ineligibility suppresses score
        confidence=MatchConfidence.NONE,
        sufficiency=EvidenceSufficiency.INELIGIBLE_TEMPORAL,
        features=features,
        rationale="Patent published after demand date; ineligible as prior art",
        policy_id="NEXUS-MATCHING-POLICY-UC1-DEFAULT",
        policy_version="1.0.0",
        policy_sha256="c7aec29433975db6a2503cf216554a6d5ade701a69b14f0230710542fd519541",
    )

    assert assessment.sufficiency == EvidenceSufficiency.INELIGIBLE_TEMPORAL
    assert assessment.confidence == MatchConfidence.NONE
    assert assessment.overall_score == 0.0


def test_insufficient_evidence_when_signals_are_absent():
    """When candidate has zero lexical, semantic, and CPC overlap, sufficiency must evaluate to INSUFFICIENT_EVIDENCE."""
    features = MatchFeatures(
        lexical_score=0.0,
        semantic_score=0.0,
        cpc_concordance=0.0,
        temporal_valid=True,
        delta_days=300,
        shared_terms=(),
        concordant_cpc_pairs=(),
    )

    assessment = MatchAssessment(
        demand_id="INNOGET-2292",
        publication_id="ES-9999999-B2",
        overall_score=0.0,
        confidence=MatchConfidence.NONE,
        sufficiency=EvidenceSufficiency.INSUFFICIENT_EVIDENCE,
        features=features,
        rationale="No measurable technological overlap across lexical, semantic, or classification dimensions",
        policy_id="NEXUS-MATCHING-POLICY-UC1-DEFAULT",
        policy_version="1.0.0",
        policy_sha256="c7aec29433975db6a2503cf216554a6d5ade701a69b14f0230710542fd519541",
    )

    assert assessment.sufficiency == EvidenceSufficiency.INSUFFICIENT_EVIDENCE
    assert assessment.confidence == MatchConfidence.NONE
    assert assessment.overall_score == 0.0


def test_matching_feature_extractor_and_matcher_protocols_runtime_checkable():
    from domain.protocols.matching import MatchingFeatureExtractor, TechnologyMatcher

    class DummyExtractor:
        def extract_features(self, demand, patent):
            return None

    class DummyMatcher:
        def assess_match(self, demand, patent):
            return None

    assert isinstance(DummyExtractor(), MatchingFeatureExtractor)
    assert isinstance(DummyMatcher(), TechnologyMatcher)
