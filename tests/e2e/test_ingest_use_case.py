"""End-to-End (E2E) Ingestion Use Case and Clean-Clone Reproducibility Gate Tests.

Validates:
1. Production CLI execution (`nexus ingest`) over unmocked official fixtures.
2. Scientific Gate 7: Clean-Clone Reproducibility Gate (Run A == Run B).
   - Identical Merkle canonical dataset content SHA-256
   - Identical snapshot manifest SHA-256
   - Identical record counts, partition structures, and schema versions
   - Identical zero-copy DuckDB analytical query and aggregation outputs
3. Comprehensive CLI argument validation and error exit codes.
"""

import json
from pathlib import Path
import subprocess
import sys

from nexus.infrastructure.storage.duckdb_engine import DuckDbQueryEngine


def test_ingest_clean_clone_ab_reproducibility_gate(tmp_path: Path):
    """Verify Scientific Gate 7: Dual independent clean-clone ingestion runs produce exact cryptographic identity (A == B)."""
    raw_fixture = Path("data/raw/oepm_open_data_es.json")
    assert raw_fixture.exists(), f"OEPM raw data fixture missing at {raw_fixture}"

    dataset_id = "patents_es_repro"
    run_a_dir = tmp_path / "run_a"
    run_b_dir = tmp_path / "run_b"

    # 1. Independent Execution: Run A
    cmd_a = [
        sys.executable,
        "-m",
        "nexus.interfaces.cli.main",
        "ingest",
        "--source-type",
        "oepm_bopi",
        "--source-file",
        str(raw_fixture),
        "--dataset-id",
        dataset_id,
        "--output-dir",
        str(run_a_dir),
        "--transformation-version",
        "1.0.0",
    ]
    res_a = subprocess.run(cmd_a, capture_output=True, text=True)
    assert res_a.returncode == 0, f"Run A failed (code {res_a.returncode}):\nSTDOUT:\n{res_a.stdout}\nSTDERR:\n{res_a.stderr}"

    # 2. Independent Execution: Run B (in an isolated directory)
    cmd_b = [
        sys.executable,
        "-m",
        "nexus.interfaces.cli.main",
        "ingest",
        "--source-type",
        "oepm_bopi",
        "--source-file",
        str(raw_fixture),
        "--dataset-id",
        dataset_id,
        "--output-dir",
        str(run_b_dir),
        "--transformation-version",
        "1.0.0",
    ]
    res_b = subprocess.run(cmd_b, capture_output=True, text=True)
    assert res_b.returncode == 0, f"Run B failed (code {res_b.returncode}):\nSTDOUT:\n{res_b.stdout}\nSTDERR:\n{res_b.stderr}"

    # 3. Verify Manifest File Existence & Content
    manifest_a_path = run_a_dir / "snapshots" / f"{dataset_id}_manifest.json"
    manifest_b_path = run_b_dir / "snapshots" / f"{dataset_id}_manifest.json"
    assert manifest_a_path.exists(), f"Manifest A missing: {manifest_a_path}"
    assert manifest_b_path.exists(), f"Manifest B missing: {manifest_b_path}"

    manifest_a = json.loads(manifest_a_path.read_text(encoding="utf-8"))
    manifest_b = json.loads(manifest_b_path.read_text(encoding="utf-8"))

    # INVARIANT 1: Canonical dataset content SHA-256 equivalence
    assert manifest_a["dataset_content_sha256"] == manifest_b["dataset_content_sha256"]
    assert len(manifest_a["dataset_content_sha256"]) == 64

    # INVARIANT 2: Snapshot manifest SHA-256 equivalence
    assert manifest_a["manifest_sha256"] == manifest_b["manifest_sha256"]
    assert len(manifest_a["manifest_sha256"]) == 64

    # INVARIANT 3: Record count exactness
    assert manifest_a["record_count"] == manifest_b["record_count"] == 16

    # INVARIANT 4: Schema and transformation version exactness
    assert manifest_a["schema_version"] == manifest_b["schema_version"] == "1.0.0"
    assert manifest_a["transformation_version"] == manifest_b["transformation_version"] == "1.0.0"

    # INVARIANT 5: Source batches and partition parts exactness
    assert manifest_a["source_batches"] == manifest_b["source_batches"]
    assert manifest_a["parts"] == manifest_b["parts"]
    assert len(manifest_a["parts"]) >= 2  # At least patents and observations parts

    # 4. Zero-Copy In-Memory DuckDB Query Equivalence
    canonical_a_dir = run_a_dir / "canonical" / dataset_id
    canonical_b_dir = run_b_dir / "canonical" / dataset_id
    assert canonical_a_dir.exists()
    assert canonical_b_dir.exists()

    engine_a = DuckDbQueryEngine.from_parquet_dir(canonical_a_dir)
    engine_b = DuckDbQueryEngine.from_parquet_dir(canonical_b_dir)

    # Search queries produce identical sets
    c11d_a = engine_a.search_by_cpc_prefix("C11D")
    c11d_b = engine_b.search_by_cpc_prefix("C11D")
    assert len(c11d_a) == len(c11d_b) == 3
    assert [r["publication_id"] for r in c11d_a] == [r["publication_id"] for r in c11d_b]

    h01m_a = engine_a.search_by_cpc_prefix("H01M")
    h01m_b = engine_b.search_by_cpc_prefix("H01M")
    assert len(h01m_a) == len(h01m_b) == 3
    assert [r["publication_id"] for r in h01m_a] == [r["publication_id"] for r in h01m_b]

    # Cluster aggregations produce identical statistical metrics
    aggs_c11d_a = engine_a.get_cluster_aggregates("C11D")
    aggs_c11d_b = engine_b.get_cluster_aggregates("C11D")
    assert aggs_c11d_a == aggs_c11d_b
    assert aggs_c11d_a["patent_count"] == 3
    assert aggs_c11d_a["observed_citations_count"] == 3

    aggs_h01m_a = engine_a.get_cluster_aggregates("H01M")
    aggs_h01m_b = engine_b.get_cluster_aggregates("H01M")
    assert aggs_h01m_a == aggs_h01m_b
    assert aggs_h01m_a["patent_count"] == 3


