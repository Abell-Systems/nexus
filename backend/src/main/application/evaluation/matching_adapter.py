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
- Semantic retrieval_scores are a deterministic derived ranking feature under ADR 0014:
  read from the caller-supplied FrozenEmbeddingArtifact (offline-generated, hash-sealed),
  never computed live — no embedder, no network, no model weights are reachable from this
  module. Stored as RAW cosine in [-1, 1] (ADR 0015 §1); the ADR 0016 fusion transform
  in DefaultEvidenceEvaluator maps them into [0, 1] at fusion time. When no artifact is
  supplied the adapter runs M0-only and semantic scores stay absent (0.0).
- PatentCandidateEvidence is built from real EvaluationPatent data (title, abstract, CPC, date).
  This provides the engine with authentic content for CPC concordance and text feature extraction.
- The ranked list is returned in the engine's original ordering without re-sorting.
- The caller (DefaultEvaluationRunner) never sees CandidatePool, Candidate, or MatchAssessment.
"""

import math

from domain.models.demand import DemandSignal
from domain.models.evaluation import EvaluationDemand, EvaluationPatent, FrozenEmbeddingArtifact
from domain.models.matching import (
    Candidate,
    CandidatePool,
    MatchingPolicyConfig,
    PatentCandidateEvidence,
    RetrievalMethod,
    compute_bm25_scores,
)
from domain.protocols.matching import MatchingEngine


def _raw_cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Raw cosine similarity in [-1, 1] between two frozen artifact vectors.

    Local pure-arithmetic helper (not imported from infrastructure.matching.vector_math:
    the application-isolation contract forbids application → infrastructure imports).
    Production twin: infrastructure/matching/vector_math.cosine_similarity — same formula,
    same [-1, 1] clamp. No (cos + 1) / 2 remap here: normalization is the evaluator's
    fusion-time decision (ADR 0016), never this module's.
    """
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 <= 1e-9 or norm_v2 <= 1e-9:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_v1 * norm_v2)))


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
        semantic_artifact: FrozenEmbeddingArtifact | None = None,
    ) -> None:
        """`bm25_k1`/`bm25_b` are mandatory (no default) under ADR 0005's explicit-injection
        principle: the caller must read them from the frozen model configuration manifest
        (config/evaluations/model_configurations_m0_m6.json, ADR 0012) and pass them in
        explicitly. This adapter has no fallback default — an implementation default here
        would let the manifest silently stop controlling what evaluation actually runs with.

        `semantic_artifact` is optional and selects the evaluation mode explicitly:
        - None → M0-only mode; semantic retrieval_scores stay absent (0.0), exactly as before.
        - FrozenEmbeddingArtifact → M1-wired mode (ADR 0014); raw cosine per candidate.
        The artifact itself must already be hash-verified and source-dataset-verified by
        the caller (CLI bootstrap) before construction — this adapter never touches disk.
        """
        self._engine = engine
        self._policy = policy
        self._bm25_k1 = bm25_k1
        self._bm25_b = bm25_b
        self._semantic_artifact = semantic_artifact

    @property
    def semantic_artifact(self) -> FrozenEmbeddingArtifact | None:
        """Exposes the wired artifact identity for provenance stamping by the caller."""
        return self._semantic_artifact

    def _semantic_scores(self, demand_id: str, patent_ids: list[str]) -> dict[str, float]:
        """Reads RAW cosine scores from the frozen artifact (ADR 0014, ADR 0015 §1).

        Every patent in the closed pool gets exactly one score; a missing demand or
        patent key is a fail-fast ValueError, never a silent 0.0 — a 0.0 raw cosine
        means measured orthogonality, which must stay distinguishable from absent data.
        """
        artifact = self._semantic_artifact
        assert artifact is not None  # guarded by caller; M0-only path never reaches here
        demand_vector = artifact.demand_embeddings.get(demand_id)
        if demand_vector is None:
            raise ValueError(
                f"Frozen embedding artifact '{artifact.artifact_id}' has no demand vector "
                f"for demand_id '{demand_id}'."
            )
        scores: dict[str, float] = {}
        for pub_id in patent_ids:
            patent_vector = artifact.patent_embeddings.get(pub_id)
            if patent_vector is None:
                raise ValueError(
                    f"Frozen embedding artifact '{artifact.artifact_id}' has no patent vector "
                    f"for publication_id '{pub_id}'."
                )
            scores[pub_id] = _raw_cosine_similarity(demand_vector, patent_vector)
        return scores

    def rank_candidates(
        self,
        demand: EvaluationDemand,
        patents: list[EvaluationPatent],
    ) -> list[str]:
        """Translates evaluation inputs to matching types, calls engine, returns ranked pub_ids.

        Lexical retrieval_scores are computed for every patent via compute_bm25_scores, using
        the k1/b this adapter was constructed with — a derived_ranking_feature (ADR 0013),
        grounded only in each patent's observed title and abstract text plus the demand's own
        text. When a semantic artifact was supplied, raw cosine scores are read for every
        patent from the frozen artifact — a derived_ranking_feature (ADR 0014) grounded only
        in sealed vectors, never in annotations. Every patent in `patents` remains a candidate
        regardless of its scores (including 0.0): scoring ranks the closed universe, it does
        not retrieve a subset of it. Real patent content (CPC, title, abstract, date) is
        separately provided via patent_metadata using the existing PatentCandidateEvidence channel.
        """
        # Translate evaluation types → matching types
        demand_signal = _to_demand_signal(demand)

        query_text = f"{demand.title} {demand.description}"
        documents = {p.publication_id: f"{p.title} {p.abstract}" for p in patents}
        lexical_scores = compute_bm25_scores(query_text, documents, k1=self._bm25_k1, b=self._bm25_b)

        semantic_scores: dict[str, float] = {}
        if self._semantic_artifact is not None:
            semantic_scores = self._semantic_scores(demand.demand_id, [p.publication_id for p in patents])

        candidates = [
            Candidate(
                publication_id=p.publication_id,
                retrieval_scores={
                    RetrievalMethod.LEXICAL: lexical_scores[p.publication_id],
                    **(
                        {RetrievalMethod.SEMANTIC: semantic_scores[p.publication_id]}
                        if p.publication_id in semantic_scores
                        else {}
                    ),
                },
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
