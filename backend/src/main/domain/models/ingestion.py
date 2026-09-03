"""Domain models for ingestion classification, attrition tracking, and quarantine."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

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


class TemporalWindow(BaseModel):
    start_date: str
    end_date: str


class AttritionCounts(BaseModel):
    raw_payload_count: int = 0
    normalized_record_count: int = 0
    included_record_count: int = 0
    quarantined_record_count: int = 0
    excluded_record_count: int = 0
    duplicate_count: int = 0


class ExecutionEnvironment(BaseModel):
    git_commit: str
    normalizer_version: str
    python_version: str
    platform: str


class DatasetContentIdentity(BaseModel):
    """Deterministic, execution-independent identity of the analytical corpus.
    
    Excludes runtime timestamps and volatile host environment to guarantee bit-exact reproducibility.
    """

    dataset_id: str
    dataset_version: str
    source_authority: str
    source_release_id: str
    source_uri: str
    jurisdiction: str
    temporal_window: TemporalWindow
    canonical_sha256: str
    counts: AttritionCounts
    exclusion_reasons: dict[str, int] = Field(default_factory=dict)
    quarantine_reasons: dict[str, int] = Field(default_factory=dict)
    kind_code_distribution: dict[str, int] = Field(default_factory=dict)
    files: dict[str, str] = Field(default_factory=dict)


class ExecutionProvenance(BaseModel):
    """Runtime audit trail recording timestamps and execution environment."""

    created_at: datetime
    acquisition_started_at: datetime
    acquisition_finished_at: datetime
    environment: ExecutionEnvironment


class EnhancedManifest(BaseModel):
    """Authoritative cryptographic and attrition manifest for certified datasets."""

    schema_uri: str = Field(default="https://nexus.abell.ai/schemas/dataset-manifest-v2.json", alias="$schema")
    content_identity: DatasetContentIdentity
    content_identity_sha256: str = ""
    execution_provenance: ExecutionProvenance
    manifest_sha256: str = ""

    model_config = ConfigDict(populate_by_name=True)

    # Convenience properties for backward compatibility with root-level accessors
    @property
    def dataset_id(self) -> str:
        return self.content_identity.dataset_id

    @property
    def dataset_version(self) -> str:
        return self.content_identity.dataset_version

    @property
    def source_authority(self) -> str:
        return self.content_identity.source_authority

    @property
    def source_release_id(self) -> str:
        return self.content_identity.source_release_id

    @property
    def source_uri(self) -> str:
        return self.content_identity.source_uri

    @property
    def canonical_sha256(self) -> str:
        return self.content_identity.canonical_sha256

    @property
    def counts(self) -> AttritionCounts:
        return self.content_identity.counts

    @property
    def files(self) -> dict[str, str]:
        return self.content_identity.files

    @property
    def kind_code_distribution(self) -> dict[str, int]:
        return self.content_identity.kind_code_distribution

    @property
    def exclusion_reasons(self) -> dict[str, int]:
        return self.content_identity.exclusion_reasons

    @property
    def quarantine_reasons(self) -> dict[str, int]:
        return self.content_identity.quarantine_reasons
