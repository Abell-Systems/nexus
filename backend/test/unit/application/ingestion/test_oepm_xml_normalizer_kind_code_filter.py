"""Unit test: allowed_kind_codes lets callers restrict to grants-only without changing
the default (OEPM/ES) behavior (ADR 0020 §2 grants-only requirement)."""

from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer
from domain.models.ingestion import ExclusionReason, RecordDisposition
from domain.protocols.sources import RawPayload

APPLICATION_XML = b"""<?xml version="1.0"?>
<exchange-document country="US" doc-number="1234567" kind="A1">
  <invention-title>A gadget</invention-title>
  <abstract>A gadget that gadgets.</abstract>
</exchange-document>"""

GRANT_XML = b"""<?xml version="1.0"?>
<exchange-document country="US" doc-number="1234567" kind="B2">
  <invention-title>A gadget</invention-title>
  <abstract>A gadget that gadgets.</abstract>
</exchange-document>"""


def _payload(xml_bytes: bytes) -> RawPayload:
    return RawPayload(source_id="epo_ops", batch_id="b1", payload_bytes=xml_bytes, metadata={})


def test_default_allowed_kind_codes_unchanged_includes_applications():
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(_payload(APPLICATION_XML)))
    assert results[0].disposition == RecordDisposition.INCLUDED


def test_grants_only_excludes_applications():
    normalizer = OepmXmlNormalizer(allowed_kind_codes=frozenset({"B1", "B2"}))
    results = list(normalizer.normalize_results(_payload(APPLICATION_XML)))
    assert results[0].disposition == RecordDisposition.EXCLUDED
    assert results[0].excluded.reason == ExclusionReason.UNSUPPORTED_KIND_CODE


def test_grants_only_includes_grants():
    normalizer = OepmXmlNormalizer(allowed_kind_codes=frozenset({"B1", "B2"}))
    results = list(normalizer.normalize_results(_payload(GRANT_XML)))
    assert results[0].disposition == RecordDisposition.INCLUDED


# Field values below are real, fetched from the public INVENES search
# (https://consultas2.oepm.es/InvenesWeb/detalle?referencia=E14275070, Spanish
# original via Accept-Language: es-ES) on 2026-09-14, reshaped into Tomo2 XML tag
# structure (this record's raw BOPI Tomo II XML itself requires OEPM bulk-download
# registration, not obtained in this session -- see ADR 0035 SS4/SS11). Confirms the
# default normalizer now excludes a genuine EP-ES (T3) record, per ADR 0035 SS3.
REAL_EP_ES_T3_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tomo2 xmlns="https://sede.oepm.gob.es/bopiweb/xsd/Tomo2.xsd">
  <SolicitudesPatentesEuropeasEfectosEspanha>
    <Publicacion>
      <PublicacionId>ES2878119T3</PublicacionId>
      <p21_NumSolicitud>E14275070</p21_NumSolicitud>
      <p22_FechaSolicitud>14/03/2014</p22_FechaSolicitud>
      <p45_FechaPublicacionDeLaConcesion>18/11/2021</p45_FechaPublicacionDeLaConcesion>
      <p54_TituloInvencion>Sistema y procedimiento de control de un sistema de bomba mediante entradas digitales integradas</p54_TituloInvencion>
      <p73_NombreTitular>Regal Beloit America, Inc.</p73_NombreTitular>
      <p51_ClasificacionInternacionalPatentes>F04B49/06</p51_ClasificacionInternacionalPatentes>
    </Publicacion>
  </SolicitudesPatentesEuropeasEfectosEspanha>
</Tomo2>"""


def test_default_kind_codes_exclude_real_ep_es_t3_record():
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(_payload(REAL_EP_ES_T3_XML)))
    assert results[0].disposition == RecordDisposition.EXCLUDED
    assert results[0].excluded.reason == ExclusionReason.UNSUPPORTED_KIND_CODE
    assert results[0].excluded.publication_id == "ES2878119T3"
