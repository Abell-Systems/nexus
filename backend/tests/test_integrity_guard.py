"""Tests for dataset cryptographic integrity and scientific evidence separation."""

import pytest
import json
from pathlib import Path
from backend.patent_agent.tools.metrics import ExecutionMode
from scripts.run_spanish_paper_experiment import verify_dataset_manifest, run_experiment


def test_verify_manifest_success():
    manifest = verify_dataset_manifest("data/snapshots/patents_es_manifest.json")
    assert "Spanish National Patent Corpus" in manifest["dataset_name"]
    assert len(manifest["sha256_hash"]) == 64
    assert manifest["total_records"] > 0


def test_verify_manifest_detects_tampering(tmp_path):
    fake_manifest_path = tmp_path / "fake_manifest.json"
    fake_parquet_path = tmp_path / "fake.parquet"
    fake_parquet_path.write_bytes(b"corrupted binary data")

    fake_manifest = {
        "dataset_name": "Tampered Dataset",
        "sha256_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "provenance": {"parquet_file": str(fake_parquet_path)}
    }
    with open(fake_manifest_path, "w") as f:
        json.dump(fake_manifest, f)

    with pytest.raises(ValueError, match="Dataset integrity mismatch"):
        verify_dataset_manifest(str(fake_manifest_path))


def test_quantitative_metrics_run_without_llm(tmp_path):
    output_dir = tmp_path / "empirical_test_out"
    metrics_list, case_studies = run_experiment(
        mode=ExecutionMode.EMPIRICAL,
        db_path="data/snapshots/patents_es_snapshot.duckdb",
        manifest_path="data/snapshots/patents_es_manifest.json",
        output_dir=str(output_dir),
        dry_run_llm=True
    )

    # 1. Quantitative metrics exist and computed
    assert len(metrics_list) >= 4
    for m in metrics_list:
        assert 0.0 <= m["density"] <= 1.0
        assert 0.0 <= m["recency"] <= 1.0
        assert 0.0 <= m["citation_traction"] <= 1.0
        assert 0.0 <= m["white_space_score"] <= 1.0

    # 2. Metadata reflects verified SHA256
    with open(output_dir / "metadata.json") as f:
        meta = json.load(f)
    assert "EMPIRICAL (VERIFIED" in meta["dataset_status"]
    assert len(meta["dataset_sha256"]) == 64

    # 3. Case studies in dry-run are explicitly marked as synthetic
    assert meta["synthesis_status"] == "SYNTHETIC DRY-RUN (AWAITING LIVE GROQ API KEY)"
    for cs in case_studies:
        assert cs["evidence_tier"] == "synthetic_dry_run"
        assert "[DRY-RUN]" in cs["candidate"]["title"]

    # 4. Summary markdown contains audit banner
    summary_md = (output_dir / "paper_results_summary.md").read_text()
    assert "[SCIENTIFIC EVIDENCE AUDIT TRAIL]" in summary_md
    assert "EMPIRICAL (VERIFIED" in summary_md


def test_fixture_mode_banners_as_unpublishable(tmp_path):
    output_dir = tmp_path / "fixture_test_out"
    metrics_list, case_studies = run_experiment(
        mode=ExecutionMode.FIXTURE,
        db_path="data/snapshots/patents_es_snapshot.duckdb",
        output_dir=str(output_dir),
        dry_run_llm=True
    )

    with open(output_dir / "metadata.json") as f:
        meta = json.load(f)
    assert "NOT FOR PUBLICATION" in meta["dataset_status"]
