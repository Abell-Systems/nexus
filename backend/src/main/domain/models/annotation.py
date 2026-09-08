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
