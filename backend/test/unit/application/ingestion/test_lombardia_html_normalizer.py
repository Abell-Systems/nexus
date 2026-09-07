"""Unit tests for LombardiaHtmlNormalizer verifying extraction and evidence-backed origin classification.

Open Innovation Lombardia republishes EEN Partnering Opportunities Database "Technology
request" listings (identical POD reference scheme, e.g. TRES20250806011). It exposes no
explicit country field, so country_raw is decoded from the POD reference's embedded
2-letter jurisdiction code (positions 3-4, e.g. "TRES..." -> "ES") -- a deterministic
parse of a raw identifier, not a heuristic guess.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from application.ingestion.normalizers.lombardia_html_normalizer import LombardiaHtmlNormalizer
from application.ingestion.origin_resolver import DefaultOriginResolver
from domain.models.demand import DemandDisposition, SpanishOriginLevel
from domain.models.origin_policy import OriginPolicyConfig
from domain.protocols.sources import RawPayload

CANONICAL_POLICY_PATH = (
    Path(__file__).resolve().parents[5] / "config" / "policies" / "data" / "jurisdiction_policy.json"
)
_FIXTURES_DIR = Path(__file__).resolve().parents[5] / "backend" / "test" / "fixtures"


@pytest.fixture
def origin_resolver() -> DefaultOriginResolver:
    policy = OriginPolicyConfig.load_from_json(CANONICAL_POLICY_PATH)
    return DefaultOriginResolver(policy=policy)


@pytest.fixture
def spanish_bridge_payload() -> RawPayload:
    fixture_path = _FIXTURES_DIR / "lombardia_sample_spanish_1_pontes.html"
    return RawPayload(
        source_id="openinnovation_lombardia_web",
        batch_id="lombardia_collab_860",
        payload_bytes=fixture_path.read_bytes(),
        metadata={
            "url": "https://www.openinnovation.regione.lombardia.it/en/collaborations/collaboration-proposals/860/manutenzione-giunti-di-ponti"
        },
        retrieval_timestamp=datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def lithuania_payload() -> RawPayload:
    fixture_path = _FIXTURES_DIR / "lombardia_sample_lithuania_call.html"
    return RawPayload(
        source_id="openinnovation_lombardia_web",
        batch_id="lombardia_collab_2024",
        payload_bytes=fixture_path.read_bytes(),
        metadata={
            "url": "https://www.openinnovation.regione.lombardia.it/en/collaborations/collaboration-proposals/2024/gruppo-industriale-lituano-cerca-tecnologie-per-gestione-sostenibile-d"
        },
        retrieval_timestamp=datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC),
    )


def test_lombardia_normalizer_level_1_spanish_origin(
    origin_resolver: DefaultOriginResolver, spanish_bridge_payload: RawPayload
) -> None:
    normalizer = LombardiaHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(spanish_bridge_payload))
    assert len(results) == 1

    res = results[0]
    assert res.disposition == DemandDisposition.INCLUDED
    assert res.origin_level == SpanishOriginLevel.LEVEL_1_DIRECT_METADATA

    demand = res.demand
    assert demand is not None
    assert demand.demand_id == "LOMBARDIA-860"
    assert demand.title == "Manutenzione giunti di ponti"
    assert "società spagnola" in demand.description.lower() or "societa spagnola" in demand.description.lower()
    assert len(demand.description.split()) >= 25
    assert demand.is_spanish_demand is True
    assert demand.metadata.get("pod_reference") == "TRES20250806011"


def test_lombardia_normalizer_level_1_spanish_origin_second_record(
    origin_resolver: DefaultOriginResolver,
) -> None:
    """Covers the second (of exactly 2) frozen Lombardia demands in the N=39 corpus."""
    fixture_path = _FIXTURES_DIR / "lombardia_sample_spanish_2_pm10.html"
    payload = RawPayload(
        source_id="openinnovation_lombardia_web",
        batch_id="lombardia_collab_947",
        payload_bytes=fixture_path.read_bytes(),
        metadata={
            "url": "https://www.openinnovation.regione.lombardia.it/en/collaborations/collaboration-proposals/947/soluzioni-per-monitorare-e-mitigare-polveri-pm10-in-miniere"
        },
        retrieval_timestamp=datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC),
    )

    normalizer = LombardiaHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(payload))
    assert len(results) == 1

    res = results[0]
    assert res.disposition == DemandDisposition.INCLUDED
    demand = res.demand
    assert demand is not None
    assert demand.demand_id == "LOMBARDIA-947"
    assert len(demand.description.split()) >= 25
    assert demand.is_spanish_demand is True
    assert demand.metadata.get("pod_reference") == "TRES20251031029"


def test_lombardia_normalizer_excludes_lithuania_call(
    origin_resolver: DefaultOriginResolver, lithuania_payload: RawPayload
) -> None:
    normalizer = LombardiaHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(lithuania_payload))
    assert len(results) == 1

    res = results[0]
    # Lithuania is not among the 11 jurisdictions recognized by jurisdiction_policy.json,
    # so it correctly resolves to UNVERIFIED, not NON_SPANISH -- consistent with
    # docs/phase2-demand-acquisition-audit.md's finding that most non-target countries
    # fall to UNVERIFIED under the current policy rather than a confirmed NON_SPANISH.
    assert res.disposition == DemandDisposition.EXCLUDED_UNVERIFIED_ORIGIN
    assert res.origin_level == SpanishOriginLevel.UNVERIFIED

    demand = res.demand
    assert demand is not None
    assert demand.demand_id == "LOMBARDIA-2024"
    assert demand.is_spanish_demand is False
    assert demand.metadata.get("pod_reference") == "TRLT20260720004"


def test_lombardia_normalizer_quarantines_invalid_utf8(origin_resolver: DefaultOriginResolver) -> None:
    bad_bytes = b"\xff\xfe\x00\x00\x80\x81malformed"
    payload = RawPayload(
        source_id="openinnovation_lombardia_web",
        batch_id="corrupt_batch",
        payload_bytes=bad_bytes,
        metadata={"url": "https://www.openinnovation.regione.lombardia.it/en/collaborations/collaboration-proposals/9999/corrupt"},
        retrieval_timestamp=datetime.now(UTC),
    )

    normalizer = LombardiaHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(payload))
    assert len(results) == 1
    assert results[0].disposition == DemandDisposition.QUARANTINED_MALFORMED


def test_lombardia_normalizer_missing_critical_text(origin_resolver: DefaultOriginResolver) -> None:
    html_no_abstract = b"""<!DOCTYPE html><html><body>
    <h1 class="collaborations-detail-title">Titulo sin abstract</h1>
    <span class="collaborations-info-value lead">TRES20260101001</span>
    </body></html>"""

    payload = RawPayload(
        source_id="openinnovation_lombardia_web",
        batch_id="collab_no_abstract",
        payload_bytes=html_no_abstract,
        metadata={"url": "https://www.openinnovation.regione.lombardia.it/en/collaborations/collaboration-proposals/1/no-abstract"},
        retrieval_timestamp=datetime.now(UTC),
    )

    normalizer = LombardiaHtmlNormalizer(origin_resolver=origin_resolver)
    results = list(normalizer.normalize_results(payload))
    assert len(results) == 1
    assert results[0].disposition == DemandDisposition.EXCLUDED_MISSING_TEXT


def test_lombardia_normalize_stream_yields_only_included(
    origin_resolver: DefaultOriginResolver,
    spanish_bridge_payload: RawPayload,
    lithuania_payload: RawPayload,
) -> None:
    normalizer = LombardiaHtmlNormalizer(origin_resolver=origin_resolver)

    spanish_stream = list(normalizer.normalize_stream(spanish_bridge_payload))
    assert len(spanish_stream) == 1
    assert spanish_stream[0].demand_id == "LOMBARDIA-860"

    lithuania_stream = list(normalizer.normalize_stream(lithuania_payload))
    assert len(lithuania_stream) == 0
