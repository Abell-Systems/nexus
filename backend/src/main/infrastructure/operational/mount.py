import os
from pathlib import Path

from fastapi import FastAPI

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
    return True
