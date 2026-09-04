import duckdb

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import (
    Candidate,
    EligibilityReason,
    RetrievalMethod,
    compute_bm25_scores,
)
from domain.models.patent import PatentDocument
from domain.protocols.matching import (
    PatentCandidateRetriever,
    PatentEligibilityPolicy,
)

from .duckdb_helpers import resolve_patent_columns
from .eligibility import DefaultPatentEligibilityPolicy


class DuckDbBM25Retriever(PatentCandidateRetriever):
    """Real vertical slice executing Okapi BM25 retrieval over a DuckDB database or in-memory connection.

    Invariants:
    - Pre-filters eligible patents using PatentEligibilityPolicy before BM25 ranking.
    - Okapi BM25 scoring with k1=1.5, b=0.75 over (title + ' ' + abstract), via the shared
      compute_bm25_scores (domain.models.matching) — the same scoring core the evaluation
      adapter uses for the sealed benchmark (ADR 0013), computed here over the eligible
      subcorpus rather than the full closed universe.
    - Returns up to `limit` candidates with score > 0.
    - Ties broken deterministically by (score DESC, publication_id ASC).
    - Produces domain Candidate objects with RetrievalMethod.LEXICAL score.
    """

    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str = "patents",
        eligibility_policy: PatentEligibilityPolicy | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._con = connection
        self._table_name = table_name
        self._eligibility_policy = eligibility_policy or DefaultPatentEligibilityPolicy()
        self._k1 = k1
        self._b = b

    def retrieve(
        self,
        demand: DemandRecord | DemandSignal,
        *,
        limit: int = 100,
    ) -> list[Candidate]:
        # 1. Fetch all documents from DuckDB
        query = resolve_patent_columns(self._con, self._table_name)
        cursor = self._con.execute(query)
        rows = cursor.fetchall()

        # 2. Filter documents using strict eligibility policy — candidate generation for live
        # matching narrows to the eligible subcorpus; the sealed evaluation benchmark does not.
        eligible_documents: dict[str, str] = {}

        for row in rows:
            pub_id = str(row[0])
            country_code = str(row[1]) if row[1] is not None else ""
            doc_number = str(row[2]) if row[2] is not None else ""
            kind_code = str(row[3]) if row[3] is not None else ""
            title = str(row[4]) if row[4] is not None else ""
            abstract = str(row[5]) if row[5] is not None else ""
            publication_date = str(row[6]) if row[6] is not None else ""

            patent = PatentDocument(
                publication_id=pub_id,
                country_code=country_code,
                doc_number=doc_number,
                kind_code=kind_code,
                title=title,
                abstract=abstract,
                publication_date=publication_date,
            )

            eval_res = self._eligibility_policy.evaluate(patent, demand)
            if eval_res.reason != EligibilityReason.ELIGIBLE:
                continue

            eligible_documents[pub_id] = f"{title} {abstract}"

        if not eligible_documents:
            return []

        # 3. Score the eligible subcorpus
        query_text = f"{demand.title} {demand.description}"
        scores = compute_bm25_scores(query_text, eligible_documents, k1=self._k1, b=self._b)

        # 4. Candidate generation: drop zero scores, sort, truncate to `limit`
        scored_candidates = [(pub_id, score) for pub_id, score in scores.items() if score > 0.0]
        sorted_candidates = sorted(scored_candidates, key=lambda item: (-item[1], item[0]))[:limit]

        return [
            Candidate(
                publication_id=pub_id,
                retrieval_scores={RetrievalMethod.LEXICAL: score},
            )
            for pub_id, score in sorted_candidates
        ]
