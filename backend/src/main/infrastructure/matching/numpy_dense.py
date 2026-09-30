from collections.abc import Sequence

import numpy as np

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import Candidate, RetrievalMethod
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentCandidateRetriever, PatentEligibilityPolicy
from infrastructure.embeddings.embedding_texts import demand_embedding_text

from .dense_semantic import TextEmbedder


class NumpyDenseRetriever(PatentCandidateRetriever):
    """Dense retrieval over a frozen L2-normalized matrix: one matrix-vector product per demand.

    Same scoring and ordering contract as DuckDbDenseSemanticRetriever, without its per-row Python loop:
    eligibility filter first, score (cos + 1) / 2 rounded to 6 decimals, ties by (score DESC, publication_id ASC).
    Patent i in `patents` corresponds to row i of `matrix`.
    """

    def __init__(
        self,
        patents: Sequence[PatentDocument],
        matrix: np.ndarray,
        embedder: TextEmbedder,
        eligibility_policy: PatentEligibilityPolicy,
        min_threshold: float = 0.0,
    ) -> None:
        if matrix.ndim != 2 or matrix.shape[0] != len(patents):
            raise ValueError(f"patents ({len(patents)}) and matrix rows ({matrix.shape[0] if matrix.ndim else 0}) differ")
        self._patents = list(patents)
        self._matrix = matrix
        self._embedder = embedder
        self._eligibility_policy = eligibility_policy
        self._min_threshold = min_threshold

    def retrieve(
        self,
        demand: DemandRecord | DemandSignal,
        *,
        limit: int = 100,
    ) -> list[Candidate]:
        text = demand_embedding_text(demand.title, demand.description)
        if not text:
            return []

        query = np.asarray(self._embedder.embed(text), dtype=np.float32)
        if query.shape != (self._matrix.shape[1],):
            raise ValueError(f"demand vector dimension {query.shape} does not match matrix dimension {self._matrix.shape[1]}")
        norm = float(np.linalg.norm(query))
        if norm <= 1e-9:
            return []
        query = query / norm

        similarities = np.clip(self._matrix @ query, -1.0, 1.0)

        scored: list[tuple[str, float]] = []
        for index, patent in enumerate(self._patents):
            if not self._eligibility_policy.evaluate(patent, demand).is_eligible:
                continue
            score = round((float(similarities[index]) + 1.0) / 2.0, 6)
            if score >= self._min_threshold:
                scored.append((patent.publication_id, score))

        scored.sort(key=lambda item: (-item[1], item[0]))
        return [
            Candidate(publication_id=pub_id, retrieval_scores={RetrievalMethod.SEMANTIC: score})
            for pub_id, score in scored[:limit]
        ]
