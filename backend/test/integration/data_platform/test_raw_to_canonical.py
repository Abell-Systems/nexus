"""Full Data Platform Lifecycle Integration Tests.

Verifies complete unmocked end-to-end pipeline:
OepmRawSource -> FilesystemRawStore -> OepmNormalizer -> PatentValidator ->
ParquetCanonicalStore -> DatasetSnapshot -> DuckDbQueryEngine.
"""

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from application.ingestion.normalizers.oepm_normalizer import OepmNormalizer
from application.ingestion.pipeline import IngestionPipeline, IngestionSummary
from application.ingestion.validator import PatentValidator, ValidationError
from domain.models.evidence import VerificationStatus
from domain.protocols.sources import RawPayload
from infrastructure.sources.patent.oepm_raw_source import OepmRawSource
from infrastructure.storage.duckdb_engine import DuckDbQueryEngine
from infrastructure.storage.parquet_store import ParquetCanonicalStore
from infrastructure.storage.raw_store import FilesystemRawStore


def test_full_data_platform_lifecycle_oepm(tmp_path: Path):
    """End-to-end integration test verifying complete data platform lifecycle without mocks.

    Tests:
    1. OepmRawSource reads real fixture data/raw/oepm_open_data_es.json
    2. FilesystemRawStore stores raw payload immutably
    3. OepmNormalizer normalizes stream of documents and field observations
    4. PatentValidator enforces domain invariants
    5. ParquetCanonicalStore stores columnar partitions and seals Merkle manifest
    6. DatasetSnapshot captures batch identity and partition hashes
    7. DuckDbQueryEngine executes zero-copy queries and accurate aggregations
    """
    raw_file = Path("data/raw/oepm_open_data_es.json")
    assert raw_file.exists(), f"OEPM raw data file must exist at {raw_file}"

    # 1. Setup isolated data platform components
    raw_store = FilesystemRawStore(base_dir=tmp_path / "raw")
    canonical_store = ParquetCanonicalStore(base_dir=tmp_path / "canonical")
    validator = PatentValidator()
    pipeline = IngestionPipeline(
        raw_store=raw_store,
        canonical_store=canonical_store,
        validator=validator,
    )

    source = OepmRawSource(file_path=raw_file, source_id="oepm_open_data", batch_id="oepm_batch_0001")
    normalizer = OepmNormalizer(extraction_version="1.0.0")
    dataset_id = "patents_es_v1"
    manifest_dir = tmp_path / "manifests"

    # 2. Ingest
    summary: IngestionSummary = pipeline.ingest_patent_source(
        source=source,
        normalizer=normalizer,
        dataset_id=dataset_id,
        manifest_output_dir=manifest_dir,
        transformation_version="1.0.0",
    )

    # =========================================================================
    # INVARIANT 1: Record Count Exactness
    # =========================================================================
    assert summary.processed_records == 16
    assert summary.error_count == 0
    assert summary.snapshot.record_count == 16
    assert len(summary.snapshot.parts) >= 1
    assert summary.snapshot.dataset_id == dataset_id
    assert summary.snapshot.schema_version == "1.0.0"
    assert summary.snapshot.transformation_version == "1.0.0"

    # Verify Parquet files exist and row counts match snapshot record count
    patents_parquet_file = tmp_path / "canonical" / dataset_id / "patents" / "part_0000.parquet"
    assert patents_parquet_file.exists(), f"Patents parquet file {patents_parquet_file} must exist"

    patents_table = pq.read_table(patents_parquet_file)
    assert patents_table.num_rows == summary.snapshot.record_count == 16

    # Verify manifest file persisted on disk
    manifest_file = manifest_dir / f"{dataset_id}_manifest.json"
    assert manifest_file.exists(), f"Manifest file {manifest_file} must exist"
    manifest_json = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert manifest_json["record_count"] == 16
    assert manifest_json["dataset_id"] == dataset_id
    assert manifest_json["manifest_sha256"] == summary.snapshot.manifest_sha256
    assert manifest_json["dataset_content_sha256"] == summary.snapshot.dataset_content_sha256

    # =========================================================================
    # INVARIANT 2: Provenance Cryptographic Reference
    # =========================================================================
    raw_payload_bytes = raw_file.read_bytes()
    expected_raw_sha256 = hashlib.sha256(raw_payload_bytes).hexdigest()

    # Raw store verification
    assert raw_store.verify_payload_integrity(expected_raw_sha256) is True
    retrieved_bytes = raw_store.get_payload(expected_raw_sha256)
    assert retrieved_bytes == raw_payload_bytes

    # Observations parquet verification
    observations_parquet_file = (
        tmp_path / "canonical" / dataset_id / "observations" / "part_0000.parquet"
    )
    assert observations_parquet_file.exists()
    obs_table = pq.read_table(observations_parquet_file)
    assert obs_table.num_rows > 0

    obs_shas = obs_table.column("raw_payload_sha256").to_pylist()
    assert len(obs_shas) == obs_table.num_rows
    # Every single field observation references the exact raw payload SHA-256
    for sha in obs_shas:
        assert sha == expected_raw_sha256

    # Verify observation entities match patents in dataset
    patent_pub_ids = set(patents_table.column("publication_id").to_pylist())
    obs_entity_ids = set(obs_table.column("entity_id").to_pylist())
    assert obs_entity_ids.issubset(patent_pub_ids)
    assert len(obs_entity_ids) == 16

    # Verify observation verification statuses are valid
    obs_statuses = set(obs_table.column("verification_status").to_pylist())
    for st in obs_statuses:
        assert st in [s.value for s in VerificationStatus]

    # =========================================================================
    # INVARIANT 3: Null Preservation in Parquet
    # =========================================================================
    # Nullable fields without values remain NULL (not empty strings or defaults)
    family_ids = patents_table.column("family_id").to_pylist()
    assert all(fid is None for fid in family_ids)

    priority_dates = patents_table.column("priority_date").to_pylist()
    assert all(pd is None for pd in priority_dates)

    # =========================================================================
    # INVARIANT 4: Zero-Copy In-Memory DuckDB Querying
    # =========================================================================
    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / "canonical" / dataset_id)

    # Vectorized search by CPC prefix "C11D"
    c11d_matches = engine.search_by_cpc_prefix("C11D")
    assert len(c11d_matches) == 3
    c11d_pub_ids = [r["publication_id"] for r in c11d_matches]
    expected_c11d_ids = ["ES-2849102-B2", "ES-2715482-B2", "ES-2634129-B1"]
    assert sorted(c11d_pub_ids) == sorted(expected_c11d_ids)

    # Vectorized search by CPC prefix "H01M" (energy / batteries)
    h01m_matches = engine.search_by_cpc_prefix("H01M")
    assert len(h01m_matches) == 3
    h01m_pub_ids = [r["publication_id"] for r in h01m_matches]
    assert sorted(h01m_pub_ids) == sorted(["ES-2812345-B1", "ES-2789123-B2", "ES-2876540-B1"])

    # Vectorized search by CPC prefix "E03C" (sanitary installations)
    e03c_matches = engine.search_by_cpc_prefix("E03C")
    assert len(e03c_matches) == 3
    e03c_pub_ids = [r["publication_id"] for r in e03c_matches]
    assert sorted(e03c_pub_ids) == sorted(["ES-2684913-B1", "ES-2901234-A1", "ES-2754890-B2"])

    # Non-existent CPC returns empty
    assert engine.search_by_cpc_prefix("Z99Z") == []

    # =========================================================================
    # INVARIANT 5: Deterministic Aggregations
    # =========================================================================
    c11d_aggs = engine.get_cluster_aggregates("C11D")
    assert c11d_aggs["patent_count"] == 3
    assert c11d_aggs["observed_citations_count"] == 3
    # Citations in C11D records: 8 (ES-2849102), 15 (ES-2715482), 11 (ES-2634129) -> sum = 34, avg = 11.333333...
    assert c11d_aggs["avg_forward_citations"] == pytest.approx(34 / 3)

    h01m_aggs = engine.get_cluster_aggregates("H01M")
    assert h01m_aggs["patent_count"] == 3
    assert h01m_aggs["observed_citations_count"] == 3
    # Citations in H01M records: 34 (ES-2812345), 27 (ES-2789123), 12 (ES-2876540) -> sum = 73, avg = 24.333333...
    assert h01m_aggs["avg_forward_citations"] == pytest.approx(73 / 3)

    empty_aggs = engine.get_cluster_aggregates("NON_EXISTENT_CPC")
    assert empty_aggs["patent_count"] == 0
    assert empty_aggs["observed_citations_count"] == 0
    assert empty_aggs["avg_forward_citations"] is None


