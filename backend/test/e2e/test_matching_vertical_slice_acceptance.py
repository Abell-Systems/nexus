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
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever


class EmptyStubRetriever:
    """Empty retriever stub for un-implemented channels (Semantic, CPC) in this vertical slice."""

    def retrieve(self, demand, *, limit=100):
        return []


def test_matching_first_vertical_slice_acceptance():
    # 1. Real DuckDB in-memory corpus
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

    con.executemany(
        "INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "ES-2849102-B2",
                "ES",
                "2849102",
                "B2",
                "Composición detergente biodegradable enzimática",
                "Formulación acuosa para lavado a baja temperatura con tensioactivos ecológicos.",
                "2021-11-25",
            ),
            (
                "ES-2715482-B2",
                "ES",
                "2715482",
                "B2",
                "Dispositivo dosificador para lavadoras",
                "Mecanismo de distribución automática de detergente líquido.",
                "2020-04-15",
            ),
            (
                "ES-2900000-A1",
                "ES",
                "2900000",
                "A1",
                "Detergente ecológico futuro",
                "Tensioactivo biodegradable para ropa.",
                "2025-01-01",  # Future date relative to demand
            ),
        ],
    )

    # 2. Real Infrastructure Retriever for Lexical
    lexical_retriever = DuckDbBM25Retriever(connection=con)

    # 3. Empty stubs for Semantic and CPC (tested in later vertical slices)
    semantic_stub = EmptyStubRetriever()
    cpc_stub = EmptyStubRetriever()

    # 4. Real Application Rankers
    weights = RankerWeights(alpha=1.0, beta=0.0, gamma=0.0)
    service = CandidateMatchingService(
        lexical_retriever=lexical_retriever,
        semantic_retriever=semantic_stub,
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
        title="Detergente biodegradable enzimático",
        description="Buscamos formulación líquida para lavado a baja temperatura",
        posted_date="2022-01-01",
    )

    from pathlib import Path

    from domain.models.matching import MatchingPolicyConfig
    policy = MatchingPolicyConfig.load_from_json(Path("config/policies/matching/default_matching_policy.json"))

    # Act: Run complete matching flow
    result = service.match(demand, policy=policy)

    # Assert:
    # 1. ES-2900000-A1 excluded temporally
    assert len(result.pool.candidates) == 2
    pool_ids = [c.publication_id for c in result.pool.candidates]
    assert "ES-2900000-A1" not in pool_ids

    # 2. ES-2849102-B2 ranked #1 in lexical and hybrid
    lexical_ranking = result.rankings["lexical"]
    assert lexical_ranking[0].publication_id == "ES-2849102-B2"
    assert lexical_ranking[0].rank == 1

    hybrid_ranking = result.rankings["hybrid"]
    assert hybrid_ranking[0].publication_id == "ES-2849102-B2"
    assert hybrid_ranking[0].rank == 1
    assert hybrid_ranking[0].score == 1.0  # normalized max
