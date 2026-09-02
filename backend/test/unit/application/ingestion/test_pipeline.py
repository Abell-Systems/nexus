import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from application.ingestion.normalizers.oepm_normalizer import OepmNormalizer
from application.ingestion.pipeline import IngestionPipeline, IngestionSummary
from application.ingestion.validator import PatentValidator, ValidationError
from domain.models.evidence import FieldObservation, VerificationStatus
from domain.models.patent import PatentDocument
from domain.protocols.sources import RawPayload


class MockRawStore:
    def __init__(self):
        self.stored = []

    def store_payload(self, source_id, payload_bytes, metadata, file_ext="json"):
        self.stored.append((source_id, payload_bytes, metadata, file_ext))
        return Path(f"/mock/{source_id}/payload.raw.{file_ext}"), "a" * 64

    def get_payload(self, sha256_digest: str) -> bytes:
        return b""

    def verify_payload_integrity(self, sha256_digest: str) -> bool:
        return True


class MockCanonicalStore:
    def __init__(self):
        self.written_batches = []
        self.sealed = False

    def write_batch(self, dataset_id, documents, observations):
        self.written_batches.append((dataset_id, documents, observations))

    def seal_dataset(self, dataset_id):
        self.sealed = True
        total_docs = sum(len(docs) for _, docs, _ in self.written_batches)
        return [("patents/part-0000.parquet", total_docs, "b" * 64)], "c" * 64


class MockSource:
    def __init__(self, payloads=None):
        self.payloads = payloads or [
            RawPayload(
                source_id="test_src",
                batch_id="batch_01",
                payload_bytes=b'{"items": []}',
                metadata={"source_uri": "https://test.api"},
                retrieval_timestamp=datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC),
            )
        ]

    def fetch_batches(self):
        yield from self.payloads


class MockNormalizer:
    def normalize_stream(self, raw_payload):
        doc = PatentDocument(
            publication_id="ES-MOCK-001-B2",
            country_code="ES",
            doc_number="MOCK-001",
            kind_code="B2",
            title="Mock Patent Title",
            abstract="Mock Abstract Text",
            publication_date="2021-11-25",
        )
        obs = FieldObservation(
            entity_id="ES-MOCK-001-B2",
            field_name="title",
            observed_value_json='"Mock Patent Title"',
            value_type="str",
            source_authority="Mock Authority",
            source_uri="https://test.api",
            retrieval_timestamp=raw_payload.retrieval_timestamp,
            raw_payload_sha256=raw_payload.payload_sha256,
            extraction_version="1.0.0",
            verification_status=VerificationStatus.SOURCE_REPORTED,
        )
        yield doc, [obs]


def test_streaming_ingestion_pipeline_orchestration(tmp_path: Path):
    raw_store = MockRawStore()
    canonical_store = MockCanonicalStore()
    validator = PatentValidator()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store, validator=validator)

    manifest_dir = tmp_path / "manifests"

    summary = pipeline.ingest_patent_source(
        source=MockSource(),
        normalizer=MockNormalizer(),
        dataset_id="test_dataset_v1",
        manifest_output_dir=manifest_dir,
        transformation_version="1.0.0",
    )

    assert isinstance(summary, IngestionSummary)
    assert summary.processed_records == 1
    assert summary.error_count == 0
    assert summary.snapshot.dataset_id == "test_dataset_v1"
    assert summary.snapshot.record_count == 1
    assert summary.snapshot.dataset_content_sha256 == "c" * 64
    assert len(summary.snapshot.parts) == 1
    assert summary.snapshot.parts[0].part_name == "patents/part-0000.parquet"
    assert len(summary.snapshot.source_batches) == 1
    assert summary.snapshot.source_batches[0].batch_id == "batch_01"
    assert summary.snapshot.source_batches[0].source_id == "test_src"

    assert len(raw_store.stored) == 1
    assert len(canonical_store.written_batches) == 1
    assert canonical_store.sealed is True

    # Check manifest file was created on disk
    manifest_file = manifest_dir / "test_dataset_v1_manifest.json"
    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text())
    assert manifest_data["dataset_id"] == "test_dataset_v1"
    assert manifest_data["record_count"] == 1
    assert manifest_data["manifest_sha256"] == summary.snapshot.manifest_sha256
    assert len(manifest_data["manifest_sha256"]) == 64


