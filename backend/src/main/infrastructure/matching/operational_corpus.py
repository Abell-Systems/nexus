from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import EligibilityReason, EligibilityResult
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentEligibilityPolicy

_REQUIRED = ["publication_number", "country_code", "kind_code", "title", "abstract", "publication_date"]
_OPTIONAL = ["ip_type", "abstract_language", "assignees", "inventors", "cpc_codes", "filing_date", "family_id"]
OPERATIONAL_JURISDICTION = "ES"


class OperationalEligibilityPolicy(PatentEligibilityPolicy):
    """Which Spanish assets of the operational corpus are candidates for a demand.

    Jurisdiction ES AND non-empty title AND non-empty abstract, nothing else. The temporal prior-art rule
    belongs to the Lab's DefaultPatentEligibilityPolicy and is deliberately not part of this policy
    (retrieval spec, Amendment A1): it answers a different question, and the demand corpus has no dates.
    """

    def evaluate(self, patent: PatentDocument, demand: DemandRecord | DemandSignal) -> EligibilityResult:
        pub_id = patent.publication_id
        if (patent.country_code or "").upper() != OPERATIONAL_JURISDICTION:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_JURISDICTION,
                details=f"Expected jurisdiction {OPERATIONAL_JURISDICTION}, got '{patent.country_code}'",
            )
        if not (patent.title or "").strip() or not (patent.abstract or "").strip():
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_MISSING_TEXT,
                details="Asset must have both non-empty title and abstract",
            )
        return EligibilityResult(publication_id=pub_id, is_eligible=True, reason=EligibilityReason.ELIGIBLE)


def operational_eligibility_policy() -> OperationalEligibilityPolicy:
    """The single place the operational eligibility rule is obtained (API and probe builder)."""
    return OperationalEligibilityPolicy()


@dataclass(frozen=True)
class OperationalAsset:
    patent: PatentDocument
    ip_type: str
    abstract_language: str


def load_operational_assets(parquet_path: Path) -> list[OperationalAsset]:
    """Loads the operational corpus snapshot, preserving parquet row order."""
    available = set(pq.read_schema(parquet_path).names)
    columns = _REQUIRED + [c for c in _OPTIONAL if c in available]
    rows = pq.read_table(parquet_path, columns=columns).to_pylist()
    assets: list[OperationalAsset] = []
    for row in rows:
        publication_id = str(row["publication_number"])
        parts = publication_id.split("-")
        patent = PatentDocument(
            publication_id=publication_id,
            country_code=str(row["country_code"] or ""),
            doc_number=parts[1] if len(parts) > 1 else "",
            kind_code=str(row["kind_code"] or ""),
            title=str(row["title"] or ""),
            abstract=str(row["abstract"] or ""),
            publication_date=str(row["publication_date"]) if row["publication_date"] else None,
            assignees=list(row.get("assignees") or []),
            inventors=list(row.get("inventors") or []),
            classifications_cpc=list(row.get("cpc_codes") or []),
            filing_date=str(row["filing_date"]) if row.get("filing_date") else None,
            family_id=str(row["family_id"]) if row.get("family_id") else None,
        )
        assets.append(
            OperationalAsset(
                patent=patent,
                ip_type=str(row.get("ip_type") or "unknown"),
                abstract_language=str(row.get("abstract_language") or ""),
            )
        )
    return assets


def load_operational_patents(parquet_path: Path) -> list[PatentDocument]:
    return [asset.patent for asset in load_operational_assets(parquet_path)]
