from domain.models.demand import DemandSignal
from domain.models.matching import EligibilityReason
from domain.models.patent import PatentDocument
from infrastructure.matching.annotation_pool_eligibility import (
    AnnotationPoolEligibilityPolicy,
)


def _patent(publication_date: str | None) -> PatentDocument:
    return PatentDocument(
        publication_id="ES-2001",
        country_code="ES",
        doc_number="2001",
        kind_code="A1",
        title="Biodegradable liquid detergent formulation",
        abstract="Aqueous cleaning composition with biodegradable surfactants.",
        publication_date=publication_date,
    )


def _demand(posted_date: str | None) -> DemandSignal:
    return DemandSignal(
        demand_id="INNOGET-9001",
        title="Seeking biodegradable detergent technology",
        description="Looking for eco-friendly surfactant formulations.",
        posted_date=posted_date,
    )


class AnnotationPoolEligibilityPolicyTest:
    def test_should_mark_eligible_when_both_dates_known_and_patent_predates_demand(self):
        policy = AnnotationPoolEligibilityPolicy()
        result = policy.evaluate(_patent("2021-06-15"), _demand("2022-01-01"))
        assert result.is_eligible is True
        assert result.reason == EligibilityReason.ELIGIBLE

    def test_should_exclude_temporal_when_both_dates_known_and_patent_postdates_demand(self):
        policy = AnnotationPoolEligibilityPolicy()
        result = policy.evaluate(_patent("2023-05-01"), _demand("2022-01-01"))
        assert result.is_eligible is False
        assert result.reason == EligibilityReason.EXCLUDED_TEMPORAL

    def test_should_mark_temporal_unknown_not_excluded_when_demand_posted_date_missing(self):
        policy = AnnotationPoolEligibilityPolicy()
        result = policy.evaluate(_patent("2021-06-15"), _demand(None))
        assert result.is_eligible is True
        assert result.reason == EligibilityReason.TEMPORAL_UNKNOWN

    def test_should_mark_temporal_unknown_not_excluded_when_patent_publication_date_missing(self):
        policy = AnnotationPoolEligibilityPolicy()
        result = policy.evaluate(_patent(None), _demand("2022-01-01"))
        assert result.is_eligible is True
        assert result.reason == EligibilityReason.TEMPORAL_UNKNOWN

    def test_should_still_exclude_wrong_jurisdiction_regardless_of_dates(self):
        policy = AnnotationPoolEligibilityPolicy(target_jurisdiction="ES")
        patent = _patent(None)
        patent = patent.model_copy(update={"country_code": "EP"})
        result = policy.evaluate(patent, _demand(None))
        assert result.is_eligible is False
        assert result.reason == EligibilityReason.EXCLUDED_JURISDICTION

    def test_should_still_exclude_missing_text_regardless_of_dates(self):
        policy = AnnotationPoolEligibilityPolicy()
        patent = _patent(None).model_copy(update={"abstract": ""})
        result = policy.evaluate(patent, _demand(None))
        assert result.is_eligible is False
        assert result.reason == EligibilityReason.EXCLUDED_MISSING_TEXT
