"""Jurisdiction -> year -> month partition tree for enumerating PatentCorpus's universe
under EPO OPS's real per-query retrieval ceiling (PR-E0.1, docs/superpowers/specs/
2026-09-08-ops-enumeration-partitioning-contract.md).

Partitioning axes are jurisdiction and publication-date ONLY (contract §4) -- grant
status is never a partitioning key (OPS cannot filter it reliably; it stays a
downstream inclusion predicate, unchanged from PR #57). Exactly three levels; a
month-level partition still over the ceiling is NON_ENUMERABLE, not subdivided
further onto an unspecified axis (contract §4).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

PartitionLevel = Literal["jurisdiction", "year", "month"]


@dataclass(frozen=True)
class DatePartition:
    """A candidate or leaf slice of PatentCorpus's universe: one jurisdiction, a
    closed date interval [start_date, end_date] (both inclusive -- contract §4's
    half-open month semantics represented as "last included day", matching
    ops_query.py's existing closed `pd within "A B"` convention)."""

    jurisdiction: str
    start_date: date
    end_date: date
    level: PartitionLevel


def build_root_partitions(
    jurisdictions: list[str], window_start: date, window_end: date
) -> list[DatePartition]:
    """One partition per jurisdiction, each spanning the entire window (contract §5.1's
    query-space coverage, before any subdivision)."""
    if window_start > window_end:
        raise ValueError(f"window_start ({window_start}) must be <= window_end ({window_end})")
    return [
        DatePartition(jurisdiction=j, start_date=window_start, end_date=window_end, level="jurisdiction")
        for j in jurisdictions
    ]


def _year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)
    return date(year, month, 1), next_month_start - timedelta(days=1)


def subdivide(partition: DatePartition) -> list[DatePartition]:
    """Split into the next level down (jurisdiction -> year -> month), each child
    clipped to `partition`'s own [start_date, end_date] so the children's union is
    exactly `partition`'s range (contract §5.1 coverage, §5.2 disjunction).

    Raises ValueError if `partition.level == "month"` -- there is no fourth level
    (contract §4); a month-level partition that still exceeds the ceiling is a
    NON_ENUMERABLE terminal state (see `partition()` in this module), not a call
    to subdivide further.
    """
    if partition.level == "jurisdiction":
        children: list[DatePartition] = []
        for year in range(partition.start_date.year, partition.end_date.year + 1):
            y_start, y_end = _year_bounds(year)
            children.append(
                DatePartition(
                    partition.jurisdiction,
                    max(y_start, partition.start_date),
                    min(y_end, partition.end_date),
                    "year",
                )
            )
        return children

    if partition.level == "year":
        children = []
        cursor = date(partition.start_date.year, partition.start_date.month, 1)
        while cursor <= partition.end_date:
            m_start, m_end = _month_bounds(cursor.year, cursor.month)
            children.append(
                DatePartition(
                    partition.jurisdiction,
                    max(m_start, partition.start_date),
                    min(m_end, partition.end_date),
                    "month",
                )
            )
            cursor = m_end + timedelta(days=1)
        return children

    raise ValueError(
        f"Cannot subdivide a 'month'-level partition further (PR-E0.1 contract §4: "
        f"no fourth level). Partition: {partition.jurisdiction} "
        f"[{partition.start_date}, {partition.end_date}]"
    )
