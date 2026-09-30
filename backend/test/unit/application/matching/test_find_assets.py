import pytest

from application.matching.find_assets import UnknownDemandError, find_assets_for_demand, list_demand_examples
from domain.models.asset import Asset
from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, EligibilityReason, EligibilityResult, RetrievalMethod
from domain.models.patent import PatentDocument


class _Demands:
    def __init__(self, demands):
        self._by_id = {d.demand_id: d for d in demands}

    def get(self, demand_id):
        return self._by_id.get(demand_id)

    def list_all(self):
        return list(self._by_id.values())


class _Catalog:
    def __init__(self, assets):
        self._by_id = {a.patent.publication_id: a for a in assets}

    def get(self, publication_id):
        return self._by_id[publication_id]

    def list_all(self):
        return list(self._by_id.values())


class _Retriever:
    def __init__(self, ids):
        self._ids = ids
        self.calls = []

    def retrieve(self, demand, *, limit=100):
        self.calls.append((demand.demand_id, limit))
        return [Candidate(publication_id=i, retrieval_scores={RetrievalMethod.SEMANTIC: 0.5}) for i in self._ids[:limit]]


class _EligibleUnless:
    def __init__(self, *excluded):
        self._excluded = set(excluded)

    def evaluate(self, patent, demand):
        eligible = patent.publication_id not in self._excluded
        reason = EligibilityReason.ELIGIBLE if eligible else EligibilityReason.EXCLUDED_JURISDICTION
        return EligibilityResult(publication_id=patent.publication_id, is_eligible=eligible, reason=reason)


def _demand(demand_id="D-1"):
    return DemandSignal(demand_id=demand_id, title="t", description="d")


def _asset(publication_id):
    patent = PatentDocument(publication_id=publication_id, country_code="ES", doc_number="1", kind_code="A1", title="t", abstract="a")
    return Asset(patent=patent, ip_type="patent", abstract_language="es")


def _find(ids=("ES-2-A1", "ES-1-A1"), limit=5, policy=None, demands=None, retriever=None):
    catalog = _Catalog([_asset("ES-1-A1"), _asset("ES-2-A1"), _asset("EP-3-B1")])
    return find_assets_for_demand(
        "D-1", limit,
        demands=demands or _Demands([_demand()]),
        retriever=retriever or _Retriever(list(ids)),
        catalog=catalog,
        policy=policy or _EligibleUnless("EP-3-B1"),
    )


class FindAssetsForDemandTest:
    def test_should_rank_assets_from_one_in_retriever_order_when_demand_is_known(self):
        result = _find()
        assert result.demand.demand_id == "D-1"
        assert [(r.rank, r.asset.patent.publication_id) for r in result.assets] == [(1, "ES-2-A1"), (2, "ES-1-A1")]

    def test_should_pass_limit_to_retriever_when_searching(self):
        retriever = _Retriever(["ES-1-A1", "ES-2-A1"])
        result = _find(limit=1, retriever=retriever)
        assert retriever.calls == [("D-1", 1)] and len(result.assets) == 1

    def test_should_return_no_assets_when_retriever_finds_nothing(self):
        assert _find(ids=()).assets == []

    def test_should_count_only_assets_the_policy_makes_eligible_when_reporting_eligible_count(self):
        assert _find().eligible_count == 2
        assert _find(policy=_EligibleUnless("EP-3-B1", "ES-1-A1")).eligible_count == 1

    def test_should_raise_unknown_demand_when_id_is_not_in_repository(self):
        with pytest.raises(UnknownDemandError):
            find_assets_for_demand(
                "D-9", 5, demands=_Demands([_demand()]), retriever=_Retriever([]), catalog=_Catalog([]), policy=_EligibleUnless()
            )


class ListDemandExamplesTest:
    def test_should_list_every_demand_in_repository_order_when_no_selection_is_given(self):
        demands = _Demands([_demand("D-2"), _demand("D-1")])
        assert [d.demand_id for d in list_demand_examples(demands)] == ["D-2", "D-1"]

    def test_should_list_only_featured_demands_keeping_repository_order_when_a_selection_is_given(self):
        demands = _Demands([_demand("D-2"), _demand("D-1"), _demand("D-3")])
        assert [d.demand_id for d in list_demand_examples(demands, featured=frozenset({"D-3", "D-2"}))] == ["D-2", "D-3"]
