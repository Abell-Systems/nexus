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
- Lexical retrieval_scores are a deterministic derived ranking feature under ADR 0013:
  computed from each patent's own observed title/abstract text, over every patent in the
  closed pool — no filtering, no top-K truncation, no annotation ever reaches this
  computation (see ADR 0013 and its enforcement in
  test_adr_0007_invariants.py::DerivedRankingFeaturesTest). Its parameters (k1, b) are
  injected by the caller from the frozen model configuration manifest (ADR 0012) — this
  adapter never falls back to an implementation default: the frozen manifest is the
  authority for what configuration evaluation actually runs with, not the other way round.
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

    def __init__(
        self,
        engine: MatchingEngine,
        policy: MatchingPolicyConfig,
        *,
        bm25_k1: float,
        bm25_b: float,
    ) -> None:
        """`bm25_k1`/`bm25_b` are mandatory (no default) under ADR 0005's explicit-injection
        principle: the caller must read them from the frozen model configuration manifest
        (config/evaluations/model_configurations_m0_m6.json, ADR 0012) and pass them in
        explicitly. This adapter has no fallback default — an implementation default here
        would let the manifest silently stop controlling what evaluation actually runs with.
        """
        self._engine = engine
        self._policy = policy
        self._bm25_k1 = bm25_k1
        self._bm25_b = bm25_b

    def rank_candidates(
        self,
        demand: EvaluationDemand,
        patents: list[EvaluationPatent],
    ) -> list[str]:
        """Translates evaluation inputs to matching types, calls engine, returns ranked pub_ids.

        Lexical retrieval_scores are computed for every patent via compute_bm25_scores, using
        the k1/b this adapter was constructed with — a derived_ranking_feature (ADR 0013),
        grounded only in each patent's observed title and abstract text plus the demand's own
        text. Every patent in `patents` remains a candidate regardless of its score (including
        0.0): scoring ranks the closed universe, it does not retrieve a subset of it. Real
        patent content (CPC, title, abstract, date) is separately provided via patent_metadata
        using the existing PatentCandidateEvidence channel.
        """
        # Translate evaluation types → matching types
        demand_signal = _to_demand_signal(demand)

        query_text = f"{demand.title} {demand.description}"
        documents = {p.publication_id: f"{p.title} {p.abstract}" for p in patents}
        lexical_scores = compute_bm25_scores(query_text, documents, k1=self._bm25_k1, b=self._bm25_b)

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
