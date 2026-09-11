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

import math
import re
from datetime import UTC, date, datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from domain.models.demand import SpanishOriginLevel


class _HasPolicySha256(Protocol):
    """Structural type for verify_source_policy — matched by MatchingPolicyConfig
    without importing domain.models.matching, which the evaluation-adapter-boundary
    Import Linter contract forbids outside application.evaluation.matching_adapter."""

    policy_sha256: str


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
    # ADR 0027: externally-supplied patent-family identifier (e.g. from a future
    # INPADOC/OPS-backed corpus source). None means "no family metadata available
    # for this publication" -- this field is NEVER inferred here from title, CPC,
    # or assignee similarity; only ever accepted as given on the sealed dataset.
    family_id: str | None = None


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


class DemandCorpusItem(BaseModel):
    """Frozen demand record for the pre-patent-pairing acquisition stage, WITH the
    origin evidence that determines its inclusion (unlike EvaluationDemand, whose
    contract assumes origin was already verified out-of-band by the time a full
    EvaluationDataset with patents/annotations is assembled).

    A DemandCorpus's eligibility criterion IS Spanish origin; the record proving that
    (spanish_origin_level, origin_country, and the external_reference used to resolve
    it, where one exists) must be checkable from the frozen artifact itself, not only
    from a separate audit sidecar.
    """

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    posted_date: date | None = None
    target_cpc_prefixes: list[str] = Field(default_factory=list)
    origin_country: str | None = None
    spanish_origin_level: SpanishOriginLevel
    external_reference: str | None = None
    provenance: EvaluationProvenance

    @field_validator("spanish_origin_level")
    @classmethod
    def validate_target_origin(cls, v: SpanishOriginLevel) -> SpanishOriginLevel:
        target_levels = {
            SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
            SpanishOriginLevel.LEVEL_2_ORGANIZATION_METADATA,
            SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK,
        }
        if v not in target_levels:
            raise ValueError(
                f"DemandCorpus requires Spanish target-origin demands only; got spanish_origin_level={v.value}"
            )
        return v


class DemandCorpus(BaseModel):
    """Frozen demand-only corpus for the pre-patent-pairing acquisition stage.

    Distinct from EvaluationDataset (which requires a non-empty patent corpus and
    annotations): this represents the state immediately after demand acquisition and
    content/origin verification, before candidate generation or annotation exist.
    """

    model_config = ConfigDict(frozen=True)

    dataset_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    demands: list[DemandCorpusItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_demand_ids(self) -> "DemandCorpus":
        seen: set[str] = set()
        for d in self.demands:
            if d.demand_id in seen:
                raise ValueError(f"Duplicate demand_id in corpus: {d.demand_id}")
            seen.add(d.demand_id)
        return self


class PatentCorpusItem(BaseModel):
    """Frozen patent record for the demand-blind patent-side experimental artifact (ADR 0020).

    Field set matches PatentDocument's core retrieval/eligibility-relevant fields, not its
    full shape (ADR 0020 §5 explicitly does not require reusing PatentDocument's exact
    schema) -- enough for a later PR-E1 step to map 1:1 into PatentDocument for retrieval.
    """

    model_config = ConfigDict(frozen=True)

    publication_id: str = Field(min_length=1)
    country_code: str = Field(min_length=2, max_length=2)
    kind_code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)
    publication_date: str | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    provenance: EvaluationProvenance


