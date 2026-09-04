import duckdb
import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import RetrievalMethod
from infrastructure.matching.dense_semantic import DuckDbDenseSemanticRetriever, TextEmbedder
from domain.models.matching import cosine_similarity


class MockDeterministicEmbedder(TextEmbedder):
    """Deterministic embedder returning fixed orthogonal or aligned vectors for testing."""

    def __init__(self, mapping: dict[str, list[float]], default_dim: int = 4) -> None:
        self.mapping = mapping
        self.default_dim = default_dim

    def embed(self, text: str) -> list[float]:
        # Prefix match or exact match from mapping
        for key, vec in self.mapping.items():
            if key.lower() in text.lower():
                return vec
        return [0.0] * self.default_dim


def test_vector_math_cosine_similarity_properties():
    # 1. Identical vectors -> 1.0
    v1 = [1.0, 2.0, 3.0]
    assert cosine_similarity(v1, v1) == pytest.approx(1.0)

    # 2. Orthogonal vectors -> 0.0
    v_x = [1.0, 0.0]
    v_y = [0.0, 1.0]
    assert cosine_similarity(v_x, v_y) == 0.0

    # 3. Opposite vectors -> -1.0
    v_pos = [1.0, 1.0]
    v_neg = [-1.0, -1.0]
    assert cosine_similarity(v_pos, v_neg) == pytest.approx(-1.0)

    # 4. Zero vector or dimension mismatch -> 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert cosine_similarity([], []) == 0.0


@pytest.fixture
def memory_duckdb_semantic_patents():
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

    # 4-dimensional embeddings
    docs = [
        # P1: High alignment with target demand vector [1.0, 0.0, 0.0, 0.0]
        (
            "ES-3001",
            "ES",
            "3001",
            "A1",
            "Formulacion detergente enzimatica",
            "Tensioactivos acuosos.",
            "2021-05-01",
            "[1.0, 0.0, 0.0, 0.0]",  # cos = 1.0 -> norm_score = 1.0
        ),
        # P2: Partial alignment [0.7071, 0.7071, 0.0, 0.0]
        (
            "ES-3002",
            "ES",
            "3002",
            "A1",
            "Dispensador industrial de detergente",
            "Distribuidor automatico.",
            "2021-06-01",
            "[0.7071, 0.7071, 0.0, 0.0]",  # cos = 0.7071 -> norm_score approx 0.85355
        ),
        # P3: Orthogonal vector [0.0, 1.0, 0.0, 0.0]
        (
            "ES-3003",
            "ES",
            "3003",
            "B1",
            "Extrusion de tubos de laton",
            "Aleaciones metalicas.",
            "2021-07-01",
            "[0.0, 1.0, 0.0, 0.0]",  # cos = 0.0 -> norm_score = 0.50
        ),
        # P4: High alignment but TEMPORALLY INVALID (published 2025 > 2022)
        (
            "ES-3004",
            "ES",
            "3004",
            "A1",
            "Detergente del futuro",
            "Tensioactivo biodegradable.",
            "2025-01-01",
            "[1.0, 0.0, 0.0, 0.0]",
        ),
        # P5 & P6: Identical embeddings to verify deterministic tie-breaking (ES-3005 vs ES-3006)
        (
            "ES-3006",
            "ES",
            "3006",
            "A1",
            "Detergente secundario B",
            "Limpieza.",
            "2021-08-01",
            "[0.5, 0.5, 0.5, 0.5]",
        ),
        (
            "ES-3005",
            "ES",
            "3005",
            "A1",
            "Detergente secundario A",
            "Limpieza.",
            "2021-08-01",
            "[0.5, 0.5, 0.5, 0.5]",
        ),
    ]

    con.executemany("INSERT INTO patents VALUES (?, ?, ?, ?, ?, ?, ?, ?)", docs)
    return con


def test_duckdb_dense_semantic_retriever_vertical_slice(memory_duckdb_semantic_patents):
    embedder = MockDeterministicEmbedder(
        mapping={"biodegradable detergent": [1.0, 0.0, 0.0, 0.0]}
    )
    retriever = DuckDbDenseSemanticRetriever(
        connection=memory_duckdb_semantic_patents,
        embedder=embedder,
    )

    demand = DemandSignal(
        demand_id="INNOGET-2292",
        source_network="InnoGet",
        title="Biodegradable detergent",
        description="Seeking low-temperature cleaning formulation",
        posted_date="2022-01-01",
    )

    candidates = retriever.retrieve(demand, limit=100)
    retrieved_ids = [c.publication_id for c in candidates]

    # Invariant 1: Ineligible patent ES-3004 (2025) MUST NOT appear
    assert "ES-3004" not in retrieved_ids

    # Invariant 2: ES-3001 (cos=1.0, score=1.0) must be rank 1
    assert retrieved_ids[0] == "ES-3001"
    assert candidates[0].retrieval_scores[RetrievalMethod.SEMANTIC] == 1.0

    # Invariant 3: ES-3002 (cos=0.7071, score approx 0.8536) must be rank 2
    assert retrieved_ids[1] == "ES-3002"
    assert candidates[1].retrieval_scores[RetrievalMethod.SEMANTIC] > candidates[2].retrieval_scores[RetrievalMethod.SEMANTIC]

    # Invariant 4: Deterministic tie-breaking between ES-3005 and ES-3006
    idx_3005 = retrieved_ids.index("ES-3005")
    idx_3006 = retrieved_ids.index("ES-3006")
    assert idx_3005 < idx_3006  # ES-3005 precedes ES-3006
