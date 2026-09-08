"""Contract test: OepmXmlNormalizer generalizes to multi-jurisdiction EPO OPS XML
(EP/US/JP/CN/KR/WO), restricted to grants-only. ADR 0020 §6: this is verified here,
not assumed."""

from pathlib import Path

from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer
from domain.models.ingestion import ExclusionReason, RecordDisposition
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient

FIXTURE = Path("backend/test/fixtures/epo_ops_multi_jurisdiction_sample.xml")


def test_normalizer_extracts_grants_across_all_target_jurisdictions():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    normalizer = OepmXmlNormalizer(allowed_kind_codes=frozenset({"B1", "B2"}))

    results = []
    for payload in client.fetch_batches():
        results.extend(normalizer.normalize_results(payload))

    included = [r for r in results if r.disposition == RecordDisposition.INCLUDED]
    excluded = [r for r in results if r.disposition == RecordDisposition.EXCLUDED]

    included_countries = {r.document.country_code for r in included}
    assert included_countries == {"EP", "US", "JP", "KR"}, (
        f"Expected EP/US/JP/KR grants included, got {included_countries}. "
        "If this fails, OepmXmlNormalizer does NOT generalize cleanly to non-ES XML -- "
        "per ADR 0020 §6/§7 item 5, do not assume it does; a jurisdiction-specific "
        "adapter is required scope, not this plan's Task 5."
    )

    # CN fixture uses kind="B" (not B1/B2) -- exercises that non-normative single-letter
    # grant codes from some offices are NOT silently accepted; this is expected to
    # exclude, and documents the boundary rather than hiding it.
    excluded_by_id = {r.excluded.publication_id: r.excluded for r in excluded}
    assert "CN112233445B" in excluded_by_id
    assert (
        excluded_by_id["CN112233445B"].reason == ExclusionReason.UNSUPPORTED_KIND_CODE
    )
    assert "WO2021123456A1" in excluded_by_id  # pending application, correctly excluded
    assert (
        excluded_by_id["WO2021123456A1"].reason
        == ExclusionReason.UNSUPPORTED_KIND_CODE
    )

    us_doc = next(r.document for r in included if r.document.country_code == "US")
    assert us_doc.title == "Battery management circuit"
    assert us_doc.classifications_cpc == ["H01M10/48"]
    assert us_doc.publication_date == "2020-06-01"
