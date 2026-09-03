"""Pure domain models for technology demand signals, evidence-backed Spanish origin, and discovery."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from domain.models.evidence import FieldObservation


class DemandSignal(BaseModel):
    """External technological demand or market challenge signal (for Step 1-8 compatibility)."""

    demand_id: str
    source_network: str = "innoget"
    title: str
    description: str
    technical_requirements: list[str] = Field(default_factory=list)
    origin_country: str | None = None
    posted_date: str | None = None
    deadline_date: str | None = None
    classified_cpc_prefixes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class SpanishOriginLevel(StrEnum):
    """Four-level hierarchical classification of Spanish origin under Protocol Section 3.4."""

    LEVEL_1_DIRECT_METADATA = "level_1_direct_metadata"
    LEVEL_2_ORGANIZATION_METADATA = "level_2_organization_metadata"
    LEVEL_3_REGISTRY_CROSS_CHECK = "level_3_registry_cross_check"
    NON_SPANISH = "non_spanish"
    UNVERIFIED = "unverified"


class DemandDiscoveryChannel(StrEnum):
    """Orthogonal discovery mechanisms defined under Protocol Section 3.3."""

    DIRECTORY = "directory"
    SITEMAP = "sitemap"
    EXTERNAL_REFERENCE = "external_reference"


class RawExtractedDemandFields(BaseModel):
    """Factual, uninterpreted fields extracted directly from raw demand source markup."""

    demand_id: str | None = None
    title: str | None = None
    description: str | None = None
    organization_raw: str | None = None
    country_raw: str | None = None
    deadline_date_raw: str | None = None
    budget_range_raw: str | None = None
    canonical_url: str | None = None
    extraction_timestamp: datetime
    source_uri: str


class OriginEvidence(BaseModel):
    """Verifiable proof supporting an origin classification decision."""

    level: SpanishOriginLevel
    field_name: str
    observed_value: str
    verification_source: str
    rule_applied: str
    is_authoritative: bool = True


class OriginAssessment(BaseModel):
    """Auditable result of evaluating a demand against the Spanish origin verification hierarchy."""

    level: SpanishOriginLevel
    is_target_origin: bool
    rationale: str
    evidence: list[OriginEvidence] = Field(default_factory=list)


class DemandRecord(BaseModel):
    """Canonical domain representation of an industrial technology demand signal."""

    demand_id: str
    title: str
    description: str
    requesting_organization: str
    origin_country: str
    spanish_origin_level: SpanishOriginLevel
    is_spanish_demand: bool
    cpc_prefix: str | None = None
    posted_date: str | None = None
    deadline_date: str | None = None
    url: str
    discovery_channel: DemandDiscoveryChannel = DemandDiscoveryChannel.DIRECTORY
    budget_range: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class DemandDisposition(StrEnum):
    """Disposition of an extracted demand under the empirical acquisition protocol."""

    INCLUDED = "included"
    EXCLUDED_NON_SPANISH = "excluded_non_spanish"
    EXCLUDED_UNVERIFIED_ORIGIN = "excluded_unverified_origin"
    EXCLUDED_MISSING_TEXT = "excluded_missing_text"
    QUARANTINED_MALFORMED = "quarantined_malformed"
    DUPLICATE = "duplicate"


class DemandNormalizationResult(BaseModel):
    """Result of normalizing an acquired technology demand payload with granular audit evidence."""

    disposition: DemandDisposition
    demand: DemandRecord | None = None
    origin_assessment: OriginAssessment
    raw_snippet: str = ""
    error_detail: str | None = None
    field_observations: list[FieldObservation] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")

    @property
    def origin_level(self) -> SpanishOriginLevel:
        return self.origin_assessment.level
