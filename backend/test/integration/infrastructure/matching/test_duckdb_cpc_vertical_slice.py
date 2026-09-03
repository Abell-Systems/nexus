import duckdb
import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import (
    CPCModality,
    DemandCPC,
    RetrievalMethod,
)
from infrastructure.matching.duckdb_cpc import DuckDbCPCRetriever, extract_demand_cpc_auto


@pytest.fixture
def memory_duckdb_cpc_patents():
    """Creates a controlled patent subcorpus with structured CPC classifications."""
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

    docs = [
        # P1: Exact Subgroup match with C11D1/02 -> 1.00
        (
            "ES-2001",
            "ES",
            "2001",
            "A1",
            "Detergente sulfatado",
            "Formulacion de limpieza.",
            "2021-05-01",
            '["C11D1/02", "C11D11/00"]',
        ),
        # P2: Same Main Group C11D1 -> 0.75 (C11D1/66)
        (
            "ES-2002",
            "ES",
            "2002",
            "A1",
            "Detergente no ionico",
            "Tensioactivo ester.",
            "2021-06-01",
            '["C11D1/66"]',
        ),
        # P3: Same Subclass C11D -> 0.50 (C11D3/386)
        (
            "ES-2003",
            "ES",
            "2003",
            "B1",
            "Enzimas para lavado",
            "Proteasas para detergencia.",
            "2021-07-01",
            '["C11D3/386"]',
        ),
        # P4: Same Section C -> 0.25 (C22C1/00)
        (
            "ES-2004",
            "ES",
            "2004",
            "A1",
            "Aleacion de cobre",
            "Metales no ferrosos.",
            "2021-08-01",
            '["C22C1/00"]',
        ),
        # P5: Different Section H -> 0.00 (H01M10/0525) -> should NOT be retrieved (threshold 0.25)
        (
            "ES-2005",
            "ES",
            "2005",
            "A1",
            "Bateria de litio",
            "Electrolito solido.",
            "2021-09-01",
            '["H01M10/0525"]',
        ),
        # P6: Exact match C11D1/02 but TEMPORALLY INVALID (2025 > 2022)
        (
            "ES-2006",
            "ES",
            "2006",
            "A1",
            "Detergente futuro",
            "Composicion avanzada.",
            "2025-01-01",
            '["C11D1/02"]',
        ),
        # P7 & P8: Same Subclass C11D -> 0.50, tests deterministic tie-breaking
        (
            "ES-2008",
            "ES",
            "2008",
            "A1",
            "Detergente aromatizado B",
            "Fragancias.",
            "2021-04-01",
            '["C11D3/50"]',
        ),
        (
            "ES-2007",
            "ES",
            "2007",
            "A1",
            "Detergente aromatizado A",
            "Fragancias.",
            "2021-04-01",
            '["C11D3/50"]',
        ),
    ]

    con.executemany("INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?, ?)", docs)
    return con


def test_duckdb_cpc_retriever_hierarchical_scoring_and_invariants(memory_duckdb_cpc_patents):
    # Demand with curated/exact CPC C11D1/02
    demand_cpc = DemandCPC(
        symbols=["C11D1/02"],
        modality=CPCModality.CURATED,
        provenance="expert_curated",
    )
    retriever = DuckDbCPCRetriever(
        connection=memory_duckdb_cpc_patents,
        demand_cpc=demand_cpc,
    )

    demand = DemandSignal(
        demand_id="INNOGET-2292",
        source_network="InnoGet",
        title="Detergente biodegradable",
        description="Tensioactivos para limpieza",
        posted_date="2022-01-01",
    )

    candidates = retriever.retrieve(demand, limit=100)
    retrieved_ids = [c.publication_id for c in candidates]

    # Invariant 1: Temporally invalid ES-2006 MUST NOT appear
    assert "ES-2006" not in retrieved_ids

    # Invariant 2: Unrelated section ES-2005 (score 0.0) MUST NOT appear
    assert "ES-2005" not in retrieved_ids

    # Invariant 3: Hierarchical ordering:
    # ES-2001 (1.00) > ES-2002 (0.75) > ES-2003/ES-2007/ES-2008 (0.50) > ES-2004 (0.25)
    assert retrieved_ids[0] == "ES-2001"
    assert candidates[0].retrieval_scores[RetrievalMethod.CPC] == 1.00

    assert retrieved_ids[1] == "ES-2002"
    assert candidates[1].retrieval_scores[RetrievalMethod.CPC] == 0.75

    # Check ties between ES-2007 and ES-2008 (both 0.50): ES-2007 must precede ES-2008
    idx_2007 = retrieved_ids.index("ES-2007")
    idx_2008 = retrieved_ids.index("ES-2008")
    assert idx_2007 < idx_2008

    # Check ES-2004 has section-level concordance 0.25
    cand_2004 = next(c for c in candidates if c.publication_id == "ES-2004")
    assert cand_2004.retrieval_scores[RetrievalMethod.CPC] == 0.25


def test_extract_demand_cpc_auto():
    demand = DemandSignal(
        demand_id="D-1",
        source_network="InnoGet",
        title="Biodegradable surfactant detergent",
        description="Liquid cleaning formulation for washing",
        posted_date="2022-01-01",
    )
    cpc = extract_demand_cpc_auto(demand)
    assert cpc.modality == CPCModality.AUTO
    # Matches 'detergent', 'surfactant' in CPC_TAXONOMY_MAP
    assert any("C11D" in s for s in cpc.symbols)