def test_pipeline_multi_batch_orchestration(tmp_path: Path):
    raw_store = MockRawStore()
    canonical_store = MockCanonicalStore()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store)

    payload1 = RawPayload(
        source_id="src_multi",
        batch_id="batch_01",
        payload_bytes=json.dumps({"publications": [{"publication_id": "ES-001-A1", "title": "T1", "abstract": "A1"}]}).encode("utf-8"),
        retrieval_timestamp=datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC),
    )
    payload2 = RawPayload(
        source_id="src_multi",
        batch_id="batch_02",
        payload_bytes=json.dumps({"publications": [{"publication_id": "ES-002-A1", "title": "T2", "abstract": "A2"}]}).encode("utf-8"),
        retrieval_timestamp=datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC),
    )

    source = MockSource(payloads=[payload1, payload2])
    manifest_dir = tmp_path / "manifests"

    summary = pipeline.ingest_patent_source(
        source=source,
        normalizer=OepmNormalizer(),
        dataset_id="multi_batch_ds",
        manifest_output_dir=manifest_dir,
    )

    assert summary.processed_records == 2
    assert len(summary.snapshot.source_batches) == 2
    assert len(raw_store.stored) == 2
    assert len(canonical_store.written_batches) == 2


def test_oepm_normalizer_stream_parsing_and_provenance():
    normalizer = OepmNormalizer(extraction_version="1.0.0")

    raw_json = {
        "dataset_metadata": {
            "dataset_id": "OEPM-TEST-V1",
            "dataset_title": "Patentes OEPM Test",
            "official_catalog_url": "https://datos.gob.es/catalogo/oepm",
        },
        "publications": [
            {
                "publication_number": "ES-2849102-B2",
                "application_number": "P202030431",
                "title": "Formulación detergente enzimática",
                "abstract": "Composición detergente acuosa concentrada.",
                "assignee": "Laboratorios Bilper S.A. / CSIC",
                "inventors": ["García Pérez, Elena", "Martínez Soto, Iñigo"],
                "filing_date": "2020-05-12",
                "publication_date": "2021-11-25",
                "cpc_codes": ["C11D1/00", "C11D3/386"],
                "citation_count": 8,
                "backward_citation_count": 14,
                "invenes_url": "https://consultas2.oepm.es/InvenesWeb/detalle?ref=P202030431",
                "verification_status": "verified_invenes_bopi_record",
            },
            {
                "publication_number": "ES-2999999-A1",
                "title": "Dispositivo solar",
                "abstract": "Panel con refrigeración líquida.",
                "assignees": ["Solar Corp S.L."],
                "inventor": "Inventor Solitario",
                "filing_date": "2021-01-15",
                "publication_date": "2022-06-30",
                "cpc_codes": ["H02S20/00"],
                "citation_count": None,
                "backward_citation_count": None,
            },
        ],
    }

    payload_bytes = json.dumps(raw_json).encode("utf-8")
    raw_payload = RawPayload(
        source_id="oepm_open_data",
        batch_id="batch_oepm_01",
        payload_bytes=payload_bytes,
        metadata={"source_uri": "https://datos.gob.es/catalogo/oepm"},
        retrieval_timestamp=datetime(2026, 9, 2, 11, 0, 0, tzinfo=UTC),
    )

    results = list(normalizer.normalize_stream(raw_payload))
    assert len(results) == 2

    # Doc 1 checks
    doc1, obs1 = results[0]
    assert doc1.publication_id == "ES-2849102-B2"
    assert doc1.country_code == "ES"
    assert doc1.doc_number == "2849102"
    assert doc1.kind_code == "B2"
    assert doc1.application_number == "P202030431"
    assert doc1.title == "Formulación detergente enzimática"
    assert doc1.assignees == ["Laboratorios Bilper S.A.", "CSIC"]
    assert doc1.inventors == ["García Pérez, Elena", "Martínez Soto, Iñigo"]
    assert doc1.filing_date == "2020-05-12"
    assert doc1.publication_date == "2021-11-25"
    assert doc1.classifications_cpc == ["C11D1/00", "C11D3/386"]
    assert doc1.forward_citation_count == 8
    assert doc1.backward_citation_count == 14

    # Observations for Doc 1
    assert len(obs1) > 0
    obs_fields = {o.field_name: o for o in obs1}
    assert "title" in obs_fields
    assert "abstract" in obs_fields
    assert "publication_date" in obs_fields
    assert "forward_citation_count" in obs_fields
    assert "backward_citation_count" in obs_fields

    for obs in obs1:
        assert obs.entity_id == "ES-2849102-B2"
        assert obs.raw_payload_sha256 == raw_payload.payload_sha256
        assert len(obs.raw_payload_sha256) == 64
        assert obs.extraction_version == "1.0.0"
        assert obs.verification_status == VerificationStatus.INDEPENDENTLY_VERIFIED
        assert obs.source_authority == "Patentes OEPM Test"

    # Doc 2 checks (Strict null preservation)
    doc2, obs2 = results[1]
    assert doc2.publication_id == "ES-2999999-A1"
    assert doc2.forward_citation_count is None
    assert doc2.backward_citation_count is None
    assert doc2.assignees == ["Solar Corp S.L."]
    assert doc2.inventors == ["Inventor Solitario"]

    obs2_fields = {o.field_name: o for o in obs2}
    assert "forward_citation_count" not in obs2_fields
    assert "backward_citation_count" not in obs2_fields


