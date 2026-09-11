import html
import re
from collections.abc import Sequence
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PermittedSourceConfig(BaseModel):
    """Configuration for an authorized acquisition source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    permitted_constructs: tuple[str, ...] = Field(..., min_length=1)
    public_access_mode: str = Field(..., min_length=1)


class TemporalWindowConfig(BaseModel):
    """Temporal boundaries for demand publication."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_publication_date: date
    max_publication_date: date
    date_interpretation: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_date_order(self) -> "TemporalWindowConfig":
        if self.min_publication_date > self.max_publication_date:
            raise ValueError("min_publication_date must be <= max_publication_date")
        return self


class GeographicStratumConfig(BaseModel):
    """Specification of an authorized geographic sampling stratum."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stratum_id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)


class ContentRequirementsConfig(BaseModel):
    """Pre-specified content completeness and integrity criteria."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_word_count: int = Field(..., ge=0)
    require_technical_problem: bool
    allow_explicit_confidentiality_redaction: bool

    @field_validator("min_word_count", mode="before")
    @classmethod
    def validate_min_word_count(cls, v: int) -> int:
        if v < 0:
            raise ValueError("min_word_count must be >= 0")
        return v


class ConcentrationMonitoringConfig(BaseModel):
    """Thresholds for monitoring corpus-level concentration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sector_warning_threshold: float = Field(..., gt=0.0, le=1.0)
    max_independent_per_organization: int = Field(..., ge=1)

    @field_validator("sector_warning_threshold", mode="before")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError("sector_warning_threshold must be in (0.0, 1.0]")
        return v


class UnknownHandlingConfig(BaseModel):
    """Handling rules for indeterminate organization independence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unknown_organization_split_policy: str = Field(..., min_length=1)
    counts_towards_independent_target: bool


class TargetSampleSizeConfig(BaseModel):
    """Target statistical power requirements for the independent corpus."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_independent_demands: int = Field(..., ge=1)
    power_analysis_reference: str = Field(..., min_length=1)


class CorpusExpansionPolicy(BaseModel):
    """Declarative versioned policy governing Phase-2 corpus expansion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_version: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    target_sample_size: TargetSampleSizeConfig
    sources: tuple[PermittedSourceConfig, ...] = Field(..., min_length=1)
    temporal_window: TemporalWindowConfig
    geographic_strata: tuple[GeographicStratumConfig, ...] = Field(..., min_length=1)
    content_requirements: ContentRequirementsConfig
    concentration_monitoring: ConcentrationMonitoringConfig
    unknown_handling: UnknownHandlingConfig

    @field_validator("policy_version")
    @classmethod
    def validate_policy_version_prefix(cls, v: str) -> str:
        if not v.startswith("corpus_expansion_policy_"):
            raise ValueError("policy_version must start with 'corpus_expansion_policy_'")
        return v


def calculate_canonical_word_count(text: str) -> int:
    """Calculate the canonical word count for technical demand text.

    Normalization procedure:
    1. Strip HTML/XML markup tags (<[^>]+>).
    2. Unescape HTML entities (&amp; -> &, &nbsp; -> space, etc.).
    3. Tokenize words with Unicode word characters (\\w) allowing internal
       single hyphens and apostrophes (e.g. 'state-of-the-art', 'company\\'s').
    """
    if not text:
        return 0

    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    tokens = re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", clean, flags=re.UNICODE)
    return len(tokens)


class DemandCandidateContractRecord(BaseModel):
    """Canonical representation of an acquired candidate prior to policy validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    demand_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    source_construct: str = Field(..., min_length=1)
    publication_date: date
    publication_date_evidence_field: str = Field(..., min_length=1)
    publication_date_evidence_text: str = Field(..., min_length=1)
    geographic_stratum: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description_text: str = Field(..., min_length=1)
    language_code: str = Field(..., min_length=2, max_length=5)
    organization_raw: str | None = None
    is_publicly_accessible: bool
    has_confidentiality_redaction: bool
    has_articulated_technical_problem: bool
    technical_problem_evidence_text: str | None = None


class CandidateRejectionReason(StrEnum):
    """Pre-specified candidate exclusion reasons."""

    UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"
    INCOMPATIBLE_CONSTRUCT = "INCOMPATIBLE_CONSTRUCT"
    OUT_OF_TEMPORAL_WINDOW = "OUT_OF_TEMPORAL_WINDOW"
    UNAUTHORIZED_GEOGRAPHIC_STRATUM = "UNAUTHORIZED_GEOGRAPHIC_STRATUM"
    CONTENT_TOO_SHORT = "CONTENT_TOO_SHORT"
    CONFIDENTIALITY_REDACTED = "CONFIDENTIALITY_REDACTED"
    ACCESS_NOT_PUBLIC = "ACCESS_NOT_PUBLIC"
    NO_TECHNICAL_PROBLEM = "NO_TECHNICAL_PROBLEM"


class CandidateValidationResult(BaseModel):
    """Result of validating a candidate against corpus expansion policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str
    rejection_reasons: tuple[CandidateRejectionReason, ...]

    @classmethod
    def accept(cls) -> "CandidateValidationResult":
        return cls(status="ACCEPT", rejection_reasons=())

    @classmethod
    def reject(cls, reasons: Sequence[CandidateRejectionReason]) -> "CandidateValidationResult":
        # Deduplicate and sort deterministically by enum name
        sorted_reasons = tuple(sorted(set(reasons), key=lambda r: r.value))
        return cls(status="REJECT", rejection_reasons=sorted_reasons)
