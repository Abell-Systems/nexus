"""Evaluation-to-Matching adapter under ADR 0007.

This module is the **only** module in application/evaluation/ permitted to import from the
matching domain. It resolves the impedance mismatch between evaluation-domain types
(EvaluationDemand, EvaluationPatent) and matching-domain types (DemandSignal, CandidatePool,
PatentCandidateEvidence, MatchingPolicyConfig).

Architecture:

    Evaluation domain (EvaluationDemand, EvaluationPatent)
                ↓
    DefaultMatchingAdapter          ← THIS MODULE
    (translates evaluation ↔ matching types)
                ↓
    DefaultMatchingEngine.evaluate(DemandSignal, CandidatePool, policy, patent_metadata)
                ↓
    list[str] (ranked publication_ids, returned to evaluation runner)

Invariants:
- Implements EvaluationRankingPort protocol (evaluation domain owns the contract).
- retrieval_scores={} for all candidates: no synthetic evidence is introduced.
  CandidatePool in a sealed benchmark does NOT represent a retrieval result.
- PatentCandidateEvidence is built from real EvaluationPatent data (title, abstract, CPC, date).
  This provides the engine with authentic content for CPC concordance and text feature extraction.
- The ranked list is returned in the engine's original ordering without re-sorting.
- The caller (DefaultEvaluationRunner) never sees CandidatePool, Candidate, or MatchAssessment.
"""

from domain.models.demand import DemandSignal
from domain.models.evaluation import EvaluationDemand, EvaluationPatent
from domain.models.matching import (
    Candidate,
    CandidatePool,
    MatchingPolicyConfig,
    PatentCandidateEvidence,
)
from domain.protocols.evaluation import EvaluationRankingPort
from domain.protocols.matching import MatchingEngine


def _to_patent_candidate_evidence(patent: EvaluationPatent) -> PatentCandidateEvidence:
    """Builds PatentCandidateEvidence from a benchmark EvaluationPatent.

    Uses only data observed in the evaluation dataset. No synthetic scores are fabricated.
    """
    return PatentCandidateEvidence(
        publication_id=patent.publication_id,
        publication_date=patent.publication_date.isoformat() if patent.publication_date else None,
        classifications_cpc=list(patent.classifications_cpc),
        title=patent.title,
        abstract=patent.abstract,
    )


def _to_demand_signal(demand: EvaluationDemand) -> DemandSignal:
    """Converts an evaluation-domain EvaluationDemand to a matching-domain DemandSignal."""
    return DemandSignal(
        demand_id=demand.demand_id,
        source_network=demand.provenance.source_authority,
        title=demand.title,
        description=demand.description,
        posted_date=demand.posted_date.isoformat() if demand.posted_date else None,
        classified_cpc_prefixes=demand.target_cpc_prefixes,
    )


class DefaultMatchingAdapter:
    """Adapter that translates evaluation-domain inputs into matching-domain inputs and back.

    Satisfies EvaluationRankingPort via structural subtyping. The evaluation runner holds
    a reference to this adapter typed as EvaluationRankingPort, so it never sees any
    matching-domain type.

    The adapter is instantiated by the CLI bootstrap layer, which is the appropriate place
    for cross-subsystem wiring.
    """

    def __init__(self, engine: MatchingEngine, policy: MatchingPolicyConfig) -> None:
        self._engine = engine
        self._policy = policy

    def rank_candidates(
        self,
        demand: EvaluationDemand,
        patents: list[EvaluationPatent],
    ) -> list[str]:
        """Translates evaluation inputs to matching types, calls engine, returns ranked pub_ids.

        retrieval_scores={} for all candidates — no synthetic retrieval evidence is fabricated.
        Real patent content (CPC, title, abstract, date) is provided via patent_metadata using
        the existing PatentCandidateEvidence channel designed for this purpose.
        """
        # Translate evaluation types → matching types
        demand_signal = _to_demand_signal(demand)
        candidates = [
            Candidate(publication_id=p.publication_id, retrieval_scores={}) for p in patents
        ]
        pool = CandidatePool(demand_id=demand.demand_id, candidates=candidates)
        evidence = [_to_patent_candidate_evidence(p) for p in patents]

        # Invoke matching engine with honest inputs
        assessments = self._engine.evaluate(
            demand=demand_signal,
            candidates=pool,
            policy=self._policy,
            patent_metadata=evidence,
        )

        # Return ranked publication_ids in original engine order (no re-sorting)
        return [a.publication_id for a in assessments]
