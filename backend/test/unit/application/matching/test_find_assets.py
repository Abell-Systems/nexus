import pytest

from application.matching.find_assets import AssetMatch, UnknownDemandError, find_assets_for_demand
from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, RetrievalMethod


class _Demands:
    def __init__(self, demands):
        self._by_id = {d.demand_id: d for d in demands}

    def get(self, demand_id):
        return self._by_id.get(demand_id)

    def list_all(self):
        return list(self._by_id.values())


class _Retriever:
    """Boundary fake: the retrieval port, not an internal layer."""

    def __init__(self, ids):
        self._ids = ids
        self.calls = []

    def retrieve(self, demand, *, limit=100):
        self.calls.append((demand.demand_id, limit))
        return [Candidate(publication_id=i, retrieval_scores={RetrievalMethod.SEMANTIC: 0.5}) for i in self._ids[:limit]]


def _demand(demand_id="D-1"):
    return DemandSignal(demand_id=demand_id, title="t", description="d")


class FindAssetsForDemandTest:
    def test_should_rank_from_one_in_retriever_order_when_demand_is_known(self):
        retriever = _Retriever(["ES-2-A1", "ES-1-A1"])
        demand, matches = find_assets_for_demand("D-1", 5, demands=_Demands([_demand()]), retriever=retriever)
        assert demand.demand_id == "D-1"
        assert matches == [AssetMatch(1, "ES-2-A1"), AssetMatch(2, "ES-1-A1")]

    def test_should_pass_limit_to_retriever_when_searching(self):
        retriever = _Retriever(["A", "B", "C"])
        _, matches = find_assets_for_demand("D-1", 2, demands=_Demands([_demand()]), retriever=retriever)
        assert retriever.calls == [("D-1", 2)] and len(matches) == 2

    def test_should_return_empty_list_when_retriever_finds_nothing(self):
        _, matches = find_assets_for_demand("D-1", 5, demands=_Demands([_demand()]), retriever=_Retriever([]))
        assert matches == []

    def test_should_raise_unknown_demand_when_id_is_not_in_repository(self):
        with pytest.raises(UnknownDemandError):
            find_assets_for_demand("D-9", 5, demands=_Demands([_demand()]), retriever=_Retriever([]))
