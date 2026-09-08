"""Real (no-fake) integration test for the seam Findings 1+2 of the final review fixed:
retrievers gating on is_eligible rather than reason==ELIGIBLE, and CandidatePoolBuilder
only filtering excluded candidates. Covers the exact ADR 0019 scenario from the real
N=39 corpus: a demand with posted_date=None (unknown) must still produce a non-empty
pool when using AnnotationPoolEligibilityPolicy, with the candidate tagged TEMPORAL_UNKNOWN.
"""

import duckdb

from application.matching.candidate_pool_builder import CandidatePoolBuilder
from domain.models.demand import DemandSignal
from domain.models.matching import EligibilityReason
from infrastructure.matching.annotation_pool_eligibility import AnnotationPoolEligibilityPolicy
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever


def test_should_produce_nonempty_pool_with_temporal_unknown_when_demand_posted_date_is_none():
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE patents (
            publication_id VARCHAR PRIMARY KEY,
            country_code VARCHAR,
            doc_number VARCHAR,
            kind_code VARCHAR,
            title VARCHAR,
            abstract VARCHAR,
            publication_date VARCHAR
        )
    """)
    con.execute(
        "INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "ES-2001",
            "ES",
            "2001",
            "A1",
            "Biodegradable liquid detergent formulation",
            "Aqueous cleaning composition containing biodegradable surfactants and enzymes for cold wash.",
            "2021-06-15",
        ),
    )

    policy = AnnotationPoolEligibilityPolicy()
    retriever = DuckDbBM25Retriever(connection=con, eligibility_policy=policy)
    builder = CandidatePoolBuilder(retrievers=[retriever], eligibility_policy=policy, connection=con)

    demand = DemandSignal(
        demand_id="D-UNKNOWN-DATE",
        source_network="InnoGet",
        title="Biodegradable liquid detergent",
        description="Seeking biodegradable liquid detergent for cold low temperature washing",
        posted_date=None,
    )

    result = builder.build(demand, limit_per_method=100)

    assert len(result.pool.candidates) > 0
    assert {c.publication_id for c in result.pool.candidates} == {"ES-2001"}
    assert result.temporal_reasons["ES-2001"] == EligibilityReason.TEMPORAL_UNKNOWN
