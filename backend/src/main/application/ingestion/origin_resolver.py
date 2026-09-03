"""Auditable Spanish Origin Resolver adhering to Protocol Section 3.4.

Evaluates uninterpreted raw demand fields and returns a deterministic OriginAssessment
with explicit OriginEvidence records.
Eliminates hardcoded ad-hoc organization lists and country lists.
Distinguishes strictly between proven non-Spanish jurisdiction and unverified origin.
"""

from typing import Protocol

from domain.models.demand import (
    OriginAssessment,
    OriginEvidence,
    RawExtractedDemandFields,
    SpanishOriginLevel,
)


class ExternalRegistryVerifier(Protocol):
    """Protocol for Level 3 authoritative external registry verification (Mercantile Registry / VIES)."""

    def is_registered_spanish_entity(self, organization_name: str) -> tuple[bool, str]:
        """Verify if an entity is an authenticated Spanish legal entity.

        Returns (is_verified, registry_reference).
        """
        ...


class DefaultOriginResolver:
    """Deterministic, policy-driven Spanish Origin Resolver with explicit provenance."""

    def __init__(
        self,
        target_country_names: frozenset[str] | None = None,
        registry_verifier: ExternalRegistryVerifier | None = None,
    ) -> None:
        self.target_country_names = target_country_names or frozenset({"spain", "españa", "es"})
        self.registry_verifier = registry_verifier

    def assess_origin(self, fields: RawExtractedDemandFields) -> OriginAssessment:
        """Evaluate raw demand facts against the 4-level hierarchy and return OriginAssessment."""
        country_raw = (fields.country_raw or "").strip()
        norm_country = country_raw.lower()
        org_raw = (fields.organization_raw or "").strip()

        # Rule 1: Level 1 - Direct Platform Country Metadata matches target jurisdiction
        if norm_country in self.target_country_names:
            evidence = OriginEvidence(
                level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
                field_name="origin_country",
                observed_value=country_raw,
                verification_source="platform_metadata",
                rule_applied="direct_country_metadata_equals_spain",
                is_authoritative=True,
            )
            return OriginAssessment(
                level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
                is_target_origin=True,
                rationale=f"Explicit platform country metadata indicates '{country_raw}'",
                evidence=[evidence],
            )

        # Rule 2: Explicit foreign country present (e.g. United States, Germany, France, etc.)
        # Any non-empty country that does NOT match target jurisdiction is a proven foreign country
        if country_raw and norm_country not in self.target_country_names:
            evidence = OriginEvidence(
                level=SpanishOriginLevel.NON_SPANISH,
                field_name="origin_country",
                observed_value=country_raw,
                verification_source="platform_metadata",
                rule_applied="explicit_foreign_country_metadata",
                is_authoritative=True,
            )
            return OriginAssessment(
                level=SpanishOriginLevel.NON_SPANISH,
                is_target_origin=False,
                rationale=f"Explicit platform country metadata indicates foreign jurisdiction: '{country_raw}'",
                evidence=[evidence],
            )

        # Rule 3: Level 2 - Sponsoring organization designated in Spain by source metadata
        # (e.g. source provides organization address/region or verified institutional call)
        # Note: Corporate suffixes like S.L. or S.A. alone DO NOT constitute Level 2 proof.
        # They only indicate commercial corporate form, not certified jurisdiction.

        # Rule 4: Level 3 - Authoritative external registry cross-check
        if self.registry_verifier and org_raw:
            is_reg, ref = self.registry_verifier.is_registered_spanish_entity(org_raw)
            if is_reg:
                evidence = OriginEvidence(
                    level=SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK,
                    field_name="requesting_organization",
                    observed_value=org_raw,
                    verification_source="external_registry",
                    rule_applied=f"authoritative_cross_check:{ref}",
                    is_authoritative=True,
                )
                return OriginAssessment(
                    level=SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK,
                    is_target_origin=True,
                    rationale=f"Organization '{org_raw}' verified via external registry: {ref}",
                    evidence=[evidence],
                )

        # Rule 5: Default Fallback -> UNVERIFIED
        # When neither target jurisdiction nor foreign jurisdiction is definitively proven.
        return OriginAssessment(
            level=SpanishOriginLevel.UNVERIFIED,
            is_target_origin=False,
            rationale="Insufficient evidence to prove target or foreign origin",
            evidence=[],
        )
