import itertools

from application.annotation.construct_eligibility import derive_construct_status
from domain.models.annotation import ConstructEligibilityRubric, ConstructEligibilityStatus, RubricValue


def _rubric(problem, solution, spec, exclusion) -> ConstructEligibilityRubric:
    return ConstructEligibilityRubric(
        technical_problem_present=problem,
        technology_solution_requested=solution,
        technical_specification_present=spec,
        exclusion_criterion_1=exclusion,
    )


class DeriveConstructStatusTest:
    def test_should_return_uncertain_when_any_field_is_indeterminate(self):
        rubric = _rubric(
            RubricValue.INDETERMINATE, RubricValue.YES, RubricValue.YES, RubricValue.NO
        )
        assert derive_construct_status(rubric) == ConstructEligibilityStatus.UNCERTAIN

    def test_should_return_ineligible_when_exclusion_criterion_is_yes(self):
        rubric = _rubric(RubricValue.YES, RubricValue.YES, RubricValue.YES, RubricValue.YES)
        assert derive_construct_status(rubric) == ConstructEligibilityStatus.INELIGIBLE

    def test_should_return_ineligible_when_technical_problem_absent(self):
        rubric = _rubric(RubricValue.NO, RubricValue.YES, RubricValue.YES, RubricValue.NO)
        assert derive_construct_status(rubric) == ConstructEligibilityStatus.INELIGIBLE

    def test_should_return_eligible_when_all_required_fields_are_yes_and_no_exclusion(self):
        rubric = _rubric(RubricValue.YES, RubricValue.YES, RubricValue.YES, RubricValue.NO)
        assert derive_construct_status(rubric) == ConstructEligibilityStatus.ELIGIBLE

    def test_should_be_exhaustively_consistent_with_the_decision_rule_over_every_combination(self):
        """Given ANY rubric — not a specific experiment's data — the derived
        status matches protocol §4.1's decision rule exactly."""
        for problem, solution, spec, exclusion in itertools.product(RubricValue, repeat=4):
            rubric = _rubric(problem, solution, spec, exclusion)
            status = derive_construct_status(rubric)

            if RubricValue.INDETERMINATE in (problem, solution, spec, exclusion):
                assert status == ConstructEligibilityStatus.UNCERTAIN
            elif (
                exclusion == RubricValue.YES
                or problem == RubricValue.NO
                or solution == RubricValue.NO
                or spec == RubricValue.NO
            ):
                assert status == ConstructEligibilityStatus.INELIGIBLE
            else:
                assert status == ConstructEligibilityStatus.ELIGIBLE