def test_lifecycle_null_forward_citation_preservation_and_scientific_gate(tmp_path: Path):
    """Verify Scientific Gate 1 (None != 0) and strict NULL preservation across the full pipeline.

    If a patent has unobserved forward citations (None/NULL), it MUST NOT be converted
    to 0, and MUST NOT pull down cluster averages.
    """
    raw_store = FilesystemRawStore(tmp_path / "raw")
    canonical_store = ParquetCanonicalStore(tmp_path / "canonical")
    validator = PatentValidator()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store, validator=validator)

    raw_data = {
        "dataset_metadata": {
            "dataset_id": "TEST-NULL-CITATIONS",
            "dataset_title": "Null Citations Ingestion Test",
            "official_catalog_url": "https://datos.gob.es",
        },
        "publications": [
            {
                "publication_number": "ES-1000001-B2",
                "title": "Document with 10 forward citations",
                "abstract": "Abstract 1",
                "cpc_codes": ["C11D1/00"],
                "citation_count": 10,
                "publication_date": "2021-01-01",
            },
            {
                "publication_number": "ES-1000002-B2",
                "title": "Document with unobserved citations",
                "abstract": "Abstract 2",
                "cpc_codes": ["C11D1/02"],
                # citation_count omitted -> unobserved (None)
                "publication_date": "2021-02-01",
            },
        ],
    }
    raw_file = tmp_path / "test_null_citations.json"
    raw_bytes = json.dumps(raw_data).encode("utf-8")
    raw_file.write_bytes(raw_bytes)

    source = OepmRawSource(file_path=raw_file, source_id="test_null_src", batch_id="batch_null_001")
    normalizer = OepmNormalizer()
    dataset_id = "patents_null_test"

    summary = pipeline.ingest_patent_source(
        source=source,
        normalizer=normalizer,
        dataset_id=dataset_id,
        manifest_output_dir=tmp_path / "manifests",
    )

    assert summary.processed_records == 2

    # Invariant 3: NULL preservation in Parquet
    patents_parquet_file = tmp_path / "canonical" / dataset_id / "patents" / "part_0000.parquet"
    table = pq.read_table(patents_parquet_file)
    fwd_cits = table.column("forward_citation_count").to_pylist()
    assert fwd_cits == [10, None]
    assert table.column("forward_citation_count").is_null().to_pylist() == [False, True]

    # Invariant 2: Provenance verification for unobserved citation field
    obs_file = tmp_path / "canonical" / dataset_id / "observations" / "part_0000.parquet"
    obs_table = pq.read_table(obs_file)
    obs_pylist = obs_table.to_pylist()

    # ES-1000001-B2 should have a forward_citation_count observation
    es1_obs_fields = [
        o["field_name"] for o in obs_pylist if o["entity_id"] == "ES-1000001-B2"
    ]
    assert "forward_citation_count" in es1_obs_fields

    # ES-1000002-B2 should NOT have a forward_citation_count observation
    es2_obs_fields = [
        o["field_name"] for o in obs_pylist if o["entity_id"] == "ES-1000002-B2"
    ]
    assert "forward_citation_count" not in es2_obs_fields

    # Invariant 5: Scientific Gate 1 (avg should be 10.0, NOT 5.0)
    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / "canonical" / dataset_id)
    aggs = engine.get_cluster_aggregates("C11D")
    assert aggs["patent_count"] == 2
    assert aggs["observed_citations_count"] == 1
    assert aggs["avg_forward_citations"] == 10.0


