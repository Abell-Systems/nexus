"""Domain models for ingestion classification, attrition tracking, and quarantine."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from domain.models.evidence import FieldObservation
from domain.models.patent import PatentDocument


class RecordDisposition(StrEnum):
    """Classification status of an ingested raw document."""

    INCLUDED = "included"
    EXCLUDED = "excluded"
    QUARANTINED = "quarantined"
    DUPLICATE = "duplicate"


class ExclusionReason(StrEnum):
    """Formal taxonomy of exclusion reasons for non-target records."""

    UNSUPPORTED_KIND_CODE = "unsupported_kind_code"
    OUT_OF_SCOPE_TEMPORAL_WINDOW = "out_of_scope_temporal_window"
    NON_SPANISH_JURISDICTION = "non_spanish_jurisdiction"
    NON_INVENTION_MODALITY = "non_invention_modality"
    MISSING_CRITICAL_TEXT = "missing_critical_text"


class QuarantineReason(StrEnum):
    """Formal taxonomy of quarantine reasons for malformed or unverifiable records."""

    MALFORMED_XML_SYNTAX = "malformed_xml_syntax"
    MISSING_REQUIRED_IDENTIFIER = "missing_required_identifier"
    INVALID_DATE_FORMAT = "invalid_date_format"
    UNVERIFIABLE_METADATA = "unverifiable_metadata"


class ExcludedRecord(BaseModel):
    """Valid well-formed record that falls outside the target evaluation boundary."""

    publication_id: str
    country_code: str
    kind_code: str
    reason: ExclusionReason
    detail: str
    source_uri: str
    observations: list[FieldObservation] = Field(default_factory=list)


class QuarantinedRecord(BaseModel):
    """Record that cannot be validated or parsed reliably due to structural defects."""

    raw_identifier: str | None = None
    reason: QuarantineReason
    error_message: str
    raw_snippet: str
    detected_at: datetime
    source_uri: str


class NormalizationResult(BaseModel):
    """Comprehensive output of normalizing an ingestion payload or item."""

    disposition: RecordDisposition
    document: PatentDocument | None = None
    excluded: ExcludedRecord | None = None
    quarantined: QuarantinedRecord | None = None
    observations: list[FieldObservation] = Field(default_factory=list)
