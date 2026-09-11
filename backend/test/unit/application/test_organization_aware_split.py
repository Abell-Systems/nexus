"""Tests for generic organization-aware split mechanism (ADR 0030).

Validates domain-agnostic partitioning behavior:
- Strict UNKNOWN quarantine to Dev (zero PRNG consumption).
- Exact-match organization isolation between Dev and Test.
- Fail-fast validation against invalid inputs, duplicate IDs, and pseudoreplicates.
- Reproducibility and feasibility floor mechanics via stratified_split delegation.
"""

from typing import NamedTuple

import pytest
from pydantic import ValidationError

from application.evaluation.organization_aware_split import (
    OrganizationAwareSplitResult,
    organization_aware_split,
)
from domain.models.annotation import DemandIndependenceStatus
from domain.models.evaluation import DevPartition, TestPartition


class _DummyItem(NamedTuple):
    item_id: str
    stratum: str
    org: str | None = None
    status: DemandIndependenceStatus = DemandIndependenceStatus.INDEPENDENT


def _iid(item: _DummyItem) -> str:
    return item.item_id


def _org(item: _DummyItem) -> str | None:
    return item.org


def _status(item: _DummyItem) -> DemandIndependenceStatus:
    return item.status


def _stratum(item: _DummyItem) -> str:
    return item.stratum


def test_rejects_empty_items() -> None:
    with pytest.raises(ValueError, match="organization_aware_split: items must not be empty"):
        organization_aware_split(
            [],
            item_id=_iid,
            org_key=_org,
            status_key=_status,
            stratum_key=_stratum,
            dev_fraction=0.5,
            base_seed=42,
        )


@pytest.mark.parametrize("bad_fraction", [0.0, 1.0, -0.1, 1.5])
def test_rejects_invalid_dev_fraction(bad_fraction: float) -> None:
    items = [_DummyItem("D1", "S1", "Org1")]
    with pytest.raises(ValueError, match="dev_fraction must be in \\(0, 1\\)"):
        organization_aware_split(
            items,
            item_id=_iid,
            org_key=_org,
            status_key=_status,
            stratum_key=_stratum,
            dev_fraction=bad_fraction,
            base_seed=42,
        )


