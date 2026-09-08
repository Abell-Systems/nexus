from datetime import date

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import EligibilityReason, EligibilityResult
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentEligibilityPolicy


def _parse_iso_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str.split("T")[0])
    except (ValueError, TypeError):
        return None


class AnnotationPoolEligibilityPolicy(PatentEligibilityPolicy):
    """ADR 0019: eligibility policy for PR-E annotation-pool construction only.

    Distinct from DefaultPatentEligibilityPolicy (live retrieval/matching, which
    this class does not modify or replace): when the demand's posted_date or the
    patent's publication_date is unresolvable, this policy returns
    TEMPORAL_UNKNOWN (is_eligible=True, included in the pool, marked) instead of
    excluding the candidate. UNKNOWN is an eligibility outcome, not an exclusion
    reason (ADR 0019 Decision §2) — it must never be read as, or converted to,
    ELIGIBLE by any downstream code.
    """

    def __init__(self, target_jurisdiction: str = "ES") -> None:
        self.target_jurisdiction = target_jurisdiction.upper()

    def evaluate(
        self,
        patent: PatentDocument,
        demand: DemandRecord | DemandSignal,
    ) -> EligibilityResult:
        pub_id = patent.publication_id

        if not patent.country_code or patent.country_code.upper() != self.target_jurisdiction:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_JURISDICTION,
                details=f"Expected jurisdiction {self.target_jurisdiction}, got '{patent.country_code}'",
            )

        title_clean = patent.title.strip() if patent.title else ""
        abstract_clean = patent.abstract.strip() if patent.abstract else ""
        if not title_clean or not abstract_clean:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_MISSING_TEXT,
                details="Patent must have both non-empty title and abstract",
            )

        demand_date = _parse_iso_date(demand.posted_date)
        pub_date = _parse_iso_date(patent.publication_date)

        if demand_date is None or pub_date is None:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=True,
                reason=EligibilityReason.TEMPORAL_UNKNOWN,
                details=(
                    f"Cannot evaluate t_pub < t_demand: demand.posted_date="
                    f"{demand.posted_date!r}, patent.publication_date={patent.publication_date!r}"
                ),
            )

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
