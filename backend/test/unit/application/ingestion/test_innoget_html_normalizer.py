"""Unit tests for InnogetHtmlNormalizer verifying extraction and evidence-backed origin classification."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from application.ingestion.normalizers.innoget_html_normalizer import InnogetHtmlNormalizer
from domain.models.demand import (
    DemandDisposition,
    SpanishOriginLevel,
)
from domain.protocols.sources import RawPayload


@pytest.fixture
def pg_us_payload() -> RawPayload:
    fixture_path = Path("data/verification/innoget/sample_call_2446.html")
    return RawPayload(
        source_id="innoget_web",
        batch_id="innoget_call_2446",
        payload_bytes=fixture_path.read_bytes(),
        metadata={"url": "https://www.innoget.com/technology-calls/2446/seeking-oral-care-solutions-for-non-bleach-whiteners"},
        retrieval_timestamp=datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def spanish_call_payload() -> RawPayload:
    fixture_path = Path("backend/test/fixtures/innoget_sample_spanish_call.html")
    return RawPayload(
        source_id="innoget_web",
        batch_id="innoget_call_2292",
        payload_bytes=fixture_path.read_bytes(),
        metadata={"url": "https://www.innoget.com/technology-calls/2292/recubrimientos-enzimaticos-biodegradables"},
        retrieval_timestamp=datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC),
    )


def test_innoget_normalizer_level_1_spanish_origin(spanish_call_payload: RawPayload) -> None:
    normalizer = InnogetHtmlNormalizer()
    results = list(normalizer.normalize_results(spanish_call_payload))
    assert len(results) == 1

    res = results[0]
    assert res.disposition == DemandDisposition.INCLUDED
    assert res.origin_level == SpanishOriginLevel.LEVEL_1_DIRECT_METADATA

    demand = res.demand
    assert demand is not None
    assert demand.demand_id == "INNOGET-2292"
    assert "Recubrimientos enzimáticos" in demand.title
    assert "tensioactivos y enzimas biodegradables" in demand.description
    assert demand.requesting_organization == "INDUSAC S.L."
    assert demand.origin_country == "Spain"
    assert demand.is_spanish_demand is True
    assert demand.deadline_date == "2024-12-15"
    assert "100,000 - 250,000 €" in (demand.budget_range or "")

    # Check evidence attached
    assert len(res.origin_assessment.evidence_observations) == 1
    assert res.origin_assessment.evidence_observations[0].field_name == "origin_country"
    assert res.origin_assessment.evidence_observations[0].observed_value_json == '"Spain"'


def test_innoget_normalizer_excludes_us_call(pg_us_payload: RawPayload) -> None:
    normalizer = InnogetHtmlNormalizer()
    results = list(normalizer.normalize_results(pg_us_payload))
    assert len(results) == 1

    res = results[0]
    assert res.disposition == DemandDisposition.EXCLUDED_NON_SPANISH
    assert res.origin_level == SpanishOriginLevel.NON_SPANISH

    demand = res.demand
    assert demand is not None
    assert demand.demand_id == "INNOGET-2446"
    assert demand.origin_country == "United States"
    assert demand.is_spanish_demand is False
    assert "The Procter & Gamble Company" in demand.requesting_organization


def test_innoget_normalizer_quarantines_invalid_utf8() -> None:
    bad_bytes = b"\xff\xfe\x00\x00\x80\x81malformed"
    payload = RawPayload(
        source_id="innoget_web",
        batch_id="corrupt_batch",
        payload_bytes=bad_bytes,
        metadata={"url": "https://www.innoget.com/technology-calls/7777/corrupt"},
        retrieval_timestamp=datetime.now(UTC),
    )

    normalizer = InnogetHtmlNormalizer()
    results = list(normalizer.normalize_results(payload))
    assert len(results) == 1
    assert results[0].disposition == DemandDisposition.QUARANTINED_MALFORMED
    assert "Unicode decoding failed" in (results[0].error_detail or "")


def test_innoget_normalizer_missing_critical_text() -> None:
    html_no_desc = b"""<!DOCTYPE html><html><head>
    <title>Solo titulo sin descripcion</title>
    <meta property="og:url" content="https://www.innoget.com/technology-calls/8888/no-desc" />
    </head><body><div class="user-meta">Posted by Repsol</div></body></html>"""

    payload = RawPayload(
        source_id="innoget_web",
        batch_id="call_no_desc",
        payload_bytes=html_no_desc,
        metadata={"url": "https://www.innoget.com/technology-calls/8888/no-desc"},
        retrieval_timestamp=datetime.now(UTC),
    )

    normalizer = InnogetHtmlNormalizer()
    results = list(normalizer.normalize_results(payload))
    assert len(results) == 1
    assert results[0].disposition == DemandDisposition.EXCLUDED_MISSING_TEXT


def test_innoget_normalize_stream_yields_only_included(
    spanish_call_payload: RawPayload, pg_us_payload: RawPayload
) -> None:
    normalizer = InnogetHtmlNormalizer()

    # Spanish call -> yields 1
    spanish_stream = list(normalizer.normalize_stream(spanish_call_payload))
    assert len(spanish_stream) == 1
    assert spanish_stream[0].demand_id == "INNOGET-2292"

    # US call -> yields 0
    us_stream = list(normalizer.normalize_stream(pg_us_payload))
    assert len(us_stream) == 0
