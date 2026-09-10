"""Tests for the generic stratified Dev/Test split (#79).

Synthetic strata only -- this function is domain-agnostic (ADR 0026): no WPI
sector name, no real demand_id, no experiment-specific fraction/seed appears
here. See docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md.
"""

import inspect

import pytest

from application.evaluation.stratified_split import stratified_split


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
