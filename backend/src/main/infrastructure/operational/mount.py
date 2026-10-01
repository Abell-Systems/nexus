from pathlib import Path

from fastapi import FastAPI, Request

from application.matching.find_assets import find_assets_for_demand
from infrastructure.operational.artifacts import load_operational_artifacts
from infrastructure.operational.errors import install_error_contract
from infrastructure.operational.router import build_router
from infrastructure.operational.selection import read_demo_selection

_DEFAULT_SELECTION = Path(__file__).resolve().parent / "demo_selection_v1.json"


def mount_operational_mvp(app: FastAPI, artifacts_dir: Path, selection: Path = _DEFAULT_SELECTION) -> None:
    artifacts = load_operational_artifacts(artifacts_dir)
    featured = read_demo_selection(selection, artifacts.demands)
    app.include_router(build_router(artifacts, featured))
    install_error_contract(app)

    @app.middleware("http")
    async def hardening_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    # The first query pays a cold-memory cost (~2 s); pay it at startup, not on the first click of a demo.
    if first := next(iter(artifacts.demands.list_all()), None):
        find_assets_for_demand(
            first.demand_id, 1, demands=artifacts.demands, retriever=artifacts.retriever,
            catalog=artifacts.catalog, policy=artifacts.policy,
        )
