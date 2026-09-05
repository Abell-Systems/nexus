"""Cloud Run entrypoint: FastAPI routes over the ADK agent graph.

Local dev: uvicorn main:app --reload --port 8080
Cloud Run: this module is the container's entrypoint (see Dockerfile).

Shared runtime singletons (agent runner, datasources, job store) live in
infrastructure/api_dependencies.py; the /api/analyze background job orchestration and its
LLM-output validation live in infrastructure/analysis_pipeline.py.
"""

import asyncio
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from application.landscape.clustering import patents_for_demand_signal
from application.landscape.context import is_supported_domain
from infrastructure.analysis_pipeline import AnalyzeRequest, _check_rate_limit, _run_job
from infrastructure.api_dependencies import (
    AGENTS_DIR,
    _demand_datasource,
    _execution_policy,
    _job_store,
    _patents_datasource,
    _research_service,
    app,
)

_background_tasks: set[asyncio.Task] = set()

# get_fast_api_app() (in api_dependencies.py) already registers its own GET /health route as
# part of building the ADK scaffold app. Starlette matches routes in registration order, so
# without evicting it here, our health_check below — registered afterward — would be dead code:
# every request would keep matching ADK's generic route first, silently hiding the
# provider/agents/version diagnostics ours reports.
app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/health"]


def _check_domain_supported(domain: str) -> None:
    if not is_supported_domain(domain):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Domain '{domain}' is not supported. Supported domains: "
                "solid_state_battery, surgical_robotics, quantum_computing, "
                "green_hydrogen, carbon_capture, neuromorphic_chips, "
                "synthetic_biology, autonomous_drones, fusion_energy, "
                "perovskite_solar, lab_grown_meat, brain_computer_interface."
            ),
        )


@app.get("/health")
async def health_check():
    provider_name = os.getenv("MODEL_PROVIDER", "gemini").lower()
    return {
        "status": "healthy",
        "provider": provider_name,
        "agents": [
            "research_service",
            "patent_inventor",
            "adversarial_prior_art_agent",
            "commercial_governor",
        ],
        "version": "2.0.0",
    }


@app.get("/api/research")
@app.get("/api/landscape")
async def get_research(
    query: str = Query(..., description="Query string for patent search"),
    domain: str = Query(..., description="Domain slug"),
    max_results: int = Query(20, ge=1, le=100),
):
    _check_domain_supported(domain)
    res = await _research_service.conduct_research(query=query, domain=domain, max_patents=max_results)
    return {
        "query": res.query,
        "domain": res.domain,
        "clusters": [c.model_dump() for c in res.clusters],
        "patents": [p.model_dump() for p in res.patents],
    }


@app.get("/api/demands")
async def get_demands(
    domain: str = Query(..., description="Domain slug"),
    cluster_id: str | None = Query(None, description="Optional cluster CPC prefix to filter demands"),
):
    _check_domain_supported(domain)
    if hasattr(_demand_datasource, "get_demands_for_cluster") and cluster_id:
        demands = _demand_datasource.get_demands_for_cluster(cluster_id)
    elif hasattr(_demand_datasource, "get_spanish_demands"):
        demands = _demand_datasource.get_spanish_demands()
    else:
        demands = _demand_datasource.search_demand(domain=domain)
    return {
        "domain": domain,
        "cluster_id": cluster_id,
        "demands": [d.model_dump() for d in demands],
    }


@app.get("/api/landscape/demand-patents")
async def get_patents_for_demand(
    demand_id: str = Query(..., description="Demand signal ID"),
    domain: str = Query(..., description="Domain slug"),
    max_results: int = Query(20, ge=1, le=100),
):
    _check_domain_supported(domain)
    demands = (
        _demand_datasource.get_spanish_demands()
        if hasattr(_demand_datasource, "get_spanish_demands")
        else _demand_datasource.search_demand(domain=domain)
    )
    signal = next((d for d in demands if d.demand_id == demand_id), None)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Demand signal '{demand_id}' not found.")
    patents = patents_for_demand_signal(
        signal=signal,
        domain=domain,
        patents_datasource=_patents_datasource,
        max_results=max_results,
    )
    return {
        "demand_id": demand_id,
        "domain": domain,
        "patents": [p.model_dump() for p in patents],
    }


@app.post("/api/analyze", status_code=202)
async def analyze(req: AnalyzeRequest, request: Request) -> dict:
    """Kicks off the unified research service + agent graph in the background and returns a job id immediately."""
    _check_domain_supported(req.domain)
    _check_rate_limit(request.client.host if request.client else "unknown")
    if _execution_policy.is_busy():
        raise HTTPException(status_code=503, detail="An analyze run is already in progress.")
    job_id = uuid.uuid4().hex
    _job_store.create_job(
        job_id=job_id,
        domain=req.domain,
        query=req.query,
    )
    task = asyncio.create_task(_run_job(job_id, req))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"job_id": job_id, "status": "running", "stage": "queued"}


@app.get("/api/analyze")
async def list_analyze_jobs() -> dict:
    jobs = _job_store.list_jobs()
    return {
        "jobs": [
            {
                "job_id": job.get("id"),
                "domain": job.get("domain"),
                "query": job.get("query"),
                "status": job.get("status"),
                "stage": job.get("stage"),
                "created_at": job.get("created_at"),
                "candidate_count": len(job.get("result", {}).get("candidates") or []) if job.get("result") else 0,
            }
            for job in jobs
        ]
    }


@app.get("/api/analyze/{job_id}")
async def analyze_status(job_id: str) -> dict:
    job = _job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id.")
    response = dict(job)
    response["job_id"] = response.pop("id", job_id)
    result = response.pop("result", None) or {}
    response["candidates"] = result.get("candidates", [])
    response["verdicts"] = result.get("verdicts", [])
    response["scorecards"] = result.get("scorecards", [])
    return response


def _get_dist_dir() -> str | None:
    static_dir = os.path.join(AGENTS_DIR, "static")
    if os.path.exists(static_dir):
        return static_dir
    dist_dir = os.path.abspath(os.path.join(AGENTS_DIR, "../frontend/dist"))
    if os.path.exists(dist_dir):
        return dist_dir
    return None


_initial_dist = _get_dist_dir()
if _initial_dist and os.path.exists(os.path.join(_initial_dist, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(_initial_dist, "assets")), name="assets")


@app.get("/")
async def serve_root():
    dist_dir = _get_dist_dir()
    if dist_dir:
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
    raise HTTPException(
        status_code=404,
        detail="Frontend static build not found. Run 'npm run build' inside frontend/ directory.",
    )


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path.startswith(("api/", "health")):
        raise HTTPException(status_code=404, detail="API route not found.")
    dist_dir = _get_dist_dir()
    if dist_dir:
        resolved_dist = Path(dist_dir).resolve()
        target_file = (resolved_dist / full_path).resolve()
        if target_file.is_relative_to(resolved_dist) and target_file.is_file():
            return FileResponse(str(target_file))
        index_file = (resolved_dist / "index.html").resolve()
        if index_file.is_relative_to(resolved_dist) and index_file.is_file():
            return FileResponse(str(index_file))
    raise HTTPException(status_code=404, detail="Frontend route not found.")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=int(os.getenv("PORT", "8080")))