@pytest.mark.parametrize("bad_seed", [True, False, 1.5, "42", None])
def test_rejects_non_int_seed(bad_seed: object) -> None:
    items = [_DummyItem("D1", "S1", "Org1")]
    with pytest.raises(ValueError, match="base_seed must be an int"):
        organization_aware_split(
            items,
            item_id=_iid,
            org_key=_org,
            status_key=_status,
            stratum_key=_stratum,
            dev_fraction=0.5,
            base_seed=bad_seed,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad_policy", ["random", "test_only", "50_50", ""])
def test_rejects_invalid_unknown_policy(bad_policy: str) -> None:
    items = [_DummyItem("D1", "S1", "Org1")]
    with pytest.raises(ValueError, match="unknown_policy must be 'dev_only'"):
        organization_aware_split(
            items,
            item_id=_iid,
            org_key=_org,
            status_key=_status,
            stratum_key=_stratum,
            dev_fraction=0.5,
            base_seed=42,
            unknown_policy=bad_policy,
        )


def test_rejects_duplicate_item_id() -> None:
    items = [
        _DummyItem("D1", "S1", "Org1"),
        _DummyItem("D1", "S2", "Org2"),
    ]
    with pytest.raises(ValueError, match="item_id values must be unique across items"):
        organization_aware_split(
            items,
            item_id=_iid,
            org_key=_org,
            status_key=_status,
            stratum_key=_stratum,
            dev_fraction=0.5,
            base_seed=42,
        )


def test_rejects_pseudoreplicate_status() -> None:
    items = [
        _DummyItem("D1", "S1", "Org1", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("D2", "S1", "Org1", DemandIndependenceStatus.PSEUDOREPLICATE),
    ]
    with pytest.raises(
        ValueError,
        match="organization_aware_split: PSEUDOREPLICATE status is not permitted in partition universe",
    ):
        organization_aware_split(
            items,
            item_id=_iid,
            org_key=_org,
            status_key=_status,
            stratum_key=_stratum,
            dev_fraction=0.5,
            base_seed=42,
        )


def test_rejects_duplicate_organization_among_independent_items() -> None:
    items = [
        _DummyItem("D1", "S1", "DuplicateOrg", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("D2", "S2", "DuplicateOrg", DemandIndependenceStatus.INDEPENDENT),
    ]
    with pytest.raises(
        ValueError,
        match="duplicate organization 'DuplicateOrg' among INDEPENDENT items",
    ):
        organization_aware_split(
            items,
            item_id=_iid,
            org_key=_org,
            status_key=_status,
            stratum_key=_stratum,
            dev_fraction=0.5,
            base_seed=42,
        )


def test_unknown_items_routed_100_percent_to_dev() -> None:
    # 2 independent items in S1 (so S1 splits 1 dev / 1 test), plus 3 UNKNOWN items
    items = [
        _DummyItem("IND-1", "S1", "OrgA", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("IND-2", "S1", "OrgB", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("UNK-1", "S1", "Anonymous Org", DemandIndependenceStatus.UNKNOWN),
        _DummyItem("UNK-2", "S2", None, DemandIndependenceStatus.UNKNOWN),
        _DummyItem("UNK-3", "S3", "Anonymous Org", DemandIndependenceStatus.UNKNOWN),
    ]
    result = organization_aware_split(
        items,
        item_id=_iid,
        org_key=_org,
        status_key=_status,
        stratum_key=_stratum,
        dev_fraction=0.5,
        base_seed=42,
    )

    # All UNKNOWNs must be in Dev
    assert "UNK-1" in result.dev.demand_ids
    assert "UNK-2" in result.dev.demand_ids
    assert "UNK-3" in result.dev.demand_ids

    # Zero UNKNOWNs in Test
    assert "UNK-1" not in result.test.demand_ids
    assert "UNK-2" not in result.test.demand_ids
    assert "UNK-3" not in result.test.demand_ids

    assert result.unknown_count == 3
    assert result.independent_count == 2
    assert len(result.dev.demand_ids) == 4  # 1 independent + 3 unknown
    assert len(result.test.demand_ids) == 1  # 1 independent


def test_feasibility_floor_on_singletons() -> None:
    # S_SINGLE has 1 independent item -> feasibility floor must allocate it to Test
    # S_MULTI has 2 independent items -> splits 1 dev, 1 test
    items = [
        _DummyItem("SINGLE-1", "S_SINGLE", "OrgSingle", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("MULTI-1", "S_MULTI", "OrgMulti1", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("MULTI-2", "S_MULTI", "OrgMulti2", DemandIndependenceStatus.INDEPENDENT),
    ]
    result = organization_aware_split(
        items,
        item_id=_iid,
        org_key=_org,
        status_key=_status,
        stratum_key=_stratum,
        dev_fraction=0.5,
        base_seed=42,
    )

    assert "SINGLE-1" in result.test.demand_ids
    assert "SINGLE-1" not in result.dev.demand_ids
    assert len(result.dev.demand_ids) == 1
    assert len(result.test.demand_ids) == 2


def test_clean_isolation_and_disjoint_organizations() -> None:
    items = [
        _DummyItem("IND-1", "S1", "Org1", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("IND-2", "S1", "Org2", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("IND-3", "S2", "Org3", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("IND-4", "S2", "Org4", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("UNK-1", "S1", None, DemandIndependenceStatus.UNKNOWN),
    ]
    result = organization_aware_split(
        items,
        item_id=_iid,
        org_key=_org,
        status_key=_status,
        stratum_key=_stratum,
        dev_fraction=0.5,
        base_seed=42,
    )

    item_org_map = {i.item_id: i.org for i in items}
    dev_orgs = {item_org_map[did] for did in result.dev.demand_ids if item_org_map[did] is not None}
    test_orgs = {item_org_map[did] for did in result.test.demand_ids if item_org_map[did] is not None}

    assert dev_orgs.isdisjoint(test_orgs)
    # Dev and Test partition sets must be disjoint
    assert set(result.dev.demand_ids).isdisjoint(set(result.test.demand_ids))
    # Full coverage of items
    assert set(result.dev.demand_ids) | set(result.test.demand_ids) == {i.item_id for i in items}


def test_deterministic_reproducibility() -> None:
    items = [
        _DummyItem(f"IND-{i}", f"S{i % 3}", f"Org{i}", DemandIndependenceStatus.INDEPENDENT)
        for i in range(12)
    ] + [
        _DummyItem(f"UNK-{j}", f"S{j % 2}", None, DemandIndependenceStatus.UNKNOWN)
        for j in range(6)
    ]

    res1 = organization_aware_split(
        items,
        item_id=_iid,
        org_key=_org,
        status_key=_status,
        stratum_key=_stratum,
        dev_fraction=0.5,
        base_seed=42,
    )
    res2 = organization_aware_split(
        items,
        item_id=_iid,
        org_key=_org,
        status_key=_status,
        stratum_key=_stratum,
        dev_fraction=0.5,
        base_seed=42,
    )

    assert res1.dev.demand_ids == res2.dev.demand_ids
    assert res1.test.demand_ids == res2.test.demand_ids
    assert res1.per_stratum_counts == res2.per_stratum_counts
    assert res1.independent_count == res2.independent_count
    assert res1.unknown_count == res2.unknown_count


def test_split_result_types_and_immutability() -> None:
    items = [
        _DummyItem("IND-1", "S1", "Org1", DemandIndependenceStatus.INDEPENDENT),
        _DummyItem("IND-2", "S1", "Org2", DemandIndependenceStatus.INDEPENDENT),
    ]
    result = organization_aware_split(
        items,
        item_id=_iid,
        org_key=_org,
        status_key=_status,
        stratum_key=_stratum,
        dev_fraction=0.5,
        base_seed=42,
    )

    assert isinstance(result, OrganizationAwareSplitResult)
    assert isinstance(result.dev, DevPartition)
    assert isinstance(result.test, TestPartition)

    with pytest.raises(ValidationError):
        result.independent_count = 999  # type: ignore[misc]

    with pytest.raises(ValidationError):
        result.dev = DevPartition(demand_ids=("MUTATED",))  # type: ignore[misc]
