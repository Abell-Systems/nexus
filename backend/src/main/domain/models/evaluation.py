"""Domain models for scientific evaluation datasets and provenance under ADR 0006.

Invariants:
- Strict immutability (frozen=True) on all evaluation entities.
- Epistemic classification via DataModality (OBSERVED, EXPERT_LABELLED, SYNTHETIC_CONTROL).
- Typed provenance record with validated SHA-256 payload identity digest.
- Explicit discrete RelevanceGrade scale (0 to 3, or UNCERTAIN=-1).
- Referential integrity: annotations must strictly reference demands and patents in dataset.
- Rejection of unlabelled synthetic data (must explicitly declare SYNTHETIC_CONTROL).
- Decoupling between EvaluationDataset (scientific content), EvaluationDatasetManifest (metadata/identity),
  and ValidatedDataset (execution boundary).
- Zero filesystem access or relative path resolution.
"""

import re
from datetime import UTC, datetime
from enum import Enum, StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DataModality(StrEnum):
    """Epistemic modality of data in the evaluation corpus (ADR 0006 §2)."""

    OBSERVED = "observed"
    EXPERT_LABELLED = "expert_labelled"
    SYNTHETIC_CONTROL = "synthetic_control"


class RelevanceGrade(int, Enum):
    """Discrete relevance grade for demand-patent alignment evaluation.
    
    0: Irrelevant / out of domain.
    1: Domain related (same technological sector, does not address specific problem).
    2: Technologically relevant (addresses problem components or analogous solution).
    3: Directly addressing demand (target solution or substantial prior art).
    -1: Uncertain / requires deeper domain investigation.
    """

    GRADE_0 = 0
    GRADE_1 = 1
    GRADE_2 = 2
    GRADE_3 = 3
    UNCERTAIN = -1


class EvaluationProvenance(BaseModel):
    """Fine-grained provenance record for an evaluation corpus item (ADR 0006 §5)."""

    model_config = ConfigDict(frozen=True)

    source_authority: str = Field(min_length=1)
    source_uri: str = Field(min_length=1)
    extraction_timestamp: datetime
    raw_payload_sha256: str = Field(min_length=64, max_length=64)
    modality: DataModality

    @field_validator("raw_payload_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()

    @field_validator("extraction_timestamp")
    @classmethod
    def validate_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("extraction_timestamp must be timezone-aware (UTC)")
        return v


class EvaluationDemand(BaseModel):
    """Normalized, frozen demand record for scientific evaluation."""

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    posted_date: str | None = None
    target_cpc_prefixes: list[str] = Field(default_factory=list)
    is_synthetic: bool = False
    provenance: EvaluationProvenance

    @model_validator(mode="after")
    def validate_modality_consistency(self) -> "EvaluationDemand":
        if self.is_synthetic and self.provenance.modality != DataModality.SYNTHETIC_CONTROL:
            raise ValueError("Synthetic data must explicitly declare modality SYNTHETIC_CONTROL")
        return self


class EvaluationPatent(BaseModel):
    """Normalized, frozen patent publication record for scientific evaluation."""

    model_config = ConfigDict(frozen=True)

    publication_id: str = Field(min_length=1)
    publication_date: str | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)
    is_synthetic: bool = False
    provenance: EvaluationProvenance

    @model_validator(mode="after")
    def validate_modality_consistency(self) -> "EvaluationPatent":
        if self.is_synthetic and self.provenance.modality != DataModality.SYNTHETIC_CONTROL:
            raise ValueError("Synthetic data must explicitly declare modality SYNTHETIC_CONTROL")
        return self


class EvaluationAnnotation(BaseModel):
    """Subjective expert label or technical judgement for a demand-patent pair."""

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    grade: RelevanceGrade
    annotator_role: str = Field(min_length=1)
    notes: str = ""
    modality: DataModality = DataModality.EXPERT_LABELLED


class EvaluationDataset(BaseModel):
    """Scientific content of an evaluation benchmark (ADR 0006 §3)."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    demands: list[EvaluationDemand] = Field(min_length=1)
    patents: list[EvaluationPatent] = Field(min_length=1)
    annotations: list[EvaluationAnnotation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_referential_integrity(self) -> "EvaluationDataset":
        valid_demands = {d.demand_id for d in self.demands}
        valid_patents = {p.publication_id for p in self.patents}

        for idx, anno in enumerate(self.annotations):
            if anno.demand_id not in valid_demands:
                raise ValueError(
                    f"Annotation #{idx} references unknown demand_id '{anno.demand_id}' not in dataset demands"
                )
            if anno.publication_id not in valid_patents:
                raise ValueError(
                    f"Annotation #{idx} references unknown publication_id '{anno.publication_id}' not in dataset patents"
                )
        return self


class EvaluationDatasetManifest(BaseModel):
    """External descriptor and cryptographic identity for an evaluation dataset."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    source_authorities: list[str] = Field(min_length=1)
    demand_count: int = Field(ge=0)
    patent_count: int = Field(ge=0)
    annotation_count: int = Field(ge=0)
    content_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("content_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()


class ValidatedDataset(BaseModel):
    """Execution boundary object produced only after full cryptographic and schema validation."""

    model_config = ConfigDict(frozen=True)

    dataset: EvaluationDataset
    manifest: EvaluationDatasetManifest
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_manifest_consistency(self) -> "ValidatedDataset":
        if self.dataset.dataset_id != self.manifest.dataset_id:
            raise ValueError(
                f"Dataset ID mismatch: dataset '{self.dataset.dataset_id}' vs manifest '{self.manifest.dataset_id}'"
            )
        if self.dataset.dataset_version != self.manifest.dataset_version:
            raise ValueError(
                f"Dataset version mismatch: dataset '{self.dataset.dataset_version}' vs manifest '{self.manifest.dataset_version}'"
            )
        if len(self.dataset.demands) != self.manifest.demand_count:
            raise ValueError(
                f"Manifest demand_count ({self.manifest.demand_count}) does not match dataset ({len(self.dataset.demands)})"
            )
        if len(self.dataset.patents) != self.manifest.patent_count:
            raise ValueError(
                f"Manifest patent_count ({self.manifest.patent_count}) does not match dataset ({len(self.dataset.patents)})"
            )
        if len(self.dataset.annotations) != self.manifest.annotation_count:
            raise ValueError(
                f"Manifest annotation_count ({self.manifest.annotation_count}) does not match dataset ({len(self.dataset.annotations)})"
            )
        return self
