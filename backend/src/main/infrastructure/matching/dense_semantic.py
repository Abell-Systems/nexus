import json
from typing import Protocol, runtime_checkable

import duckdb

from domain.models.demand import DemandSignal
from domain.models.matching import (
    Candidate,
    EligibilityReason,
    RetrievalMethod,
)
from domain.models.patent import PatentDocument
from domain.protocols.matching import (
    PatentCandidateRetriever,
    PatentEligibilityPolicy,
)

from .duckdb_helpers import resolve_patent_columns
from .eligibility import DefaultPatentEligibilityPolicy
from .vector_math import cosine_similarity


@runtime_checkable
class TextEmbedder(Protocol):
    """Protocol for generating dense text representations."""

    def embed(self, text: str) -> list[float]:
        """Generates embedding vector for a single text."""
        ...


class DuckDbDenseSemanticRetriever(PatentCandidateRetriever):
    """Real vertical slice executing dense semantic retrieval using cosine similarity over precomputed embeddings.

    Invariants:
    - Pre-filters eligible patents using PatentEligibilityPolicy before vector ranking.
    - Embeds demand text (title + ' ' + description) via TextEmbedder.
    - Queries precomputed/persisted patent embeddings in DuckDB (JSON array or FLOAT list).
    - Computes cosine similarity between demand vector and each eligible patent vector.
    - Normalizes cosine similarity to [0, 1] via (cos + 1.0) / 2.0 for non-negative ranking score.
    - Returns up to `limit` candidates with score > 0.
    - Ties broken deterministically by (score DESC, publication_id ASC).
    - Produces domain Candidate objects with RetrievalMethod.SEMANTIC score.
    """

    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection,
        embedder: TextEmbedder,
        table_name: str = "patents",
        embedding_column: str = "embedding",
        eligibility_policy: PatentEligibilityPolicy | None = None,
        min_threshold: float = 0.0,
    ) -> None:
        self._con = connection
        self._embedder = embedder
        self._table_name = table_name
        self._embedding_column = embedding_column
        self._eligibility_policy = eligibility_policy or DefaultPatentEligibilityPolicy()
        self._min_threshold = min_threshold

    def retrieve(
        self,
        demand: DemandSignal,
        *,
        limit: int = 100,
    ) -> list[Candidate]:
        # 1. Embed demand query text
        demand_text = f"{demand.title} {demand.description}".strip()
        if not demand_text:
            return []

        demand_vector = self._embedder.embed(demand_text)
        if not demand_vector:
            return []

        # 2. Fetch patents, metadata, and embeddings from DuckDB
        query = resolve_patent_columns(self._con, self._table_name, extra_column=self._embedding_column)
        cursor = self._con.execute(query)
        rows = cursor.fetchall()

        # 3. Filter eligible patents and compute cosine similarity
        scored_candidates: list[tuple[str, float]] = []

        for row in rows:
            pub_id = str(row[0])
            country_code = str(row[1]) if row[1] is not None else ""
            doc_number = str(row[2]) if row[2] is not None else ""
            kind_code = str(row[3]) if row[3] is not None else ""
            title = str(row[4]) if row[4] is not None else ""
            abstract = str(row[5]) if row[5] is not None else ""
            publication_date = str(row[6]) if row[6] is not None else ""
            raw_emb = row[7]

            patent = PatentDocument(
                publication_id=pub_id,
                country_code=country_code,
                doc_number=doc_number,
                kind_code=kind_code,
                title=title,
                abstract=abstract,
                publication_date=publication_date,
            )

            # Strict pre-retrieval eligibility check
            eval_res = self._eligibility_policy.evaluate(patent, demand)
            if eval_res.reason != EligibilityReason.ELIGIBLE:
                continue

            # Parse patent embedding vector
            patent_vector: list[float] = []
            if isinstance(raw_emb, list):
                patent_vector = [float(x) for x in raw_emb]
            elif isinstance(raw_emb, str):
                try:
                    parsed = json.loads(raw_emb)
                    if isinstance(parsed, list):
                        patent_vector = [float(x) for x in parsed]
                except (json.JSONDecodeError, ValueError):
                    pass

            if not patent_vector:
                continue

            raw_cos = cosine_similarity(demand_vector, patent_vector)
            # Monotonic scaling to [0, 1] range: (cos + 1) / 2
            norm_score = (raw_cos + 1.0) / 2.0

            if norm_score >= self._min_threshold:
                scored_candidates.append((pub_id, round(norm_score, 6)))

        # 4. Deterministic sorting: (score DESC, publication_id ASC)
        sorted_candidates = sorted(scored_candidates, key=lambda item: (-item[1], item[0]))[:limit]

        return [
            Candidate(
                publication_id=pub_id,
                retrieval_scores={RetrievalMethod.SEMANTIC: score},
            )
            for pub_id, score in sorted_candidates
        ]
