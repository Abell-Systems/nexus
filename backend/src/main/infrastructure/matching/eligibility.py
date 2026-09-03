from datetime import date

from domain.models.demand import DemandSignal
from domain.models.matching import (
    EligibilityReason,
    EligibilityResult,
)
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentEligibilityPolicy


def _parse_iso_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        # Accepts YYYY-MM-DD or ISO timestamp
        return date.fromisoformat(date_str.split("T")[0])
    except (ValueError, TypeError):
        return None


class DefaultPatentEligibilityPolicy(PatentEligibilityPolicy):
    """Enforces jurisdiction, text availability, and temporal prior-art eligibility."""

    def __init__(self, target_jurisdiction: str = "ES") -> None:
        self.target_jurisdiction = target_jurisdiction.upper()

    def evaluate(
        self,
        patent: PatentDocument,
        demand: DemandSignal,
    ) -> EligibilityResult:
        pub_id = patent.publication_id

        # 1. Jurisdiction Check
        if not patent.country_code or patent.country_code.upper() != self.target_jurisdiction:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_JURISDICTION,
                details=f"Expected jurisdiction {self.target_jurisdiction}, got '{patent.country_code}'",
            )

        # 2. Text Availability Check (Both Title and Abstract must be present and non-empty)
        title_clean = patent.title.strip() if patent.title else ""
        abstract_clean = patent.abstract.strip() if patent.abstract else ""
        if not title_clean or not abstract_clean:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_MISSING_TEXT,
                details="Patent must have both non-empty title and abstract",
            )

        # 3. Temporal Eligibility Check: publication_date < demand.posted_date
        demand_date = _parse_iso_date(demand.posted_date)
        if not demand_date:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_TEMPORAL,
                details=f"Demand missing valid posted_date: '{demand.posted_date}'",
            )

        pub_date = _parse_iso_date(patent.publication_date)
        if not pub_date:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_TEMPORAL,
                details=f"Patent missing valid publication_date: '{patent.publication_date}'",
            )

        # Strict inequality: t_pub < t_demand
        if pub_date >= demand_date:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_TEMPORAL,
                details=f"Publication date {pub_date} is not strictly prior to demand date {demand_date}",
            )

        return EligibilityResult(
            publication_id=pub_id,
            is_eligible=True,
            reason=EligibilityReason.ELIGIBLE,
            details=f"Eligible: {pub_date} < {demand_date}",
        )
