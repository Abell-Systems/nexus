"""Pure sampling logic for the pre-registered dense-exclusive stratified
sample (docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md).

No I/O here -- this module only implements SS6 (demand allocation) and SS8
(within-demand selection) of the spec. The scripts that call it are
responsible for reading the frozen source data and writing output.
"""

import random

SAMPLING_SEED = 104
BLIND_EXPORT_SEED = 42


def largest_remainder_allocation(total_n: int, sizes: dict[str, int]) -> dict[str, int]:
    """Spreads total_n as evenly as possible across sizes.keys(), largest-remainder
    rounding, remainder assigned in ascending lexicographic demand_id order (the
    spec's SS6 deterministic tie-break). Raises ValueError if total_n exceeds the
    combined capacity, or if any single demand's allocation would exceed its size.
    """
    if total_n > sum(sizes.values()):
        raise ValueError(
            f"total_n={total_n} exceeds combined capacity={sum(sizes.values())}"
        )
    ids = sorted(sizes)
    m = len(ids)
    base = total_n // m
    remainder = total_n - base * m
    allocation = {demand_id: base for demand_id in ids}
    for demand_id in ids[:remainder]:
        allocation[demand_id] += 1
    for demand_id in ids:
        if allocation[demand_id] > sizes[demand_id]:
            raise ValueError(
                f"{demand_id}: allocation {allocation[demand_id]} exceeds pool size {sizes[demand_id]}"
            )
    return allocation


def select_stratified_sample(
    candidates_by_demand: dict[str, list[str]],
    allocation: dict[str, int],
    seed: int,
) -> dict[str, list[str]]:
    """Uniform random draw without replacement per demand (spec SS8). One
    random.Random instance is seeded once and reused across all demands, visited
    in ascending lexicographic demand_id order, each demand's candidate list
    pre-sorted before sampling -- both required for bit-for-bit reproducibility
    regardless of input dict ordering.
    """
    rng = random.Random(seed)
    selected: dict[str, list[str]] = {}
    for demand_id in sorted(allocation):
        pool = sorted(candidates_by_demand[demand_id])
        k = allocation[demand_id]
        selected[demand_id] = rng.sample(pool, k)
    return selected
