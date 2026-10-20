"""Descriptive base rates of first co-classifications (characterization §7).

Counts only: no detector, no score, no performance. The activity threshold is the one the characterization
used for its counts and has no scientific justification (ADR 0036, P2). A *seen pair* at origin t is a pair of
IPC subclasses classified together on a publication of year <= t; an *active subclass* has at least
``min_documents`` distinct documents (identifiers) first published in year <= t, each counted with the
subclasses of its earliest publication; a *candidate* is a pair of active subclasses that is
not seen; a *positive* is a candidate classified together on a publication of years t+1..t+horizon.
Each origin uses its own active set, and every subclass of a publication counts (ADR 0036 P5, all entries).
Pairs use every record, repeats included: records with the same identifier and publication date are not
always identical (19 of the 3,371 differ in their subclasses), so none is dropped here.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from itertools import combinations
from typing import Any, Literal

from application.whitespace.analysis_records import AnalysisRecord

_Pair = int
_SHIFT = 10  # pair key = low index << 10 | high index; fewer than 1,024 subclasses exist


def _percent(part: int, whole: int) -> float:
    return round(100 * part / whole, 2) if whole else 0.0


def _bits(first: int, last: int, base: int) -> int:
    return sum(1 << (year - base) for year in range(first, last + 1))


CopyPolicy = Literal["first", "last", "union"]


def base_rates(
    records: Iterable[AnalysisRecord],
    origins: Sequence[int],
    *,
    min_documents: int = 20,
    horizon: int = 3,
    filing_diagnostic: bool = True,
    filing_outcome_until: int | None = None,
    hidden_year_origins: Sequence[int] = (),
    hidden_years: Sequence[int] = (),
    copy_policy: CopyPolicy = "first",
) -> dict[str, Any]:
    """Figures per origin over ``records``.

    ``filing_diagnostic``: share of positives whose contributing publications were filed by the origin (§7.1).
    ``filing_outcome_until``: also count candidates whose earliest filing year over all publications falls in
    the horizon, for origins with ``origin + horizon <= filing_outcome_until`` (§7.2).
    ``hidden_year_origins`` and ``hidden_years``: counterfactual estimate of the positives that a missing year
    would have created, from candidates seen only in that year and observed again in the horizon (§7).
    ``copy_policy``: which subclasses a document contributes to the activity count when several copies share
    its identifier and earliest publication date but differ: those of the first copy in input order (the
    default, which reproduces the printed figures), of the last, or the union of all. Not a decision of the
    ADR: ADR 0036 leaves the policy open and this parameter exists to measure how much it matters.
    """
    publications = [r for r in records if r.subclasses]
    if not publications:
        return {}
    base = min(r.published.year for r in publications)
    index = {s: i for i, s in enumerate(sorted({s for r in publications for s in r.subclasses}))}

    documents: dict[int, Counter[int]] = defaultdict(Counter)  # subclass -> year of first publication -> documents
    first_publication: dict[str, list[AnalysisRecord]] = {}  # identifier -> copies of its earliest publication date
    years_of: dict[_Pair, int] = defaultdict(int)  # pair -> bitmask of the years it occurs in
    first_filing: dict[_Pair, int] = {}  # pair -> earliest filing year over all publications
    by_year: dict[int, list[tuple[AnalysisRecord, list[_Pair]]]] = defaultdict(list)
    for record in publications:
        ids = sorted(index[s] for s in record.subclasses)
        year = record.published.year
        copies = first_publication.setdefault(record.doc_id, [])
        if not copies or record.published < copies[0].published:
            first_publication[record.doc_id] = [record]
        elif record.published == copies[0].published:
            copies.append(record)
        pairs = [(a << _SHIFT) | b for a, b in combinations(ids, 2)]
        for pair in pairs:
            years_of[pair] |= 1 << (year - base)
            if record.filing_year is not None and record.filing_year < first_filing.get(pair, 10_000):
                first_filing[pair] = record.filing_year
        by_year[year].append((record, pairs))

    for copies in first_publication.values():
        contributed = (
            set().union(*(c.subclasses for c in copies))
            if copy_policy == "union"
            else (copies[-1] if copy_policy == "last" else copies[0]).subclasses
        )
        for s in contributed:
            documents[index[s]][copies[0].published.year] += 1

    def active_at(origin: int) -> set[int]:
        return {
            i
            for i, per_year in documents.items()
            if sum(c for y, c in per_year.items() if y <= origin) >= min_documents
        }

    def both_active(pair: _Pair, active: set[int]) -> bool:
        return (pair >> _SHIFT) in active and (pair & ((1 << _SHIFT) - 1)) in active

    result: dict[str, Any] = {}
    for origin in origins:
        seen_years = _bits(base, origin, base)
        horizon_years = _bits(origin + 1, origin + horizon, base)
        active = active_at(origin)
        seen_active = sum(1 for p, y in years_of.items() if y & seen_years and both_active(p, active))
        positives = {
            p for p, y in years_of.items() if not y & seen_years and y & horizon_years and both_active(p, active)
        }
        candidates = len(active) * (len(active) - 1) // 2 - seen_active
        figures: dict[str, Any] = {
            "active_subclasses": len(active),
            "candidate_pairs": candidates,
            "positives": len(positives),
            "positive_rate_percent": _percent(len(positives), candidates),
        }
        if filing_diagnostic:
            figures["filing_diagnostic"] = _filing_diagnostic(by_year, positives, origin, horizon)
        if filing_outcome_until is not None:
            if origin + horizon <= filing_outcome_until:
                figures["positives_filing_year_outcome"] = sum(
                    1
                    for p, y in years_of.items()
                    if not y & seen_years
                    and both_active(p, active)
                    and origin < first_filing.get(p, 0) <= origin + horizon
                )
            else:
                figures["positives_filing_year_outcome"] = None
        if origin in hidden_year_origins:
            figures["hidden_year"] = _hidden_year(
                years_of, active, both_active, hidden_years, origin, base, horizon_years
            )
            figures["hidden_year"]["positives"] = len(positives)
        result[str(origin)] = figures
    return result


def _filing_diagnostic(
    by_year: dict[int, list[tuple[AnalysisRecord, list[_Pair]]]], positives: set[_Pair], origin: int, horizon: int
) -> dict[str, Any]:
    """§7.1 over the positives: earliest filing year (and the latest) among the publications that make each one.

    ``filed_by_origin``: the earliest contributing filing year is <= origin (at least one contributing
    publication was filed by then); ``all_filed_by_origin`` is the stricter reading (the latest is <= origin).
    """
    earliest: dict[_Pair, int] = {}
    latest: dict[_Pair, int] = {}
    ep: dict[_Pair, set[bool]] = defaultdict(set)
    for year in range(origin + 1, origin + horizon + 1):
        for record, pairs in by_year.get(year, ()):
            for pair in pairs:
                if pair in positives:
                    ep[pair].add(record.is_ep_translation)
                    if record.filing_year is not None:
                        earliest[pair] = min(earliest.get(pair, record.filing_year), record.filing_year)
                        latest[pair] = max(latest.get(pair, record.filing_year), record.filing_year)
    n = len(positives)
    return {
        "positives": n,
        "without_filing_year": n - len(earliest),
        "filed_by_origin_percent": _percent(sum(y <= origin for y in earliest.values()), n),
        "filed_5_years_before_origin_percent": _percent(sum(y <= origin - 5 for y in earliest.values()), n),
        "all_filed_by_origin_percent": _percent(sum(y <= origin for y in latest.values()), n),
        "every_contributor_ep_translation_percent": _percent(sum(s == {True} for s in ep.values()), n),
        "no_contributor_ep_translation_percent": _percent(sum(s == {False} for s in ep.values()), n),
        "filed_by_origin": sum(y <= origin for y in earliest.values()),
    }


def _hidden_year(
    years_of: dict[_Pair, int],
    active: set[int],
    both_active: Any,
    hidden_years: Sequence[int],
    origin: int,
    base: int,
    horizon_years: int,
) -> dict[str, Any]:
    """Counterfactual: pairs seen up to the origin only in one year, and observed again in the horizon.

    Had that year been missing from the history these pairs would have counted as new. This describes a year
    of ordinary volume; it is not a measurement of any unobserved year.
    """
    counts = {
        str(year): sum(
            1
            for pair, y in years_of.items()
            if y & horizon_years and (y & _bits(base, origin, base)) == 1 << (year - base) and both_active(pair, active)
        )
        for year in hidden_years
    }
    return {"by_hidden_year": counts, "min": min(counts.values()), "max": max(counts.values())}
