"""Generic organization-aware Dev/Test split mechanism (ADR 0030).

Implements the domain-agnostic organization-aware split contract:
- Quarantines UNKNOWN status observations 100% to Dev (zero PRNG consumption).
- Partitions INDEPENDENT status observations into Dev and Test via stratified_split,
  verifying exact-match organization uniqueness (zero cross-partition leakage).
- Forbids PSEUDOREPLICATE status observations in the partition universe.
"""

from collections.abc import Callable, Sequence

from pydantic import BaseModel, ConfigDict

from application.evaluation.stratified_split import StratumCount, stratified_split
from domain.models.annotation import DemandIndependenceStatus
from domain.models.evaluation import DevPartition, TestPartition


class OrganizationAwareSplitResult(BaseModel):
    """Immutable result carrying the partitions and stratification audit metadata."""

    model_config = ConfigDict(frozen=True)

    dev: DevPartition
    test: TestPartition
    per_stratum_counts: tuple[StratumCount, ...]
    independent_count: int
    unknown_count: int


def organization_aware_split[T](
    items: Sequence[T],
    item_id: Callable[[T], str],
    org_key: Callable[[T], str | None],
    status_key: Callable[[T], DemandIndependenceStatus],
    stratum_key: Callable[[T], str],
    dev_fraction: float,
    base_seed: int,
    unknown_policy: str = "dev_only",
) -> OrganizationAwareSplitResult:
    """Split items into Dev and Test partitions with organization isolation."""
    if not items:
        raise ValueError("organization_aware_split: items must not be empty")
    if not (0.0 < dev_fraction < 1.0):
        raise ValueError(
            f"organization_aware_split: dev_fraction must be in (0, 1), got {dev_fraction!r}"
        )
    if not isinstance(base_seed, int) or isinstance(base_seed, bool):
        raise ValueError(
            f"organization_aware_split: base_seed must be an int, got {base_seed!r}"
        )
    if unknown_policy != "dev_only":
        raise ValueError(
            f"organization_aware_split: unknown_policy must be 'dev_only', got {unknown_policy!r}"
        )

    ids = [item_id(item) for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(
            "organization_aware_split: item_id values must be unique across items"
        )

    dev_unknown_ids: list[str] = []
    independent_items: list[T] = []

    for item in items:
        status = status_key(item)
        if status == DemandIndependenceStatus.PSEUDOREPLICATE:
            raise ValueError(
                "organization_aware_split: PSEUDOREPLICATE status is not permitted in partition universe"
            )
        if status == DemandIndependenceStatus.UNKNOWN:
            dev_unknown_ids.append(item_id(item))
        elif status == DemandIndependenceStatus.INDEPENDENT:
            independent_items.append(item)
        else:
            raise ValueError(
                f"organization_aware_split: unsupported status {status!r} for item_id={item_id(item)!r}"
            )

    seen_orgs: set[str] = set()
    for item in independent_items:
        org = org_key(item)
        if org is not None:
            if org in seen_orgs:
                raise ValueError(
                    f"organization_aware_split: duplicate organization {org!r} among INDEPENDENT items"
                )
            seen_orgs.add(org)

    stratified_res = stratified_split(
        independent_items,
        stratum_key=stratum_key,
        item_id=item_id,
        dev_fraction=dev_fraction,
        seed=base_seed,
    )

    dev_ids = tuple(sorted(dev_unknown_ids + list(stratified_res.dev.demand_ids)))
    test_ids = tuple(sorted(stratified_res.test.demand_ids))

    return OrganizationAwareSplitResult(
        dev=DevPartition(demand_ids=dev_ids),
        test=TestPartition(demand_ids=test_ids),
        per_stratum_counts=stratified_res.per_stratum_counts,
        independent_count=len(independent_items),
        unknown_count=len(dev_unknown_ids),
    )
