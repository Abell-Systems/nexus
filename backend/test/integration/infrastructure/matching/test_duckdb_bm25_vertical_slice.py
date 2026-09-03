import duckdb
import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import (
    EligibilityReason,
    RetrievalMethod,
)
from domain.models.patent import PatentDocument
from infrastructure.matching.duckdb_bm25 import DuckDbBM25Retriever
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy


@pytest.fixture
def memory_duckdb_patents():
    """Creates a controlled adversarial patent subcorpus in in-memory DuckDB."""
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

    # Populate adversarial corpus
    docs = [
        # P1: Exact match on core terms, valid date
        (
            "ES-1001",
            "ES",
            "1001",
            "A1",
            "Biodegradable liquid detergent formulation",
            "Aqueous cleaning composition containing biodegradable surfactants and enzymes for cold wash.",
            "2021-06-15",
        ),
        # P2: Partial match (detergent without biodegradable), valid date
        (
            "ES-1002",
            "ES",
            "1002",
            "A1",
            "Industrial detergent dispenser",
            "Automated dosing mechanism for liquid detergent in washing machines.",
            "2020-03-10",
        ),
        # P3: Completely irrelevant, valid date
        (
            "ES-1003",
            "ES",
            "1003",
            "B1",
            "Copper alloy extrusion process",
            "Method for manufacturing high-strength brass pipes and metallurgical tubes.",
            "2019-11-20",
        ),
        # P4: EXACT match on terms, but TEMPORALLY INVALID (publication_date > demand_date)
        (
            "ES-1004",
            "ES",
            "1004",
            "A1",
            "Advanced biodegradable liquid detergent formulation",
            "Ultra concentrated biodegradable surfactant composition for low temperature cleaning.",
            "2023-05-01",  # published AFTER demand (2022-01-01)
        ),
        # P5: EXACT match on terms, but TEMPORALLY INVALID (publication_date == demand_date)
        (
            "ES-1005",
            "ES",
            "1005",
            "A1",
            "Biodegradable enzymatic detergent",
            "Enzymatic formulation for cold wash.",
            "2022-01-01",  # published ON demand date
        ),
        # P6: High match, but WRONG JURISDICTION (EP instead of ES)
        (
            "EP-1006",
            "EP",
            "1006",
            "A1",
            "Biodegradable detergent composition",
            "Surfactant and enzyme blend for liquid detergent.",
            "2021-01-01",
        ),
        # P7: High match, but MISSING TEXT (empty abstract)
        (
            "ES-1007",
            "ES",
            "1007",
            "A1",
            "Biodegradable liquid detergent",
            "",
            "2021-01-01",
        ),
        # P8 & P9: Identical text to test deterministic tie-breaking by publication_id
        (
            "ES-1009",
            "ES",
            "1009",
            "A1",
            "Standard detergent wash formulation",
            "General surfactant detergent solution for cleaning.",
            "2021-02-01",
        ),
        (
            "ES-1008",
            "ES",
            "1008",
            "A1",
            "Standard detergent wash formulation",
            "General surfactant detergent solution for cleaning.",
            "2021-02-01",
        ),
    ]

    con.executemany(
        "INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?)",
        docs,
    )
    return con


