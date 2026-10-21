"""Observed pairs of IPC subclasses at an origin, with the counts behind each (vertical 2 contract, section 4).

The universe is the study's: subclasses active at the origin (``min_documents`` publication identifiers first
published up to it) and every pair of two of them. A pair is *observed* if one source record published up to the
origin states both; only observed pairs are stored, the unobserved ones are the complement. A document is counted once
per pair, in the year of the earliest record that carries both. A subclass's first year is the earliest publication
year of its documents. Describes the corpus; nothing here ranks anything.
"""

from collections.abc import Iterable
from itertools import combinations
from typing import Any

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.base_rates import active_subclass_sets, activity_counts


def subclass_pairs(records: Iterable[AnalysisRecord], origin: int, min_documents: int = 20) -> dict[str, Any]:
    records = [r for r in records if r.published.year <= origin]
    active = active_subclass_sets(records, [origin], min_documents=min_documents, copy_policy="union")[origin]
    activity = {s: per_year for s, per_year in activity_counts(records, "union").items() if s in active}
    per_subclass = {s: sum(per_year.values()) for s, per_year in activity.items()}
    first_years = {
        s: min(year for year, count in per_year.items() if count) for s, per_year in sorted(activity.items())
    }
    first_record: dict[tuple[str, str], dict[str, int]] = {}
    for record in records:
        for a, b in combinations(sorted(s for s in record.subclasses if s in active), 2):
            years = first_record.setdefault((a, b), {})
            year = record.published.year
            if record.doc_id not in years or year < years[record.doc_id]:
                years[record.doc_id] = year
    pairs = {}
    for (a, b), years in sorted(first_record.items()):
        by_year: dict[str, int] = {}
        for year in sorted(years.values()):
            by_year[str(year)] = by_year.get(str(year), 0) + 1
        pairs[f"{a}|{b}"] = {"documents": len(years), "by_year": by_year, "first_year": min(years.values())}
    return {
        "origin": origin,
        "min_documents": min_documents,
        "active": dict(sorted(per_subclass.items())),
        "first_years": first_years,
        "pairs": pairs,
    }
