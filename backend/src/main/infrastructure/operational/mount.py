import os
from pathlib import Path

from fastapi import FastAPI, Request

from infrastructure.operational.router import build_router
from infrastructure.operational.service import OperationalMatchingService

ENABLE_ENV = "NEXUS_MVP_ENABLED"
DIR_ENV = "NEXUS_OPERATIONAL_DIR"
SELECTION_ENV = "NEXUS_DEMO_SELECTION"
_DEFAULT_DIR = Path(__file__).resolve().parents[5] / "data" / "snapshots" / "operational_corpus_v1"
_DEFAULT_SELECTION = Path(__file__).resolve().parent / "demo_selection_v1.json"


def mount_operational_mvp(app: FastAPI) -> bool:
    """Mounts the MVP routes only when NEXUS_MVP_ENABLED=1; then any bad artifact aborts startup."""
    if os.getenv(ENABLE_ENV) != "1":
        return False
    directory = Path(os.getenv(DIR_ENV, str(_DEFAULT_DIR)))
    selection = Path(os.getenv(SELECTION_ENV, str(_DEFAULT_SELECTION)))
    service = OperationalMatchingService.from_directory(directory, selection_path=selection)
    app.include_router(build_router(service))

    @app.middleware("http")
    async def hardening_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    # The first query pays a cold-memory cost (~2 s); pay it at startup, not on the first click of a demo.
    examples = service.examples()["demands"]
    if examples:
        service.matches(examples[0]["demand_id"])
    return True
