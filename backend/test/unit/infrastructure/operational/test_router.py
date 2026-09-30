import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.operational.artifacts import load_operational_artifacts
from infrastructure.operational.errors import install_error_contract
from infrastructure.operational.notices import NOTICES
from infrastructure.operational.router import build_router

_SCORE_KEYS = {"score", "scores", "retrieval_scores", "similarity", "band", "relevance_band", "distance"}


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


def _client(artifacts, featured=None):
    app = FastAPI()
    app.include_router(build_router(artifacts, featured))
    install_error_contract(app)
    return TestClient(app)


@pytest.fixture
def artifacts(operational_dir):
    return load_operational_artifacts(operational_dir)


@pytest.fixture
def client(artifacts):
    return _client(artifacts)


def _matches(client, demand_id="D-1", **params):
    return client.get("/api/matches", params={"demand_id": demand_id, **params})


class DemandExamplesRouteTest:
    def test_should_list_example_demands_in_corpus_order_with_notices_when_requested(self, client):
        body = client.get("/api/demand-examples").json()
        assert [d["demand_id"] for d in body["demands"]] == ["D-1", "D-2"]
        assert body["demands"][0]["source_url"] == "https://example.org/d1"
        assert body["notices"] == list(NOTICES)

    def test_should_list_only_featured_demands_when_a_selection_is_given(self, artifacts):
        body = _client(artifacts, frozenset({"D-2"})).get("/api/demand-examples").json()
        assert [d["demand_id"] for d in body["demands"]] == ["D-2"]

    def test_should_still_answer_matches_for_a_demand_outside_the_selection(self, artifacts):
        assert len(_matches(_client(artifacts, frozenset({"D-2"})), "D-1").json()["assets"]) == 3


class MatchesRouteTest:
    def test_should_rank_assets_by_dense_similarity_when_demand_is_known(self, client):
        assets = _matches(client).json()["assets"]
        assert [a["publication_id"] for a in assets] == ["ES-1000002-U", "ES-1000003-A1", "ES-1000001-A1"]
        assert [a["rank"] for a in assets] == [1, 2, 3]

    def test_should_return_results_when_demand_has_no_posted_date(self, client):
        body = _matches(client, "D-2").json()
        assert body["demand"]["demand_id"] == "D-2" and len(body["assets"]) == 3

    def test_should_not_pad_when_limit_exceeds_eligible_assets(self, client):
        body = _matches(client, limit=10).json()
        assert len(body["assets"]) == 3 and body["meta"]["eligible_count"] == 3

    def test_should_honour_limit_when_fewer_assets_requested(self, client):
        assert len(_matches(client, limit=1).json()["assets"]) == 1

    def test_should_exclude_ep_asset_when_jurisdiction_is_not_es(self, client):
        assert "EP-1000004-B1" not in [a["publication_id"] for a in _matches(client).json()["assets"]]

    def test_should_expose_holders_type_abstract_cpc_and_links_when_asset_is_returned(self, client):
        asset = _matches(client).json()["assets"][0]
        assert asset["ip_type"] == "utility_model" and asset["assignees"] == ["BETA SL"]
        assert asset["abstract"] == "Abstract two" and asset["abstract_language"] == "es"
        assert asset["source_links"]["google_patents"].endswith("ES1000002U")
        assert asset["cpc_codes"] == [] and asset["publication_date"] == "2020-02-01"

    def test_should_not_expose_any_score_like_key_when_serialising_matches_and_examples(self, client):
        keys = set(_keys(_matches(client).json())) | set(_keys(client.get("/api/demand-examples").json()))
        assert not keys & _SCORE_KEYS

    def test_should_serve_the_four_fixed_notices_and_corpus_identity_in_meta(self, client):
        meta = _matches(client).json()["meta"]
        assert meta["notices"] == list(NOTICES) and meta["retrieval"] == "dense"
        assert meta["corpus_id"] == "NEXUS-OPERATIONAL-CORPUS-V1"
        assert len(meta["corpus_parquet_sha256"]) == 64 and len(meta["embedding_index_sha256"]) == 64

    def test_should_answer_a_repeated_request_from_memory_when_artifacts_are_frozen(self, artifacts):
        calls = []
        real = artifacts.retriever.retrieve
        artifacts.retriever.retrieve = lambda demand, limit: calls.append(demand.demand_id) or real(demand, limit=limit)
        client = _client(artifacts)
        first = _matches(client, limit=3).json()
        assert _matches(client, limit=3).json() == first and calls == ["D-1"]

    def test_should_return_404_when_demand_is_unknown(self, client):
        assert _matches(client, "D-9").status_code == 404

    @pytest.mark.parametrize("limit", [0, 11, -1])
    def test_should_return_422_when_limit_is_outside_one_to_ten(self, client, limit):
        assert _matches(client, limit=limit).status_code == 422

    def test_should_return_422_when_demand_id_is_missing(self, client):
        assert client.get("/api/matches").status_code == 422

    def test_should_return_422_when_demand_id_is_absurdly_long(self, client):
        assert _matches(client, "D" * 65).status_code == 422
