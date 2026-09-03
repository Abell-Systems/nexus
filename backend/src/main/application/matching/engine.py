"""Clean Architecture implementation of MatchingEngine under ADR 0004.

Invariants:
- Evaluates candidate pool against a demand document under MatchingPolicyConfig.
- Coordinates decoupled components: MatchingFeatureExtractor, EvidenceEvaluator, and deterministic sorting.
- Adheres strictly to single source of truth: weights, concordance levels, and sufficiency rules come from policy.
- Zero in-code policy defaults; zero synthetic fallback inventions.
- Strict determinism: ties broken deterministically by publication_id ASC.
"""

from typing import Any

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import (
    CandidatePool,
    MatchAssessment,
    MatchingPolicyConfig,
    PatentCandidateEvidence,
)
from domain.protocols.matching import MatchingEngine

from .evaluator import DefaultEvidenceEvaluator
from .feature_extractor import DefaultMatchingFeatureExtractor, extract_demand_context


def _to_evidence_lookup(
    raw_evidence: dict[str, Any] | list[PatentCandidateEvidence] | None,
) -> dict[str, PatentCandidateEvidence]:
    """Converts structured evidence into canonical PatentCandidateEvidence objects."""
    if not raw_evidence:
        return {}

    lookup: dict[str, PatentCandidateEvidence] = {}
    if isinstance(raw_evidence, list):
        for ev in raw_evidence:
            if isinstance(ev, PatentCandidateEvidence):
                lookup[ev.publication_id] = ev
        return lookup

    for pub_id, data in raw_evidence.items():
        if isinstance(data, PatentCandidateEvidence):
            lookup[pub_id] = data
        elif isinstance(data, dict):
            raw_cpcs = data.get("classifications_cpc") or data.get("cpc_codes") or []
            cpc_list = [str(c) for c in raw_cpcs] if isinstance(raw_cpcs, (list, tuple)) else []
            lookup[pub_id] = PatentCandidateEvidence(
                publication_id=pub_id,
                publication_date=data.get("publication_date"),
                classifications_cpc=cpc_list,
                shared_terms=tuple(data.get("shared_terms", ())),
                title=data.get("title", ""),
                abstract=data.get("abstract", ""),
            )
    return lookup


class DefaultMatchingEngine(MatchingEngine):
    """Reference orchestrator implementation of MatchingEngine protocol."""

    def __init__(
        self,
        feature_extractor: DefaultMatchingFeatureExtractor | None = None,
        evaluator: DefaultEvidenceEvaluator | None = None,
    ) -> None:
        self._feature_extractor = feature_extractor or DefaultMatchingFeatureExtractor()
        self._evaluator = evaluator or DefaultEvidenceEvaluator()

    def evaluate(
        self,
        demand: DemandRecord | DemandSignal,
        candidates: CandidatePool,
        policy: MatchingPolicyConfig,
        patent_metadata: dict[str, Any] | list[PatentCandidateEvidence] | None = None,
    ) -> list[MatchAssessment]:
        """Orchestrates candidate evaluation through feature extraction, evaluation, and deterministic ranking."""
        demand_id, _title, _desc, _date_str, _cpc_prefix = extract_demand_context(demand)
        evidence_lookup = _to_evidence_lookup(patent_metadata)

        assessments: list[MatchAssessment] = []

        for candidate in candidates.candidates:
            pub_id = candidate.publication_id
            cand_evidence = evidence_lookup.get(pub_id)

            # 1. Feature Extraction (decoupled)
            features = self._feature_extractor.extract_candidate_features(
                demand=demand,
                retrieval_scores=candidate.retrieval_scores,
                evidence=cand_evidence,
                policy=policy,
            )

            # 2. Evidence Assessment (decoupled)
            assessment = self._evaluator.evaluate_candidate(
                demand_id=demand_id,
                publication_id=pub_id,
                features=features,
                policy=policy,
            )
            assessments.append(assessment)

        # 3. Deterministic Decision / Sorting: overall_score DESC, publication_id ASC
        assessments.sort(key=lambda a: (-a.overall_score, a.publication_id))
        return assessments
