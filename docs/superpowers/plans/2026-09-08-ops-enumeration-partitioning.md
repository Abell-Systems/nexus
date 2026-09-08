# OPS Enumeration Partitioning (PR-E0.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `scripts/freeze_patent_corpus.py::main()` able to actually enumerate ADR 0020's full `PatentCorpus` universe, by decomposing it into jurisdiction/date partitions small enough for EPO OPS to answer, per the approved partitioning contract — without ever changing what universe `P` represents.

**Architecture:** A new pure module (`DatePartition`, `subdivide`, `partition`) implements the jurisdiction → year → month decomposition and its five invariants entirely without I/O, tested against synthetic `total-result-count` values. A thin OPS-integration layer (`peek_total_result_count`, `enumerate_partition_tree`) supplies real counts and drives `fetch_all_ops_batches` (PR #57, unchanged) per eligible leaf, unioning the results. `scripts/freeze_patent_corpus.py::build_patent_corpus()` swaps its single `cql_query` fetch for this partitioned fetch; everything downstream (normalize → grants-only → dedup → `sha256(publication_id)` → `select_frozen_patents` → freeze) is untouched.

**Tech Stack:** Python 3.12, stdlib `datetime.date` (no new dependency), `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-08-ops-enumeration-partitioning-contract.md` (PR-E0.1 contract, approved after two review rounds). Also binding: `docs/adr/0020-experimental-corpus-architecture-demand-times-patent.md` (ADR 0020, unchanged by this plan).

## Global Constraints

- Partitioning axes are jurisdiction and publication-date only — never grant/kind status, CPC, or anything topical (spec §4).
- Exactly three levels: jurisdiction → year → month. No fourth level; a month-level partition still over the ceiling is `NON_ENUMERABLE`, not further subdivided (spec §4).
- Leaves are closed-interval `[start_date, end_date]` (both inclusive) — a `publication_date` belongs to exactly one leaf, with month/year boundaries clipped to the parent window (spec §4).
- Coverage is over the CQL query space (jurisdiction × date window) only — grants-only inclusion stays a downstream predicate (`allowed_kind_codes`, unchanged), never a partitioning key (spec §5.1).
- "Eligible for enumeration" (`total-result-count ≤ ceiling`) and "enumerated completely" (`fetch_all_ops_batches` succeeded) are distinct conditions — do not conflate them (spec §5.3).
- Fail-closed: any `NonEnumerablePartitionError`, or any leaf's `fetch_all_ops_batches` failure, must abort the ENTIRE construction — no partial `PatentCorpus`, no manifest, no output files (spec §5.4).
- Determinism: same jurisdictions/window/counts → same leaves, same order, independent of OPS delivery order (spec §5.5).
- The OPS retrieval ceiling (working value 2000) is infrastructure-layer configuration (a function default, like `fetch_all_ops_batches`'s `max_records`), never a literal embedded in the partitioning algorithm's logic (spec §7).
- Does not modify ADR 0020, `PatentCorpus`'s schema, `select_frozen_patents`'s dedup/selection logic, `AnnotationPoolEligibilityPolicy`, or `CandidatePoolBuilder`.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/src/main/infrastructure/sources/patent/ops_partitioning.py` (new) | `DatePartition` model, `build_root_partitions`, `subdivide`, `partition` (pure, no I/O), `NonEnumerablePartitionError`, `build_partition_cql`, `enumerate_partition_tree` (OPS-integration driver). |
| `backend/src/main/infrastructure/sources/patent/ops_pagination.py` (modify) | Add `peek_total_result_count` — fetch page 1 only, return its declared total, for partition-eligibility decisions. |
| `scripts/freeze_patent_corpus.py` (modify) | `build_patent_corpus()` takes `window_start`/`window_end`/`ceiling` instead of `cql_query`; fetches via `enumerate_partition_tree` instead of a single `fetch_all_ops_batches` call; `main()` computes an exact 10-year date window and drops the now-resolved `KNOWN LIMITATION` docstring. |

---

### Task 1: `DatePartition` model and tree mechanics (`subdivide`)

**Files:**
- Create: `backend/src/main/infrastructure/sources/patent/ops_partitioning.py`
- Test: `backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py`

**Interfaces:**
- Produces: `DatePartition` (frozen dataclass: `jurisdiction: str`, `start_date: date`, `end_date: date`, `level: Literal["jurisdiction", "year", "month"]`), `build_root_partitions(jurisdictions: list[str], window_start: date, window_end: date) -> list[DatePartition]`, `subdivide(partition: DatePartition) -> list[DatePartition]` (raises `ValueError` on a `"month"`-level input). Consumed by Task 2's `partition()`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py
"""Unit tests for the jurisdiction -> year -> month partition tree (PR-E0.1 §4)."""

from datetime import date

import pytest

from infrastructure.sources.patent.ops_partitioning import (
    DatePartition,
    build_root_partitions,
    subdivide,
)


def test_build_root_partitions_one_per_jurisdiction_spanning_whole_window():
    roots = build_root_partitions(
        jurisdictions=["EP", "US"],
        window_start=date(2016, 3, 15),
        window_end=date(2026, 3, 15),
    )
    assert roots == [
        DatePartition("EP", date(2016, 3, 15), date(2026, 3, 15), "jurisdiction"),
        DatePartition("US", date(2016, 3, 15), date(2026, 3, 15), "jurisdiction"),
    ]


def test_build_root_partitions_rejects_inverted_window():
    with pytest.raises(ValueError, match="window_start"):
        build_root_partitions(["EP"], date(2026, 1, 1), date(2016, 1, 1))


def test_subdivide_jurisdiction_into_years_clipped_to_window():
    root = DatePartition("EP", date(2016, 3, 15), date(2018, 6, 10), "jurisdiction")
    years = subdivide(root)
    assert years == [
        DatePartition("EP", date(2016, 3, 15), date(2016, 12, 31), "year"),
        DatePartition("EP", date(2017, 1, 1), date(2017, 12, 31), "year"),
        DatePartition("EP", date(2018, 1, 1), date(2018, 6, 10), "year"),
    ]


def test_subdivide_year_into_months_clipped_to_parent():
    year_partition = DatePartition("US", date(2020, 3, 15), date(2020, 6, 10), "year")
    months = subdivide(year_partition)
    assert months == [
        DatePartition("US", date(2020, 3, 15), date(2020, 3, 31), "month"),
        DatePartition("US", date(2020, 4, 1), date(2020, 4, 30), "month"),
        DatePartition("US", date(2020, 5, 1), date(2020, 5, 31), "month"),
        DatePartition("US", date(2020, 6, 1), date(2020, 6, 10), "month"),
    ]


def test_subdivide_single_full_year_into_twelve_months():
    year_partition = DatePartition("JP", date(2021, 1, 1), date(2021, 12, 31), "year")
    months = subdivide(year_partition)
    assert len(months) == 12
    assert months[0] == DatePartition("JP", date(2021, 1, 1), date(2021, 1, 31), "month")
    assert months[-1] == DatePartition("JP", date(2021, 12, 1), date(2021, 12, 31), "month")


def test_subdivide_month_level_partition_raises():
    leaf = DatePartition("EP", date(2020, 1, 1), date(2020, 1, 31), "month")
    with pytest.raises(ValueError, match="month"):
        subdivide(leaf)


def test_subdivide_leaves_are_contiguous_and_disjoint():
    root = DatePartition("EP", date(2019, 11, 20), date(2020, 2, 5), "jurisdiction")
    years = subdivide(root)
    months: list[DatePartition] = []
    for y in years:
        months.extend(subdivide(y))
    for prev, nxt in zip(months, months[1:]):
        assert prev.end_date < nxt.start_date or prev.end_date == nxt.start_date - __import__("datetime").timedelta(days=1)
    assert months[0].start_date == date(2019, 11, 20)
    assert months[-1].end_date == date(2020, 2, 5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.sources.patent.ops_partitioning'`

- [ ] **Step 3: Implement**

```python
# backend/src/main/infrastructure/sources/patent/ops_partitioning.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/sources/patent/ops_partitioning.py backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py
git commit -m "$(cat <<'EOF'
feat: add DatePartition model and jurisdiction/year/month subdivide (PR-E0.1)

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 2: `partition()` — the recursive, count-driven algorithm, and its five invariants

**Files:**
- Modify: `backend/src/main/infrastructure/sources/patent/ops_partitioning.py`
- Modify: `backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py`

**Interfaces:**
- Consumes: `DatePartition`, `build_root_partitions`, `subdivide` (Task 1).
- Produces: `NonEnumerablePartitionError(Exception)`, `CountFn = Callable[[DatePartition], int]`, `partition(jurisdictions: list[str], window_start: date, window_end: date, count_fn: CountFn, ceiling: int) -> list[DatePartition]`. Consumed by Task 3's `enumerate_partition_tree`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py`:

```python
from infrastructure.sources.patent.ops_partitioning import (
    NonEnumerablePartitionError,
    partition,
)


def test_partition_accepts_jurisdiction_root_when_under_ceiling():
    counts = {"EP": 500, "US": 800}
    leaves = partition(
        jurisdictions=["EP", "US"],
        window_start=date(2020, 1, 1),
        window_end=date(2020, 12, 31),
        count_fn=lambda p: counts[p.jurisdiction],
        ceiling=2000,
    )
    assert [leaf.level for leaf in leaves] == ["jurisdiction", "jurisdiction"]
    assert [leaf.jurisdiction for leaf in leaves] == ["EP", "US"]


def test_partition_subdivides_jurisdiction_into_years_when_over_ceiling():
    def count_fn(p):
        if p.level == "jurisdiction":
            return 5000  # over ceiling -> must subdivide
        return 100  # every year is under ceiling -> accept

    leaves = partition(
        jurisdictions=["EP"],
        window_start=date(2020, 1, 1),
        window_end=date(2021, 12, 31),
        count_fn=count_fn,
        ceiling=2000,
    )
    assert len(leaves) == 2
    assert all(leaf.level == "year" for leaf in leaves)
    assert [leaf.start_date.year for leaf in leaves] == [2020, 2021]


def test_partition_subdivides_year_into_months_when_over_ceiling():
    def count_fn(p):
        if p.level in ("jurisdiction", "year"):
            return 5000
        return 50

    leaves = partition(
        jurisdictions=["US"],
        window_start=date(2020, 1, 1),
        window_end=date(2020, 3, 31),
        count_fn=count_fn,
        ceiling=2000,
    )
    assert len(leaves) == 3
    assert all(leaf.level == "month" for leaf in leaves)


def test_partition_raises_non_enumerable_when_month_still_over_ceiling():
    def count_fn(p):
        return 999999  # never under ceiling, at any level

    with pytest.raises(NonEnumerablePartitionError, match="month"):
        partition(
            jurisdictions=["EP"],
            window_start=date(2020, 1, 1),
            window_end=date(2020, 1, 31),
            count_fn=count_fn,
            ceiling=2000,
        )


def test_partition_fails_closed_no_partial_leaves_on_non_enumerable():
    """One bad partition aborts the WHOLE tree -- a sibling jurisdiction's already-
    computed leaves must not be returned either (contract §5.4)."""
    def count_fn(p):
        if p.jurisdiction == "EP":
            return 100  # fine
        return 999999  # US never enumerable

    with pytest.raises(NonEnumerablePartitionError):
        partition(
            jurisdictions=["EP", "US"],
            window_start=date(2020, 1, 1),
            window_end=date(2020, 1, 31),
            count_fn=count_fn,
            ceiling=2000,
        )


def test_partition_is_deterministic_given_deterministic_count_fn():
    def count_fn(p):
        return 5000 if p.level != "month" else 100

    args = dict(
        jurisdictions=["EP", "US", "JP"],
        window_start=date(2020, 1, 1),
        window_end=date(2020, 6, 30),
        count_fn=count_fn,
        ceiling=2000,
    )
    first = partition(**args)
    second = partition(**args)
    assert first == second


def test_partition_leaf_at_exactly_the_ceiling_is_accepted_not_subdivided():
    leaves = partition(
        jurisdictions=["EP"],
        window_start=date(2020, 1, 1),
        window_end=date(2020, 12, 31),
        count_fn=lambda p: 2000,
        ceiling=2000,
    )
    assert len(leaves) == 1
    assert leaves[0].level == "jurisdiction"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py -v`
Expected: FAIL with `ImportError: cannot import name 'partition'`

- [ ] **Step 3: Implement**

Append to `backend/src/main/infrastructure/sources/patent/ops_partitioning.py`:

```python
from collections.abc import Callable

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py -v`
Expected: PASS (14 tests total)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/sources/patent/ops_partitioning.py backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py
git commit -m "$(cat <<'EOF'
feat: add partition() recursive enumerability-eligibility algorithm (PR-E0.1)

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 3: OPS integration — `peek_total_result_count` and `enumerate_partition_tree`

**Files:**
- Modify: `backend/src/main/infrastructure/sources/patent/ops_pagination.py`
- Modify: `backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py`
- Modify: `backend/src/main/infrastructure/sources/patent/ops_partitioning.py`
- Modify: `backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py`

**Interfaces:**
- Consumes: `parse_total_result_count` (existing, `ops_pagination.py`), `fetch_all_ops_batches` (existing, `ops_pagination.py`), `partition`, `DatePartition`, `NonEnumerablePartitionError` (Task 2).
- Produces: `peek_total_result_count(client, cql_query: str) -> int` (`ops_pagination.py`), `build_partition_cql(partition: DatePartition) -> str`, `PartitionFetchResult` (frozen dataclass: `batches: list[RawPayload]`, `leaf_count: int`), and `enumerate_partition_tree(client, jurisdictions: list[str], window_start: date, window_end: date, ceiling: int = 2000) -> PartitionFetchResult` (`ops_partitioning.py`). `leaf_count` is included so a caller (Task 4) can record how many partitions the run actually needed, for manifest/audit purposes, without a second pass over the tree. Consumed by Task 4's `build_patent_corpus`.

- [ ] **Step 1: Write the failing tests — `peek_total_result_count`**

Append to `backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py`:

```python
from infrastructure.sources.patent.ops_pagination import peek_total_result_count


def test_peek_total_result_count_reads_page_one_only():
    client = _FakeClient({(1, 1): ONE_DOC_PAGE})
    total = peek_total_result_count(client, cql_query="pn=US")
    assert total == 3
    assert client.calls == [(1, 1)]


def test_peek_total_result_count_raises_on_missing_total():
    client = _FakeClient({(1, 1): NO_COUNT_PAGE})
    with pytest.raises(RuntimeError, match="total-result-count"):
        peek_total_result_count(client, cql_query="pn=US")
```

(`_FakeClient`, `ONE_DOC_PAGE`, `NO_COUNT_PAGE` already exist in this file from PR #57's Task 3 — reuse them, do not redefine.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py -v`
Expected: FAIL with `ImportError: cannot import name 'peek_total_result_count'`

- [ ] **Step 3: Implement `peek_total_result_count`**

Append to `backend/src/main/infrastructure/sources/patent/ops_pagination.py`:

```python
def peek_total_result_count(client: _PaginatedPatentSource, cql_query: str) -> int:
    """Fetch page 1 only of `cql_query` and return its declared total-result-count,
    without paginating further. Used to decide partition eligibility (PR-E0.1 contract
    §5.3) before committing to a full fetch_all_ops_batches run. Raises RuntimeError
    with the same diagnostic style as fetch_all_ops_batches if total-result-count is
    missing or unparseable.
    """
    batch = next(iter(client.fetch_batches(cql_query=cql_query, range_start=1, range_end=1)))
    total = parse_total_result_count(batch.payload_bytes)
    if total is None:
        raise RuntimeError(
            f"EPO OPS response for query {cql_query!r} is missing total-result-count; "
            "cannot determine partition eligibility (PR-E0.1 contract §5.3)."
        )
    return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py -v`
Expected: PASS (all prior tests plus 2 new)

- [ ] **Step 5: Write the failing tests — `build_partition_cql` and `enumerate_partition_tree`**

Append to `backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py`:

```python
from infrastructure.sources.patent.ops_partitioning import build_partition_cql, enumerate_partition_tree


def test_build_partition_cql_single_jurisdiction_day_precision():
    p = DatePartition("US", date(2020, 3, 15), date(2020, 6, 10), "year")
    query = build_partition_cql(p)
    assert query == 'pn=US and pd within "20200315 20200610"'


class _FakeOpsClient:
    """Test double: every call returns the same fixed total-result-count and a
    trivial biblio-search payload, regardless of the query -- enough to drive
    enumerate_partition_tree's control flow without real XML content."""

    def __init__(self, total: int) -> None:
        self.total = total
        self.calls: list[tuple[str, int, int]] = []

    def fetch_batches(self, cql_query="", range_start=1, range_end=25):
        self.calls.append((cql_query, range_start, range_end))
        xml = (
            f'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org">'
            f'<ops:biblio-search total-result-count="{self.total}"/></ops:world-patent-data>'
        ).encode()
        from domain.protocols.sources import RawPayload

        yield RawPayload(source_id="epo_ops", batch_id=f"b_{range_start}_{range_end}", payload_bytes=xml, metadata={})


def test_enumerate_partition_tree_unions_eligible_leaves():
    client = _FakeOpsClient(total=5)  # well under ceiling -> jurisdiction-level leaves, no subdivision
    result = enumerate_partition_tree(
        client,
        jurisdictions=["EP", "US"],
        window_start=date(2020, 1, 1),
        window_end=date(2020, 12, 31),
        ceiling=2000,
    )
    # One fetch_all_ops_batches call per leaf (2 jurisdiction-level leaves), each
    # single-page since total=5 fits in one page.
    assert len(result.batches) == 2
    assert result.leaf_count == 2


def test_enumerate_partition_tree_raises_on_non_enumerable_leaf():
    client = _FakeOpsClient(total=999999)  # never eligible, at any level
    with pytest.raises(NonEnumerablePartitionError):
        enumerate_partition_tree(
            client,
            jurisdictions=["EP"],
            window_start=date(2020, 1, 1),
            window_end=date(2020, 1, 31),
            ceiling=2000,
        )
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py -v`
Expected: FAIL with `ImportError: cannot import name 'build_partition_cql'`

- [ ] **Step 7: Implement**

Append to `backend/src/main/infrastructure/sources/patent/ops_partitioning.py`:

```python
from domain.protocols.sources import RawPayload
from infrastructure.sources.patent.ops_pagination import fetch_all_ops_batches, peek_total_result_count


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
    client,
    jurisdictions: list[str],
    window_start: date,
    window_end: date,
    ceiling: int = 2000,
) -> PartitionFetchResult:
    """Drive `partition()` using real OPS total-result-count peeks, then fully
    enumerate every eligible leaf via `fetch_all_ops_batches`, returning the union
    plus the leaf count.

    Fail-closed at both stages (contract §5.4): a NonEnumerablePartitionError from
    `partition()`, or a RuntimeError from any leaf's `fetch_all_ops_batches` call,
    propagates immediately -- no partial result is ever returned. `ceiling`'s default
    (2000) is the OPS-adapter's working assumption (contract §7), not a domain fact;
    override it explicitly once PR-E0.2's live integration test confirms or corrects it.
    """
    def count_fn(p: DatePartition) -> int:
        return peek_total_result_count(client, build_partition_cql(p))

    leaves = partition(jurisdictions, window_start, window_end, count_fn=count_fn, ceiling=ceiling)

    all_batches = []
    for leaf in leaves:
        all_batches.extend(fetch_all_ops_batches(client, cql_query=build_partition_cql(leaf)))
    return PartitionFetchResult(batches=all_batches, leaf_count=len(leaves))
```

Note: `client`'s type is intentionally left unannotated with a concrete class here (matching `_PaginatedPatentSource`'s structural role in `ops_pagination.py`) — if the codebase's style prefers an explicit type hint, use `EpoOpsClient` (imported from `infrastructure.sources.patent.epo_ops_client`) to match `scripts/freeze_patent_corpus.py`'s existing convention; either is acceptable, prefer consistency with whichever this file already leans toward once Task 1/2's imports are in place.

- [ ] **Step 8: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py -v`
Expected: PASS (all tests)

- [ ] **Step 9: Commit**

```bash
git add backend/src/main/infrastructure/sources/patent/ops_pagination.py backend/src/main/infrastructure/sources/patent/ops_partitioning.py backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py backend/test/unit/infrastructure/sources/patent/test_ops_partitioning.py
git commit -m "$(cat <<'EOF'
feat: add OPS-integration driver for the partition tree (PR-E0.1)

peek_total_result_count + build_partition_cql + enumerate_partition_tree:
real total-result-count peeks drive partition(), then fetch_all_ops_batches
enumerates each eligible leaf, unioned. Fail-closed at both stages.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 4: Wire `enumerate_partition_tree` into `freeze_patent_corpus.py`

**Files:**
- Modify: `scripts/freeze_patent_corpus.py`
- Modify: `backend/test/integration/scripts/test_freeze_patent_corpus.py`

**Interfaces:**
- Consumes: `enumerate_partition_tree`, `NonEnumerablePartitionError` (Task 3).
- Produces: `build_patent_corpus(client, jurisdictions: list[str], window_start: date, window_end: date, ceiling: int, target_n: int, minimum_acceptable_n: int, dataset_id: str, dataset_version: str, description: str) -> PatentCorpusBuildResult` — the `cql_query: str` parameter is REMOVED, replaced by `window_start`/`window_end`/`ceiling`. `PatentCorpusBuildResult` gains a `leaf_count: int` field for manifest/audit purposes.

**Note on the existing fixture:** `EpoOpsClient.from_fixture_file`'s fixture-mode ignores `cql_query`/`range_start`/`range_end` entirely and always returns the whole fixture file's bytes (confirmed in PR #57's Task 3/5 review). With the multi-jurisdiction fixture's small `total-result-count` (6, well under the 2000 ceiling), `partition()` will accept each of the 6 jurisdiction-level roots as leaves with NO subdivision — so `enumerate_partition_tree` calls `fetch_all_ops_batches` once per jurisdiction (6 times), each returning the SAME full fixture content. The existing per-document jurisdiction whitelist in `build_patent_corpus` still filters correctly per document, and `select_frozen_patents`'s identical-content-dedupes-silently rule (also from PR #57's review) means the redundant refetching converges to the same 4-document result as before. This is expected and does not need architectural correction — deeper subdivision behavior is already fully covered by Task 1-3's synthetic-`count_fn` unit tests. Do not "fix" this by changing the fixture or the ceiling for this test.

- [ ] **Step 1: Write the failing tests**

Read the current `backend/test/integration/scripts/test_freeze_patent_corpus.py` first (it currently calls `build_patent_corpus` with a `cql_query=` kwarg from PR #57) and rewrite both existing tests plus add the required fail-closed end-to-end test:

```python
# backend/test/integration/scripts/test_freeze_patent_corpus.py
"""End-to-end fixture test for scripts/freeze_patent_corpus.py's build_patent_corpus(),
now driven by the partition tree (PR-E0.1) instead of a single CQL query.

No live EPO OPS credentials required -- runs entirely against the multi-jurisdiction
fixture from PR #57's Task 5.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from freeze_patent_corpus import build_patent_corpus, main  # noqa: E402

from application.evaluation.patent_corpus_builder import PatentCorpusConstructionError  # noqa: E402
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient  # noqa: E402
from infrastructure.sources.patent.ops_partitioning import NonEnumerablePartitionError  # noqa: E402

FIXTURE = REPO_ROOT / "backend" / "test" / "fixtures" / "epo_ops_multi_jurisdiction_sample.xml"
JURISDICTIONS = ["EP", "US", "JP", "CN", "KR", "WO"]


def test_build_patent_corpus_from_fixture_succeeds_below_target():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    result = build_patent_corpus(
        client=client,
        jurisdictions=JURISDICTIONS,
        window_start=date(2016, 1, 1),
        window_end=date(2026, 12, 31),
        ceiling=2000,
        target_n=50000,
        minimum_acceptable_n=1,
        dataset_id="nexus-patent-corpus-p-test",
        dataset_version="0.0.1-test",
        description="test run over fixture, partitioned",
    )

    # Fixture has 6 docs; CN (kind=B) and WO (kind=A1) are excluded by grants-only filter.
    assert len(result.corpus.patents) == 4
    assert {p.country_code for p in result.corpus.patents} == {"EP", "US", "JP", "KR"}
    assert result.leaf_count == 6  # one jurisdiction-level leaf each, no subdivision needed


def test_build_patent_corpus_raises_below_floor():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    with pytest.raises(PatentCorpusConstructionError):
        build_patent_corpus(
            client=client,
            jurisdictions=["EP"],
            window_start=date(2016, 1, 1),
            window_end=date(2026, 12, 31),
            ceiling=2000,
            target_n=50000,
            minimum_acceptable_n=1000,  # far above the 4 grants the fixture yields
            dataset_id="nexus-patent-corpus-p-test",
            dataset_version="0.0.1-test",
            description="test run over fixture, partitioned",
        )


def test_build_patent_corpus_produces_no_output_on_non_enumerable_partition(tmp_path, monkeypatch):
    """Fail-closed, end-to-end (PR-E0.1 contract §5.4): if a single partition ends up
    NON_ENUMERABLE, main() must write NO dataset file, NO manifest, NO sha256 sidecar --
    not a partial PatentCorpus."""
    import freeze_patent_corpus as script

    class _AlwaysHugeClient:
        """Every peek reports a total-result-count far above any ceiling, at every
        partition level -- forces NON_ENUMERABLE once month-level is reached."""

        def fetch_batches(self, cql_query="", range_start=1, range_end=25):
            from domain.protocols.sources import RawPayload

            xml = (
                b'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org">'
                b'<ops:biblio-search total-result-count="999999999"/></ops:world-patent-data>'
            )
            yield RawPayload(source_id="epo_ops", batch_id="huge", payload_bytes=xml, metadata={})

    monkeypatch.setattr(script, "EpoOpsClient", lambda: _AlwaysHugeClient())
    monkeypatch.setattr(script, "OUT_DIR", tmp_path)

    with pytest.raises(NonEnumerablePartitionError):
        main()

    assert list(tmp_path.iterdir()) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest backend/test/integration/scripts/test_freeze_patent_corpus.py -v`
Expected: FAIL — `TypeError: build_patent_corpus() got an unexpected keyword argument 'jurisdictions'` (or similar, against the pre-Task-4 signature) for the first two tests; `ImportError` for `NonEnumerablePartitionError` in the third.

- [ ] **Step 3: Rewrite `scripts/freeze_patent_corpus.py`**

Read the current file first (`scripts/freeze_patent_corpus.py`) — it already has `PatentCorpusBuildResult`, `build_patent_corpus`, `main`, and the module constants (`JURISDICTIONS`, `GRANT_KIND_CODES`, `TARGET_N`, `MINIMUM_ACCEPTABLE_N`, `NORMALIZER_MIN_YEAR`/`MAX_YEAR`). Apply these changes:

1. Add the import: `from infrastructure.sources.patent.ops_partitioning import enumerate_partition_tree  # noqa: E402` (remove the now-unused `from infrastructure.sources.patent.ops_query import build_patent_corpus_cql` import — `ops_query.py` itself is untouched and keeps its own tests, just no longer called from this script).

2. Add `OPS_RETRIEVAL_CEILING = 2000` beside the existing `TARGET_N`/`MINIMUM_ACCEPTABLE_N` module constants, with a one-line comment: `# PR-E0.1 contract §7: OPS-adapter working assumption, not a domain fact -- see enumerate_partition_tree's own default and the spec's confidence note.`

3. Add `leaf_count: int` to the `PatentCorpusBuildResult` dataclass, alongside the existing `corpus`, `disposition_counts`, `eligible_available_records` fields.

4. Change `build_patent_corpus`'s signature: remove `cql_query: str`, add `window_start: date`, `window_end: date`, `ceiling: int` (keep `client`, `jurisdictions`, `target_n`, `minimum_acceptable_n`, `dataset_id`, `dataset_version`, `description` unchanged). Add `from datetime import date` to the existing `from datetime import UTC, datetime` import line.

5. Inside `build_patent_corpus`, replace:
   ```python
   for raw_payload in fetch_all_ops_batches(client, cql_query=cql_query):
   ```
   with:
   ```python
   partition_result = enumerate_partition_tree(client, jurisdictions, window_start, window_end, ceiling)
   for raw_payload in partition_result.batches:
   ```
   (also remove the now-unused `fetch_all_ops_batches` import if nothing else in this file calls it directly).

6. At the end of `build_patent_corpus`, when constructing `PatentCorpusBuildResult`, add `leaf_count=partition_result.leaf_count` (from Task 3's `PartitionFetchResult`, which already carries both the unioned batches and the leaf count together — no second pass over the tree needed).

7. Replace `main()`'s docstring (the `KNOWN LIMITATION` block) with:
   ```python
   def main() -> None:
       """Run the real EPO OPS ingestion. Requires EPO_OPS_KEY/EPO_OPS_SECRET.

       Enumerates the full ADR 0020 §2 universe via jurisdiction/date partitioning
       (PR-E0.1, docs/superpowers/specs/2026-09-08-ops-enumeration-partitioning-contract.md)
       rather than one unpartitioned query -- see enumerate_partition_tree. Fails closed
       (NonEnumerablePartitionError) if any partition cannot be shown enumerable even at
       month granularity; produces no output files in that case.
       """
   ```

8. Replace `main()`'s window computation. Current:
   ```python
   current_year = datetime.now(UTC).year
   min_publication_year = current_year - 10
   max_publication_year = current_year
   cql_query = build_patent_corpus_cql(
       jurisdictions=JURISDICTIONS,
       min_publication_year=min_publication_year,
       max_publication_year=max_publication_year,
   )
   client = EpoOpsClient()
   print(f"Fetching PatentCorpus universe: {cql_query}")
   result = build_patent_corpus(
       client=client,
       cql_query=cql_query,
       jurisdictions=JURISDICTIONS,
       ...
   )
   ```
   becomes:
   ```python
   window_end = datetime.now(UTC).date()
   try:
       window_start = window_end.replace(year=window_end.year - 10)
   except ValueError:
       # window_end is Feb 29 with no Feb 29 ten years prior
       window_start = window_end.replace(year=window_end.year - 10, day=28)
   client = EpoOpsClient()
   print(f"Fetching PatentCorpus universe: {JURISDICTIONS} x [{window_start}, {window_end}]")
   result = build_patent_corpus(
       client=client,
       jurisdictions=JURISDICTIONS,
       window_start=window_start,
       window_end=window_end,
       ceiling=OPS_RETRIEVAL_CEILING,
       target_n=TARGET_N,
       minimum_acceptable_n=MINIMUM_ACCEPTABLE_N,
       dataset_id=DATASET_ID,
       dataset_version=DATASET_VERSION,
       description=(
           f"Nexus PatentCorpus (P): {', '.join(JURISDICTIONS)} grants, "
           f"{window_start} to {window_end}. See docs/adr/"
           "0020-experimental-corpus-architecture-demand-times-patent.md."
       ),
   )
   ```

9. Update the manifest dict in `main()`: replace `"cql_query": cql_query, "min_publication_year": min_publication_year, "max_publication_year": max_publication_year,` with `"window_start": window_start.isoformat(), "window_end": window_end.isoformat(), "ops_retrieval_ceiling": OPS_RETRIEVAL_CEILING, "leaf_count": result.leaf_count,`.

10. Update the final `print` block similarly (drop any reference to `cql_query`, add `leaf_count`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest backend/test/integration/scripts/test_freeze_patent_corpus.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full backend suite once**

Run: `backend/.venv/bin/python -m pytest -q`
Expected: all tests pass. Paste the verbatim final summary line in your report — this plan's predecessor (PR #57) had two separate incidents of an implementer's own full-suite run reporting phantom failures that didn't reproduce independently; be precise, and if your own run shows unexpected failures, re-run once cleanly before reporting rather than asserting a remembered count.

- [ ] **Step 6: Commit**

```bash
git add scripts/freeze_patent_corpus.py backend/test/integration/scripts/test_freeze_patent_corpus.py
git commit -m "$(cat <<'EOF'
feat: wire partitioned OPS enumeration into freeze_patent_corpus.py (PR-E0.1)

build_patent_corpus() now fetches via enumerate_partition_tree (jurisdiction/
date partitioning) instead of one unpartitioned CQL query; main() computes an
exact 10-year window and no longer carries the KNOWN LIMITATION this resolves.
Fail-closed end-to-end: a NON_ENUMERABLE partition produces zero output files.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 5: Full-suite regression check

**Files:** none (verification only).

- [ ] **Step 1: Run the entire backend test suite**

Run: `backend/.venv/bin/python -m pytest -q`
Expected: all tests pass, including every test from Tasks 1-4 and the full pre-existing suite (especially PR #57's `test_ops_pagination.py`, `test_ops_query.py`, `test_oepm_xml_normalizer_kind_code_filter.py`, `test_epo_ops_multi_jurisdiction_normalization.py`, and `test_patent_corpus_builder.py` — this plan must not alter any of their outcomes).

- [ ] **Step 2: If anything regressed, fix forward**

`ops_query.py`'s `build_patent_corpus_cql` is no longer called by `scripts/freeze_patent_corpus.py` after Task 4, but its own tests (`test_ops_query.py`) must still pass unchanged — it remains a valid, tested utility, not dead code to delete in this plan (deleting it is out of scope; flag it in the final report as a candidate for a future cleanup pass if truly unused elsewhere, but do not remove it here).

- [ ] **Step 3: No commit needed for this task** (verification-only; any fixes made in Step 2 get their own commit under the task they belong to).

---

## What this plan does not do

- Does not run a live EPO OPS ingestion, and does not require credentials for anything in Tasks 1-5.
- Does not resolve the deferred question of OPS's actual behavior at/near the retrieval ceiling (spec §6) — that is PR-E0.2's live integration test.
- Does not change `OPS_RETRIEVAL_CEILING`'s working value (2000) from a "best-available assumption" to a confirmed fact — spec §7 explicitly defers that confirmation.
- Does not modify ADR 0020, PR-E1, `AnnotationPoolEligibilityPolicy`, `CandidatePoolBuilder`, `select_frozen_patents`'s dedup/selection logic, or `PatentCorpus`'s schema.
- Does not add a partitioning axis beyond jurisdiction/date (no CPC, no kind/grant status as a partition key — spec §4).

## Self-Review

**1. Spec coverage:**
- Contract §4 (axes, 3 levels, no fourth level, half-open/closed leaf semantics) → Task 1 (`build_root_partitions`, `subdivide`), tests for clipping/contiguity. ✓
- Contract §5.1 (coverage over query space, grant-only stays downstream) → Task 1/2's leaves compose with Task 4's unchanged `allowed_kind_codes` filter; explicitly noted in Task 4's file-structure table and Global Constraints. ✓
- Contract §5.2 (disjunction) → Task 1's `test_subdivide_leaves_are_contiguous_and_disjoint`. ✓
- Contract §5.3 (eligible-for-enumeration vs. enumerated-completely) → Task 2's `partition()` (eligibility) + Task 3's `enumerate_partition_tree` (completeness via unchanged `fetch_all_ops_batches`), kept as two distinct functions/tests, never conflated. ✓
- Contract §5.4 (fail-closed) → Task 2's `NonEnumerablePartitionError` + `test_partition_fails_closed_no_partial_leaves_on_non_enumerable`; Task 4's `test_build_patent_corpus_produces_no_output_on_non_enumerable_partition` (the explicit end-to-end "no partial artifact" test required by review). ✓
- Contract §5.5 (order-independence/determinism) → Task 2's `test_partition_is_deterministic_given_deterministic_count_fn`; unchanged downstream `sha256(publication_id)` ordering untouched by this plan. ✓
- Contract §7 (ceiling as adapter config, not domain constant) → `ceiling`/`OPS_RETRIEVAL_CEILING` threaded as a parameter throughout Tasks 2-4, never hardcoded inside `partition()`'s logic; Task 4 places the named constant in the infrastructure-adjacent script layer. ✓
- User's explicit 5-phase sequence (model → pure `partition()` → invariant tests → OPS integration → `freeze_patent_corpus.py` integration) → Tasks 1, 2, 2 (tests are TDD-first within the same task), 3, 4. ✓

**2. Placeholder scan:** No TBD/TODO markers. An earlier draft of this plan had `enumerate_partition_tree` return a bare `list[RawPayload]` and only discovered while drafting Task 4 that the caller also needs the leaf count for manifest/audit purposes; fixed by having Task 3 define and return `PartitionFetchResult` (`batches` + `leaf_count`) from the start, so Task 3's own tests already exercise the real interface Task 4 consumes — no forward reference or later revision needed.

**3. Type consistency:** `DatePartition(jurisdiction, start_date, end_date, level)` field order/names used identically across Tasks 1-3. `CountFn = Callable[[DatePartition], int]` from Task 2 matches `count_fn`'s usage in Task 3's `enumerate_partition_tree`. `partition(...)`'s five keyword arguments (`jurisdictions, window_start, window_end, count_fn, ceiling`) match every call site in Tasks 2-3's tests. `build_patent_corpus`'s new signature (Task 4) matches both its test call sites and `PatentCorpusBuildResult`'s new `leaf_count` field consistently.
