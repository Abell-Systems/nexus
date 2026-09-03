"""Sprint A Acceptance Test: Full End-to-End Certified Ingestion Pipeline.

Validates:
Raw XML Payload -> FilesystemRawStore (immutable Tier 1)
                -> OepmXmlNormalizer (semantic INID extraction + kind-code filtering)
                -> PatentValidator (deduplication + calendar integrity)
                -> ParquetCanonicalStore (columnar Tier 2 partition chunks)
                -> EnhancedManifest (cryptographic digest + exact attrition counts)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq

from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer
from application.ingestion.pipeline import IngestionPipeline
from application.ingestion.validator import PatentValidator
from domain.protocols.sources import PatentSourceProtocol, RawPayload
from infrastructure.storage.parquet_store import ParquetCanonicalStore
from infrastructure.storage.raw_store import FilesystemRawStore


class MockOepmXmlSource(PatentSourceProtocol):
    def __init__(self, xml_bytes: bytes) -> None:
        self.xml_bytes = xml_bytes

    def fetch_batches(self):
        yield RawPayload(
            source_id="oepm_bopi_xml",
            batch_id="bopi_tomo2_certified_batch",
            payload_bytes=self.xml_bytes,
            metadata={
                "source_authority": "Oficina Española de Patentes y Marcas (OEPM)",
                "official_catalog_url": "https://sede.oepm.gob.es/bopiweb",
                "source_uri": "https://sede.oepm.gob.es/bopiweb/descargaPublicaciones/",
                "file_ext": "xml",
            },
            retrieval_timestamp=datetime(2021, 11, 25, 10, 0, 0, tzinfo=UTC),
        )


def test_sprint_a_full_end_to_end_ingestion_and_sealing(tmp_path: Path) -> None:
    # 1. Setup isolated three-tier storage paths
    raw_dir = tmp_path / "raw"
    canonical_dir = tmp_path / "canonical"
    manifest_dir = tmp_path / "manifests"

    raw_store = FilesystemRawStore(base_dir=raw_dir)
    canonical_store = ParquetCanonicalStore(base_dir=canonical_dir)
    validator = PatentValidator()

    pipeline = IngestionPipeline(
        raw_store=raw_store,
        canonical_store=canonical_store,
        validator=validator,
    )

    # 2. Load representative XML fixture
    fixture_path = Path("backend/test/fixtures/oepm_bopi_sample.xml")
    xml_bytes = fixture_path.read_bytes()
    source = MockOepmXmlSource(xml_bytes=xml_bytes)
    normalizer = OepmXmlNormalizer()

    # 3. Execute certified ingestion run
    dataset_id = "OEPM-ES-CORPUS-2016-2024-CANONICAL"
    summary = pipeline.ingest_patent_source(
        source=source,
        normalizer=normalizer,
        dataset_id=dataset_id,
        manifest_output_dir=manifest_dir,
        transformation_version="2.0.0",
        file_ext="xml",
    )

    # 4. Verify Tier 1: Raw Storage
    raw_files = list(raw_dir.rglob("*.xml"))
    assert len(raw_files) == 1, "Raw XML payload must be stored with .xml extension"
    stored_xml = raw_files[0].read_bytes()
    assert stored_xml == xml_bytes, "Raw payload must be preserved bit-for-bit"

    meta_files = list(raw_dir.rglob("*.meta.json"))
    assert len(meta_files) == 1, "Metadata sidecar must be generated"

    # 5. Verify Tier 2: Canonical Parquet Storage
    dataset_path = canonical_dir / dataset_id
    patents_parts = list((dataset_path / "patents").glob("*.parquet"))
    obs_parts = list((dataset_path / "observations").glob("*.parquet"))
    assert len(patents_parts) >= 1
    assert len(obs_parts) >= 1

    patents_table = pq.read_table(patents_parts[0])
    # Fixture contains 3 INCLUDED records: ES2849102B2, ES2715482T3, ES1087654U
    assert patents_table.num_rows == 3

    p_ids = patents_table.column("publication_id").to_pylist()
    assert sorted(p_ids) == ["ES1087654U", "ES2715482T3", "ES2849102B2"]

    # Verify T3 claims fallback is sealed into Parquet
    t3_idx = p_ids.index("ES2715482T3")
    t3_abstract = patents_table.column("abstract").to_pylist()[t3_idx]
    assert "Microcápsulas poliméricas biocompatibles" in t3_abstract

    # 6. Verify Enhanced Manifest
    assert summary.enhanced_manifest is not None
    manifest = summary.enhanced_manifest
    manifest_file = manifest_dir / "enhanced_manifest.json"
    assert manifest_file.exists()

    persisted_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert persisted_manifest["dataset_id"] == dataset_id
    assert persisted_manifest["counts"]["raw_payload_count"] == 1
    assert persisted_manifest["counts"]["normalized_record_count"] == 7
    assert persisted_manifest["counts"]["included_record_count"] == 3
    assert persisted_manifest["counts"]["excluded_record_count"] == 2
    assert persisted_manifest["counts"]["quarantined_record_count"] == 2
    assert persisted_manifest["counts"]["duplicate_count"] == 0

    # Verify strict attrition sum
    counts = persisted_manifest["counts"]
    assert counts["included_record_count"] + counts["excluded_record_count"] + counts["quarantined_record_count"] + counts["duplicate_count"] == counts["normalized_record_count"]

    # Verify files manifest contains parquet parts and their hashes
    assert len(manifest.files) >= 2
    for part_name, part_sha in manifest.files.items():
        part_file = dataset_path / part_name
        assert part_file.exists()
        assert len(part_sha) == 64

    # Verify cryptographic sealing
    assert len(manifest.canonical_sha256) == 64
    assert len(manifest.manifest_sha256) == 64
