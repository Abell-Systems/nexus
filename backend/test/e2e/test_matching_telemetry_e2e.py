import json

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
from infrastructure.matching.telemetry import FileSystemMatchingTelemetrySink


class DeterministicEmbedder(TextEmbedder):
    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0] if "detergente" in text.lower() else [0.0, 1.0]


def test_matching_execution_to_telemetry_and_api_ui_consumption(tmp_path):
    # 1. Real DuckDB in-memory database
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
                "Composición acuosa concentrada para lavado textil.",
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
        ],
    )

    lex_retriever = DuckDbBM25Retriever(connection=con)
    sem_retriever = DuckDbDenseSemanticRetriever(connection=con, embedder=DeterministicEmbedder())
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

    # Act 1: Run matching use case
    result = service.match(demand)

    # Act 2: Record telemetry via sink
    sink = FileSystemMatchingTelemetrySink(base_dir=tmp_path)
    metadata = {
        "run_id": "RUN-PILOT-001",
        "snapshot_sha256": "fake_sha256_oepm_snapshot",
        "engine_version": "2.0.0",
    }
    patent_evidence = {
        "ES-2849102-B2": {
            "title": "Formulación detergente enzimática",
            "abstract": "Composición acuosa concentrada para lavado textil.",
            "publication_date": "2021-11-25",
            "cpc_codes": ["C11D1/00", "C11D3/386"],
        },
        "ES-2715482-B2": {
            "title": "Microencapsulación de fragancias",
            "abstract": "Método de encapsulado para detergente.",
            "publication_date": "2020-04-15",
            "cpc_codes": ["C11D3/50"],
        },
    }
    run_id = sink.record_run(result, metadata, patent_evidence)
    assert run_id == "RUN-PILOT-001"

    # Act 3: Verify machine & human UI consumption contract
    run_dir = tmp_path / run_id
    result_json_path = run_dir / "result.json"
    assert result_json_path.exists()

    contract = result_json_path.read_text(encoding="utf-8")
    parsed_contract = json.loads(contract)

    assert parsed_contract["schema_version"] == "1.0"
    assert parsed_contract["run_id"] == "RUN-PILOT-001"
    assert parsed_contract["demand_id"] == "INNOGET-2292"
    assert parsed_contract["shared_pool_size"] == 2
    assert "hybrid" in parsed_contract["rankings"]
    assert "lexical" in parsed_contract["rankings"]
    assert "semantic" in parsed_contract["rankings"]
    assert "cpc" in parsed_contract["rankings"]

    # Check that UI human explanation evidence is present
    top_hybrid = parsed_contract["rankings"]["hybrid"][0]
    assert top_hybrid["publication_id"] == "ES-2849102-B2"
    assert top_hybrid["rank"] == 1
    assert top_hybrid["evidence"]["title"] == "Formulación detergente enzimática"
    assert "norm_lexical" in top_hybrid["signals"]
    assert "semantic" in top_hybrid["signals"]
    assert "cpc" in top_hybrid["signals"]
