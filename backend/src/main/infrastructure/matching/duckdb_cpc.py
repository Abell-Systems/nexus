import json
from typing import Any

import duckdb

from application.landscape.cpc_taxonomy import map_concept_to_cpc
from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import (
    Candidate,
    CPCConcordanceLevels,
    CPCModality,
    DemandCPC,
    EligibilityReason,
    MatchingPolicyConfig,
    RetrievalMethod,
    compute_max_cpc_similarity,
)
from domain.models.patent import PatentDocument
from domain.protocols.matching import (
    PatentCandidateRetriever,
    PatentEligibilityPolicy,
)

from .duckdb_helpers import resolve_patent_columns
from .eligibility import DefaultPatentEligibilityPolicy


def extract_demand_cpc_auto(demand: DemandRecord | DemandSignal, policy: Any | None = None) -> DemandCPC:
    """Extracts automated CPC classification symbols (C_d^auto) from demand text."""
    combined_text = f"{demand.title} {demand.description}"
    symbols = map_concept_to_cpc(combined_text, policy=policy) if policy else []
    return DemandCPC(
        symbols=symbols,
        modality=CPCModality.AUTO,
        provenance="rule_based_taxonomy_map",
    )


class DuckDbCPCRetriever(PatentCandidateRetriever):
    """Real vertical slice executing hierarchical CPC concordance retrieval over DuckDB.

    Invariants:
    - Pre-filters eligible patents using PatentEligibilityPolicy before CPC evaluation.
    - Resolves demand CPC representation according to pre-registered modality (AUTO by default).
    - Computes hierarchical concordance sim(C_d, C_p) = max_{c1, c2} sim_CPC(c1, c2).
    - Returns up to `limit` candidates with concordance score >= min_threshold (default 0.25).
    - Ties broken deterministically by (score DESC, publication_id ASC).
    - Produces domain Candidate objects with RetrievalMethod.CPC score.
    """

    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str = "patents",
        eligibility_policy: PatentEligibilityPolicy | None = None,
        demand_cpc: DemandCPC | None = None,
        policy: MatchingPolicyConfig | None = None,
        min_threshold: float | None = None,
    ) -> None:
        self._con = connection
        self._table_name = table_name
        self._eligibility_policy = eligibility_policy or DefaultPatentEligibilityPolicy()
        self._demand_cpc = demand_cpc
        self._policy = policy
        self._levels = (
            policy.cpc_concordance_levels
            if policy
            else CPCConcordanceLevels(
                subgroup=1.0, main_group=0.75, subclass=0.5, section=0.25, none=0.0
            )
        )
        self._min_threshold = (
            min_threshold
            if min_threshold is not None
            else self._levels.section
        )

    def retrieve(
        self,
        demand: DemandRecord | DemandSignal,
        *,
        limit: int = 100,
    ) -> list[Candidate]:
        # 1. Determine demand CPC representation
        demand_cpc = self._demand_cpc or extract_demand_cpc_auto(demand, policy=self._policy)
        if not demand_cpc.symbols:
            return []

        # 2. Fetch all documents and CPC classifications from DuckDB
        query = resolve_patent_columns(self._con, self._table_name, extra_column="cpc_codes")
        cursor = self._con.execute(query)
        rows = cursor.fetchall()

        # 3. Filter eligible patents and score by hierarchical CPC concordance
        scored_candidates: list[tuple[str, float]] = []

        for row in rows:
            pub_id = str(row[0])
            country_code = str(row[1]) if row[1] is not None else ""
            doc_number = str(row[2]) if row[2] is not None else ""
            kind_code = str(row[3]) if row[3] is not None else ""
            title = str(row[4]) if row[4] is not None else ""
            abstract = str(row[5]) if row[5] is not None else ""
            publication_date = str(row[6]) if row[6] is not None else ""
            raw_cpc = row[7]

            patent = PatentDocument(
                publication_id=pub_id,
                country_code=country_code,
                doc_number=doc_number,
                kind_code=kind_code,
                title=title,
                abstract=abstract,
                publication_date=publication_date,
            )

            # Strict pre-retrieval eligibility evaluation
            eval_res = self._eligibility_policy.evaluate(patent, demand)
            if eval_res.reason != EligibilityReason.ELIGIBLE:
                continue

            # Parse patent CPC symbols (supports JSON string, list or comma-delimited)
            patent_cpcs: list[str] = []
            if isinstance(raw_cpc, list):
                patent_cpcs = [str(c) for c in raw_cpc]
            elif isinstance(raw_cpc, str):
                try:
                    parsed = json.loads(raw_cpc)
                    patent_cpcs = [str(c) for c in parsed] if isinstance(parsed, list) else [raw_cpc]
                except (json.JSONDecodeError, ValueError):
                    patent_cpcs = [c.strip() for c in raw_cpc.split(",") if c.strip()]

            similarity = compute_max_cpc_similarity(demand_cpc.symbols, patent_cpcs, levels=self._levels)
            if similarity >= self._min_threshold:
                scored_candidates.append((pub_id, round(similarity, 4)))

        # 4. Deterministic sorting: (score DESC, publication_id ASC)
        sorted_candidates = sorted(scored_candidates, key=lambda item: (-item[1], item[0]))[:limit]

        return [
            Candidate(
                publication_id=pub_id,
                retrieval_scores={RetrievalMethod.CPC: score},
            )
            for pub_id, score in sorted_candidates
        ]
