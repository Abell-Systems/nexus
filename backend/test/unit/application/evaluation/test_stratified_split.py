"""Tests for the generic stratified Dev/Test split (#79).

Synthetic strata only -- this function is domain-agnostic (ADR 0026): no WPI
sector name, no real demand_id, no experiment-specific fraction/seed appears
here. See docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md.
"""

import inspect

import pytest
from pydantic import ValidationError

from application.evaluation.stratified_split import StratifiedSplitResult, StratumCount, stratified_split
from domain.models.evaluation import DevPartition, TestPartition


def _counts_by_stratum(result: StratifiedSplitResult) -> dict[str, dict[str, int]]:
    """Test-only convenience view; production code must consume StratumCount
    objects directly, never through a dict rebuilt like this."""
    return {c.stratum: {"dev": c.dev, "test": c.test} for c in result.per_stratum_counts}


class _Item:
    def __init__(self, item_id: str, stratum: str | None):
        self.item_id = item_id
        self.stratum = stratum


def _sk(item: _Item) -> str | None:
    return item.stratum


def _iid(item: _Item) -> str:
    return item.item_id


def test_rejects_empty_items():
    with pytest.raises(ValueError, match="items must not be empty"):
        stratified_split([], stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


@pytest.mark.parametrize("bad_fraction", [0.0, 1.0, -0.1, 1.1])
def test_rejects_dev_fraction_out_of_range(bad_fraction):
    items = [_Item("A", "S1"), _Item("B", "S1")]
    with pytest.raises(ValueError, match="dev_fraction"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=bad_fraction, seed=1)


def test_rejects_non_int_seed():
    items = [_Item("A", "S1"), _Item("B", "S1")]
    with pytest.raises(ValueError, match="seed"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1.5)


def test_rejects_duplicate_item_id():
    items = [_Item("A", "S1"), _Item("A", "S2")]
    with pytest.raises(ValueError, match="item_id values must be unique"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


def test_rejects_none_stratum_key():
    items = [_Item("A", "S1"), _Item("B", None)]
    with pytest.raises(ValueError, match="stratum_key returned"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


def test_rejects_empty_string_stratum_key():
    items = [_Item("A", "S1"), _Item("B", "")]
    with pytest.raises(ValueError, match="stratum_key returned"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


def test_dev_fraction_and_seed_have_no_default_value():
    """Structural guard (not a source-text regex): dev_fraction/seed must always
    come from the caller, never a backend-side default -- the #79 review's
    'verifiable prohibition' on hardcoding 0.40 in the mechanism."""
    sig = inspect.signature(stratified_split)
    assert sig.parameters["dev_fraction"].default is inspect.Parameter.empty
    assert sig.parameters["seed"].default is inspect.Parameter.empty


def _make_stratum(prefix: str, n: int) -> list[_Item]:
    return [_Item(f"{prefix}{i}", prefix) for i in range(n)]


@pytest.mark.parametrize(
    "n,expected_dev,expected_test",
    [(2, 1, 1), (3, 1, 2), (4, 2, 2), (5, 2, 3), (10, 4, 6)],
)
def test_floor_policy_table_at_dev_fraction_040(n, expected_dev, expected_test):
    """n>=2 always yields a non-empty Dev and Test on its own -- no companion
    stratum needed (unlike n=1, see test_n1_floor_requires_companion_to_observe)."""
    items = _make_stratum("S", n)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)
    assert _counts_by_stratum(result)["S"] == {"dev": expected_dev, "test": expected_test}
    assert len(result.dev.demand_ids) == expected_dev
    assert len(result.test.demand_ids) == expected_test


def test_n1_floor_requires_companion_to_observe():
    """n=1 always gets dev=0 (hardcoded, not the general formula). A companion
    stratum is required so the call doesn't hit the aggregate-empty-Dev ValueError
    that test_rejects_all_singleton_strata_as_empty_dev_partition covers in
    isolation -- this test is only about observing the n=1 count itself."""
    items = _make_stratum("S", 1) + _make_stratum("COMPANION", 2)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)
    assert _counts_by_stratum(result)["S"] == {"dev": 0, "test": 1}


def test_floor_bumps_zero_dev_up_to_one():
    """dev_fraction=0.1, n=2: formula alone gives floor(0.2+0.5)=0. Floor must bump to 1."""
    items = _make_stratum("S", 2)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.1, seed=1)
    assert _counts_by_stratum(result)["S"] == {"dev": 1, "test": 1}


def test_floor_reduces_full_dev_down_to_n_minus_one():
    """dev_fraction=0.9, n=2: formula alone gives floor(1.8+0.5)=2=n. Floor must reduce to 1."""
    items = _make_stratum("S", 2)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.9, seed=1)
    assert _counts_by_stratum(result)["S"] == {"dev": 1, "test": 1}


