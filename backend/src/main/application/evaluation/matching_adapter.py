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
- Lexical (BM25) retrieval_scores are a derived_ranking_feature under ADR 0013: computed
  deterministically from each patent's own observed title/abstract text via
  domain.models.matching.compute_bm25_scores, over every patent in the closed pool — no
  filtering, no top-K truncation, no annotation ever reaches this computation (see
  ADR 0013 and its enforcement in test_adr_0007_invariants.py::DerivedRankingFeaturesTest).
  Semantic retrieval_scores remain absent (0.0): M1 is not yet defined (separate decision).
  CandidatePool in a sealed benchmark does NOT represent a retrieval result — every patent
  remains a candidate regardless of its lexical score.
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
    RetrievalMethod,
    compute_bm25_scores,
)
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

        Lexical retrieval_scores are computed for every patent via compute_bm25_scores — a
        derived_ranking_feature (ADR 0013), grounded only in each patent's observed title and
        abstract text plus the demand's own text. Every patent in `patents` remains a candidate
        regardless of its score (including 0.0): scoring ranks the closed universe, it does not
        retrieve a subset of it. Real patent content (CPC, title, abstract, date) is separately
        provided via patent_metadata using the existing PatentCandidateEvidence channel.
        """
        # Translate evaluation types → matching types
        demand_signal = _to_demand_signal(demand)

        query_text = f"{demand.title} {demand.description}"
        documents = {p.publication_id: f"{p.title} {p.abstract}" for p in patents}
        lexical_scores = compute_bm25_scores(query_text, documents)

        candidates = [
            Candidate(
                publication_id=p.publication_id,
                retrieval_scores={RetrievalMethod.LEXICAL: lexical_scores[p.publication_id]},
            )
            for p in patents
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
