import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.operational.router import build_router
from infrastructure.operational.service import OperationalMatchingService


@pytest.fixture
def client(operational_dir):
    app = FastAPI()
    app.include_router(build_router(OperationalMatchingService.from_directory(operational_dir)))
    return TestClient(app)


class OperationalRouterTest:
    def test_should_list_example_demands_with_notices_when_requested(self, client):
        body = client.get("/api/demand-examples").json()
        assert [d["demand_id"] for d in body["demands"]] == ["D-1", "D-2"] and len(body["notices"]) == 4

    def test_should_return_ranked_assets_with_default_limit_when_demand_is_known(self, client):
        response = client.get("/api/matches", params={"demand_id": "D-1"})
        assert response.status_code == 200
        assert [a["rank"] for a in response.json()["assets"]] == [1, 2, 3]

    def test_should_return_404_when_demand_is_unknown(self, client):
        assert client.get("/api/matches", params={"demand_id": "D-9"}).status_code == 404

    @pytest.mark.parametrize("limit", [0, 11, -1])
    def test_should_return_422_when_limit_is_outside_one_to_ten(self, client, limit):
        assert client.get("/api/matches", params={"demand_id": "D-1", "limit": limit}).status_code == 422

    def test_should_return_422_when_demand_id_is_missing(self, client):
        assert client.get("/api/matches").status_code == 422

    def test_should_honour_limit_when_fewer_assets_requested(self, client):
        assert len(client.get("/api/matches", params={"demand_id": "D-1", "limit": 1}).json()["assets"]) == 1

    def test_should_return_422_when_demand_id_is_absurdly_long(self, client):
        assert client.get("/api/matches", params={"demand_id": "D" * 65}).status_code == 422