def test_no_overlap_and_exact_union_across_multiple_strata():
    items = _make_stratum("A", 3) + _make_stratum("B", 4) + _make_stratum("C", 1)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=7)
    dev = set(result.dev.demand_ids)
    test = set(result.test.demand_ids)
    all_ids = {i.item_id for i in items}
    assert dev & test == set()
    assert dev | test == all_ids
    assert len(dev) + len(test) == len(items)


def test_deterministic_for_same_seed():
    items = _make_stratum("A", 5) + _make_stratum("B", 4)
    r1 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=99)
    r2 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=99)
    assert r1.dev.demand_ids == r2.dev.demand_ids
    assert r1.test.demand_ids == r2.test.demand_ids


def test_different_seed_changes_membership():
    items = _make_stratum("A", 4)
    r1 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)
    r2 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=2)
    assert r1.dev.demand_ids != r2.dev.demand_ids


def test_result_independent_of_input_order():
    items = _make_stratum("A", 5) + _make_stratum("B", 4)
    reversed_items = list(reversed(items))
    r1 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=13)
    r2 = stratified_split(reversed_items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=13)
    assert r1.dev.demand_ids == r2.dev.demand_ids
    assert r1.test.demand_ids == r2.test.demand_ids


def test_rejects_all_singleton_strata_as_empty_dev_partition():
    """All strata size 1 -> every stratum's dev_count is 0 -> aggregate Dev would be
    empty. Must raise the module's own ValueError contract, not a raw pydantic
    ValidationError from DevPartition's min_length=1."""
    items = _make_stratum("A", 1) + _make_stratum("B", 1) + _make_stratum("C", 1)
    with pytest.raises(ValueError, match="resulting Dev partition would be empty"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


def test_dev_and_test_are_distinct_partition_types_on_real_result():
    items = _make_stratum("A", 3)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)
    assert isinstance(result.dev, DevPartition)
    assert isinstance(result.test, TestPartition)


def test_stratified_split_result_wraps_both_partitions_and_counts():
    result = StratifiedSplitResult(
        dev=DevPartition(demand_ids=("A",)),
        test=TestPartition(demand_ids=("B", "C")),
        per_stratum_counts=(StratumCount(stratum="SECTOR_X", dev=1, test=2),),
    )
    assert result.dev.demand_ids == ("A",)
    assert result.test.demand_ids == ("B", "C")
    assert _counts_by_stratum(result) == {"SECTOR_X": {"dev": 1, "test": 2}}


def test_per_stratum_counts_is_genuinely_immutable():
    """Regression for the review finding that frozen=True on StratifiedSplitResult
    did not stop `result.per_stratum_counts["S"]["dev"] = 999` when the field was a
    plain dict[str, dict[str, int]] -- a tuple of frozen StratumCount closes this at
    both the container (no __setitem__) and element (frozen model) level."""
    items = _make_stratum("A", 3)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)

    with pytest.raises(TypeError):
        result.per_stratum_counts[0] = StratumCount(stratum="A", dev=999, test=0)

    with pytest.raises(ValidationError):
        result.per_stratum_counts[0].dev = 999
    assert not isinstance(result.dev, TestPartition)
