"""Auditable Spanish Origin Resolver adhering to Protocol Section 3.4.

Evaluates uninterpreted raw demand facts against a versioned OriginPolicyConfig.
Returns a deterministic OriginAssessment containing explicit FieldObservation evidence records.
Distinguishes strictly between target jurisdiction, verified foreign jurisdiction, and UNVERIFIED.
"""

from typing import Protocol

from domain.models.demand import (
    OriginAssessment,
    RawExtractedDemandFields,
    SpanishOriginLevel,
)
from domain.models.evidence import FieldObservation, VerificationStatus
from domain.models.origin_policy import OriginPolicyConfig


class ExternalRegistryVerifier(Protocol):
    """Protocol for Level 3 authoritative external registry verification (Mercantile Registry / VIES)."""

    def is_registered_spanish_entity(self, organization_name: str) -> tuple[bool, str]:
        """Verify if an entity is an authenticated Spanish legal entity.

        Returns (is_verified, registry_reference).
        """
        ...


class DefaultOriginResolver:
    """Deterministic, policy-driven Spanish Origin Resolver with cryptographic policy versioning.

    Requires an explicit OriginPolicyConfig injected via constructor.
    Fail-fast: does not guess filesystem paths or synthesize fake policies.
    """

    def __init__(
        self,
        policy: OriginPolicyConfig,
        registry_verifier: ExternalRegistryVerifier | None = None,
    ) -> None:
        if policy is None:
            raise ValueError("policy must be provided as a valid OriginPolicyConfig")
        self.policy = policy
        self.registry_verifier = registry_verifier

    def assess_origin(
        self,
        fields: RawExtractedDemandFields,
        raw_payload_sha256: str = "",
    ) -> OriginAssessment:
        """Evaluate raw demand facts against the versioned policy and return OriginAssessment."""
        sha = raw_payload_sha256 if len(raw_payload_sha256) == 64 else ("0" * 64)
        country_raw = (fields.country_raw or "").strip()
        org_raw = (fields.organization_raw or "").strip()
        org_loc_raw = (fields.organization_location_raw or "").strip()

        entity_id = fields.demand_id or "DEMAND_PENDING"
        ts = fields.extraction_timestamp

        # 1. Resolve country token through versioned policy
        resolved_country_code = self.policy.resolve_jurisdiction(country_raw)

        # Rule 1: Level 1 - Direct Platform Country Metadata matches target jurisdiction
        if resolved_country_code == self.policy.target_jurisdiction:
            obs = FieldObservation(
                entity_id=entity_id,
                field_name="origin_country",
                observed_value_json=f'"{country_raw}"',
                value_type="str",
                source_authority="InnoGet Platform Metadata",
                source_uri=fields.source_uri,
                retrieval_timestamp=ts,
                raw_payload_sha256=sha,
                extraction_version="2.0.0",
                verification_status=VerificationStatus.SOURCE_REPORTED,
            )
            return OriginAssessment(
                level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
                is_target_origin=True,
                resolved_jurisdiction_code=resolved_country_code,
                rationale=f"Platform country metadata '{country_raw}' resolved to target jurisdiction '{resolved_country_code}'",
                policy_id=self.policy.policy_id,
                policy_version=self.policy.policy_version,
                policy_sha256=self.policy.policy_sha256,
                evidence_observations=[obs],
            )

        # Rule 2: Verified Foreign Country (country is recognized in policy, but is NOT the target jurisdiction)
        if resolved_country_code is not None and resolved_country_code != self.policy.target_jurisdiction:
            obs = FieldObservation(
                entity_id=entity_id,
                field_name="origin_country",
                observed_value_json=f'"{country_raw}"',
                value_type="str",
                source_authority="InnoGet Platform Metadata",
                source_uri=fields.source_uri,
                retrieval_timestamp=ts,
                raw_payload_sha256=sha,
                extraction_version="2.0.0",
                verification_status=VerificationStatus.SOURCE_REPORTED,
            )
            return OriginAssessment(
                level=SpanishOriginLevel.NON_SPANISH,
                is_target_origin=False,
                resolved_jurisdiction_code=resolved_country_code,
                rationale=f"Platform country metadata '{country_raw}' resolved to foreign jurisdiction '{resolved_country_code}'",
                policy_id=self.policy.policy_id,
                policy_version=self.policy.policy_version,
                policy_sha256=self.policy.policy_sha256,
                evidence_observations=[obs],
            )

        # Rule 3: Level 2 - Sponsoring organization designated in target jurisdiction by source metadata
        resolved_org_loc = self.policy.resolve_jurisdiction(org_loc_raw)
        if resolved_org_loc == self.policy.target_jurisdiction:
            obs = FieldObservation(
                entity_id=entity_id,
                field_name="organization_location",
                observed_value_json=f'"{org_loc_raw}"',
                value_type="str",
                source_authority="InnoGet Organization Metadata",
                source_uri=fields.source_uri,
                retrieval_timestamp=ts,
                raw_payload_sha256=sha,
                extraction_version="2.0.0",
                verification_status=VerificationStatus.SOURCE_REPORTED,
            )
            return OriginAssessment(
                level=SpanishOriginLevel.LEVEL_2_ORGANIZATION_METADATA,
                is_target_origin=True,
                resolved_jurisdiction_code=resolved_org_loc,
                rationale=f"Organization location metadata '{org_loc_raw}' resolved to target jurisdiction '{resolved_org_loc}'",
                policy_id=self.policy.policy_id,
                policy_version=self.policy.policy_version,
                policy_sha256=self.policy.policy_sha256,
                evidence_observations=[obs],
            )

        # Rule 4: Level 3 - Authoritative external registry cross-check
        if self.registry_verifier and org_raw:
            is_reg, ref = self.registry_verifier.is_registered_spanish_entity(org_raw)
            if is_reg:
                obs = FieldObservation(
                    entity_id=entity_id,
                    field_name="requesting_organization",
                    observed_value_json=f'"{org_raw}"',
                    value_type="str",
                    source_authority="Authoritative Commercial Registry",
                    source_uri=ref,
                    retrieval_timestamp=ts,
                    raw_payload_sha256=sha,
                    extraction_version="2.0.0",
                    verification_status=VerificationStatus.INDEPENDENTLY_VERIFIED,
                )
                return OriginAssessment(
                    level=SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK,
                    is_target_origin=True,
                    resolved_jurisdiction_code=self.policy.target_jurisdiction,
                    rationale=f"Organization '{org_raw}' verified via external registry: {ref}",
                    policy_id=self.policy.policy_id,
                    policy_version=self.policy.policy_version,
                    policy_sha256=self.policy.policy_sha256,
                    evidence_observations=[obs],
                )

        # Rule 5: Default Fallback -> UNVERIFIED
        # When neither target jurisdiction nor foreign jurisdiction is definitively proven.
        return OriginAssessment(
            level=SpanishOriginLevel.UNVERIFIED,
            is_target_origin=False,
            resolved_jurisdiction_code=None,
            rationale="Insufficient evidence to prove target or foreign jurisdiction (unrecognized or missing country)",
            policy_id=self.policy.policy_id,
            policy_version=self.policy.policy_version,
            policy_sha256=self.policy.policy_sha256,
            evidence_observations=[],
        )
