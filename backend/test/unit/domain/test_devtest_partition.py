"""Tests for DevPartition/TestPartition/StratifiedSplitResult (#79).

DevPartition and TestPartition are deliberately distinct types -- not two fields
on one class -- so a future consumer's constructor can type-hint one and be
statically/structurally unable to accept the other. See
docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md.
"""

import pytest
from pydantic import ValidationError

from domain.models.evaluation import DevPartition, StratifiedSplitResult, TestPartition


def test_dev_partition_holds_demand_ids():
    p = DevPartition(demand_ids=("A", "B"))
    assert p.demand_ids == ("A", "B")


def test_test_partition_holds_demand_ids():
    p = TestPartition(demand_ids=("C", "D"))
    assert p.demand_ids == ("C", "D")


def test_dev_partition_is_frozen():
    p = DevPartition(demand_ids=("A",))
    with pytest.raises(ValidationError):
        p.demand_ids = ("B",)


def test_dev_partition_rejects_empty():
    with pytest.raises(ValidationError):
        DevPartition(demand_ids=())


def test_dev_partition_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        DevPartition(demand_ids=("A", "A"))


def test_test_partition_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        TestPartition(demand_ids=("A", "A"))


def test_dev_partition_and_test_partition_are_distinct_types():
    dev = DevPartition(demand_ids=("A",))
    test = TestPartition(demand_ids=("A",))
    assert type(dev) is not type(test)
    assert not isinstance(dev, TestPartition)
    assert not isinstance(test, DevPartition)


def test_stratified_split_result_wraps_both_partitions_and_counts():
    result = StratifiedSplitResult(
        dev=DevPartition(demand_ids=("A",)),
        test=TestPartition(demand_ids=("B", "C")),
        per_stratum_counts={"SECTOR_X": {"dev": 1, "test": 2}},
    )
    assert result.dev.demand_ids == ("A",)
    assert result.test.demand_ids == ("B", "C")
    assert result.per_stratum_counts == {"SECTOR_X": {"dev": 1, "test": 2}}
