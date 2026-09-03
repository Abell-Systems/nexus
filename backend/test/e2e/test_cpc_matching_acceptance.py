import duckdb

from application.matching.rankers import (
    CPCRanker,
    HybridRanker,
    LexicalRanker,
    SemanticRanker,
)
from application.matching.service import CandidateMatchingService
from domain.models.demand import DemandSignal
from domain.models.matching import RankerWeights
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever


class EmptyStubRetriever:
    def retrieve(self, demand, *, limit=100):
        return []


def test_cpc_matching_acceptance_flow():
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE patents (
            publication_id VARCHAR PRIMARY KEY,
            country_code VARCHAR,
            doc_number VARCHAR,
            kind_code VARCHAR,
            title VARCHAR,
            abstract VARCHAR,
            publication_date VARCHAR,
            cpc_codes VARCHAR
        )
    """)

    con.executemany(
        "INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "ES-2849102-B2",
                "ES",
                "2849102",
                "B2",
                "Formulación detergente",
                "Detergente para lavado textil.",
                "2021-11-25",
                '["C11D1/00", "C11D3/386"]',
            ),
            (
                "ES-2684913-B1",
                "ES",
                "2684913",
                "B1",
                "Aleación de latón",
                "Mecanizado de tuberías.",
                "2018-10-15",
                '["C22C9/00"]',
            ),
            (
                "ES-2900000-A1",
                "ES",
                "2900000",
                "A1",
                "Detergente futuro",
                "Detergente.",
                "2025-01-01",  # Ineligible
                '["C11D1/00"]',
            ),
        ],
    )

    cpc_retriever = DuckDbCPCRetriever(connection=con)
    lexical_stub = EmptyStubRetriever()
    semantic_stub = EmptyStubRetriever()

    weights = RankerWeights(alpha=0.0, beta=0.0, gamma=1.0)
    service = CandidateMatchingService(
        lexical_retriever=lexical_stub,
        semantic_retriever=semantic_stub,
        cpc_retriever=cpc_retriever,
        rankers={
            "lexical": LexicalRanker(),
            "semantic": SemanticRanker(),
            "cpc": CPCRanker(),
            "hybrid": HybridRanker(weights),
        },
    )

    demand = DemandSignal(
        demand_id="INNOGET-2292",
        source_network="InnoGet",
        title="Detergent Demand",
        description="Seeking industrial surfactant detergent",
        posted_date="2022-01-01",
    )

    # Act
    result = service.match(demand)

    # Assert
    # 1. ES-2900000-A1 excluded temporally
    pool_ids = [c.publication_id for c in result.pool.candidates]
    assert "ES-2900000-A1" not in pool_ids

    # 2. ES-2849102-B2 has subclass C11D match -> rank 1 in cpc and hybrid
    cpc_ranking = result.rankings["cpc"]
    assert cpc_ranking[0].publication_id == "ES-2849102-B2"
    assert cpc_ranking[0].rank == 1

    hybrid_ranking = result.rankings["hybrid"]
    assert hybrid_ranking[0].publication_id == "ES-2849102-B2"
    assert hybrid_ranking[0].rank == 1
