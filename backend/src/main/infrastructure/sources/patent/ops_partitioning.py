"""Jurisdiction -> year -> month partition tree for enumerating PatentCorpus's universe
under EPO OPS's real per-query retrieval ceiling (PR-E0.1, docs/superpowers/specs/
2026-09-08-ops-enumeration-partitioning-contract.md).

Partitioning axes are jurisdiction and publication-date ONLY (contract §4) -- grant
status is never a partitioning key (OPS cannot filter it reliably; it stays a
downstream inclusion predicate, unchanged from PR #57). Exactly three levels; a
month-level partition still over the ceiling is NON_ENUMERABLE, not subdivided
further onto an unspecified axis (contract §4).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from domain.protocols.sources import RawPayload
from infrastructure.sources.patent.ops_pagination import (
    _PaginatedPatentSource,
    fetch_all_ops_batches,
    peek_total_result_count,
)

PartitionLevel = Literal["jurisdiction", "year", "month"]

# PR-E0.1 contract §7: OPS-adapter working assumption, not a domain fact -- see
# enumerate_partition_tree's default and the spec's confidence note.
OPS_RETRIEVAL_CEILING: int = 2000


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
    if not jurisdictions:
        raise ValueError("jurisdictions must be a non-empty list")
    return [
        DatePartition(jurisdiction=j, start_date=window_start, end_date=window_end, level="jurisdiction")
        for j in jurisdictions
    ]


def _year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    next_month_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
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


CountFn = Callable[[DatePartition], int]


class NonEnumerablePartitionError(Exception):
    """A month-level partition's total-result-count still exceeds the OPS retrieval
    ceiling. PR-E0.1 contract §4/§5.4: construction fails closed -- this is an explicit
    terminal state requiring a human decision, never an automatic deeper recursion onto
    an unspecified axis, and never silently accepted as a partial universe."""


def partition(
    jurisdictions: list[str],
    window_start: date,
    window_end: date,
    count_fn: CountFn,
    ceiling: int,
) -> list[DatePartition]:
    """Recursively decompose jurisdictions x [window_start, window_end] into leaves
    whose count_fn(leaf) <= ceiling (contract §5.3's "eligible for enumeration").
    Deterministic given a deterministic count_fn: same inputs -> same leaves, in
    jurisdiction-input order then chronological order (contract §5.5). Raises
    NonEnumerablePartitionError -- aborting the whole call, no partial leaf list
    returned -- if any month-level partition still exceeds the ceiling (contract §5.4).
    """
    leaves: list[DatePartition] = []
    for root in build_root_partitions(jurisdictions, window_start, window_end):
        leaves.extend(_partition_node(root, count_fn, ceiling))
    return leaves


def _partition_node(node: DatePartition, count_fn: CountFn, ceiling: int) -> list[DatePartition]:
    count = count_fn(node)
    if count <= ceiling:
        return [node]
    if node.level == "month":
        raise NonEnumerablePartitionError(
            f"Partition {node.jurisdiction} [{node.start_date}, {node.end_date}] "
            f"(month-level) has total-result-count={count} > ceiling={ceiling} and "
            "cannot be subdivided further (PR-E0.1 contract §4: no fourth level). "
            "Construction fails closed -- this requires an explicit decision about "
            "the inclusion contract or ceiling, not automatic recursion."
        )
    result: list[DatePartition] = []
    for child in subdivide(node):
        result.extend(_partition_node(child, count_fn, ceiling))
    return result


def build_partition_cql(partition: DatePartition) -> str:
    """CQL for one candidate/leaf partition: a single jurisdiction, day-precision
    closed date range. Mirrors ops_query.build_patent_corpus_cql's `pd within "A B"`
    convention, generalized to a single jurisdiction and arbitrary day granularity."""
    start = partition.start_date.strftime("%Y%m%d")
    end = partition.end_date.strftime("%Y%m%d")
    return f'pn={partition.jurisdiction.upper()} and pd within "{start} {end}"'


@dataclass(frozen=True)
class PartitionFetchResult:
    """Return value of enumerate_partition_tree: the unioned, verified batches plus
    how many leaf partitions the run actually needed (manifest/audit purposes --
    contract §5.5 determinism means this count is itself reproducible)."""

    batches: list[RawPayload]
    leaf_count: int


def enumerate_partition_tree(
    client: _PaginatedPatentSource,
    jurisdictions: list[str],
    window_start: date,
    window_end: date,
    ceiling: int = OPS_RETRIEVAL_CEILING,
) -> PartitionFetchResult:
    """Drive `partition()` using real OPS total-result-count peeks, then fully
    enumerate every eligible leaf via `fetch_all_ops_batches`, returning the union
    plus the leaf count.

    Fail-closed at both stages (contract §5.4): a NonEnumerablePartitionError from
    `partition()`, or a RuntimeError from any leaf's `fetch_all_ops_batches` call,
    propagates immediately -- no partial result is ever returned. `ceiling`'s default
    (OPS_RETRIEVAL_CEILING) is the OPS-adapter's working assumption (contract §7), not
    a domain fact; override it explicitly once PR-E0.2's live integration test confirms
    or corrects it.
    """

    def count_fn(p: DatePartition) -> int:
        return peek_total_result_count(client, build_partition_cql(p))

    leaves = partition(jurisdictions, window_start, window_end, count_fn=count_fn, ceiling=ceiling)

    all_batches: list[RawPayload] = []
    for leaf in leaves:
        all_batches.extend(fetch_all_ops_batches(client, cql_query=build_partition_cql(leaf)))
    return PartitionFetchResult(batches=all_batches, leaf_count=len(leaves))