def test_cli_missing_source_file_fails(tmp_path: Path):
    """Verify CLI gracefully rejects non-existent input files with non-zero exit code."""
    non_existent = tmp_path / "does_not_exist.json"
    cmd = [
        sys.executable,
        "-m",
        "nexus.interfaces.cli.main",
        "ingest",
        "--source-type",
        "oepm_bopi",
        "--source-file",
        str(non_existent),
        "--dataset-id",
        "err_test",
        "--output-dir",
        str(tmp_path / "out"),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert "does not exist" in res.stderr.lower() or "not found" in res.stderr.lower()


def test_cli_unsupported_source_type_fails(tmp_path: Path):
    """Verify CLI rejects unknown source types with non-zero exit code and error description."""
    raw_fixture = Path("data/raw/oepm_open_data_es.json")
    cmd = [
        sys.executable,
        "-m",
        "nexus.interfaces.cli.main",
        "ingest",
        "--source-type",
        "unsupported_source_xyz",
        "--source-file",
        str(raw_fixture),
        "--dataset-id",
        "err_test",
        "--output-dir",
        str(tmp_path / "out"),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert "unsupported source type" in res.stderr.lower()


def test_cli_missing_required_arguments_fails():
    """Verify CLI exits with standard argument parser error when mandatory parameters are omitted."""
    cmd = [
        sys.executable,
        "-m",
        "nexus.interfaces.cli.main",
        "ingest",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert "required" in res.stderr.lower()


def test_cli_validation_failure_exits_nonzero(tmp_path: Path):
    """Verify CLI exits with non-zero status and reports error when domain validation fails."""
    invalid_file = tmp_path / "invalid_patents.json"
    invalid_file.write_text(
        json.dumps({
            "publications": [
                {
                    "publication_number": "",  # Empty publication id -> triggers ValidationError
                    "title": "Invalid Patent",
                }
            ]
        }),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "nexus.interfaces.cli.main",
        "ingest",
        "--source-type",
        "oepm_bopi",
        "--source-file",
        str(invalid_file),
        "--dataset-id",
        "invalid_test",
        "--output-dir",
        str(tmp_path / "out"),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode != 0
    assert "validation failure" in res.stderr.lower() or "publication_id" in res.stderr.lower()
