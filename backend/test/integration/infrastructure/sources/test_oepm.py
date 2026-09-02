import hashlib
import json
from pathlib import Path

import pytest

from application.ingestion.normalizers.oepm_normalizer import OepmNormalizer
from domain.models.evidence import VerificationStatus
from domain.protocols.sources import PatentSourceProtocol, RawPayload
from infrastructure.sources.patent.oepm_raw_source import OepmRawSource


def test_oepm_raw_source_implements_patent_source_protocol():
    source = OepmRawSource(file_path="data/raw/oepm_open_data_es.json")
    assert isinstance(source, PatentSourceProtocol)


def test_oepm_raw_source_reads_real_fixture_bytes():
    raw_file = Path("data/raw/oepm_open_data_es.json")
    assert raw_file.exists(), f"Raw file {raw_file} must exist"

    expected_bytes = raw_file.read_bytes()
    expected_sha256 = hashlib.sha256(expected_bytes).hexdigest()

    source = OepmRawSource(file_path=raw_file)
    batches = list(source.fetch_batches())

    assert len(batches) == 1
    batch = batches[0]
    assert isinstance(batch, RawPayload)
    assert batch.payload_bytes == expected_bytes
    assert batch.payload_sha256 == expected_sha256
    assert len(batch.payload_sha256) == 64
    assert batch.source_id == "oepm_open_data"
    assert "source_authority" in batch.metadata
    assert "OEPM" in batch.metadata["source_authority"]
    assert "official_catalog_url" in batch.metadata
    assert batch.metadata["official_catalog_url"].startswith("https://datos.gob.es")
    assert batch.retrieval_timestamp is not None


def test_oepm_raw_source_and_normalizer_generates_16_documents():
    source = OepmRawSource(file_path="data/raw/oepm_open_data_es.json")
    normalizer = OepmNormalizer(extraction_version="1.0.0")

    batches = list(source.fetch_batches())
    assert len(batches) == 1
    raw_payload = batches[0]

    records = list(normalizer.normalize_stream(raw_payload))
    assert len(records) == 16

    doc_ids = set()
    for doc, obs_list in records:
        assert doc.country_code == "ES"
        assert doc.publication_id.startswith("ES-")
        assert doc.publication_id not in doc_ids
        doc_ids.add(doc.publication_id)

        assert len(doc.title) > 0
        assert len(doc.abstract) > 0
        assert doc.publication_date is not None
        assert len(doc.assignees) > 0

        # Provenance verification: 100% fine-grained FieldObservation provenance
        assert len(obs_list) > 0
        for obs in obs_list:
            assert obs.entity_id == doc.publication_id
            assert obs.raw_payload_sha256 == raw_payload.payload_sha256
            assert len(obs.raw_payload_sha256) == 64
            assert obs.extraction_version == "1.0.0"
            assert obs.verification_status == VerificationStatus.INDEPENDENTLY_VERIFIED
            assert obs.source_authority == "Patentes y Modelos de Utilidad Concedidos en España (OEPM / BOPI)"


def test_oepm_raw_source_missing_file_raises():
    source = OepmRawSource(file_path="data/raw/non_existent_file.json")
    with pytest.raises(FileNotFoundError, match="not found"):
        list(source.fetch_batches())


def test_oepm_raw_source_custom_file_path(tmp_path: Path):
    custom_json = {
        "dataset_metadata": {
            "dataset_id": "CUSTOM-OEPM-01",
            "dataset_title": "Custom OEPM Ingestion",
            "official_catalog_url": "https://custom.datos.gob.es",
        },
        "publications": [
            {
                "publication_number": "ES-3000001-B2",
                "title": "Custom Invention",
                "abstract": "Custom Abstract",
                "publication_date": "2023-01-01",
            }
        ],
    }
    custom_file = tmp_path / "custom_oepm.json"
    custom_file.write_text(json.dumps(custom_json), encoding="utf-8")

    source = OepmRawSource(file_path=custom_file)
    batches = list(source.fetch_batches())
    assert len(batches) == 1
    assert batches[0].payload_sha256 == hashlib.sha256(custom_file.read_bytes()).hexdigest()

    normalizer = OepmNormalizer()
    records = list(normalizer.normalize_stream(batches[0]))
    assert len(records) == 1
    assert records[0][0].publication_id == "ES-3000001-B2"
