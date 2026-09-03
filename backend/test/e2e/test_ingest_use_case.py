"""End-to-End (E2E) Ingestion Use Case and Clean-Clone Reproducibility Gate Tests.

Validates:
1. Production CLI execution over unmocked official fixtures.
2. Scientific Gate 7: Clean-Clone Reproducibility Gate (Run A == Run B).
   - Identical Merkle canonical dataset content SHA-256
   - Identical snapshot manifest SHA-256
   - Identical record counts, partition structures, and schema versions
   - Identical zero-copy DuckDB analytical query and aggregation outputs
3. Comprehensive CLI argument validation and error exit codes.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from infrastructure.storage.duckdb_engine import DuckDbQueryEngine

CLI_ENV = {
    **os.environ,
    "PYTHONPATH": str(Path("backend/src/main").resolve()),
}


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "infrastructure.cli"] + args
    return subprocess.run(cmd, capture_output=True, text=True, env=CLI_ENV)


def test_ingest_clean_clone_ab_reproducibility_gate(tmp_path: Path):
    """Verify Scientific Gate 7: Dual independent clean-clone ingestion runs produce exact cryptographic identity (A == B)."""
    raw_fixture = Path("data/raw/oepm_open_data_es.json")
    assert raw_fixture.exists(), f"OEPM raw data fixture missing at {raw_fixture}"

    dataset_id = "patents_es_repro"
    run_a_dir = tmp_path / "run_a"
    run_b_dir = tmp_path / "run_b"

    # 1. Independent Execution: Run A
    res_a = run_cli([
        "ingest",
        "--source-type", "oepm_bopi",
        "--source-file", str(raw_fixture),
        "--dataset-id", dataset_id,
        "--output-dir", str(run_a_dir),
        "--transformation-version", "1.0.0",
    ])
    assert res_a.returncode == 0, f"Run A failed (code {res_a.returncode}):\nSTDOUT:\n{res_a.stdout}\nSTDERR:\n{res_a.stderr}"

    # 2. Independent Execution: Run B (in an isolated directory)
    res_b = run_cli([
        "ingest",
        "--source-type", "oepm_bopi",
        "--source-file", str(raw_fixture),
        "--dataset-id", dataset_id,
        "--output-dir", str(run_b_dir),
        "--transformation-version", "1.0.0",
    ])
    assert res_b.returncode == 0, f"Run B failed (code {res_b.returncode}):\nSTDOUT:\n{res_b.stdout}\nSTDERR:\n{res_b.stderr}"

    # 3. Verify Manifest File Existence & Content
    manifest_a_path = run_a_dir / "canonical" / dataset_id / "manifest.json"
    manifest_b_path = run_b_dir / "canonical" / dataset_id / "manifest.json"

    assert manifest_a_path.exists(), f"Manifest A missing at {manifest_a_path}"
    assert manifest_b_path.exists(), f"Manifest B missing at {manifest_b_path}"

    with open(manifest_a_path, encoding="utf-8") as f:
        manifest_a = json.load(f)
    with open(manifest_b_path, encoding="utf-8") as f:
        manifest_b = json.load(f)

    # 4. Assert Bit-for-Bit Merkle and Manifest Equality
    assert manifest_a["dataset_content_sha256"] == manifest_b["dataset_content_sha256"], (
        f"dataset_content_sha256 mismatch!\nRun A: {manifest_a['dataset_content_sha256']}\nRun B: {manifest_b['dataset_content_sha256']}"
    )
    assert len(manifest_a["dataset_content_sha256"]) == 64

    assert manifest_a["manifest_sha256"] == manifest_b["manifest_sha256"], (
        f"manifest_sha256 mismatch!\nRun A: {manifest_a['manifest_sha256']}\nRun B: {manifest_b['manifest_sha256']}"
    )
    assert len(manifest_a["manifest_sha256"]) == 64

    assert manifest_a["record_count"] == 16
    assert manifest_b["record_count"] == 16
    assert manifest_a["schema_version"] == "1.0.0"
    assert manifest_b["schema_version"] == "1.0.0"

    assert len(manifest_a["parts"]) == len(manifest_b["parts"])
    for part_a, part_b in zip(manifest_a["parts"], manifest_b["parts"], strict=False):
        assert part_a["part_name"] == part_b["part_name"]
        assert part_a["row_count"] == part_b["row_count"]
        assert part_a["file_sha256"] == part_b["file_sha256"]

    # 5. Query Engine Equivalence
    canonical_a_dir = run_a_dir / "canonical" / dataset_id
    canonical_b_dir = run_b_dir / "canonical" / dataset_id

    engine_a = DuckDbQueryEngine.from_parquet_dir(canonical_a_dir)
    engine_b = DuckDbQueryEngine.from_parquet_dir(canonical_b_dir)

    results_a_c11d = engine_a.search_by_cpc_prefix("C11D")
    results_b_c11d = engine_b.search_by_cpc_prefix("C11D")
    assert len(results_a_c11d) == 3
    assert len(results_b_c11d) == 3
    assert [r["publication_id"] for r in results_a_c11d] == [r["publication_id"] for r in results_b_c11d]

    agg_a = engine_a.get_cluster_aggregates("C11D")
    agg_b = engine_b.get_cluster_aggregates("C11D")
    assert agg_a == agg_b
    assert agg_a["patent_count"] == 3
    assert agg_a["observed_citations_count"] == 3


def test_cli_missing_source_file_fails(tmp_path: Path):
    """Verify CLI exits with non-zero status and reports error when source file is not found."""
    non_existent = tmp_path / "does_not_exist.json"
    res = run_cli([
        "ingest",
        "--source-type", "oepm_bopi",
        "--source-file", str(non_existent),
        "--dataset-id", "test_ds",
        "--output-dir", str(tmp_path / "out"),
    ])
    assert res.returncode != 0
    assert "not found" in res.stderr.lower() or "error" in res.stderr.lower()


def test_cli_unsupported_source_type_fails(tmp_path: Path):
    """Verify CLI exits with non-zero status and reports error when source format is unsupported."""
    raw_fixture = Path("data/raw/oepm_open_data_es.json")
    res = run_cli([
        "ingest",
        "--source-type", "unsupported_source_xyz",
        "--source-file", str(raw_fixture),
        "--dataset-id", "err_test",
        "--output-dir", str(tmp_path / "out"),
    ])
    assert res.returncode != 0
    assert "unsupported" in res.stderr.lower()


def test_cli_missing_required_arguments_fails():
    """Verify CLI exits with standard argument parser error when mandatory parameters are omitted."""
    res = run_cli(["ingest"])
    assert res.returncode != 0
    assert "required" in res.stderr.lower()


def test_cli_validation_failure_exits_nonzero(tmp_path: Path):
    """Verify CLI exits with non-zero status and reports error when domain validation fails."""
    invalid_file = tmp_path / "invalid_patents.json"
    invalid_file.write_text(
        json.dumps({
            "publications": [
                {
                    "publication_number": "",
                    "title": "Invalid Patent",
                }
            ]
        }),
        encoding="utf-8",
    )

    res = run_cli([
        "ingest",
        "--source-type", "oepm_bopi",
        "--source-file", str(invalid_file),
        "--dataset-id", "invalid_test",
        "--output-dir", str(tmp_path / "out"),
    ])
    assert res.returncode != 0
    assert "validation error" in res.stderr.lower() or "publication_id" in res.stderr.lower() or "validation" in res.stderr.lower()
