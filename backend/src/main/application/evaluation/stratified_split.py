"""Generic stratified Dev/Test split with a feasibility-floor allocation policy.

Implements the algorithm fixed by docs/superpowers/specs/
2026-09-10-stratified-devtest-split-design.md. Domain-agnostic (ADR 0026): callers
supply the stratum key, the item id, the target Dev fraction, and the seed --
nothing here assumes a WPI sector name, a specific N, or a specific fraction/seed
value. dev_fraction and seed have no default value by design (see that spec's
"Architecture" section) so a caller cannot silently inherit a backend-side default.
"""

import random
from collections.abc import Callable, Sequence
from typing import TypeVar

from domain.models.evaluation import DevPartition, StratifiedSplitResult, TestPartition

T = TypeVar("T")


def stratified_split(
    items: Sequence[T],
    stratum_key: Callable[[T], str | None],
    item_id: Callable[[T], str],
    dev_fraction: float,
    seed: int,
) -> StratifiedSplitResult:
    if not items:
        raise ValueError("stratified_split: items must not be empty")
    if not (0.0 < dev_fraction < 1.0):
        raise ValueError(f"stratified_split: dev_fraction must be in (0, 1), got {dev_fraction!r}")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"stratified_split: seed must be an int, got {seed!r}")

    ids = [item_id(item) for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("stratified_split: item_id values must be unique across items")

    strata: dict[str, list[T]] = {}
    for item in items:
        key = stratum_key(item)
        if not key:
            raise ValueError(
                f"stratified_split: stratum_key returned {key!r} for "
                f"item_id={item_id(item)!r} -- a missing/empty stratum key is not permitted"
            )
        strata.setdefault(key, []).append(item)

    raise NotImplementedError("allocation policy implemented in Task 3")
