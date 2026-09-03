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
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever


class AcceptMockEmbedder(TextEmbedder):
    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0] if "detergente" in text.lower() else [0.0, 1.0]


def test_complete_matching_pipeline_e2e_acceptance():
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

    con.executemany(
        "INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "ES-2849102-B2",
                "ES",
                "2849102",
                "B2",
                "Formulación detergente enzimática",
                "Composición detergente acuosa concentrada para lavado textil.",
                "2021-11-25",
                '["C11D1/00", "C11D3/386"]',
                "[1.0, 0.0]",
            ),
            (
                "ES-2715482-B2",
                "ES",
                "2715482",
                "B2",
                "Microencapsulación de fragancias",
                "Método de encapsulado para detergente.",
                "2020-04-15",
                '["C11D3/50"]',
                "[0.7, 0.7]",
            ),
            (
                "ES-2900000-A1",
                "ES",
                "2900000",
                "A1",
                "Detergente del futuro",
                "Fórmula avanzada.",
                "2025-01-01",  # Ineligible
                '["C11D1/00"]',
                "[1.0, 0.0]",
            ),
        ],
    )

    lex_retriever = DuckDbBM25Retriever(connection=con)
    sem_retriever = DuckDbDenseSemanticRetriever(connection=con, embedder=AcceptMockEmbedder())
    cpc_retriever = DuckDbCPCRetriever(connection=con)

    weights = RankerWeights(alpha=0.35, beta=0.45, gamma=0.20)
    service = CandidateMatchingService(
        lexical_retriever=lex_retriever,
        semantic_retriever=sem_retriever,
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
        title="Detergente biodegradable enzimático",
        description="Formulación líquida para lavado textil",
        posted_date="2022-01-01",
    )

    result = service.match(demand)

    # Observable Acceptance Assertions
    # 1. Temporal filtering: ineligible patent 2025 is excluded
    assert "ES-2900000-A1" not in {c.publication_id for c in result.pool.candidates}

    # 2. Both eligible patents are present in shared pool
    assert {c.publication_id for c in result.pool.candidates} == {"ES-2849102-B2", "ES-2715482-B2"}

    # 3. All 4 rankings populated with full pool size (2)
    for name in ("lexical", "semantic", "cpc", "hybrid"):
        assert len(result.rankings[name]) == 2
        assert result.rankings[name][0].rank == 1
        assert result.rankings[name][1].rank == 2

    # 4. Top ranked document in hybrid is ES-2849102-B2
    assert result.rankings["hybrid"][0].publication_id == "ES-2849102-B2"
    assert result.rankings["hybrid"][0].score > result.rankings["hybrid"][1].score
