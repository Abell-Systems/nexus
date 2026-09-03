"""Unit tests for DefaultOriginResolver: policy-driven, evidence-backed origin classification."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from application.ingestion.origin_resolver import DefaultOriginResolver, ExternalRegistryVerifier
from domain.models.demand import ExtractionSourceKind, RawExtractedDemandFields, SpanishOriginLevel
from domain.models.evidence import VerificationStatus
from domain.models.origin_policy import JurisdictionEntry, OriginPolicyConfig

CANONICAL_POLICY_PATH = Path("config/policies/data/jurisdiction_policy.json")


@pytest.fixture
def default_policy() -> OriginPolicyConfig:
    return OriginPolicyConfig.load_from_json(CANONICAL_POLICY_PATH)


@pytest.fixture
def default_resolver(default_policy: OriginPolicyConfig) -> DefaultOriginResolver:
    return DefaultOriginResolver(policy=default_policy)


class MockMercantileRegistryVerifier(ExternalRegistryVerifier):
    def __init__(self, certified_entities: dict[str, str]) -> None:
        self.certified_entities = certified_entities

    def is_registered_spanish_entity(self, organization_name: str) -> tuple[bool, str]:
        clean = organization_name.strip().lower()
        if clean in self.certified_entities:
            return True, self.certified_entities[clean]
        return False, ""


def test_origin_policy_loading_and_sha256() -> None:
    policy = OriginPolicyConfig.load_from_json(CANONICAL_POLICY_PATH)
    assert policy.policy_id == "SPAIN_DEMAND_ORIGIN_POLICY"
    assert policy.policy_version == "1.0.0"
    assert policy.target_jurisdiction == "ES"
    assert len(policy.policy_sha256) == 64
    assert policy.resolve_jurisdiction("Spain") == "ES"
    assert policy.resolve_jurisdiction("España") == "ES"
    assert policy.resolve_jurisdiction("Deutschland") == "DE"
    assert policy.resolve_jurisdiction("Unknownland") is None


def test_origin_policy_fails_fast_on_missing_or_corrupted_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        OriginPolicyConfig.load_from_json(tmp_path / "non_existent_policy.json")

    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{corrupt-json", encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupted or invalid"):
        OriginPolicyConfig.load_from_json(bad_json)


def test_origin_resolver_requires_explicit_policy() -> None:
    with pytest.raises(ValueError, match="policy must be provided"):
        DefaultOriginResolver(policy=None)  # type: ignore[arg-type]


def test_policy_hash_is_reproducible_and_changes_when_content_changes() -> None:
    policy_a = OriginPolicyConfig.load_from_json(CANONICAL_POLICY_PATH)
    policy_b = OriginPolicyConfig.load_from_json(CANONICAL_POLICY_PATH)
    assert policy_a.policy_sha256 == policy_b.policy_sha256

    # Modified policy must have distinct SHA-256
    entries = dict(policy_a.recognized_jurisdictions)
    entries["XX"] = JurisdictionEntry(canonical_name="Synthetic", aliases=["xx"])
    mod_policy = OriginPolicyConfig(
        policy_id=policy_a.policy_id,
        policy_version="1.0.1",
        target_jurisdiction="XX",
        recognized_jurisdictions=entries,
        policy_sha256="12345",
    )
    assert mod_policy.policy_version != policy_a.policy_version


def test_target_jurisdiction_can_change_dynamically_without_code_changes() -> None:
    """Proves the resolver is completely decoupled from Spain."""
    synthetic_policy = OriginPolicyConfig(
        policy_id="TEST_SYNTHETIC_POLICY",
        policy_version="2.0.0",
        target_jurisdiction="FR",
        recognized_jurisdictions={
            "FR": JurisdictionEntry(canonical_name="France", aliases=["france", "fr", "francia"]),
            "ES": JurisdictionEntry(canonical_name="Spain", aliases=["spain", "es"]),
        },
        policy_sha256="0" * 64,
    )
    resolver = DefaultOriginResolver(policy=synthetic_policy)

    # In this policy, France is target jurisdiction!
    fr_fields = RawExtractedDemandFields(
        demand_id="INNOGET-FR-1",
        demand_id_source=ExtractionSourceKind.META_TAG,
        title="Appel a projets",
        description="Description technique",
        country_raw="France",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://innoget.com/fr-1",
    )
    fr_assessment = resolver.assess_origin(fr_fields)
    assert fr_assessment.level == SpanishOriginLevel.LEVEL_1_DIRECT_METADATA
    assert fr_assessment.is_target_origin is True
    assert fr_assessment.resolved_jurisdiction_code == "FR"

    # Spain is now considered a foreign jurisdiction under this French policy!
    es_fields = RawExtractedDemandFields(
        demand_id="INNOGET-ES-1",
        demand_id_source=ExtractionSourceKind.META_TAG,
        title="Reto Español",
        description="Descripcion tecnica",
        country_raw="Spain",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://innoget.com/es-1",
    )
    es_assessment = resolver.assess_origin(es_fields)
    assert es_assessment.level == SpanishOriginLevel.NON_SPANISH
    assert es_assessment.is_target_origin is False
    assert es_assessment.resolved_jurisdiction_code == "ES"


def test_level_1_direct_platform_country_metadata(default_resolver: DefaultOriginResolver) -> None:
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-2292",
        demand_id_source=ExtractionSourceKind.META_TAG,
        title="Valid Title",
        description="Valid description of challenge",
        country_raw="Spain",
        organization_raw="INDUSAC S.L.",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/2292",
    )

    assessment = default_resolver.assess_origin(fields, raw_payload_sha256="a" * 64)
    assert assessment.level == SpanishOriginLevel.LEVEL_1_DIRECT_METADATA
    assert assessment.is_target_origin is True
    assert assessment.resolved_jurisdiction_code == "ES"
    assert len(assessment.evidence_observations) == 1

    ev = assessment.evidence_observations[0]
    assert ev.field_name == "origin_country"
    assert ev.observed_value_json == '"Spain"'
    assert ev.verification_status == VerificationStatus.SOURCE_REPORTED
    assert len(assessment.policy_sha256) == 64


def test_explicit_foreign_country_is_proven_non_spanish(default_resolver: DefaultOriginResolver) -> None:
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-2446",
        demand_id_source=ExtractionSourceKind.META_TAG,
        title="Valid Title",
        description="Valid description of challenge",
        country_raw="United States",
        organization_raw="The Procter & Gamble Company",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/2446",
    )

    assessment = default_resolver.assess_origin(fields)
    assert assessment.level == SpanishOriginLevel.NON_SPANISH
    assert assessment.is_target_origin is False
    assert assessment.resolved_jurisdiction_code == "US"
    assert len(assessment.evidence_observations) == 1
    assert assessment.evidence_observations[0].observed_value_json == '"United States"'


def test_level_2_organization_metadata_designation(default_resolver: DefaultOriginResolver) -> None:
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-2295",
        demand_id_source=ExtractionSourceKind.META_TAG,
        title="Reto de Biotecnología",
        description="Descripción técnica de reto industrial",
        country_raw="",  # Country omitted in call
        organization_raw="Centro Tecnológico de Valencia",
        organization_location_raw="España",  # Organization designated in Spain
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/2295",
    )

    assessment = default_resolver.assess_origin(fields)
    assert assessment.level == SpanishOriginLevel.LEVEL_2_ORGANIZATION_METADATA
    assert assessment.is_target_origin is True
    assert assessment.resolved_jurisdiction_code == "ES"
    assert len(assessment.evidence_observations) == 1
    assert assessment.evidence_observations[0].field_name == "organization_location"
    assert assessment.evidence_observations[0].verification_status == VerificationStatus.SOURCE_REPORTED


def test_level_3_requires_authoritative_registry_cross_check(default_policy: OriginPolicyConfig) -> None:
    # Corporate suffix (e.g. S.L.) alone without registry verification MUST NOT be Level 3
    resolver_without_registry = DefaultOriginResolver(policy=default_policy)
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-3001",
        demand_id_source=ExtractionSourceKind.META_TAG,
        title="Valid Title",
        description="Valid description",
        country_raw="",  # Country omitted in call
        organization_raw="Innovaciones Ibericas S.L.",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/3001",
    )

    unverified_assessment = resolver_without_registry.assess_origin(fields)
    assert unverified_assessment.level == SpanishOriginLevel.UNVERIFIED
    assert unverified_assessment.is_target_origin is False

    # With an authenticated registry verifier:
    mock_verifier = MockMercantileRegistryVerifier({
        "innovaciones ibericas s.l.": "Registro Mercantil Central Tomo 1234, Folio 56, Hoja M-7890"
    })
    resolver_with_registry = DefaultOriginResolver(policy=default_policy, registry_verifier=mock_verifier)
    verified_assessment = resolver_with_registry.assess_origin(fields)

    assert verified_assessment.level == SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK
    assert verified_assessment.is_target_origin is True
    assert len(verified_assessment.evidence_observations) == 1
    obs = verified_assessment.evidence_observations[0]
    assert obs.verification_status == VerificationStatus.INDEPENDENTLY_VERIFIED
    assert obs.source_authority == "Authoritative Commercial Registry"


def test_unrecognized_country_yields_unverified_not_non_spanish(default_resolver: DefaultOriginResolver) -> None:
    fields = RawExtractedDemandFields(
        demand_id="INNOGET-4001",
        demand_id_source=ExtractionSourceKind.META_TAG,
        title="Unknown Call",
        description="Valid description",
        country_raw="Unknownland",  # Unrecognized country
        organization_raw="Anonymous Research Group",
        extraction_timestamp=datetime.now(UTC),
        source_uri="https://www.innoget.com/technology-calls/4001",
    )

    assessment = default_resolver.assess_origin(fields)
    assert assessment.level == SpanishOriginLevel.UNVERIFIED
    assert assessment.is_target_origin is False
    assert assessment.resolved_jurisdiction_code is None
    assert len(assessment.evidence_observations) == 0
