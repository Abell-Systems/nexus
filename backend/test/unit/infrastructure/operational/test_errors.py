import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from infrastructure.operational.artifacts import load_operational_artifacts
from infrastructure.operational.errors import install_error_contract
from infrastructure.operational.router import build_router


@pytest.fixture
def client(operational_dir):
    app = FastAPI()
    app.include_router(build_router(load_operational_artifacts(operational_dir)))

    @app.get("/api/legacy")
    def legacy(n: int = Query(...)) -> dict:
        return {"n": n}

    install_error_contract(app)
    return TestClient(app, raise_server_exceptions=False)


class ErrorContractTest:
    def test_should_return_demand_not_found_code_when_demand_is_unknown(self, client):
        response = client.get("/api/matches", params={"demand_id": "D-9"})
        assert response.status_code == 404
        assert response.json() == {"code": "DEMAND_NOT_FOUND", "message": "La demanda 'D-9' no existe."}

    @pytest.mark.parametrize("params, field", [({"demand_id": "D-1", "limit": 0}, "limit"), ({}, "demand_id")])
    def test_should_return_invalid_request_code_naming_the_field_when_a_parameter_is_invalid(self, client, params, field):
        response = client.get("/api/matches", params=params)
        assert response.status_code == 422
        assert response.json() == {"code": "INVALID_REQUEST", "message": f"Valor no válido para el parámetro '{field}'."}

    def test_should_return_the_same_contract_when_method_is_not_allowed(self, client):
        response = client.post("/api/matches")
        assert response.status_code == 405
        assert set(response.json()) == {"code", "message"}

    def test_should_return_internal_error_without_details_when_the_use_case_fails_unexpectedly(self, operational_dir):
        artifacts = load_operational_artifacts(operational_dir)
        artifacts.retriever.retrieve = lambda demand, limit: (_ for _ in ()).throw(RuntimeError("secret path /srv/x"))
        app = FastAPI()
        app.include_router(build_router(artifacts))
        install_error_contract(app)
        response = TestClient(app, raise_server_exceptions=False).get("/api/matches", params={"demand_id": "D-1"})
        assert response.status_code == 500
        assert response.json() == {"code": "INTERNAL_ERROR", "message": "Error interno."}

    def test_should_leave_the_legacy_error_shape_untouched_when_a_non_mvp_route_fails_validation(self, client):
        response = client.get("/api/legacy")
        assert response.status_code == 422 and "detail" in response.json()