class PatentCorpus(BaseModel):
    """Frozen, demand-blind patent corpus (ADR 0020's `P`).

    Composition is fixed by jurisdiction + grant + temporal-window inclusion contract
    (ADR 0020 §2) and sha256(publication_id)-order selection (ADR 0020 §3) -- never by
    any demand-side property. See scripts/freeze_patent_corpus.py for the construction
    pipeline that produces this artifact.
    """

    model_config = ConfigDict(frozen=True)

    dataset_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    patents: list[PatentCorpusItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_publication_ids(self) -> "PatentCorpus":
        seen: set[str] = set()
        for p in self.patents:
            if p.publication_id in seen:
                raise ValueError(f"Duplicate publication_id in corpus: {p.publication_id}")
            seen.add(p.publication_id)
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
    # ADR 0018: which Φ_temporal pool-eligibility regime this run used. Mandatory,
    # no default (ADR 0005 explicit-injection) — never inferred from a CLI flag or
    # implicit filtering. "strict" excludes temporally-ineligible patents from the
    # pool before ranking; "unconstrained" keeps the full universe (pre-ADR-0018
    # behavior) and must be paired with require_temporal_validity=False by the
    # caller (see application.evaluation.runner.validate_temporal_pool_mode_consistency).
    temporal_pool_mode: Literal["strict", "unconstrained"]
    # ADR 0027: family-aware evaluation policy. Mandatory, no default (ADR 0005
    # explicit-injection principle, same as temporal_pool_mode / ADR 0018).
    # "allow": no family-based collapsing/exclusion (pre-ADR-0027 baseline).
    # "collapse": pool is reduced to one representative per family_id before ranking.
    # "exclude_related": every patent in a multi-member family is dropped before ranking.
    family_policy: Literal["allow", "collapse", "exclude_related"]

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
    """Immutable set of standard evaluation metrics under ADR 0007 §4.

    Recall@K and nDCG@K are None exactly when undefined (zero relevant items /
    IDCG == 0): the protocol excludes such demands from macro averages instead of
    imputing values (PR #44, docs/metrics-endpoint-alignment.md). nDCG@10 is the
    primary endpoint metric (protocol §7); MRR stays secondary.
    """

    model_config = ConfigDict(frozen=True)

    precision_at_1: float = Field(ge=0.0, le=1.0)
    precision_at_3: float = Field(ge=0.0, le=1.0)
    precision_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_1: float | None = Field(default=None, ge=0.0, le=1.0)
    recall_at_3: float | None = Field(default=None, ge=0.0, le=1.0)
    recall_at_5: float | None = Field(default=None, ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    mrr_at_5: float = Field(ge=0.0, le=1.0)
    ndcg_at_5: float | None = Field(default=None, ge=0.0, le=1.0)
    ndcg_at_10: float | None = Field(default=None, ge=0.0, le=1.0)
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
    # Explicit per-demand nDCG validity (IDCG > 0): mirrors the None-ness of the
    # nDCG fields so exclusion from macro averages stays auditable per demand.
    has_relevant_judged: bool
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
    # Explicit macro denominators (PR #44): metric field name → number of valid
    # (non-None) per-demand observations averaged into the corresponding macro value.
    # Excluded demands per metric = len(demand_reports) - macro_denominators[metric].
    macro_denominators: dict[str, int]
    uncertainty_rate: float = Field(ge=0.0, le=1.0)
    # ADR 0027: whether every patent in this run's sealed universe carried family_id.
    # Recorded unconditionally (even under family_policy="allow") so the audit trail
    # is honest about whether a family-sensitive policy could have been requested.
    family_metadata_complete: bool
    # ADR 0028: fixed identifier for how this run's Recall/nDCG denominators were
    # computed. Always "eligible_universe_v1" for any run produced by this codebase's
    # current DefaultEvaluationRunner -- never caller-selected, never a policy choice.
    # Its purpose is comparative safety: a frozen pre-ADR-0028 EvaluationRunReport
    # (e.g. data/experiments/m0_run_report.json) has no such field and therefore
    # fails to parse as this model at all, which is the correct, honest outcome --
    # it must never be silently paired against a post-fix run (see comparative.py's
    # guard, Task 2 of the eligible-universe-denominators plan).
    denominator_semantics: Literal["eligible_universe_v1"]

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
    wilcoxon: "object"  # WilcoxonResult (PR #22 frozen dataclass)
    bootstrap_ci: "object"  # BootstrapCIResult (PR #22 frozen dataclass)
    adjusted_q_value: float = Field(ge=0.0, le=1.0)
    rejected: bool
    # Paired-observation accounting (PR #44): demands excluded from this hypothesis
    # because the metric was undefined (None) on either side, and the resulting n.
    n_paired: int = Field(ge=0)
    excluded_demand_ids: list[str] = Field(default_factory=list)


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


# ---------------------------------------------------------------------------
# Frozen Model Configuration Provenance (ADR 0012)
# ---------------------------------------------------------------------------

ProvenanceStatus = Literal[
    "PRE_EXISTING_INITIAL_CONFIGURATION",
    "INHERITED",
    "DERIVED",
]

TuningStatus = Literal["NOT_TUNED_NO_INDEPENDENT_DEV_SET"]


class FusionTransformRecord(BaseModel):
    """Pre-registered score-space fusion transform (ADR 0016 §4).

    Records the exact functional form mapping heterogeneous raw ranking features
    into [0, 1] before the convex combination in DefaultEvidenceEvaluator. Fixed
    ex ante; changing any field defines a new transform_id, never an edit.
    """

    model_config = ConfigDict(frozen=True)

    transform_id: str = Field(min_length=1)
    f_lex: str = Field(min_length=1)
    f_lex_k: float = Field(gt=0.0)
    f_sem: str = Field(min_length=1)
    applied_at: str = Field(min_length=1)
    adr: str = Field(min_length=1)


class ModelConfigurationRecord(BaseModel):
    """Frozen, provenance-tagged configuration for a single M0-M6 model variant (ADR 0012).

    provenance_status is closed by the ProvenanceStatus Literal: TUNED / OPTIMIZED /
    VALIDATED cannot be expressed, because no hyperparameter search process exists
    in this codebase to justify those claims.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    ranker: str = Field(min_length=1)
    weights: dict[str, float] | None = None
    version: str = Field(min_length=1)
    provenance_status: ProvenanceStatus
    fusion_transform: FusionTransformRecord | None = None


class SourcePolicyReference(BaseModel):
    """Points to the exact matching policy version a configuration freeze was derived from.

    A manifest's own config_sha256 proves internal self-consistency; it says nothing
    about whether the weights it recorded still match the matching policy it was
    derived from, after that policy legitimately changes for unrelated reasons
    months later. source_policy makes that cross-file provenance explicit and
    checkable via ModelConfigurationManifest.verify_source_policy.
    """

    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    policy_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("policy_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()


class ModelConfigurationManifest(BaseModel):
    """Integrity-checked freeze record for M0-M6 configurations (ADR 0012).

    config_sha256 is self-referential (verified against the rest of the payload on
    load, same pattern as MatchingPolicyConfig.policy_sha256 in domain/models/matching.py).
    This is tamper-evidence, not a cryptographic seal — it detects accidental drift,
    not deliberate edits made by someone who also updates the hash. The real freeze
    guarantee comes from Git history and PR review.
    """

    model_config = ConfigDict(frozen=True)

    study_id: str = Field(min_length=1)
    frozen_at: date
    tuning_status: TuningStatus
    development_set: str | None
    source_policy: SourcePolicyReference
    models: list[ModelConfigurationRecord] = Field(min_length=1)
    config_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("config_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()

    def verify_source_policy(self, policy: _HasPolicySha256) -> None:
        """Fails fast if the given, already-loaded policy no longer matches this freeze.

        Takes an already-loaded policy object (structurally typed — see
        _HasPolicySha256, matched by MatchingPolicyConfig) rather than a path: this
        manifest stays CWD-independent and does no filesystem discovery of its own,
        matching the explicit-path-injection invariant already established for
        dataset loading (ADR 0006) — callers load the policy explicitly and hand it
        over. It also keeps this module free of importing domain.models.matching,
        which the evaluation-adapter-boundary Import Linter contract restricts to
        application.evaluation.matching_adapter alone.
        """
        if policy.policy_sha256 != self.source_policy.policy_sha256:
            raise ValueError(
                f"Source policy drift detected for manifest '{self.study_id}': "
                f"declares source_policy.policy_sha256={self.source_policy.policy_sha256}, "
                f"but the loaded policy has policy_sha256={policy.policy_sha256}. "
                f"This freeze (ADR 0012) no longer matches the policy it was derived from."
            )

    @classmethod
    def load_from_json(cls, file_path: str | Path) -> "ModelConfigurationManifest":
        import hashlib
        import json as _json

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model configuration manifest not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = _json.load(f)

        declared_sha = data.pop("config_sha256", None)
        if not declared_sha:
            raise ValueError(
                f"Cryptographic integrity verification failed for {path}: "
                f"missing mandatory declared 'config_sha256'"
            )

        canonical_bytes = _json.dumps(data, sort_keys=True, indent=2).encode("utf-8")
        computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

        if declared_sha.lower() != computed_sha.lower():
            raise ValueError(
                f"Cryptographic integrity verification failed for {path}: "
                f"declared {declared_sha}, computed {computed_sha}"
            )

        data["config_sha256"] = computed_sha
        return cls(**data)


# ---------------------------------------------------------------------------
# Frozen M1 Semantic Embedding Artifact (ADR 0014)
# ---------------------------------------------------------------------------


class FrozenEmbeddingArtifact(BaseModel):
    """Frozen, provenance-sealed M1 semantic embedding artifact (ADR 0014).

    demand_embeddings/patent_embeddings are keyed by the sealed dataset's own
    demand_id/publication_id — no separate id-list fields, since a list that could
    drift from the embeddings dict is exactly the kind of authority-inversion bug
    ADR 0012/PR #29 found for M0 (a value that could silently disagree with what's
    actually used). n_demands/n_patents are likewise derived from dict length, not
    stored, for the same reason.

    artifact_sha256 is self-referential (tamper-evidence, not a cryptographic seal —
    same pattern as ModelConfigurationManifest.config_sha256). dataset_sha256 ties
    this artifact to the exact sealed dataset it was derived from; verify_source_dataset
    checks both facts against an already-loaded ValidatedDataset, mirroring
    ModelConfigurationManifest.verify_source_policy's explicit-injection pattern.
    """

    model_config = ConfigDict(frozen=True)

    artifact_id: str = Field(min_length=1)
    frozen_at: date
    model_name: str = Field(min_length=1)
    model_revision: str = Field(min_length=40, max_length=40)
    license: str = Field(min_length=1)
    generation_script_path: str = Field(min_length=1)
    generation_script_commit: str = Field(min_length=7, max_length=40)
    library_versions: dict[str, str] = Field(min_length=1)
    generation_device: Literal["cpu"]
    dataset_sha256: str = Field(min_length=64, max_length=64)
    embedding_dimension: int = Field(gt=0)
    normalization: str = Field(min_length=1)
    similarity_metric: str = Field(min_length=1)
    demand_embeddings: dict[str, list[float]] = Field(min_length=1)
    patent_embeddings: dict[str, list[float]] = Field(min_length=1)
    artifact_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("model_revision")
    @classmethod
    def validate_revision_hex(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{40}$", v.lower()):
            raise ValueError(f"Invalid model_revision '{v}': expected exactly 40 hex characters (a full git SHA)")
        return v.lower()

    @field_validator("generation_script_commit")
    @classmethod
    def validate_commit_hash(cls, v: str) -> str:
        if not re.match(r"^[0-9a-fA-F]{7,40}$", v):
            raise ValueError(f"Invalid generation_script_commit '{v}': expected 7-40 hexadecimal characters")
        return v.lower()

    @field_validator("dataset_sha256", "artifact_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()

    @model_validator(mode="after")
    def validate_embedding_invariants(self) -> "FrozenEmbeddingArtifact":
        """Enforces the vector-shape invariants ADR 0014 §8-9 freeze: exact dimension,
        no NaN/inf components, and L2 normalization. These are science invariants, not
        an optimization — a vector with the right length but non-finite components or
        the wrong norm is not a valid observation of what this artifact declares itself
        to be, and must fail here rather than reach cosine-similarity computation later.
        """
        for space_name, space in (
            ("demand", self.demand_embeddings),
            ("patent", self.patent_embeddings),
        ):
            for key, vector in space.items():
                if len(vector) != self.embedding_dimension:
                    raise ValueError(
                        f"{space_name} embedding '{key}' has dimension {len(vector)}, "
                        f"expected embedding_dimension={self.embedding_dimension}"
                    )
                if not all(math.isfinite(x) for x in vector):
                    raise ValueError(
                        f"{space_name} embedding '{key}' contains a non-finite value (NaN/inf) — "
                        f"invalid under ADR 0014's frozen encoding procedure"
                    )
                norm = math.sqrt(sum(x * x for x in vector))
                if abs(norm - 1.0) > 1e-3:
                    raise ValueError(
                        f"{space_name} embedding '{key}' has L2 norm {norm:.6f}, expected ≈1.0 — "
                        f"ADR 0014 §9 requires L2-normalized embeddings"
                    )
        return self

    def verify_source_dataset(self, validated_dataset: ValidatedDataset) -> None:
        """Fails fast if this artifact no longer matches the sealed dataset it declares.

        Checks both the dataset's content hash (ADR 0006) and the exact identifier sets —
        an artifact whose dataset_sha256 matches but whose embedded ids are a stale subset
        (or superset) of the current dataset would otherwise pass a hash-only check.
        """
        if self.dataset_sha256 != validated_dataset.manifest.content_sha256:
            raise ValueError(
                f"Source dataset drift detected for artifact '{self.artifact_id}': "
                f"declares dataset_sha256={self.dataset_sha256}, but the loaded dataset "
                f"has content_sha256={validated_dataset.manifest.content_sha256}. "
                f"This artifact (ADR 0014) no longer matches the dataset it was derived from."
            )

        actual_demand_ids = {d.demand_id for d in validated_dataset.dataset.demands}
        actual_patent_ids = {p.publication_id for p in validated_dataset.dataset.patents}

        if set(self.demand_embeddings.keys()) != actual_demand_ids:
            raise ValueError(
                f"Artifact '{self.artifact_id}' demand_embeddings keys "
                f"{sorted(self.demand_embeddings.keys())} do not exactly match the sealed "
                f"dataset's demand_ids {sorted(actual_demand_ids)}"
            )
        if set(self.patent_embeddings.keys()) != actual_patent_ids:
            raise ValueError(
                f"Artifact '{self.artifact_id}' patent_embeddings keys "
                f"{sorted(self.patent_embeddings.keys())} do not exactly match the sealed "
                f"dataset's publication_ids {sorted(actual_patent_ids)}"
            )

    @classmethod
    def load_from_json(cls, file_path: str | Path) -> "FrozenEmbeddingArtifact":
        import hashlib
        import json as _json

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Frozen embedding artifact not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = _json.load(f)

        declared_sha = data.pop("artifact_sha256", None)
        if not declared_sha:
            raise ValueError(
                f"Cryptographic integrity verification failed for {path}: "
                f"missing mandatory declared 'artifact_sha256'"
            )

        canonical_bytes = _json.dumps(data, sort_keys=True, indent=2).encode("utf-8")
        computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

        if declared_sha.lower() != computed_sha.lower():
            raise ValueError(
                f"Cryptographic integrity verification failed for {path}: "
                f"declared {declared_sha}, computed {computed_sha}"
            )

        data["artifact_sha256"] = computed_sha
        return cls(**data)


# ---------------------------------------------------------------------------
# Stratified Dev/Test Split Models (Issue #79)
# ---------------------------------------------------------------------------


class DevPartition(BaseModel):
    """Frozen membership set for a Development split (protocol §3 D_dev). A future
    tuning component (ADR 0016 alpha/beta/gamma grid search) must be constructible
    only from this type -- never from TestPartition or an undivided corpus -- so
    that no-leakage is an interface property, not only a test (see
    docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md).
    """

    model_config = ConfigDict(frozen=True)

    demand_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("demand_ids")
    @classmethod
    def validate_unique(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if len(v) != len(set(v)):
            raise ValueError("DevPartition.demand_ids must not contain duplicates")
        return v


class TestPartition(BaseModel):
    """Mirror of DevPartition for the Test split (protocol §3 D_test)."""

    __test__ = False  # not a pytest test class despite the name

    model_config = ConfigDict(frozen=True)

    demand_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("demand_ids")
    @classmethod
    def validate_unique(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if len(v) != len(set(v)):
            raise ValueError("TestPartition.demand_ids must not contain duplicates")
        return v
