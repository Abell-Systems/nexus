from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from infrastructure.operational.app import create_mvp_app
from infrastructure.operational.notices import NOTICES

REAL_ARTIFACTS = Path(__file__).resolve().parents[4] / "data" / "snapshots" / "operational_corpus_v1"
pytestmark = pytest.mark.skipif(not REAL_ARTIFACTS.exists(), reason="frozen operational artifacts are not in this checkout")

PRIMARY_JOURNEYS = ["INNOGET-1935", "INNOGET-2258", "INNOGET-2417"]


@pytest.fixture(scope="module")
def client():
    return TestClient(create_mvp_app(REAL_ARTIFACTS), raise_server_exceptions=False)


class OperationalMvpOverHttpTest:
    def test_should_list_the_twenty_one_demo_demands_with_the_four_notices_when_the_screen_loads(self, client):
        body = client.get("/api/demand-examples").json()
        assert len(body["demands"]) == 21 and body["notices"] == list(NOTICES)

    @pytest.mark.parametrize("demand_id", PRIMARY_JOURNEYS)
    def test_should_return_five_ranked_spanish_assets_with_sources_when_a_journey_demand_is_chosen(self, client, demand_id):
        body = client.get("/api/matches", params={"demand_id": demand_id}).json()
        assets = body["assets"]
        assert [a["rank"] for a in assets] == [1, 2, 3, 4, 5]
        assert all(a["country_code"] == "ES" and a["abstract"] and a["source_links"]["google_patents"] for a in assets)
        assert body["demand"]["demand_id"] == demand_id and body["meta"]["eligible_count"] > 0

    def test_should_keep_the_frozen_top_result_when_the_water_quality_demand_is_chosen(self, client):
        top = client.get("/api/matches", params={"demand_id": "INNOGET-1935"}).json()["assets"][0]
        assert top["publication_id"] == "ES-1295722-U"

    def test_should_answer_with_the_error_contract_when_the_demand_is_unknown(self, client):
        response = client.get("/api/matches", params={"demand_id": "NOPE"})
        assert response.status_code == 404 and response.json()["code"] == "DEMAND_NOT_FOUND"
