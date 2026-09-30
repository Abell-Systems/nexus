from fastapi import FastAPI

from infrastructure.operational.router import MVP_PATHS

# The ADK scaffold behind `app` exposes unauthenticated agent execution (/run, /run_sse, sessions, docs),
# and the hackathon agent exposes /api/analyze, which starts paid model runs. The product needs none of them.
_PRODUCT_PATHS = {"/health", "/", "/assets", "/{full_path:path}", *MVP_PATHS}


def _is_product_route(route) -> bool:
    included = getattr(route, "original_router", None)  # FastAPI wraps include_router()'d routers
    paths = [getattr(r, "path", None) for r in included.routes] if included else [getattr(route, "path", None)]
    return all(path in _PRODUCT_PATHS for path in paths)


def restrict_to_product_routes(app: FastAPI, *, legacy_enabled: bool) -> None:
    if legacy_enabled:
        return
    app.router.routes = [r for r in app.router.routes if _is_product_route(r)]
