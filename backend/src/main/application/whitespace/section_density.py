"""Share of subclass pairs already seen together, by pair of IPC sections: a descriptive map of the observed corpus.

Among the subclasses active at an origin (at least ``min_documents`` documents first published up to it), a pair is
*seen* if one source record published up to the origin states both. Counts are aggregated by the section letter of
each subclass (A to H). It describes the corpus; an unseen pair is an absence, not an opportunity, and nothing here
ranks anything.
"""

from collections.abc import Iterable
from itertools import combinations
from typing import Any

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.base_rates import active_subclass_sets


def section_density(records: Iterable[AnalysisRecord], origin: int, min_documents: int = 20) -> dict[str, Any]:
    """Per section pair: active subclasses on each side, possible pairs, seen pairs and their share."""
    records = [r for r in records if r.published.year <= origin]
    active = active_subclass_sets(records, [origin], min_documents=min_documents, copy_policy="union")[origin]
    seen: set[tuple[str, str]] = set()
    for record in records:
        seen.update(combinations(sorted(s for s in record.subclasses if s in active), 2))
    sections = sorted({s[0] for s in active})
    per_section = {section: sum(1 for s in active if s[0] == section) for section in sections}
    cells = {}
    for i, a in enumerate(sections):
        for b in sections[i:]:
            possible = per_section[a] * (per_section[a] - 1) // 2 if a == b else per_section[a] * per_section[b]
            observed = sum(1 for x, y in seen if {x[0], y[0]} == {a, b} and (a == b or x[0] != y[0]))
            cells[f"{a}{b}"] = {
                "possible_pairs": possible,
                "seen_pairs": observed,
                "seen_percent": round(100 * observed / possible, 2) if possible else 0.0,
            }
    return {
        "origin": origin,
        "min_documents": min_documents,
        "active_subclasses": len(active),
        "active_subclasses_by_section": per_section,
        "seen_pairs": len(seen),
        "cells": cells,
    }
