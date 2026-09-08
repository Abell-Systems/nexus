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
