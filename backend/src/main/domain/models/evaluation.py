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
from datetime import UTC, date, datetime
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
    posted_date: date | None = None
    target_cpc_prefixes: list[str] = Field(default_factory=list)
    provenance: EvaluationProvenance


class EvaluationPatent(BaseModel):
    """Normalized, frozen patent publication record for scientific evaluation."""

    model_config = ConfigDict(frozen=True)

    publication_id: str = Field(min_length=1)
    publication_date: date | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)
    provenance: EvaluationProvenance


class EvaluationAnnotation(BaseModel):
    """Subjective expert label or technical judgement for a demand-patent pair."""

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    grade: RelevanceGrade
    annotator_role: str = Field(min_length=1)
    notes: str = ""
    modality: DataModality


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


class EvaluationExecutionContext(BaseModel):
    """Externalized execution environment context under ADR 0007 §5."""

    model_config = ConfigDict(frozen=True)

    engine_name: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    engine_commit_hash: str = Field(min_length=7, max_length=40)
    execution_timestamp: datetime
    environment: str = Field(min_length=1)

    @field_validator("engine_commit_hash")
    @classmethod
    def validate_commit_hash(cls, v: str) -> str:
        if not re.match(r"^[0-9a-fA-F]{7,40}$", v):
            raise ValueError(f"Invalid git commit hash: '{v}'. Expected 7-40 hexadecimal characters.")
        return v.lower()

    @field_validator("execution_timestamp")
    @classmethod
    def validate_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("execution_timestamp must be timezone-aware (UTC)")
        return v


class MetricSet(BaseModel):
    """Immutable set of standard evaluation metrics under ADR 0007 §4."""

    model_config = ConfigDict(frozen=True)

    precision_at_1: float = Field(ge=0.0, le=1.0)
    precision_at_3: float = Field(ge=0.0, le=1.0)
    precision_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_1: float = Field(ge=0.0, le=1.0)
    recall_at_3: float = Field(ge=0.0, le=1.0)
    recall_at_5: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    mrr_at_5: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float = Field(ge=0.0, le=1.0)
    judged_at_1: float = Field(ge=0.0, le=1.0)
    judged_at_3: float = Field(ge=0.0, le=1.0)
    judged_at_5: float = Field(ge=0.0, le=1.0)


class DemandMetricsReport(BaseModel):
    """Evaluation metrics for a single demand under strict and broad relevance thresholds."""

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    candidate_count: int = Field(ge=0)
    judged_count: int = Field(ge=0)
    uncertain_count: int = Field(ge=0)
    strict_metrics: MetricSet
    broad_metrics: MetricSet


class EvaluationRunReport(BaseModel):
    """Sealed, immutable evaluation report preserving complete provenance and metrics under ADR 0007."""

    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    context: EvaluationExecutionContext
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    dataset_sha256: str = Field(min_length=64, max_length=64)
    policy_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    policy_sha256: str = Field(min_length=64, max_length=64)
    demand_reports: list[DemandMetricsReport]
    macro_strict: MetricSet
    macro_broad: MetricSet
    uncertainty_rate: float = Field(ge=0.0, le=1.0)

    @field_validator("dataset_sha256", "policy_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()


# ---------------------------------------------------------------------------
# Comparative Evaluation Domain Models (ADR 0011)
# ---------------------------------------------------------------------------

_VALID_SCOPES = {"strict", "broad"}
_VALID_ALTERNATIVES = {"greater", "less", "two-sided"}


class StudyHypothesis(BaseModel):
    """Pre-registered hypothesis for a single pairwise comparative test (ADR 0011 §2).

    Invariants:
    - scope must be 'strict' or 'broad' (maps to evaluation metric thresholds).
    - alternative must be one of 'greater', 'less', 'two-sided'.
    - All fields are fixed at registration time and must not change after protocol sealing.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    baseline: str = Field(min_length=1)
    treatment: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    scope: str
    alternative: str
    description: str = ""

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, v: str) -> str:
        if v not in _VALID_SCOPES:
            raise ValueError(f"Invalid scope '{v}'. Must be one of {sorted(_VALID_SCOPES)}")
        return v

    @field_validator("alternative")
    @classmethod
    def validate_alternative(cls, v: str) -> str:
        if v not in _VALID_ALTERNATIVES:
            raise ValueError(f"Invalid alternative '{v}'. Must be one of {sorted(_VALID_ALTERNATIVES)}")
        return v


class StudyProtocol(BaseModel):
    """Sealed, versioned pre-registration of comparative study parameters (ADR 0011 §2).

    Invariants:
    - At least one hypothesis must be registered.
    - protocol_sha256 must be a 64-character hex digest.
    - alpha, bootstrap_confidence_level, and seed are fixed at registration.
    """

    model_config = ConfigDict(frozen=True)

    study_id: str = Field(min_length=1)
    study_version: str = Field(min_length=1)
    protocol_sha256: str = Field(min_length=64, max_length=64)
    alpha: float = Field(gt=0.0, lt=1.0)
    multiple_testing_method: str = Field(min_length=1)
    bootstrap_iterations: int = Field(ge=100)
    bootstrap_confidence_level: float = Field(gt=0.0, lt=1.0)
    seed: int
    hypotheses: list[StudyHypothesis] = Field(min_length=1)

    @field_validator("protocol_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()


class HypothesisTestResult(BaseModel):
    """Statistical test outcome for a single pre-registered hypothesis (ADR 0011 §3).

    Carries the raw Wilcoxon result, paired bootstrap CI, BH-adjusted q-value, and
    rejection decision. Wraps PR #22 frozen dataclasses by reference; no re-wrapping.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    hypothesis_id: str = Field(min_length=1)
    baseline: str = Field(min_length=1)
    treatment: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    scope: str
    wilcoxon: object  # WilcoxonResult (PR #22 frozen dataclass)
    bootstrap_ci: object  # BootstrapCIResult (PR #22 frozen dataclass)
    adjusted_q_value: float = Field(ge=0.0, le=1.0)
    rejected: bool


class ComparativeRunReport(BaseModel):
    """Sealed comparative evaluation report preserving full protocol provenance chain.

    Invariants under ADR 0011 §4:
    - study_protocol_id and study_protocol_sha256 link report to pre-registered protocol.
    - study_status distinguishes PILOT runs from final frozen evaluations.
    - run_ids maps model labels to their individual EvaluationRunReport.run_id.
    """

    model_config = ConfigDict(frozen=True)

    study_protocol_id: str = Field(min_length=1)
    study_protocol_sha256: str = Field(min_length=64, max_length=64)
    study_status: str  # "PILOT" or "FINAL"
    run_ids: dict[str, str]  # model_label -> run_id
    results: list[HypothesisTestResult]

    @field_validator("study_protocol_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()

    @field_validator("study_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in {"PILOT", "FINAL"}:
            raise ValueError(f"Invalid study_status '{v}'. Must be 'PILOT' or 'FINAL'")
        return v
