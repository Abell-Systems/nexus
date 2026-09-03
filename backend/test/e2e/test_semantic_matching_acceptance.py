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
from infrastructure.matching.dense_semantic import DuckDbDenseSemanticRetriever, TextEmbedder


class MockEmbedder(TextEmbedder):
    def embed(self, text: str) -> list[float]:
        if "detergente" in text.lower():
            return [1.0, 0.0]
        return [0.0, 1.0]


class EmptyStubRetriever:
    def retrieve(self, demand, *, limit=100):
        return []


def test_semantic_matching_acceptance_flow():
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
            embedding VARCHAR
        )
    """)

    con.executemany(
        "INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "ES-3001-A1",
                "ES",
                "3001",
                "A1",
                "Detergente biodegradable",
                "Composicion de limpieza.",
                "2021-01-01",
                "[1.0, 0.0]",  # Cosine 1.0 with demand
            ),
            (
                "ES-3002-A1",
                "ES",
                "3002",
                "A1",
                "Tubos de laton",
                "Aleacion metalica.",
                "2021-01-01",
                "[0.0, 1.0]",  # Cosine 0.0 with demand
            ),
            (
                "ES-3003-A1",
                "ES",
                "3003",
                "A1",
                "Detergente futuro",
                "Limpieza.",
                "2025-01-01",  # Ineligible temporal
                "[1.0, 0.0]",
            ),
        ],
    )

    embedder = MockEmbedder()
    semantic_retriever = DuckDbDenseSemanticRetriever(connection=con, embedder=embedder)
    lexical_stub = EmptyStubRetriever()
    cpc_stub = EmptyStubRetriever()

    weights = RankerWeights(alpha=0.0, beta=1.0, gamma=0.0)
    service = CandidateMatchingService(
        lexical_retriever=lexical_stub,
        semantic_retriever=semantic_retriever,
        cpc_retriever=cpc_stub,
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
        title="Detergente acuoso",
        description="Buscamos formulacion para lavado",
        posted_date="2022-01-01",
    )

    # Act
    result = service.match(demand)

    # Assert
    # 1. ES-3003-A1 excluded temporally
    pool_ids = [c.publication_id for c in result.pool.candidates]
    assert "ES-3003-A1" not in pool_ids

    # 2. ES-3001-A1 is #1 in semantic and hybrid
    sem_ranked = result.rankings["semantic"]
    assert sem_ranked[0].publication_id == "ES-3001-A1"
    assert sem_ranked[0].rank == 1
    assert sem_ranked[0].score == 1.0

    hybrid_ranked = result.rankings["hybrid"]
    assert hybrid_ranked[0].publication_id == "ES-3001-A1"
    assert hybrid_ranked[0].rank == 1
    assert hybrid_ranked[0].score == 1.0
