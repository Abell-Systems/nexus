"""Unit tests for DefaultOriginResolver: deterministic evidence-backed origin classification."""

from datetime import UTC, datetime

from application.ingestion.origin_resolver import DefaultOriginResolver, ExternalRegistryVerifier
from domain.models.demand import RawExtractedDemandFields, SpanishOriginLevel


class MockMercantileRegistryVerifier(ExternalRegistryVerifier):
    def __init__(self, certified_entities: dict[str, str]) -> None:
        self.certified_entities = certified_entities

    def is_registered_spanish_entity(self, organization_name: str) -> tuple[bool, str]:
        clean = organization_name.strip().lower()
        if clean in self.certified_entities:
            return True, self.certified_entities[clean]
        return False, ""


def test_level_1_direct_platform_country_metadata() -> None:
    resolver = DefaultOriginResolver()
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-2292",
        title="Valid Title",
        description="Valid description of challenge",
        country_raw="Spain",
        organization_raw="INDUSAC S.L.",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/2292",
    )

    assessment = resolver.assess_origin(fields)
    assert assessment.level == SpanishOriginLevel.LEVEL_1_DIRECT_METADATA
    assert assessment.is_target_origin is True
    assert len(assessment.evidence) == 1
    ev = assessment.evidence[0]
    assert ev.field_name == "origin_country"
    assert ev.observed_value == "Spain"
    assert ev.verification_source == "platform_metadata"


def test_explicit_foreign_country_is_proven_non_spanish() -> None:
    resolver = DefaultOriginResolver()
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-2446",
        title="Valid Title",
        description="Valid description of challenge",
        country_raw="United States",
        organization_raw="The Procter & Gamble Company",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/2446",
    )

    assessment = resolver.assess_origin(fields)
    assert assessment.level == SpanishOriginLevel.NON_SPANISH
    assert assessment.is_target_origin is False
    assert len(assessment.evidence) == 1
    assert assessment.evidence[0].observed_value == "United States"


def test_level_3_requires_authoritative_registry_cross_check() -> None:
    # Corporate suffix (e.g. S.L.) alone without registry verification MUST NOT be Level 3
    resolver_without_registry = DefaultOriginResolver()
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-3001",
        title="Valid Title",
        description="Valid description",
        country_raw="",  # Country omitted in call
        organization_raw="Innovaciones Ibericas S.L.",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/3001",
    )

    unverified_assessment = resolver_without_registry.assess_origin(fields)
    # Without an external registry, must fall back to UNVERIFIED, never Level 3!
    assert unverified_assessment.level == SpanishOriginLevel.UNVERIFIED
    assert unverified_assessment.is_target_origin is False

    # With an authenticated registry verifier:
    mock_verifier = MockMercantileRegistryVerifier({
        "innovaciones ibericas s.l.": "Registro Mercantil Central Tomo 1234, Folio 56, Hoja M-7890"
    })
    resolver_with_registry = DefaultOriginResolver(registry_verifier=mock_verifier)
    verified_assessment = resolver_with_registry.assess_origin(fields)

    assert verified_assessment.level == SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK
    assert verified_assessment.is_target_origin is True
    assert len(verified_assessment.evidence) == 1
    assert "Registro Mercantil Central" in verified_assessment.evidence[0].rule_applied


def test_unverified_origin_when_no_evidence_exists() -> None:
    resolver = DefaultOriginResolver()
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-4001",
        title="Unknown Call",
        description="Valid description",
        country_raw="",
        organization_raw="Anonymous Research Group",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/4001",
    )

    assessment = resolver.assess_origin(fields)
    assert assessment.level == SpanishOriginLevel.UNVERIFIED
    assert assessment.is_target_origin is False
    assert len(assessment.evidence) == 0
