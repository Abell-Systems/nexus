import os
from pathlib import Path

from fastapi import FastAPI, Request

from application.matching.find_assets import find_assets_for_demand
from infrastructure.operational.artifacts import load_operational_artifacts
from infrastructure.operational.errors import install_error_contract
from infrastructure.operational.router import build_router
from infrastructure.operational.selection import read_demo_selection

ENABLE_ENV = "NEXUS_MVP_ENABLED"
DIR_ENV = "NEXUS_OPERATIONAL_DIR"
SELECTION_ENV = "NEXUS_DEMO_SELECTION"
_DEFAULT_DIR = Path(__file__).resolve().parents[5] / "data" / "snapshots" / "operational_corpus_v1"
_DEFAULT_SELECTION = Path(__file__).resolve().parent / "demo_selection_v1.json"


def mount_operational_mvp(app: FastAPI) -> bool:
    if os.getenv(ENABLE_ENV) != "1":
        return False
    artifacts = load_operational_artifacts(Path(os.getenv(DIR_ENV, str(_DEFAULT_DIR))))
    featured = read_demo_selection(Path(os.getenv(SELECTION_ENV, str(_DEFAULT_SELECTION))), artifacts.demands)
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
    return True