def test_oepm_normalizer_handles_plain_list():
    normalizer = OepmNormalizer()
    raw_list = [
        {
            "publication_id": "ES-1234567-B1",
            "country_code": "ES",
            "doc_number": "1234567",
            "kind_code": "B1",
            "title": "Test Title",
            "abstract": "Test Abstract",
        }
    ]
    payload_bytes = json.dumps(raw_list).encode("utf-8")
    raw_payload = RawPayload(
        source_id="oepm_plain",
        batch_id="batch_02",
        payload_bytes=payload_bytes,
        retrieval_timestamp=datetime(2026, 9, 2, tzinfo=UTC),
    )

    results = list(normalizer.normalize_stream(raw_payload))
    assert len(results) == 1
    doc, obs = results[0]
    assert doc.publication_id == "ES-1234567-B1"
    assert doc.forward_citation_count is None
    assert doc.backward_citation_count is None


def test_oepm_normalizer_verification_status_variants():
    normalizer = OepmNormalizer()
    raw_dict = {
        "publications": [
            {
                "publication_id": "ES-001-A1",
                "title": "Derived status doc",
                "abstract": "Derived",
                "verification_status": "derived",
            },
            {
                "publication_id": "ES-002-A1",
                "title": "Unavailable status doc",
                "abstract": "Unavailable",
                "verification_status": "unavailable",
            },
        ]
    }
    payload_bytes = json.dumps(raw_dict).encode("utf-8")
    raw_payload = RawPayload(
        source_id="oepm_status",
        batch_id="batch_03",
        payload_bytes=payload_bytes,
        retrieval_timestamp=datetime(2026, 9, 2, tzinfo=UTC),
    )

    results = list(normalizer.normalize_stream(raw_payload))
    assert len(results) == 2
    doc1, obs1 = results[0]
    assert all(o.verification_status == VerificationStatus.DERIVED for o in obs1)

    doc2, obs2 = results[1]
    assert all(o.verification_status == VerificationStatus.UNAVAILABLE for o in obs2)


def test_pipeline_integration_with_real_oepm_normalizer(tmp_path: Path):
    raw_store = MockRawStore()
    canonical_store = MockCanonicalStore()
    validator = PatentValidator()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store, validator=validator)

    raw_json = {
        "dataset_metadata": {
            "dataset_id": "OEPM-SAMPLE",
            "dataset_title": "OEPM Sample Ingestion",
        },
        "publications": [
            {
                "publication_number": "ES-1111111-B2",
                "title": "Title 1",
                "abstract": "Abstract 1",
                "publication_date": "2021-01-01",
            },
            {
                "publication_number": "ES-2222222-B2",
                "title": "Title 2",
                "abstract": "Abstract 2",
                "publication_date": "2022-02-02",
            },
        ],
    }
    payload_bytes = json.dumps(raw_json).encode("utf-8")
    source = MockSource(
        payloads=[
            RawPayload(
                source_id="oepm_sample",
                batch_id="batch_s1",
                payload_bytes=payload_bytes,
                retrieval_timestamp=datetime(2026, 9, 2, tzinfo=UTC),
            )
        ]
    )

    summary = pipeline.ingest_patent_source(
        source=source,
        normalizer=OepmNormalizer(),
        dataset_id="sample_dataset",
        manifest_output_dir=tmp_path / "manifests",
    )

    assert summary.processed_records == 2
    assert summary.error_count == 0
    assert len(canonical_store.written_batches) == 1
    docs, obs = canonical_store.written_batches[0][1], canonical_store.written_batches[0][2]
    assert len(docs) == 2
    assert len(obs) > 0


def test_pipeline_rejects_invalid_batch_document(tmp_path: Path):
    raw_store = MockRawStore()
    canonical_store = MockCanonicalStore()
    validator = PatentValidator()
    pipeline = IngestionPipeline(raw_store=raw_store, canonical_store=canonical_store, validator=validator)

    # Missing publication number / publication_id
    raw_json = {
        "publications": [
            {
                "publication_number": "",
                "title": "Invalid Patent",
                "abstract": "No ID",
            }
        ]
    }
    payload_bytes = json.dumps(raw_json).encode("utf-8")
    source = MockSource(
        payloads=[
            RawPayload(
                source_id="invalid_src",
                batch_id="batch_inv",
                payload_bytes=payload_bytes,
                retrieval_timestamp=datetime(2026, 9, 2, tzinfo=UTC),
            )
        ]
    )

    with pytest.raises(ValidationError, match="publication_id cannot be empty"):
        pipeline.ingest_patent_source(
            source=source,
            normalizer=OepmNormalizer(),
            dataset_id="invalid_dataset",
            manifest_output_dir=tmp_path / "manifests",
        )
