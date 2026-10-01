from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from infrastructure.operational.mount import _DEFAULT_SELECTION, mount_operational_mvp

_SPA_ROUTES = ("", "matches")  # the screens the frontend router owns; any other path is a 404, never the SPA


def create_mvp_app(artifacts_dir: Path, static_dir: Path | None = None, selection: Path = _DEFAULT_SELECTION
) -> FastAPI:
    """The deployable product: verified artifacts, the two MVP routes, readiness, and optionally the built SPA.

    Artifacts load (and are verified) before the app exists, so a process that answers is always ready.
    """
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    mount_operational_mvp(app, artifacts_dir, selection)

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ready": True}

    if static_dir is not None:
        root = static_dir.resolve()
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @app.get("/{path:path}")
        def spa(path: str) -> FileResponse:
            target = (root / path).resolve()
            if path in _SPA_ROUTES:
                return FileResponse(root / "index.html")
            if target.is_relative_to(root) and target.is_file():
                return FileResponse(target)
            raise HTTPException(status_code=404)

    return app
