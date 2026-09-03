import json
from pathlib import Path

from domain.models.matching import (
    Candidate,
    CandidatePool,
    MatchingResult,
    RankedCandidate,
    RetrievalMethod,
)
from infrastructure.matching.corpus_manifest import compute_file_sha256, verify_corpus_manifest
from infrastructure.matching.telemetry import FileSystemMatchingTelemetrySink


def test_corpus_manifest_verification_and_tampering(tmp_path: Path):
    corpus_file = tmp_path / "corpus.parquet"
    corpus_file.write_text("dummy patent corpus content", encoding="utf-8")

    expected_hash = compute_file_sha256(corpus_file)
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps({"sha256": expected_hash}), encoding="utf-8")

    # 1. Valid verification
    valid, hash_val = verify_corpus_manifest(corpus_file, manifest_file)
    assert valid
    assert hash_val == expected_hash

    # 2. Tampered corpus
    corpus_file.write_text("tampered content", encoding="utf-8")
    valid_tampered, _ = verify_corpus_manifest(corpus_file, manifest_file)
    assert not valid_tampered


def test_filesystem_telemetry_sink_persists_canonical_artifacts(tmp_path: Path):
    sink = FileSystemMatchingTelemetrySink(base_dir=tmp_path)

    cand1 = Candidate(
        publication_id="ES-1",
        retrieval_scores={RetrievalMethod.LEXICAL: 10.0, RetrievalMethod.SEMANTIC: 0.9},
    )
    cand2 = Candidate(
        publication_id="ES-2",
        retrieval_scores={RetrievalMethod.CPC: 1.0},
    )
    pool = CandidatePool(demand_id="D-100", candidates=[cand1, cand2])

    result = MatchingResult(
        demand_id="D-100",
        pool=pool,
        rankings={
            "hybrid": [
                RankedCandidate(publication_id="ES-1", rank=1, score=0.95, components={"alpha": 0.5}),
                RankedCandidate(publication_id="ES-2", rank=2, score=0.50, components={"alpha": 0.5}),
            ],
            "lexical": [
                RankedCandidate(publication_id="ES-1", rank=1, score=1.0),
                RankedCandidate(publication_id="ES-2", rank=2, score=0.0),
            ],
        },
    )

    metadata = {
        "run_id": "RUN-TEST-001",
        "corpus_snapshot_sha256": "abcdef123456",
        "model_version": "1.0.0",
        "weights": {"alpha": 0.5, "beta": 0.5, "gamma": 0.0},
    }

    patent_evidence = {
        "ES-1": {
            "title": "Detergente enzimático",
            "abstract": "Tensioactivos para lavado a baja temperatura.",
            "publication_date": "2021-05-01",
            "cpc_codes": ["C11D1/00"],
        }
    }

    # Act
    returned_run_id = sink.record_run(result, metadata, patent_evidence)
    assert returned_run_id == "RUN-TEST-001"

    run_dir = tmp_path / "RUN-TEST-001"
    assert run_dir.is_dir()

    # Assert 1: result.json (Canonical result for machine & UI)
    result_path = run_dir / "result.json"
    assert result_path.exists()
    with result_path.open("r", encoding="utf-8") as f:
        res_data = json.load(f)
    assert res_data["schema_version"] == "1.0"
    assert res_data["demand_id"] == "D-100"
    assert res_data["shared_pool_size"] == 2
    assert "hybrid" in res_data["rankings"]
    assert "lexical" in res_data["rankings"]

    # Check UI explainability evidence
    top_hybrid = res_data["rankings"]["hybrid"][0]
    assert top_hybrid["publication_id"] == "ES-1"
    assert top_hybrid["rank"] == 1
    assert top_hybrid["score"] == 0.95
    assert top_hybrid["evidence"]["title"] == "Detergente enzimático"
    assert top_hybrid["evidence"]["cpc_codes"] == ["C11D1/00"]

    # Assert 2: metadata.json
    metadata_path = run_dir / "metadata.json"
    assert metadata_path.exists()
    with metadata_path.open("r", encoding="utf-8") as f:
        meta_data = json.load(f)
    assert meta_data["corpus_snapshot_sha256"] == "abcdef123456"
    assert "result_sha256" in meta_data

    # Assert 3: candidates.jsonl (P_shared)
    cand_path = run_dir / "candidates.jsonl"
    assert cand_path.exists()
    lines = cand_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    c1 = json.loads(lines[0])
    assert c1["publication_id"] == "ES-1"
    assert c1["retrieval_scores"]["lexical"] == 10.0

    # Assert 4: rankings.jsonl
    rank_path = run_dir / "rankings.jsonl"
    assert rank_path.exists()
    rank_lines = rank_path.read_text(encoding="utf-8").strip().split("\n")
    # 2 rankings * 2 items = 4 lines
    assert len(rank_lines) == 4
