"""Unit tests for the jurisdiction -> year -> month partition tree (PR-E0.1 §4)."""

from datetime import date

import pytest

from infrastructure.sources.patent.ops_partitioning import (
    DatePartition,
    NonEnumerablePartitionError,
    build_root_partitions,
    partition,
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
