from dataclasses import dataclass

import duckdb

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import Candidate, CandidatePool, EligibilityReason
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentCandidateRetriever, PatentEligibilityPolicy


@dataclass(frozen=True)
class CandidatePoolBuildResult:
    """Output of CandidatePoolBuilder.build(): the union pool plus each candidate's
    temporal eligibility outcome (ADR 0019). Kept separate from CandidatePool itself
    so the shared domain model is not extended for this PR-E-specific concern."""

    pool: CandidatePool
    temporal_reasons: dict[str, EligibilityReason]


class CandidatePoolBuilder:
    """Builds an annotation candidate pool as the union of independently-injected
    first-stage retrievers — deliberately never routes through MatchingAdapter or
    any final ranking, to avoid selection-bias/circularity between what gets
    annotated and what is later evaluated (see PR-E spec §3).
    """

    def __init__(
        self,
        retrievers: list[PatentCandidateRetriever],
        eligibility_policy: PatentEligibilityPolicy,
        connection: duckdb.DuckDBPyConnection,
        table_name: str = "patents",
    ) -> None:
        if not retrievers:
            raise ValueError("CandidatePoolBuilder requires at least one retriever")
        self._retrievers = retrievers
        self._eligibility_policy = eligibility_policy
        self._con = connection
        self._table_name = table_name

    def build(
        self,
        demand: DemandRecord | DemandSignal,
        *,
        limit_per_method: int = 20,
    ) -> CandidatePoolBuildResult:
        merged: dict[str, Candidate] = {}
        for retriever in self._retrievers:
            for candidate in retriever.retrieve(demand, limit=limit_per_method):
                if candidate.publication_id in merged:
                    existing = merged[candidate.publication_id]
                    merged[candidate.publication_id] = Candidate(
                        publication_id=candidate.publication_id,
                        retrieval_scores={**existing.retrieval_scores, **candidate.retrieval_scores},
                    )
                else:
                    merged[candidate.publication_id] = candidate

        patents_by_id = self._fetch_patents(set(merged.keys()))
        temporal_reasons: dict[str, EligibilityReason] = {}
        for pub_id in merged:
            patent = patents_by_id.get(pub_id)
            if patent is None:
                temporal_reasons[pub_id] = EligibilityReason.EXCLUDED_MISSING_TEXT
                continue
            result = self._eligibility_policy.evaluate(patent, demand)
            temporal_reasons[pub_id] = result.reason

        pool = CandidatePool(demand_id=demand.demand_id, candidates=list(merged.values()))
        return CandidatePoolBuildResult(pool=pool, temporal_reasons=temporal_reasons)

    def _fetch_patents(self, publication_ids: set[str]) -> dict[str, PatentDocument]:
        # Inlined instead of reusing infrastructure.matching.duckdb_helpers
        # .resolve_patent_columns: application/ must not import infrastructure/
        # (.importlinter application-isolation contract).
        rows = self._con.execute(
            f"SELECT publication_id, country_code, doc_number, kind_code, "
            f"title, abstract, publication_date FROM {self._table_name}"
        ).fetchall()
        result: dict[str, PatentDocument] = {}
        for row in rows:
            pub_id = str(row[0])
            if pub_id not in publication_ids:
                continue
            result[pub_id] = PatentDocument(
                publication_id=pub_id,
                country_code=str(row[1]) if row[1] is not None else "",
                doc_number=str(row[2]) if row[2] is not None else "",
                kind_code=str(row[3]) if row[3] is not None else "",
                title=str(row[4]) if row[4] is not None else "",
                abstract=str(row[5]) if row[5] is not None else "",
                publication_date=str(row[6]) if row[6] is not None else None,
            )
        return result
