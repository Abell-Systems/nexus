"""The unobserved pairs of IPC subclasses at an origin with their expected count under independence (vertical 3 contract, section 6).

Data of the exploratory view of ADR 0038. The universe is the study's (subclasses active at the origin, every pair of two of
them); a pair is unobserved if no single source record published up to the origin states both. Each carries the quantity of
``expected_count`` and nothing else: no rank, no score, no flag of merit. The browser filters and sorts what is stored here.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.base_rates import active_subclass_sets, activity_counts
from application.whitespace.expected_count import documents_per_year, unobserved_pairs_expected

DECIMALS = 9
QUANTITY = "expected co-classifications under independence within publication years (ADR 0038 E3)"
FORMULA = "sum over the years y with documents of n_i(y) * n_j(y) / N(y)"
SCHEMA = "vertical3-unobserved-pairs/1"
UNIT = "O4"  # the publication identifier, with the union of the subclasses of its earliest date
QUANTITY_PARAMETER = "ADR 0038 E3"


def _canonical_number(value: int | float) -> int | str:
    """Integers stay integers; any other number is a decimal string without trailing zeros, so 1.0 and 1 give the same bytes."""
    if isinstance(value, int):
        return value
    return format(Decimal(repr(value)).normalize(), "f")


def configuration_id(parameters: dict[str, Any]) -> str:
    """SHA-256 of the canonical form: keys sorted by code point, no whitespace, UTF-8 (vertical 3 contract, section 6)."""
    canonical = json.dumps(parameters, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def configuration(origin: int, min_documents: int, e_min: float) -> dict[str, Any]:
    """The declared configuration: the parameters that change what the generation computes or how the result is read; not the code that ran.

    ``e_min`` is a reading parameter: ``pairs`` lists every unobserved pair whatever its value, and the reader applies the threshold
    (type A with expected count >= ``e_min``). It is in the identifier because the identifier names the configuration the result is
    offered under (vertical 3 contract, section 6), not because it changes ``pairs``.
    """
    parameters = {
        "schema": SCHEMA,
        "origin": origin,
        "min_documents": min_documents,
        "e_min": _canonical_number(float(e_min)),  # a threshold, always the string form, however it was written
        "unit": UNIT,
        "quantity": QUANTITY_PARAMETER,
    }
    return {"id": configuration_id(parameters), "parameters": parameters}


def unobserved_pairs(
    records: Iterable[AnalysisRecord], origin: int, min_documents: int = 20, e_min: float = 1.0
) -> dict[str, Any]:
    records = [r for r in records if r.published.year <= origin]
    active = active_subclass_sets(records, [origin], min_documents=min_documents, copy_policy="union")[origin]
    counts_by_year = activity_counts(records, "union")
    documents = {s: sum(c.values()) for s, c in sorted(counts_by_year.items()) if s in active}
    documents_by_year = {s: {str(y): n for y, n in sorted(counts_by_year[s].items())} for s in documents}
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
        "configuration": configuration(origin, min_documents, e_min),
        "documents_per_year": {str(y): c for y, c in sorted(Counter(documents_per_year(records)).items())},
        "active": documents,
        "documents_by_year": documents_by_year,
        "counts": {"active": n, "pairs": n * (n - 1) // 2, "unobserved": count},
        "pairs": pairs,
    }
