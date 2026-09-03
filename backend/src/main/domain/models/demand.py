"""Pure domain models for technology demand signals, Spanish origin hierarchy, and discovery."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DemandSignal(BaseModel):
    """External technological demand or market challenge signal."""

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
    """Result of normalizing an acquired technology demand payload."""

    disposition: DemandDisposition
    demand: DemandRecord | None = None
    origin_level: SpanishOriginLevel = SpanishOriginLevel.UNVERIFIED
    raw_snippet: str = ""
    error_detail: str | None = None

    model_config = ConfigDict(extra="ignore")
