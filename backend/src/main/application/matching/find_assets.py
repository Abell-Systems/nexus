from dataclasses import dataclass

from domain.models.demand import DemandSignal
from domain.protocols.demand_repository import DemandRepository
from domain.protocols.matching import PatentCandidateRetriever


class UnknownDemandError(KeyError):
    """The demand is not one of the demands this product offers."""


@dataclass(frozen=True)
class AssetMatch:
    rank: int
    publication_id: str


def find_assets_for_demand(
    demand_id: str,
    limit: int,
    *,
    demands: DemandRepository,
    retriever: PatentCandidateRetriever,
) -> tuple[DemandSignal, list[AssetMatch]]:
    """Ranks eligible assets for a known demand. The rank is the only ordering signal exposed to callers."""
    demand = demands.get(demand_id)
    if demand is None:
        raise UnknownDemandError(demand_id)
    candidates = retriever.retrieve(demand, limit=limit)
    return demand, [AssetMatch(rank=i, publication_id=c.publication_id) for i, c in enumerate(candidates, start=1)]
