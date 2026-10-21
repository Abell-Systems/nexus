"""Publication lag and completeness of filing-year cohorts (characterization §4.2).

Lag is the publication year minus the filing year (``AnalysisRecord.filing_year``). Percentiles are
nearest-rank, so on integer lags they are integers. Completeness is read off the pooled curve of older
cohorts and assumes that the lag distribution is stable; it is an extrapolation, not a measurement.
"""

from collections import Counter
from collections.abc import Iterable
from math import ceil
from typing import Any

from application.whitespace.analysis_records import AnalysisRecord


def _nearest_rank(lags: Counter[int], fraction: float) -> int:
    rank = ceil(fraction * sum(lags.values()))
    seen = 0
    for lag in sorted(lags):
        seen += lags[lag]
        if seen >= rank:
            return lag
    raise ValueError("no lags")


def _lag_statistics(lags: Counter[int]) -> dict[str, Any]:
    n = sum(lags.values())
    return {
        "records": n,
        "mean": round(sum(lag * c for lag, c in lags.items()) / n, 2),
        "median": _nearest_rank(lags, 0.5),
        "p90": _nearest_rank(lags, 0.9),
    }


def lag_figures(
    records: Iterable[AnalysisRecord],
    *,
    from_year: int = 2012,
    cohort_years: range = range(2003, 2011),
    max_lag: int = 15,
    completeness_cohorts: tuple[int, ...] = (2013, 2016, 2019, 2022),
    observed_until: int = 2025,
) -> dict[str, Any]:
    """Lag by group over publications from ``from_year``; cumulative curve of EP translations of ``cohort_years``."""
    by_group: dict[str, Counter[int]] = {"ep_translation": Counter(), "national": Counter()}
    curve: Counter[int] = Counter()
    without_filing_year = negative = 0
    for record in records:
        if record.filing_year is None:
            without_filing_year += 1
            continue
        lag = record.published.year - record.filing_year
        negative += lag < 0
        if record.published.year >= from_year:
            by_group["ep_translation" if record.is_ep_translation else "national"][lag] += 1
        if record.is_ep_translation and record.filing_year in cohort_years:
            curve[lag] += 1
    cohort_size = sum(curve.values())
    cumulative = {
        str(limit): round(100 * sum(c for lag, c in curve.items() if lag <= limit) / cohort_size, 1)
        for limit in range(max_lag + 1)
        if cohort_size
    }
    return {
        "records_without_filing_year": without_filing_year,
        "records_with_negative_lag": negative,
        "lag": {group: _lag_statistics(lags) for group, lags in by_group.items() if lags},
        "cohort_records": cohort_size,
        "cumulative_share_percent": cumulative,
        "completeness_percent": {
            str(c): cumulative[str(observed_until - c)]
            for c in completeness_cohorts
            if str(observed_until - c) in cumulative
        },
    }
