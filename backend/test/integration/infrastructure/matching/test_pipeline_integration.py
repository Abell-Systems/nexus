import duckdb

from application.matching.rankers import (
    CPCRanker,
    HybridRanker,
    LexicalRanker,
    SemanticRanker,
)
from application.matching.service import CandidateMatchingService
from domain.models.demand import DemandSignal
from domain.models.matching import (
    CPCModality,
    DemandCPC,
    RankerWeights,
    RetrievalMethod,
)
from infrastructure.matching.dense_semantic import DuckDbDenseSemanticRetriever, TextEmbedder
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever


class IntegratedMockEmbedder(TextEmbedder):
    """Provides embeddings for integration test scenario."""

    def embed(self, text: str) -> list[float]:
        # Target demand: [1.0, 0.0, 0.0]
        if "enzimatico" in text.lower() or "detergente" in text.lower() or "detergent" in text.lower():
            return [1.0, 0.0, 0.0]
        return [0.0, 1.0, 0.0]


def test_complete_matching_pipeline_integration_partially_overlapping():
    # Setup DuckDB corpus designed for partial overlap across BM25, Semantic, and CPC
    # P1 (ES-4001): Retrieved by BM25 + Semantic + CPC (Triple overlap)
    # P2 (ES-4002): Retrieved by BM25 + Semantic (no CPC)
    # P3 (ES-4003): Retrieved by Semantic + CPC (no BM25)
    # P4 (ES-4004): Retrieved by BM25 only
    # P5 (ES-4005): Retrieved by CPC only
    # P6 (ES-4006): Ineligible (published 2025 > demand 2022)
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
            cpc_codes VARCHAR,
            embedding VARCHAR
        )
    """)

    docs = [
        # P1: BM25 (high terms), Semantic ([1, 0, 0]), CPC (C11D1/02)
        (
            "ES-4001",
            "ES",
            "4001",
            "B2",
            "Detergente biodegradable enzimatico",
            "Formulacion liquida para lavado a baja temperatura.",
            "2021-11-25",
            '["C11D1/02"]',
            "[1.0, 0.0, 0.0]",
        ),
        # P2: BM25 (terms match), Semantic ([0.8, 0.2, 0.0]), CPC (H01M10/0525 -> no match)
        (
            "ES-4002",
            "ES",
            "4002",
            "A1",
            "Dispensador automatico para detergente",
            "Mecanismo dosificador de lavado.",
            "2021-06-10",
            '["H01M10/0525"]',
            "[0.8, 0.2, 0.0]",
        ),
        # P3: BM25 (no terms overlap), Semantic ([0.9, 0.1, 0.0]), CPC (C11D3/386 -> match 0.50)
        (
            "ES-4003",
            "ES",
            "4003",
            "A1",
            "Proteasas termoestables",
            "Complejo biologico de alto rendimiento.",
            "2021-08-15",
            '["C11D3/386"]',
            "[0.9, 0.1, 0.0]",
        ),
        # P4: BM25 (terms match), Semantic ([0.0, 1.0, 0.0] -> cos 0), CPC (none)
        (
            "ES-4004",
            "ES",
            "4004",
            "A1",
            "Lavado de recipientes con detergente",
            "Limpieza mecanica de envases industriales.",
            "2020-03-01",
            '["B08B9/00"]',
            "[0.0, 1.0, 0.0]",
        ),
        # P5: BM25 (no terms), Semantic ([0.0, 1.0, 0.0]), CPC (C11D1/66 -> match 0.75)
        (
            "ES-4005",
            "ES",
            "4005",
            "A1",
            "Tensioactivos derivados de esteres",
            "Sintesis quimica pura.",
            "2019-12-01",
            '["C11D1/66"]',
            "[0.0, 1.0, 0.0]",
        ),
        # P6: Ineligible patent (temporal)
        (
            "ES-4006",
            "ES",
            "4006",
            "A1",
            "Detergente biodegradable enzimatico futuro",
            "Formulacion futura.",
            "2025-01-01",
            '["C11D1/02"]',
            "[1.0, 0.0, 0.0]",
        ),
    ]
    con.executemany("INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", docs)

    # Explicit DemandCPC for the demand
    demand_cpc = DemandCPC(
        symbols=["C11D1/00"],
        modality=CPCModality.CURATED,
        provenance="expert_benchmark",
    )

    # Instantiate real retrievers
    lexical_retriever = DuckDbBM25Retriever(connection=con)
    semantic_retriever = DuckDbDenseSemanticRetriever(
        connection=con,
        embedder=IntegratedMockEmbedder(),
        min_threshold=0.55,  # Excludes cos <= 0 (where norm_score <= 0.50)
    )
    cpc_retriever = DuckDbCPCRetriever(connection=con, demand_cpc=demand_cpc)

    weights = RankerWeights(alpha=0.30, beta=0.50, gamma=0.20)
    service = CandidateMatchingService(
        lexical_retriever=lexical_retriever,
        semantic_retriever=semantic_retriever,
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
        title="Detergente biodegradable enzimatico",
        description="Formulacion liquida para lavado a baja temperatura",
        posted_date="2022-01-01",
    )

    # Act
    result = service.match(demand)

    # Assert 1: Ineligible patent ES-4006 must never appear in CandidatePool
    pool_ids = {c.publication_id for c in result.pool.candidates}
    assert "ES-4006" not in pool_ids

    # Assert 2: CandidatePool is exact union P_shared = P_lex U P_sem U P_cpc
    # Expected eligible candidates retrieved: ES-4001, ES-4002, ES-4003, ES-4004, ES-4005
    assert pool_ids == {"ES-4001", "ES-4002", "ES-4003", "ES-4004", "ES-4005"}
    assert len(result.pool.candidates) == 5

    # Assert 3: Provenance preservation
    c_4001 = next(c for c in result.pool.candidates if c.publication_id == "ES-4001")
    assert RetrievalMethod.LEXICAL in c_4001.retrieval_scores
    assert RetrievalMethod.SEMANTIC in c_4001.retrieval_scores
    assert RetrievalMethod.CPC in c_4001.retrieval_scores

    c_4004 = next(c for c in result.pool.candidates if c.publication_id == "ES-4004")
    assert RetrievalMethod.LEXICAL in c_4004.retrieval_scores
    assert RetrievalMethod.SEMANTIC not in c_4004.retrieval_scores
    assert RetrievalMethod.CPC not in c_4004.retrieval_scores

    # Assert 4: All 4 rankers receive identical CandidatePool with identical candidates
    for strat in ("lexical", "semantic", "cpc", "hybrid"):
        assert strat in result.rankings
        ranking_ids = [r.publication_id for r in result.rankings[strat]]
        assert set(ranking_ids) == pool_ids
        assert len(ranking_ids) == 5

    # Assert 5: ES-4001 (strong on all 3 signals) is rank #1 in hybrid
    hybrid_ranking = result.rankings["hybrid"]
    assert hybrid_ranking[0].publication_id == "ES-4001"
    assert hybrid_ranking[0].rank == 1
    assert hybrid_ranking[0].score > 0.8
    # Components properly populated
    assert "alpha" in hybrid_ranking[0].components
    assert "norm_lexical" in hybrid_ranking[0].components
    assert "semantic" in hybrid_ranking[0].components
    assert "cpc" in hybrid_ranking[0].components
