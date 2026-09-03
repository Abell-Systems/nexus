"""Unit tests for PatentValidator deduplication and EnhancedManifestBuilder."""

from datetime import UTC, datetime
from pathlib import Path

from application.ingestion.manifest_builder import EnhancedManifestBuilder
from application.ingestion.validator import PatentValidator
from domain.models.ingestion import (
    ExcludedRecord,
    ExclusionReason,
    NormalizationResult,
    QuarantinedRecord,
    QuarantineReason,
    RecordDisposition,
)
from domain.models.patent import PatentDocument


def test_validator_deduplication_tracks_seen_ids() -> None:
    validator = PatentValidator()
    assert validator.is_duplicate("ES2849102B2") is False
    assert validator.is_duplicate("ES2849102B2") is True
    assert validator.is_duplicate("ES1087654U") is False

    validator.reset_deduplication()
    assert validator.is_duplicate("ES2849102B2") is False


def test_validator_reclassifies_included_duplicates() -> None:
    validator = PatentValidator()
    doc = PatentDocument(
        publication_id="ES2849102B2",
        country_code="ES",
        doc_number="2849102",
        kind_code="B2",
        title="Valid Title",
        abstract="Valid Abstract",
        publication_date="2021-11-25",
    )
    res1 = NormalizationResult(disposition=RecordDisposition.INCLUDED, document=doc)
    validated1 = validator.validate_normalization_result(res1)
    assert validated1.disposition == RecordDisposition.INCLUDED

    res2 = NormalizationResult(disposition=RecordDisposition.INCLUDED, document=doc)
    validated2 = validator.validate_normalization_result(res2)
    assert validated2.disposition == RecordDisposition.DUPLICATE


def test_manifest_builder_records_attrition_counts(tmp_path: Path) -> None:
    builder = EnhancedManifestBuilder(
        dataset_id="OEPM-TEST-DATASET",
        dataset_version="1.0.0",
        source_release_id="BOPI-2021-TEST",
    )

    builder.record_raw_payload()
    builder.record_raw_payload()

    # 1. Included B2
    doc_b2 = PatentDocument(
        publication_id="ES2849102B2",
        country_code="ES",
        doc_number="2849102",
        kind_code="B2",
        title="Title B2",
        abstract="Abstract B2",
        publication_date="2021-11-25",
    )
    builder.record_normalization_result(
        NormalizationResult(disposition=RecordDisposition.INCLUDED, document=doc_b2)
    )

    # 2. Included T3
    doc_t3 = PatentDocument(
        publication_id="ES2715482T3",
        country_code="ES",
        doc_number="2715482",
        kind_code="T3",
        title="Title T3",
        abstract="Abstract T3",
        publication_date="2020-03-15",
    )
    builder.record_normalization_result(
        NormalizationResult(disposition=RecordDisposition.INCLUDED, document=doc_t3)
    )

    # 3. Excluded: Unsupported Kind T1
    builder.record_normalization_result(
        NormalizationResult(
            disposition=RecordDisposition.EXCLUDED,
            excluded=ExcludedRecord(
                publication_id="ES2999001T1",
                country_code="ES",
                kind_code="T1",
                reason=ExclusionReason.UNSUPPORTED_KIND_CODE,
                detail="Kind code T1 outside universe",
                source_uri="https://sede.oepm.gob.es",
            ),
        )
    )

    # 4. Quarantined: Missing ID
    builder.record_normalization_result(
        NormalizationResult(
            disposition=RecordDisposition.QUARANTINED,
            quarantined=QuarantinedRecord(
                raw_identifier=None,
                reason=QuarantineReason.MISSING_REQUIRED_IDENTIFIER,
                error_message="Missing ID tag",
                raw_snippet="<Publicacion/>",
                detected_at=datetime.now(UTC),
                source_uri="https://sede.oepm.gob.es",
            ),
        )
    )

    # 5. Duplicate
    builder.record_normalization_result(
        NormalizationResult(disposition=RecordDisposition.DUPLICATE, document=doc_b2)
    )

    files = {
        "patents.parquet": "c158bdaa2426e71c4aa42db5c1885885dc36607bf6cf5431135bdfa70eee3a2e",
        "provenance.parquet": "7d7313154aad60159459c22661b188b975e49452e59e138a566a7b314fb7ed69",
    }

    manifest, manifest_file = builder.persist_manifest(tmp_path, files)

    assert manifest_file.exists()
    assert manifest.counts.raw_payload_count == 2
    assert manifest.counts.normalized_record_count == 5
    assert manifest.counts.included_record_count == 2
    assert manifest.counts.excluded_record_count == 1
    assert manifest.counts.quarantined_record_count == 1
    assert manifest.counts.duplicate_count == 1

    assert manifest.kind_code_distribution == {"B2": 1, "T3": 1}
    assert manifest.exclusion_reasons == {"EXCLUDED_UNSUPPORTED_KIND_CODE": 1}
    assert manifest.quarantine_reasons == {"QUARANTINED_MISSING_REQUIRED_IDENTIFIER": 1}
    assert len(manifest.manifest_sha256) == 64
    assert len(manifest.canonical_sha256) == 64


def test_manifest_content_identity_is_reproducible_across_different_timestamps() -> None:
    # Set up builder A with timestamp 1
    builder_a = EnhancedManifestBuilder(
        dataset_id="OEPM-TEST-REPRODUCIBLE",
        dataset_version="1.0.0",
        source_release_id="BOPI-2021-TEST",
    )
    # Set up builder B with timestamp 2
    builder_b = EnhancedManifestBuilder(
        dataset_id="OEPM-TEST-REPRODUCIBLE",
        dataset_version="1.0.0",
        source_release_id="BOPI-2021-TEST",
    )

    doc = PatentDocument(
        publication_id="ES2849102B2",
        country_code="ES",
        doc_number="2849102",
        kind_code="B2",
        title="Title B2",
        abstract="Abstract B2",
        publication_date="2021-11-25",
    )
    res = NormalizationResult(disposition=RecordDisposition.INCLUDED, document=doc)

    builder_a.record_raw_payload()
    builder_a.record_normalization_result(res)

    builder_b.record_raw_payload()
    builder_b.record_normalization_result(res)

    files = {"patents.parquet": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"}

    # Build manifest A with time 2021
    manifest_a = builder_a.build_manifest(
        files_and_hashes=files,
        acquisition_started_at=datetime(2021, 1, 1, 10, 0, 0, tzinfo=UTC),
        acquisition_finished_at=datetime(2021, 1, 1, 11, 0, 0, tzinfo=UTC),
        git_commit="commit_aaa",
    )

    # Build manifest B with completely different timestamps and commit
    manifest_b = builder_b.build_manifest(
        files_and_hashes=files,
        acquisition_started_at=datetime(2024, 8, 15, 15, 30, 0, tzinfo=UTC),
        acquisition_finished_at=datetime(2024, 8, 15, 16, 45, 0, tzinfo=UTC),
        git_commit="commit_bbb",
    )

    # Invariant: Scientific content identity hash MUST BE BIT-EXACT IDENTICAL
    assert manifest_a.content_identity_sha256 == manifest_b.content_identity_sha256
    assert len(manifest_a.content_identity_sha256) == 64

    # Execution provenance will differ
    assert manifest_a.manifest_sha256 != manifest_b.manifest_sha256
    assert manifest_a.execution_provenance.environment.git_commit != manifest_b.execution_provenance.environment.git_commit
