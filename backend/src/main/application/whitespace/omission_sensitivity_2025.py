"""Descriptive sensitivity of the 2025 unobserved pairs to artificial perturbations of the corpus (protocol: docs/whitespace/oepm-omission-sensitivity-2025-protocol.md).

Aggregate statistics only. Nothing here estimates the effect of real omitted publications, and no pair or identifier leaves these functions.
"""

import random
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

from application.whitespace.analysis_records import AnalysisRecord

Pair = tuple[str, str]


def o4_years(records: Iterable[AnalysisRecord]) -> dict[str, int]:
    """O4 unit -> year of its earliest publication date."""
    earliest: dict[str, Any] = {}
    for record in records:
        if record.doc_id not in earliest or record.published < earliest[record.doc_id]:
            earliest[record.doc_id] = record.published
    return {doc: published.year for doc, published in earliest.items()}


def units_per_year(units: dict[str, int]) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    for year in units.values():
        counts[year] += 1
    return dict(sorted(counts.items()))


def remove_units(records: Iterable[AnalysisRecord], removed: set[str]) -> list[AnalysisRecord]:
    """Dropping a unit drops every copy of it, whatever the date of the copy."""
    return [r for r in records if r.doc_id not in removed]


def units_of_year(units: dict[str, int], year: int) -> set[str]:
    return {doc for doc, y in units.items() if y == year}


def stratified_sample(units: dict[str, int], seed: int, share: float = 0.10) -> set[str]:
    """Per year, k_y = floor(share * n_y) units, chosen with random.Random(seed).sample over the identifiers sorted as strings."""
    rng = random.Random(seed)
    by_year: dict[int, list[str]] = defaultdict(list)
    for doc, year in units.items():
        by_year[year].append(doc)
    removed: set[str] = set()
    for year in sorted(by_year):
        ids = sorted(by_year[year])
        removed.update(rng.sample(ids, int(share * len(ids))))
    return removed


def _pairs(result: dict[str, Any]) -> tuple[set[str], set[Pair], set[Pair]]:
    """(active subclasses, unobserved pairs, observed pairs) of an unobserved_pairs result."""
    active = sorted(result["active"])
    unobserved = {(a, b) for a, row in result["pairs"].items() for b in row}
    observed = {(a, b) for i, a in enumerate(active) for b in active[i + 1 :]} - unobserved
    return set(active), unobserved, observed


def _ranks(values: Sequence[float]) -> list[float]:
    """Average ranks (ties share the mean of their positions)."""
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Pearson correlation of the average ranks; None if undefined (fewer than two points or a constant side)."""
    if len(xs) < 2:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sxx * syy) ** 0.5


def _expected(result: dict[str, Any]) -> dict[Pair, float]:
    return {(a, b): e for a, row in result["pairs"].items() for b, e in row.items()}


def compare(base: dict[str, Any], scenario: dict[str, Any]) -> dict[str, Any]:
    """Protocol section 3 and amendment 1. Aggregate counts and one Spearman; raises if the zero-by-construction invariant fails."""
    active_a, unobserved_a, observed_a = _pairs(base)
    active_s, unobserved_s, observed_s = _pairs(scenario)
    both = active_a & active_s

    def in_common(pairs: set[Pair]) -> set[Pair]:
        return {p for p in pairs if p[0] in both and p[1] in both}

    ua, oa = in_common(unobserved_a), in_common(observed_a)
    us, os_ = in_common(unobserved_s), in_common(observed_s)
    became_observed = ua & os_
    became_unobserved = oa & us
    common_pairs = ua | oa
    exp_a, exp_s = _expected(base), _expected(scenario)
    shared = sorted(unobserved_a & unobserved_s)
    rho = spearman([exp_a[p] for p in shared], [exp_s[p] for p in shared])
    return {
        "active": len(active_s),
        "unobserved": len(unobserved_s),
        "common_active": len(both),
        "dropped_unobserved_pairs_of_S_A": len(unobserved_a) - len(ua),
        "common_unobserved_pairs_of_S_A": len(ua),
        "became_observed": len(became_observed),
        "common_observed_pairs_of_S_A": len(oa),
        "became_unobserved": len(became_unobserved),
        "share_became_unobserved": len(became_unobserved) / len(oa) if oa else None,
        "common_universe": len(common_pairs),
        "spearman_E": rho,
        "spearman_pairs": len(shared),
        "spearman_excluded_unobserved_in_S_A": len(unobserved_a) - len(shared),
    }
