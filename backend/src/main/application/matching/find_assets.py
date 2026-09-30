from dataclasses import dataclass

from domain.models.asset import Asset
from domain.models.demand import DemandSignal
from domain.protocols.asset_catalog import AssetCatalog
from domain.protocols.demand_repository import DemandRepository
from domain.protocols.matching import PatentCandidateRetriever, PatentEligibilityPolicy


class UnknownDemandError(KeyError):
    pass


@dataclass(frozen=True)
class RankedAsset:
    rank: int
    asset: Asset


@dataclass(frozen=True)
class AssetsForDemand:
    demand: DemandSignal
    assets: list[RankedAsset]
    eligible_count: int


def find_assets_for_demand(
    demand_id: str,
    limit: int,
    *,
    demands: DemandRepository,
    retriever: PatentCandidateRetriever,
    catalog: AssetCatalog,
    policy: PatentEligibilityPolicy,
) -> AssetsForDemand:
    """Ranks eligible assets for a known demand. The rank is the only ordering signal exposed to callers."""
    demand = demands.get(demand_id)
    if demand is None:
        raise UnknownDemandError(demand_id)
    candidates = retriever.retrieve(demand, limit=limit)
    eligible_count = sum(1 for asset in catalog.list_all() if policy.evaluate(asset.patent, demand).is_eligible)
    ranked = [RankedAsset(rank, catalog.get(c.publication_id)) for rank, c in enumerate(candidates, start=1)]
    return AssetsForDemand(demand=demand, assets=ranked, eligible_count=eligible_count)


def list_demand_examples(demands: DemandRepository, *, featured: frozenset[str] | None = None) -> list[DemandSignal]:
    return [d for d in demands.list_all() if featured is None or d.demand_id in featured]
