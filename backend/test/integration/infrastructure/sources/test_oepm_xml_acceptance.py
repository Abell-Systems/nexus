"""Integration vertical-slice acceptance test for OEPM XML normalization."""

from datetime import UTC, datetime
from pathlib import Path

from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer
from domain.models.evidence import VerificationStatus
from domain.models.ingestion import (
    ExclusionReason,
    QuarantineReason,
    RecordDisposition,
)
from domain.protocols.sources import RawPayload


def test_oepm_xml_vertical_slice_end_to_end() -> None:
    # 1. Load real fixture matching official Tomo2.xsd namespace
    fixture_path = Path("backend/test/fixtures/oepm_bopi_sample.xml")
    assert fixture_path.exists(), "Sample BOPI XML fixture must exist"

    raw_payload = RawPayload(
        source_id="oepm_bopi_xml",
        batch_id="bopi_tomo2_sample_batch",
        payload_bytes=fixture_path.read_bytes(),
        metadata={
            "source_authority": "Oficina Española de Patentes y Marcas (OEPM / BOPI)",
            "official_catalog_url": "https://sede.oepm.gob.es/bopiweb",
            "source_uri": "https://sede.oepm.gob.es/bopiweb/descargaPublicaciones/",
            "content_type": "application/xml",
        },
        retrieval_timestamp=datetime(2021, 11, 25, 10, 0, 0, tzinfo=UTC),
    )

    # 2. Instantiate production normalizer
    normalizer = OepmXmlNormalizer(
        extraction_version="2.0.0",
        target_country="ES",
        min_publication_year=2016,
        max_publication_year=2024,
    )

    # 3. Stream all results
    results = list(normalizer.normalize_results(raw_payload))
    assert len(results) == 7

    # 4. Partition by disposition
    dispositions = {r.disposition for r in results}
    assert dispositions == {
        RecordDisposition.INCLUDED,
        RecordDisposition.EXCLUDED,
        RecordDisposition.QUARANTINED,
    }

    included = [r for r in results if r.disposition == RecordDisposition.INCLUDED]
    excluded = [r for r in results if r.disposition == RecordDisposition.EXCLUDED]
    quarantined = [r for r in results if r.disposition == RecordDisposition.QUARANTINED]

    assert len(included) == 3
    assert len(excluded) == 2
    assert len(quarantined) == 2

    # Verify each included record has fully populated canonical fields
    for res in included:
        doc = res.document
        assert doc is not None
        assert doc.publication_id.startswith("ES")
        assert doc.kind_code in {"A1", "A2", "B1", "B2", "U", "T3"}
        assert doc.title and len(doc.title) > 5
        assert doc.abstract and len(doc.abstract) > 10
        assert len(doc.assignees) > 0
        assert doc.publication_date is not None
        assert len(doc.publication_date) == 10  # YYYY-MM-DD
        assert len(res.observations) >= 5
        for obs in res.observations:
            assert obs.verification_status == VerificationStatus.SOURCE_REPORTED
            assert obs.entity_id == doc.publication_id

    # Verify excluded records preserve explicit reason and detail
    excluded_reasons = {e.excluded.reason for e in excluded if e.excluded}
    assert ExclusionReason.UNSUPPORTED_KIND_CODE in excluded_reasons
    assert ExclusionReason.OUT_OF_SCOPE_TEMPORAL_WINDOW in excluded_reasons

    # Verify quarantined records preserve error and snippet
    quarantine_reasons = {q.quarantined.reason for q in quarantined if q.quarantined}
    assert QuarantineReason.MISSING_REQUIRED_IDENTIFIER in quarantine_reasons
    assert QuarantineReason.INVALID_DATE_FORMAT in quarantine_reasons
