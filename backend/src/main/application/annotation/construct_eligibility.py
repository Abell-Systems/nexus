from domain.models.annotation import ConstructEligibilityRubric, ConstructEligibilityStatus, RubricValue


def derive_construct_status(rubric: ConstructEligibilityRubric) -> ConstructEligibilityStatus:
    """Protocol §4.1's construct-eligibility decision rule, as a pure function
    of the rubric. This is the only place the rule is implemented — any
    construct-eligibility audit derives its status here rather than recording
    it as an independent, unverified judgment."""
    values = (
        rubric.technical_problem_present,
        rubric.technology_solution_requested,
        rubric.technical_specification_present,
        rubric.exclusion_criterion_1,
    )
    if RubricValue.INDETERMINATE in values:
        return ConstructEligibilityStatus.UNCERTAIN
    if (
        rubric.exclusion_criterion_1 == RubricValue.YES
        or rubric.technical_problem_present == RubricValue.NO
        or rubric.technology_solution_requested == RubricValue.NO
        or rubric.technical_specification_present == RubricValue.NO
    ):
        return ConstructEligibilityStatus.INELIGIBLE
    return ConstructEligibilityStatus.ELIGIBLE