def test_eligibility_policy_rules():
    policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")
    demand = DemandSignal(
        demand_id="D-1",
        source_network="InnoGet",
        title="Demand",
        description="Description",
        posted_date="2022-01-01",
    )

    # 1. Strictly prior publication date -> ELIGIBLE
    doc_prior = PatentDocument(
        publication_id="ES-1",
        country_code="ES",
        doc_number="1",
        kind_code="A1",
        title="Title",
        abstract="Abstract",
        publication_date="2021-12-31",
    )
    assert policy.evaluate(doc_prior, demand).reason == EligibilityReason.ELIGIBLE

    # 2. Equal publication date -> EXCLUDED_TEMPORAL
    doc_equal = PatentDocument(
        publication_id="ES-2",
        country_code="ES",
        doc_number="2",
        kind_code="A1",
        title="Title",
        abstract="Abstract",
        publication_date="2022-01-01",
    )
    assert policy.evaluate(doc_equal, demand).reason == EligibilityReason.EXCLUDED_TEMPORAL

    # 3. Subsequent publication date -> EXCLUDED_TEMPORAL
    doc_after = PatentDocument(
        publication_id="ES-3",
        country_code="ES",
        doc_number="3",
        kind_code="A1",
        title="Title",
        abstract="Abstract",
        publication_date="2022-01-02",
    )
    assert policy.evaluate(doc_after, demand).reason == EligibilityReason.EXCLUDED_TEMPORAL

    # 4. Wrong jurisdiction -> EXCLUDED_JURISDICTION
    doc_wrong_jur = PatentDocument(
        publication_id="US-4",
        country_code="US",
        doc_number="4",
        kind_code="A1",
        title="Title",
        abstract="Abstract",
        publication_date="2021-01-01",
    )
    assert policy.evaluate(doc_wrong_jur, demand).reason == EligibilityReason.EXCLUDED_JURISDICTION

    # 5. Missing title/abstract -> EXCLUDED_MISSING_TEXT
    doc_empty_text = PatentDocument(
        publication_id="ES-5",
        country_code="ES",
        doc_number="5",
        kind_code="A1",
        title="Title",
        abstract="",
        publication_date="2021-01-01",
    )
    assert policy.evaluate(doc_empty_text, demand).reason == EligibilityReason.EXCLUDED_MISSING_TEXT


def test_duckdb_bm25_retriever_vertical_slice(memory_duckdb_patents):
    retriever = DuckDbBM25Retriever(connection=memory_duckdb_patents)

    demand = DemandSignal(
        demand_id="INNOGET-2292",
        source_network="InnoGet",
        title="Biodegradable liquid detergent",
        description="Seeking biodegradable liquid detergent for cold low temperature washing",
        posted_date="2022-01-01",
    )

    candidates = retriever.retrieve(demand, limit=100)

    # Invariants verification:
    # 1. ES-1004 (published 2023) and ES-1005 (published 2022-01-01) MUST NEVER appear
    retrieved_ids = [c.publication_id for c in candidates]
    assert "ES-1004" not in retrieved_ids
    assert "ES-1005" not in retrieved_ids

    # 2. EP-1006 (jurisdiction EP) and ES-1007 (empty abstract) MUST NEVER appear
    assert "EP-1006" not in retrieved_ids
    assert "ES-1007" not in retrieved_ids

    # 3. ES-1003 (completely irrelevant copper alloy) must have score 0 and not appear
    assert "ES-1003" not in retrieved_ids

    # 4. ES-1001 (exact match on biodegradable liquid detergent) must be rank 1 with highest score
    assert retrieved_ids[0] == "ES-1001"
    assert candidates[0].retrieval_scores[RetrievalMethod.LEXICAL] > 0.0

    # 5. ES-1001 score must be strictly higher than ES-1002 (partial match)
    score_1001 = candidates[0].retrieval_scores[RetrievalMethod.LEXICAL]
    cand_1002 = next(c for c in candidates if c.publication_id == "ES-1002")
    assert score_1001 > cand_1002.retrieval_scores[RetrievalMethod.LEXICAL]

    # 6. Deterministic tie-breaking: ES-1008 and ES-1009 have identical scores, ES-1008 must precede ES-1009
    idx_1008 = retrieved_ids.index("ES-1008")
    idx_1009 = retrieved_ids.index("ES-1009")
    cand_1008 = next(c for c in candidates if c.publication_id == "ES-1008")
    cand_1009 = next(c for c in candidates if c.publication_id == "ES-1009")
    assert cand_1008.retrieval_scores[RetrievalMethod.LEXICAL] == cand_1009.retrieval_scores[RetrievalMethod.LEXICAL]
    assert idx_1008 < idx_1009  # 'ES-1008' < 'ES-1009' alphabetically


def test_duckdb_bm25_limit_behavior(memory_duckdb_patents):
    retriever = DuckDbBM25Retriever(connection=memory_duckdb_patents)
    demand = DemandSignal(
        demand_id="INNOGET-2292",
        source_network="InnoGet",
        title="Detergent wash formulation",
        description="Cleaning surfactants",
        posted_date="2022-01-01",
    )

    # Limit = 2
    candidates = retriever.retrieve(demand, limit=2)
    assert len(candidates) == 2
