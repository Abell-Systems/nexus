"""Acceptance test for Sprint A Block 2: PatentValidator + EnhancedManifest pipeline integration."""

from datetime import UTC, datetime
from pathlib import Path

from application.ingestion.manifest_builder import EnhancedManifestBuilder
from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer
from application.ingestion.validator import PatentValidator
from domain.models.ingestion import RecordDisposition
from domain.protocols.sources import RawPayload


def test_validator_and_enhanced_manifest_end_to_end_acceptance(tmp_path: Path) -> None:
    # 1. Load official fixture
    fixture_path = Path("backend/test/fixtures/oepm_bopi_sample.xml")
    xml_bytes = fixture_path.read_bytes()

    payload = RawPayload(
        source_id="oepm_bopi_xml",
        batch_id="bopi_20211125_batch",
        payload_bytes=xml_bytes,
        metadata={
            "source_authority": "Oficina Española de Patentes y Marcas (OEPM)",
            "official_catalog_url": "https://sede.oepm.gob.es/bopiweb",
            "source_uri": "https://sede.oepm.gob.es/bopiweb/descargaPublicaciones/",
        },
        retrieval_timestamp=datetime(2021, 11, 25, 10, 0, 0, tzinfo=UTC),
    )

    normalizer = OepmXmlNormalizer()
    validator = PatentValidator()
    manifest_builder = EnhancedManifestBuilder(
        dataset_id="OEPM-ES-CORPUS-2016-2024-TEST",
        source_release_id="BOPI-2021-11-25",
    )

    manifest_builder.record_raw_payload()

    # Process all normalization results through validator
    validated_results = []
    for raw_result in normalizer.normalize_results(payload):
        val_result = validator.validate_normalization_result(raw_result)
        validated_results.append(val_result)
        manifest_builder.record_normalization_result(val_result)

    # Inject duplicate publication to verify validator deduplication in live flow
    duplicate_raw_result = list(normalizer.normalize_results(payload))[0]  # B2
    dup_val_result = validator.validate_normalization_result(duplicate_raw_result)
    assert dup_val_result.disposition == RecordDisposition.DUPLICATE
    manifest_builder.record_normalization_result(dup_val_result)

    # Build and persist manifest
    dummy_files = {
        "patents.parquet": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "provenance.parquet": "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
    }
    manifest, manifest_file = manifest_builder.persist_manifest(tmp_path, dummy_files)

    # Verify manifest invariants
    assert manifest_file.exists()
    assert manifest.dataset_id == "OEPM-ES-CORPUS-2016-2024-TEST"
    assert manifest.counts.raw_payload_count == 1
    assert manifest.counts.normalized_record_count == 8  # 7 original + 1 duplicate
    assert manifest.counts.included_record_count == 3
    assert manifest.counts.excluded_record_count == 2
    assert manifest.counts.quarantined_record_count == 2
    assert manifest.counts.duplicate_count == 1

    # Attrition sum invariant: included + excluded + quarantined + duplicate == normalized_record_count
    c = manifest.counts
    assert c.included_record_count + c.excluded_record_count + c.quarantined_record_count + c.duplicate_count == c.normalized_record_count

    # Check kind code distribution strictly contains included codes
    assert manifest.kind_code_distribution == {"B2": 1, "T3": 1, "U": 1}
    assert len(manifest.manifest_sha256) == 64
