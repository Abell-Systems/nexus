"""Unit tests for OepmXmlNormalizer adhering to ADR 0001 and Sprint A requirements."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer
from domain.models.ingestion import (
    ExclusionReason,
    QuarantineReason,
    RecordDisposition,
)
from domain.protocols.sources import RawPayload


@pytest.fixture
def sample_payload() -> RawPayload:
    fixture_path = Path("backend/test/fixtures/oepm_bopi_sample.xml")
    xml_bytes = fixture_path.read_bytes()
    return RawPayload(
        source_id="oepm_bopi_xml",
        batch_id="bopi_20211125_batch",
        payload_bytes=xml_bytes,
        metadata={
            "source_authority": "Oficina Española de Patentes y Marcas (OEPM)",
            "official_catalog_url": "https://sede.oepm.gob.es/bopiweb",
            "source_uri": "https://sede.oepm.gob.es/bopiweb/DescargaDocumento",
        },
        retrieval_timestamp=datetime(2021, 11, 25, 10, 0, 0, tzinfo=UTC),
    )


def test_oepm_xml_normalizer_processes_all_dispositions(sample_payload: RawPayload) -> None:
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(sample_payload))

    # Fixture contains 7 distinct elements:
    # 1. B2 patent (Included)
    # 2. T3 patent with claims fallback (Included)
    # 3. U utility model with inverted tags (Included)
    # 4. T1 patent (Excluded: unsupported kind code)
    # 5. B1 patent (Excluded: year 2012 out of scope)
    # 6. Missing ID patent (Quarantined: missing required identifier)
    # 7. Invalid date patent (Quarantined: invalid date format)
    assert len(results) == 7

    included = [r for r in results if r.disposition == RecordDisposition.INCLUDED]
    excluded = [r for r in results if r.disposition == RecordDisposition.EXCLUDED]
    quarantined = [r for r in results if r.disposition == RecordDisposition.QUARANTINED]

    assert len(included) == 3
    assert len(excluded) == 2
    assert len(quarantined) == 2


def test_included_record_case_1_standard_national_b2(sample_payload: RawPayload) -> None:
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(sample_payload))
    b2_res = next(r for r in results if r.document and r.document.kind_code == "B2")

    doc = b2_res.document
    assert doc is not None
    assert doc.publication_id == "ES2849102B2"
    assert doc.country_code == "ES"
    assert doc.doc_number == "2849102"
    assert doc.kind_code == "B2"
    assert doc.application_number == "P202030431"
    assert doc.filing_date == "2020-05-12"
    assert doc.publication_date == "2021-11-25"
    assert "Formulación detergente" in doc.title
    assert "tensioactivos biodegradables" in doc.abstract
    assert doc.assignees == ["Laboratorios Bilper S.A."]
    assert doc.inventors == ["García Pérez, Elena"]
    assert "C11D1/00" in doc.classifications_cpc
    assert "C11D3/386" in doc.classifications_cpc

    # Provenance observations
    assert len(b2_res.observations) == 5
    title_obs = next(o for o in b2_res.observations if o.field_name == "title")
    assert title_obs.entity_id == "ES2849102B2"
    assert "OEPM" in title_obs.source_authority


def test_included_record_case_2_t3_claims_fallback(sample_payload: RawPayload) -> None:
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(sample_payload))
    t3_res = next(r for r in results if r.document and r.document.kind_code == "T3")

    doc = t3_res.document
    assert doc is not None
    assert doc.publication_id == "ES2715482T3"
    assert doc.country_code == "ES"
    assert doc.kind_code == "T3"
    assert doc.publication_date == "2020-03-15"
    assert "microencapsulación" in doc.title
    # Verified fallback to claims text
    assert "Microcápsulas poliméricas biocompatibles" in doc.abstract
    assert doc.assignees == ["Consejo Superior de Investigaciones Científicas (CSIC)"]


def test_included_record_case_3_order_independence(sample_payload: RawPayload) -> None:
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(sample_payload))
    u_res = next(r for r in results if r.document and r.document.kind_code == "U")

    doc = u_res.document
    assert doc is not None
    assert doc.publication_id == "ES1087654U"
    assert doc.country_code == "ES"
    assert doc.kind_code == "U"
    assert doc.publication_date == "2019-06-10"
    assert "dosificador" in doc.title.lower()
    assert doc.assignees == ["Envases Innovadores S.L."]
    assert "B65D47/00" in doc.classifications_cpc


def test_excluded_records_traceability(sample_payload: RawPayload) -> None:
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(sample_payload))
    excluded = [r for r in results if r.disposition == RecordDisposition.EXCLUDED]

    # Excluded 1: Kind T1
    t1_rec = next(r.excluded for r in excluded if r.excluded and r.excluded.kind_code == "T1")
    assert t1_rec.reason == ExclusionReason.UNSUPPORTED_KIND_CODE
    assert "T1" in t1_rec.detail

    # Excluded 2: Year 2012
    year_rec = next(r.excluded for r in excluded if r.excluded and r.excluded.kind_code == "B1")
    assert year_rec.reason == ExclusionReason.OUT_OF_SCOPE_TEMPORAL_WINDOW
    assert "2012" in year_rec.detail


def test_quarantined_records_traceability(sample_payload: RawPayload) -> None:
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(sample_payload))
    quarantined = [r for r in results if r.disposition == RecordDisposition.QUARANTINED]

    # Quarantined 1: Missing ID
    missing_id = next(q.quarantined for q in quarantined if q.quarantined and q.quarantined.reason == QuarantineReason.MISSING_REQUIRED_IDENTIFIER)
    assert missing_id.raw_identifier is None
    assert "missing" in missing_id.error_message.lower()

    # Quarantined 2: Invalid Date
    invalid_date = next(q.quarantined for q in quarantined if q.quarantined and q.quarantined.reason == QuarantineReason.INVALID_DATE_FORMAT)
    assert invalid_date.raw_identifier == "ES2899999B2"
    assert "FECHA_INVALIDA_2021" in invalid_date.error_message


def test_quarantine_on_malformed_xml() -> None:
    malformed_payload = RawPayload(
        source_id="oepm_malformed",
        batch_id="bad_xml_batch",
        payload_bytes=b"<Tomo2><PatenteNacional><unclosed_tag></Tomo2>",
        metadata={},
        retrieval_timestamp=datetime.now(UTC),
    )
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(malformed_payload))

    assert len(results) == 1
    res = results[0]
    assert res.disposition == RecordDisposition.QUARANTINED
    assert res.quarantined is not None
    assert res.quarantined.reason == QuarantineReason.MALFORMED_XML_SYNTAX


def test_backward_compatibility_normalize_stream(sample_payload: RawPayload) -> None:
    normalizer = OepmXmlNormalizer()
    stream_output = list(normalizer.normalize_stream(sample_payload))

    # normalize_stream yields only INCLUDED records
    assert len(stream_output) == 3
    for doc, obs in stream_output:
        assert doc.kind_code in {"B2", "T3", "U"}
        assert len(obs) > 0


def test_t3_explicit_fallback_hierarchy() -> None:
    # 1. Abstract present -> Abstract chosen
    xml_with_both = b"""<Tomo2 xmlns="https://sede.oepm.gob.es/bopiweb/xsd/Tomo2.xsd">
      <SolicitudesPatentesEuropeasEfectosEspanha>
        <Publicacion>
          <PublicacionId>ES2700001T3</PublicacionId>
          <p45_FechaPublicacionDeLaConcesion>15/03/2020</p45_FechaPublicacionDeLaConcesion>
          <p54_TituloInvencion>Invencion con abstract y claims</p54_TituloInvencion>
          <p57_ResumenOReivindicacion>Texto de resumen primario oficial.</p57_ResumenOReivindicacion>
          <Claims>Texto de reivindicaciones secundario.</Claims>
        </Publicacion>
      </SolicitudesPatentesEuropeasEfectosEspanha>
    </Tomo2>"""
    payload = RawPayload(
        source_id="oepm_test",
        batch_id="test_b1",
        payload_bytes=xml_with_both,
        metadata={},
        retrieval_timestamp=datetime.now(UTC),
    )
    normalizer = OepmXmlNormalizer()
    res = list(normalizer.normalize_results(payload))[0]
    assert res.document is not None
    assert res.document.abstract == "Texto de resumen primario oficial."

    # 2. Abstract absent, claims present -> Claims chosen
    xml_claims_only = b"""<Tomo2 xmlns="https://sede.oepm.gob.es/bopiweb/xsd/Tomo2.xsd">
      <SolicitudesPatentesEuropeasEfectosEspanha>
        <Publicacion>
          <PublicacionId>ES2700002T3</PublicacionId>
          <p45_FechaPublicacionDeLaConcesion>15/03/2020</p45_FechaPublicacionDeLaConcesion>
          <p54_TituloInvencion>Invencion sin abstract</p54_TituloInvencion>
          <Claims>Texto de reivindicaciones como fallback.</Claims>
        </Publicacion>
      </SolicitudesPatentesEuropeasEfectosEspanha>
    </Tomo2>"""
    payload2 = RawPayload(
        source_id="oepm_test",
        batch_id="test_b2",
        payload_bytes=xml_claims_only,
        metadata={},
        retrieval_timestamp=datetime.now(UTC),
    )
    res2 = list(normalizer.normalize_results(payload2))[0]
    assert res2.document is not None
    assert res2.document.abstract == "Texto de reivindicaciones como fallback."


def test_critical_text_completeness_rule() -> None:
    # A record with valid kind code and date, but empty title/abstract -> EXCLUDED (MISSING_CRITICAL_TEXT)
    xml_missing_text = b"""<Tomo2 xmlns="https://sede.oepm.gob.es/bopiweb/xsd/Tomo2.xsd">
      <PatenteNacional>
        <Publicacion>
          <PublicacionId>ES2800001B2</PublicacionId>
          <p45_FechaPublicacionDeLaConcesion>15/03/2020</p45_FechaPublicacionDeLaConcesion>
        </Publicacion>
      </PatenteNacional>
    </Tomo2>"""
    payload = RawPayload(
        source_id="oepm_test",
        batch_id="test_b3",
        payload_bytes=xml_missing_text,
        metadata={},
        retrieval_timestamp=datetime.now(UTC),
    )
    normalizer = OepmXmlNormalizer()
    res = list(normalizer.normalize_results(payload))[0]
    assert res.disposition == RecordDisposition.EXCLUDED
    assert res.excluded is not None
    assert res.excluded.reason == ExclusionReason.MISSING_CRITICAL_TEXT


def test_secure_xml_parsing_defense() -> None:
    # Malicious XML with DTD / external entity injection
    malicious_xml = b"""<?xml version="1.0"?>
    <!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
    <Tomo2><PatenteNacional>&xxe;</PatenteNacional></Tomo2>"""
    payload = RawPayload(
        source_id="oepm_test",
        batch_id="test_xxe",
        payload_bytes=malicious_xml,
        metadata={},
        retrieval_timestamp=datetime.now(UTC),
    )
    normalizer = OepmXmlNormalizer()
    res = list(normalizer.normalize_results(payload))[0]
    assert res.disposition == RecordDisposition.QUARANTINED
    assert res.quarantined is not None
    assert "disallowed external entities or DTD" in res.quarantined.error_message


def test_nested_publication_elements_avoid_double_counting() -> None:
    # XML where a publication contains an inner element that might match a tag name
    xml_nested = b"""<Tomo2 xmlns="https://sede.oepm.gob.es/bopiweb/xsd/Tomo2.xsd">
      <PatenteNacional>
        <PublicacionConcesion>
          <p11_NumPatenteCCP>2849102</p11_NumPatenteCCP>
          <Kind>B2</Kind>
          <p45_FechaPublicacionDeLaConcesion>25/11/2021</p45_FechaPublicacionDeLaConcesion>
          <p54_TituloInvencion>Titulo principal</p54_TituloInvencion>
          <p57_ResumenOReivindicacion>Resumen principal</p57_ResumenOReivindicacion>
          <Detalle>
            <Patente>
              <Nota>Referencia secundaria interna</Nota>
            </Patente>
          </Detalle>
        </PublicacionConcesion>
      </PatenteNacional>
    </Tomo2>"""
    payload = RawPayload(
        source_id="oepm_test",
        batch_id="test_nested",
        payload_bytes=xml_nested,
        metadata={},
        retrieval_timestamp=datetime.now(UTC),
    )
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(payload))
    # Must identify strictly 1 publication, not 2
    assert len(results) == 1
    assert results[0].document is not None
    assert results[0].document.publication_id == "ES2849102B2"


def test_normalize_stream_exact_projection_of_normalize_results(sample_payload: RawPayload) -> None:
    normalizer = OepmXmlNormalizer()
    all_results = list(normalizer.normalize_results(sample_payload))
    stream_results = list(normalizer.normalize_stream(sample_payload))

    included_from_results = [r.document for r in all_results if r.disposition == RecordDisposition.INCLUDED]
    included_from_stream = [doc for doc, _ in stream_results]

    assert len(included_from_results) == len(included_from_stream)
    for doc_r, doc_s in zip(included_from_results, included_from_stream, strict=True):
        assert doc_r == doc_s
