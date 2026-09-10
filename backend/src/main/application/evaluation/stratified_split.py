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

from domain.models.evaluation import DevPartition, StratifiedSplitResult, TestPartition


def stratified_split[T](
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

    dev_ids: list[str] = []
    test_ids: list[str] = []
    per_stratum_counts: dict[str, dict[str, int]] = {}

    for stratum, members in strata.items():
        n_s = len(members)
        ordered = sorted(members, key=item_id)

        if n_s == 1:
            dev_count = 0
        else:
            dev_count = int(dev_fraction * n_s + 0.5)  # round-half-up: floor(x + 0.5)
            if dev_count == 0:
                dev_count = 1
            elif dev_count == n_s:
                dev_count = n_s - 1

        rng = random.Random(f"{seed}:{stratum}")
        shuffled = ordered[:]
        rng.shuffle(shuffled)

        stratum_dev = shuffled[:dev_count]
        stratum_test = shuffled[dev_count:]

        dev_ids.extend(item_id(i) for i in stratum_dev)
        test_ids.extend(item_id(i) for i in stratum_test)
        per_stratum_counts[stratum] = {"dev": len(stratum_dev), "test": len(stratum_test)}

    if not dev_ids:
        raise ValueError(
            "stratified_split: resulting Dev partition would be empty -- every "
            "stratum's size and dev_fraction combination produced zero Dev items"
        )
    if not test_ids:
        raise ValueError(
            "stratified_split: resulting Test partition would be empty -- every "
            "stratum's size and dev_fraction combination produced zero Test items"
        )

    return StratifiedSplitResult(
        dev=DevPartition(demand_ids=tuple(sorted(dev_ids))),
        test=TestPartition(demand_ids=tuple(sorted(test_ids))),
        per_stratum_counts=per_stratum_counts,
    )
