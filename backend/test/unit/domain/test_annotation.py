import pytest
from pydantic import ValidationError

from domain.models.annotation import AnnotationJudgment, ConstructEligibilityRubric, RubricValue
from domain.models.evaluation import RelevanceGrade


class AnnotationJudgmentTest:
    def test_should_construct_with_valid_ordinal_grade(self):
        judgment = AnnotationJudgment(
            demand_id="INNOGET-1605",
            publication_id="ES-3001",
            annotator_id="valentin",
            grade=RelevanceGrade.GRADE_2,
        )
        assert judgment.grade == RelevanceGrade.GRADE_2
        assert judgment.annotator_id == "valentin"

    def test_should_reject_uncertain_grade(self):
        with pytest.raises(ValidationError, match="UNCERTAIN"):
            AnnotationJudgment(
                demand_id="INNOGET-1605",
                publication_id="ES-3001",
                annotator_id="valentin",
                grade=RelevanceGrade.UNCERTAIN,
            )

    def test_should_reject_empty_annotator_id(self):
        with pytest.raises(ValidationError):
            AnnotationJudgment(
                demand_id="INNOGET-1605",
                publication_id="ES-3001",
                annotator_id="",
                grade=RelevanceGrade.GRADE_0,
            )

    def test_should_default_notes_to_empty_string(self):
        judgment = AnnotationJudgment(
            demand_id="INNOGET-1605",
            publication_id="ES-3001",
            annotator_id="lydia",
            grade=RelevanceGrade.GRADE_0,
        )
        assert judgment.notes == ""


class ConstructEligibilityRubricTest:
    def test_should_construct_with_valid_rubric_values(self):
        rubric = ConstructEligibilityRubric(
            technical_problem_present=RubricValue.YES,
            technology_solution_requested=RubricValue.YES,
            technical_specification_present=RubricValue.YES,
            exclusion_criterion_1=RubricValue.NO,
        )
        assert rubric.technical_problem_present == RubricValue.YES
        assert rubric.exclusion_criterion_1 == RubricValue.NO

    def test_should_be_frozen(self):
        rubric = ConstructEligibilityRubric(
            technical_problem_present=RubricValue.YES,
            technology_solution_requested=RubricValue.YES,
            technical_specification_present=RubricValue.YES,
            exclusion_criterion_1=RubricValue.NO,
        )
        with pytest.raises(ValidationError):
            rubric.exclusion_criterion_1 = RubricValue.YES
