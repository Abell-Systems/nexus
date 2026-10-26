"""The unobserved pairs of IPC subclasses at an origin with their expected count under independence (vertical 3 contract, section 6).

Data of the exploratory view of ADR 0038. The universe is the study's (subclasses active at the origin, every pair of two of
them); a pair is unobserved if no single source record published up to the origin states both. Each carries the quantity of
``expected_count`` and nothing else: no rank, no score, no flag of merit. The browser filters and sorts what is stored here.
"""

from collections import Counter
from collections.abc import Iterable
from typing import Any

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.base_rates import active_subclass_sets, activity_counts
from application.whitespace.expected_count import documents_per_year, unobserved_pairs_expected

DECIMALS = 9
QUANTITY = "expected co-classifications under independence within publication years (ADR 0038 E3)"
FORMULA = "sum over the years y with documents of n_i(y) * n_j(y) / N(y)"


def unobserved_pairs(
    records: Iterable[AnalysisRecord], origin: int, min_documents: int = 20, e_min: float = 1.0
) -> dict[str, Any]:
    records = [r for r in records if r.published.year <= origin]
    active = active_subclass_sets(records, [origin], min_documents=min_documents, copy_policy="union")[origin]
    documents = {s: sum(c.values()) for s, c in sorted(activity_counts(records, "union").items()) if s in active}
    pairs: dict[str, dict[str, float]] = {}
    for a, b, expected in unobserved_pairs_expected(records, origin, min_documents):
        pairs.setdefault(a, {})[b] = round(expected, DECIMALS)
    count = sum(len(v) for v in pairs.values())
    n = len(active)
    return {
        "origin": origin,
        "min_documents": min_documents,
        "e_min": e_min,
        "quantity": QUANTITY,
        "formula": FORMULA,
        "decimals": DECIMALS,
        "documents_per_year": {str(y): c for y, c in sorted(Counter(documents_per_year(records)).items())},
        "active": documents,
        "counts": {"active": n, "pairs": n * (n - 1) // 2, "unobserved": count},
        "pairs": pairs,
    }
