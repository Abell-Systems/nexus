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
