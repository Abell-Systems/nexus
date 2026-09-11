from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain.models.evaluation import RelevanceGrade


class AnnotationJudgment(BaseModel):
    """A single annotator's independent relevance judgment for one demand-patent
    pair, before any fusion, adjudication, or consolidation into a dataset (PR-E
    spec §5, non-negotiable statement 2: annotation judgments cannot alter pool
    membership). Distinct from EvaluationAnnotation (domain/models/evaluation.py),
    which represents an already-consolidated dataset annotation, not an
    individual annotator's raw independent judgment.
    """

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    annotator_id: str = Field(min_length=1)
    grade: RelevanceGrade
    notes: str = ""

    @model_validator(mode="after")
    def validate_grade_is_ordinal(self) -> "AnnotationJudgment":
        if self.grade == RelevanceGrade.UNCERTAIN:
            raise ValueError(
                "AnnotationJudgment.grade must be in {0,1,2,3} — "
                "RelevanceGrade.UNCERTAIN is not a valid PR-E dry-run grade"
            )
        return self


class RubricValue(StrEnum):
    """A single construct-eligibility rubric field's judged value (protocol
    §4.1). Domain owns this closed set — it is a property of the audit
    instrument itself, not of any particular experimental run."""

    YES = "yes"
    NO = "no"
    INDETERMINATE = "indeterminate"


class ConstructEligibilityStatus(StrEnum):
    """Outcome of the protocol §4.1 construct-eligibility decision rule."""

    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNCERTAIN = "UNCERTAIN"


class ConstructEligibilityRubric(BaseModel):
    """Structural shape of a demand construct-eligibility rubric (protocol
    §4.1). Domain owns the four-field shape and the closed value set; it does
    not know any particular demand's judged values — those are experiment
    observations (see experiments/wpi-demand-patent-matching/data/)."""

    model_config = ConfigDict(frozen=True)

    technical_problem_present: RubricValue
    technology_solution_requested: RubricValue
    technical_specification_present: RubricValue
    exclusion_criterion_1: RubricValue


class DemandIndependenceStatus(StrEnum):
    """Outcome of the demand-independence grouping decision (ADR 0029,
    docs/phase2-demand-independence-audit-protocol.md)."""

    INDEPENDENT = "INDEPENDENT"
    PSEUDOREPLICATE = "PSEUDOREPLICATE"


class DemandOrganizationObservation(BaseModel):
    """One demand's observed requesting-organization identity, as extracted at
    acquisition time (domain.models.demand.RawExtractedDemandFields.organization_raw
    / DemandRecord.requesting_organization) -- never inferred at audit time. The
    sole basis this domain currently supports for grouping demands into
    independence clusters is an exact string match on this field. A text- or
    name-similarity heuristic (e.g. matching "Bax & Company" to "Indira from
    Bax&Co" as the same entity) is explicitly out of scope -- see ADR 0029
    Context, which rejects it for the same circularity reason ADR 0027 rejected
    heuristic patent-family detection: any similarity signal strong enough to
    merge near-duplicate names is also a signal that could correlate with the
    relevance judgments this dataset exists to evaluate honestly.
    """

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    requesting_organization: str | None = None


class DemandIndependenceGroupEntry(BaseModel):
    """Outcome of the demand-independence grouping decision for one demand
    (ADR 0029). `independence_group_id` is the exact `requesting_organization`
    string when the demand was assigned to a group; `None` when the demand's
    organization is missing or was excluded as a known non-identifying
    placeholder (e.g. "Anonymous Organization") -- such a demand is always
    INDEPENDENT and is never grouped with any other demand, including another
    demand that also has `independence_group_id=None`.
    """

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    requesting_organization: str | None = None
    independence_group_id: str | None = None
    status: DemandIndependenceStatus
