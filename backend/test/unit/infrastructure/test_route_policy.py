from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from infrastructure.route_policy import restrict_to_product_routes


def _app():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"ok": True}

    product = APIRouter()

    @product.get("/api/matches")
    def matches():
        return {"matches": True}

    app.include_router(product)

    legacy = APIRouter()

    @legacy.get("/api/landscape")
    def landscape():
        return {"legacy": True}

    app.include_router(legacy)

    @app.post("/run")
    def run():
        return {"ran": True}

    @app.get("/api/demands")
    def demands():
        return {"legacy": True}

    @app.post("/api/analyze")
    def analyze():
        return {"job": 1}

    @app.get("/docs-ish")
    def docs():
        return {}

    return app


class RestrictToProductRoutesTest:
    def test_should_keep_only_health_and_the_product_routes_when_legacy_is_disabled(self):
        app = _app()
        restrict_to_product_routes(app, legacy_enabled=False)
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        assert client.get("/api/matches").status_code == 200
        assert client.get("/api/demands").status_code == 404
        assert client.get("/api/landscape").status_code == 404
        assert client.post("/api/analyze").status_code in (404, 405)
        assert client.post("/run").status_code in (404, 405)

    def test_should_leave_every_route_when_legacy_is_enabled(self):
        app = _app()
        restrict_to_product_routes(app, legacy_enabled=True)
        client = TestClient(app)
        assert client.post("/run").status_code == 200 and client.get("/api/demands").status_code == 200
