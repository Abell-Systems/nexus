"""Unit tests for InnogetHtmlNormalizer verifying extraction and evidence-backed origin classification."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from application.ingestion.normalizers.innoget_html_normalizer import InnogetHtmlNormalizer
from application.ingestion.origin_resolver import DefaultOriginResolver
from domain.models.demand import (
    DemandDisposition,
    SpanishOriginLevel,
)
from domain.models.origin_policy import OriginPolicyConfig
from domain.protocols.sources import RawPayload

# Anchored to repo root so this resolves regardless of pytest's invocation cwd
# (e.g. `pytest` from repo root vs `cd backend && pytest`).
CANONICAL_POLICY_PATH = (
    Path(__file__).resolve().parents[5] / "config" / "policies" / "data" / "jurisdiction_policy.json"
)
_FIXTURES_DIR = Path(__file__).resolve().parents[5] / "backend" / "test" / "fixtures"


@pytest.fixture
def origin_resolver() -> DefaultOriginResolver:
    policy = OriginPolicyConfig.load_from_json(CANONICAL_POLICY_PATH)
    return DefaultOriginResolver(policy=policy)


@pytest.fixture
def pg_us_payload() -> RawPayload:
    # Synthetic fixture: invented content, see the comment inside the file
    fixture_path = _FIXTURES_DIR / "innoget_synthetic_us_call.html"
    return RawPayload(
        source_id="innoget_web",
        batch_id="innoget_call_900001",
        payload_bytes=fixture_path.read_bytes(),
        metadata={"url": "https://www.innoget.com/technology-calls/900001/synthetic-example-household-products"},
        retrieval_timestamp=datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def spanish_call_payload() -> RawPayload:
    fixture_path = _FIXTURES_DIR / "innoget_synthetic_spanish_call.html"
    return RawPayload(
        source_id="innoget_web",
        batch_id="innoget_call_900002",
        payload_bytes=fixture_path.read_bytes(),
        metadata={"url": "https://www.innoget.com/technology-calls/900002/recubrimientos-sinteticos-de-ejemplo"},
        retrieval_timestamp=datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC),
    )


def test_innoget_normalizer_level_1_spanish_origin(
    origin_resolver: DefaultOriginResolver, spanish_call_payload: RawPayload
) -> None:
    normalizer = InnogetHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(spanish_call_payload))
    assert len(results) == 1

    res = results[0]
    assert res.disposition == DemandDisposition.INCLUDED
    assert res.origin_level == SpanishOriginLevel.LEVEL_1_DIRECT_METADATA

    demand = res.demand
    assert demand is not None
    assert demand.demand_id == "INNOGET-900002"
    assert "Recubrimientos sintéticos" in demand.title
    assert "formulaciones biodegradables" in demand.description
    assert demand.requesting_organization == "Empresa Ejemplo S.L."
    assert demand.origin_country == "Spain"
    assert demand.is_spanish_demand is True
    assert demand.deadline_date == "2030-01-01"
    assert "10,000 - 20,000 €" in (demand.budget_range or "")

    # Check evidence attached
    assert len(res.origin_assessment.evidence_observations) == 1
    assert res.origin_assessment.evidence_observations[0].field_name == "origin_country"
    assert res.origin_assessment.evidence_observations[0].observed_value_json == '"Spain"'


def test_innoget_normalizer_excludes_us_call(
    origin_resolver: DefaultOriginResolver, pg_us_payload: RawPayload
) -> None:
    normalizer = InnogetHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(pg_us_payload))
    assert len(results) == 1

    res = results[0]
    assert res.disposition == DemandDisposition.EXCLUDED_NON_SPANISH
    assert res.origin_level == SpanishOriginLevel.NON_SPANISH

    demand = res.demand
    assert demand is not None
    assert demand.demand_id == "INNOGET-900001"
    assert demand.origin_country == "United States"
    assert demand.is_spanish_demand is False
    assert demand.requesting_organization == "Example Household Goods Inc."


def test_innoget_normalizer_quarantines_invalid_utf8(origin_resolver: DefaultOriginResolver) -> None:
    bad_bytes = b"\xff\xfe\x00\x00\x80\x81malformed"
    payload = RawPayload(
        source_id="innoget_web",
        batch_id="corrupt_batch",
        payload_bytes=bad_bytes,
        metadata={"url": "https://www.innoget.com/technology-calls/7777/corrupt"},
        retrieval_timestamp=datetime.now(UTC),
    )

    normalizer = InnogetHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(payload))
    assert len(results) == 1
    assert results[0].disposition == DemandDisposition.QUARANTINED_MALFORMED
    assert "Unicode decoding failed" in (results[0].error_detail or "")


def test_innoget_normalizer_missing_critical_text(origin_resolver: DefaultOriginResolver) -> None:
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

    normalizer = InnogetHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(payload))
    assert len(results) == 1
    assert results[0].disposition == DemandDisposition.EXCLUDED_MISSING_TEXT


def test_innoget_normalize_stream_yields_only_included(
    origin_resolver: DefaultOriginResolver,
    spanish_call_payload: RawPayload,
    pg_us_payload: RawPayload,
) -> None:
    normalizer = InnogetHtmlNormalizer(origin_resolver=origin_resolver)

    # Spanish call -> yields 1
    spanish_stream = list(normalizer.normalize_stream(spanish_call_payload))
    assert len(spanish_stream) == 1
    assert spanish_stream[0].demand_id == "INNOGET-900002"

    # US call -> yields 0
    us_stream = list(normalizer.normalize_stream(pg_us_payload))
    assert len(us_stream) == 0