def test_lifecycle_multi_batch_provenance_and_partitioning(tmp_path: Path):
    """Verify multi-batch streaming ingestion, partition part creation, and Merkle sealing."""
    raw_store = FilesystemRawStore(tmp_path / "raw")
    canonical_store = ParquetCanonicalStore(tmp_path / "canonical")
    validator = PatentValidator()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store, validator=validator)

    batch1_bytes = json.dumps({
        "publications": [
            {"publication_number": "ES-5000001-B1", "title": "Batch 1 Doc 1", "cpc_codes": ["C11D1/00"], "publication_date": "2020-01-01"},
            {"publication_number": "ES-5000002-B1", "title": "Batch 1 Doc 2", "cpc_codes": ["C11D1/02"], "publication_date": "2020-02-01"},
        ]
    }).encode("utf-8")
    batch1_sha = hashlib.sha256(batch1_bytes).hexdigest()

    batch2_bytes = json.dumps({
        "publications": [
            {"publication_number": "ES-5000003-B1", "title": "Batch 2 Doc 1", "cpc_codes": ["C11D3/00"], "publication_date": "2020-03-01"},
        ]
    }).encode("utf-8")
    batch2_sha = hashlib.sha256(batch2_bytes).hexdigest()

    class MultiBatchSource:
        def fetch_batches(self) -> Iterator[RawPayload]:
            yield RawPayload(
                source_id="multi_source",
                batch_id="batch_01",
                payload_bytes=batch1_bytes,
                metadata={"source_authority": "OEPM Test", "batch": 1},
                retrieval_timestamp=datetime(2026, 9, 2, 8, 0, 0, tzinfo=UTC),
            )
            yield RawPayload(
                source_id="multi_source",
                batch_id="batch_02",
                payload_bytes=batch2_bytes,
                metadata={"source_authority": "OEPM Test", "batch": 2},
                retrieval_timestamp=datetime(2026, 9, 2, 9, 0, 0, tzinfo=UTC),
            )

    dataset_id = "multi_batch_dataset"
    summary = pipeline.ingest_patent_source(
        source=MultiBatchSource(),
        normalizer=OepmNormalizer(),
        dataset_id=dataset_id,
        manifest_output_dir=tmp_path / "manifests",
    )

    # 3 total records across 2 batches
    assert summary.processed_records == 3
    assert summary.snapshot.record_count == 3
    assert len(summary.snapshot.source_batches) == 2
    assert summary.snapshot.source_batches[0].payload_sha256 == batch1_sha
    assert summary.snapshot.source_batches[1].payload_sha256 == batch2_sha

    # 2 partition parts for patents and 2 partition parts for observations
    assert len(summary.snapshot.parts) == 4
    part_names = [p.part_name for p in summary.snapshot.parts]
    assert "patents/part_0000.parquet" in part_names
    assert "patents/part_0001.parquet" in part_names
    assert "observations/part_0000.parquet" in part_names
    assert "observations/part_0001.parquet" in part_names

    # Check observations in part_0000 have batch1_sha and part_0001 have batch2_sha
    obs_part0 = pq.read_table(tmp_path / "canonical" / dataset_id / "observations" / "part_0000.parquet")
    assert all(sha == batch1_sha for sha in obs_part0.column("raw_payload_sha256").to_pylist())

    obs_part1 = pq.read_table(tmp_path / "canonical" / dataset_id / "observations" / "part_0001.parquet")
    assert all(sha == batch2_sha for sha in obs_part1.column("raw_payload_sha256").to_pylist())

    # DuckDbQueryEngine transparently queries across both partition parts
    engine = DuckDbQueryEngine.from_parquet_dir(tmp_path / "canonical" / dataset_id)
    all_c11d = engine.search_by_cpc_prefix("C11D")
    assert len(all_c11d) == 3
    assert {r["publication_id"] for r in all_c11d} == {
        "ES-5000001-B1",
        "ES-5000002-B1",
        "ES-5000003-B1",
    }


def test_lifecycle_validation_failure_prevents_dirty_writes(tmp_path: Path):
    """Verify that invalid raw documents are rejected by PatentValidator before canonical write."""
    raw_store = FilesystemRawStore(tmp_path / "raw")
    canonical_store = ParquetCanonicalStore(tmp_path / "canonical")
    validator = PatentValidator()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store, validator=validator)

    invalid_data = {
        "publications": [
            {
                "publication_number": "",  # Empty publication id -> invalid!
                "title": "Invalid doc",
                "publication_date": "2020-01-01",
            }
        ]
    }
    raw_file = tmp_path / "invalid_data.json"
    raw_file.write_text(json.dumps(invalid_data), encoding="utf-8")

    source = OepmRawSource(file_path=raw_file)
    normalizer = OepmNormalizer()

    with pytest.raises(ValidationError, match="publication_id cannot be empty"):
        pipeline.ingest_patent_source(
            source=source,
            normalizer=normalizer,
            dataset_id="rejected_dataset",
            manifest_output_dir=tmp_path / "manifests",
        )

    # Canonical directory for rejected_dataset must not contain valid parquet files
    rejected_dir = tmp_path / "canonical" / "rejected_dataset"
    assert not (rejected_dir / "patents").exists() or len(list((rejected_dir / "patents").glob("*.parquet"))) == 0
