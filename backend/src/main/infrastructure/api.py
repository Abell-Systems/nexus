"""Cloud Run entrypoint: wraps the ADK agent graph in a FastAPI app.

Local dev: uvicorn main:app --reload --port 8080
Cloud Run: this module is the container's entrypoint (see Dockerfile).
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import HTTPException, Query, Request  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from google.adk.cli.fast_api import get_fast_api_app  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from application.landscape.clustering import patents_for_demand_signal  # noqa: E402
from application.landscape.context import is_supported_domain  # noqa: E402
from application.research_service import ResearchService  # noqa: E402
from application.state_keys import (  # noqa: E402
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    SCORED_CANDIDATES,
    SELECTED_CLUSTER_CONTEXT,
)
from application.synthesis.reconciliation import reconcile_candidate_verdicts  # noqa: E402
from domain.models.runtime_schemas import (  # noqa: E402
    AdversarialVerdict,
    InventionCandidate,
    ScoreCard,
)
from infrastructure.adk.agent import build_invention_pipeline  # noqa: E402
from infrastructure.llm.provider_policy import (  # noqa: E402
    ProviderPacingPlugin,
    get_execution_policy,
)
from infrastructure.sources.bigquery_patents import get_patents_datasource  # noqa: E402
from infrastructure.sources.demand_sources import get_demand_datasource  # noqa: E402
from infrastructure.storage.job_store import get_job_store  # noqa: E402
from infrastructure.telemetry import PipelineProfiler  # noqa: E402

logger = logging.getLogger(__name__)

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

_rate_limiter = ProviderPacingPlugin()
_execution_policy = get_execution_policy()
_session_service = InMemorySessionService()

_root_agent = build_invention_pipeline()

_runner = Runner(
    agent=_root_agent,
    app_name="ip_matchmaker",
    session_service=_session_service,
    plugins=[_rate_limiter],
)

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    allow_origins=_ORIGINS,
    web=False,
)

_patents_datasource = get_patents_datasource()
_demand_datasource = get_demand_datasource()
_research_service = ResearchService(
    patents_datasource=_patents_datasource,
    demand_datasource=_demand_datasource,
)
_job_store = get_job_store()
_jobs = getattr(_job_store, "_jobs", {})

_background_tasks: set[asyncio.Task] = set()


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
    signal = next((d for d in demands if d.id == demand_id), None)
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


class AnalyzeRequest(BaseModel):
    domain: str = Field(..., description="Domain slug")
    query: str = Field(..., description="Invention prompt / target direction")
    cluster_id: str | None = Field(None, description="Optional cluster to analyze")


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        for key in ("items", "candidates", "verdicts", "scorecards"):
            if key in value and isinstance(value[key], list):
                return _as_list(value[key])
        return [value]
    return list(value)


def _extract_json_object(text: str) -> str | None:
    fence_match = re.search(r"```(?:json)?\s*(\{[^}]*\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first : last + 1]
    return None


def _parse_item_to_dict(item: Any, model_name: str) -> dict | None:
    if isinstance(item, str):
        try:
            return json.loads(item)
        except Exception:
            extracted = _extract_json_object(item)
            if extracted is None:
                logger.warning("_validated(%s): no JSON object found in text: %r", model_name, item[:300])
                return None
            try:
                return json.loads(extracted)
            except Exception as exc:
                logger.warning("_validated(%s): couldn't parse JSON (%s): %r", model_name, exc, item[:300])
                return None
    if isinstance(item, dict):
        return item
    logger.warning("_validated(%s): item is not a dict: %r", model_name, item)
    return None


def _validated(model_cls: type[BaseModel], items: Any) -> list[dict]:
    out = []
    for item in _as_list(items):
        if isinstance(item, model_cls):
            out.append(item.model_dump())
            continue
        parsed_dict = _parse_item_to_dict(item, model_cls.__name__)
        if parsed_dict is None:
            continue
        try:
            out.append(model_cls(**parsed_dict).model_dump())
        except ValidationError as exc:
            logger.warning("_validated(%s): schema validation error: %s | item=%r", model_cls.__name__, exc, parsed_dict)
    return out


_ANALYZE_TIMEOUT_S = 600.0


def _emit_event(
    job_id: str,
    event_type: str,
    message: str,
    candidate_id: str | None = None,
    evidence: Any = None,
) -> None:
    ts = datetime.now(UTC).isoformat()
    evt: dict[str, Any] = {
        "type": event_type,
        "timestamp": ts,
        "message": message,
    }
    if candidate_id:
        evt["candidateId"] = candidate_id
    if evidence is not None:
        evt["evidence"] = evidence

    if hasattr(_job_store, "_jobs") and job_id in getattr(_job_store, "_jobs", {}):
        _job_store._jobs[job_id].setdefault("events", []).append(evt)
    else:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_job_store.append_event(job_id, evt))
        except RuntimeError:
            asyncio.run(_job_store.append_event(job_id, evt))


_RETRY_AFTER_RE = re.compile(r"try again in ([\d.]+)(m?s)")
_MAX_RATE_LIMIT_RETRIES = 3


def _retry_after_seconds(exc: Exception) -> float | None:
    match = _RETRY_AFTER_RE.search(str(exc))
    if not match:
        return None
    value, unit = match.groups()
    return float(value) / 1000 if unit == "ms" else float(value)


async def _handle_candidate_state(job_id: str, cands: list, seen_candidates: set[str]) -> list[dict]:
    validated_cands = _validated(InventionCandidate, cands)
    await _job_store.update_progress(job_id, "candidatesGenerated", len(cands))
    for cand in cands:
        c_id = "unknown"
        cand_title = ""
        if isinstance(cand, dict):
            c_id = str(cand.get("candidate_id", "unknown"))
            cand_title = cand.get("title", "")
        elif hasattr(cand, "candidate_id"):
            c_id = str(cand.candidate_id)
            cand_title = getattr(cand, "title", "")
        else:
            c_id = str(cand)

        if c_id not in seen_candidates:
            seen_candidates.add(c_id)
            _emit_event(
                job_id,
                "candidate_generated",
                f"Generated Candidate #{c_id}" + (f": {cand_title}" if cand_title else ""),
                candidate_id=c_id,
                evidence=cand if isinstance(cand, (dict, list, str, int, float)) else str(cand),
            )
    return validated_cands


async def _handle_verdict_state(job_id: str, verdicts: list, seen_verdict_indices: set[int]) -> list[dict]:
    validated_verdicts = _validated(AdversarialVerdict, verdicts)
    await _job_store.set_stage(job_id, "adversarial")
    counts = {"rejected": 0, "survives": 0, "revised": 0}
    for idx, v in enumerate(verdicts):
        if not isinstance(v, dict):
            continue
        v_str = str(v.get("verdict", "")).lower()
        if v_str in counts:
            counts[v_str] += 1
        elif v_str == "revise":
            counts["revised"] += 1

        if idx not in seen_verdict_indices:
            seen_verdict_indices.add(idx)
            v_cand_id = str(v.get("candidate_id", "unknown"))
            cited = v.get("cited_patents", [])
            cited_str = f"Prior art: {', '.join(cited)}" if cited else ""

            _emit_event(
                job_id,
                "candidate_challenged",
                f"Candidate #{v_cand_id} challenged" + (f" ({cited_str})" if cited_str else ""),
                candidate_id=v_cand_id,
                evidence=v,
            )
            if v_str == "rejected":
                _emit_event(job_id, "candidate_rejected", f"Candidate #{v_cand_id} rejected", candidate_id=v_cand_id, evidence=v)
            elif v_str in ("revised", "revise"):
                _emit_event(job_id, "candidate_revised", f"Candidate #{v_cand_id} revised", candidate_id=v_cand_id, evidence=v)
            elif v_str == "survives":
                _emit_event(job_id, "candidate_survived", f"Candidate #{v_cand_id} survived", candidate_id=v_cand_id, evidence=v)

    await _job_store.update_progress(job_id, "candidatesRejected", counts["rejected"])
    await _job_store.update_progress(job_id, "candidatesRevised", counts["revised"])
    await _job_store.update_progress(job_id, "candidatesSurvived", counts["survives"])
    return validated_verdicts


async def _execute_analysis(job_id: str, req: AnalyzeRequest) -> dict:
    """Runs unified research service + agent graph for one cluster."""
    profiler = PipelineProfiler()
    _rate_limiter.profiler = profiler

    await _job_store.set_stage(job_id, "researching")
    res = await _research_service.conduct_research(
        query=req.query,
        domain=req.domain,
        cluster_id=req.cluster_id,
        profiler=profiler,
    )

    await _job_store.update_progress(job_id, "patentsAnalyzed", len(res.patents))
    _emit_event(job_id, "research_completed", f"Researched {len(res.patents)} patents", evidence={"patentsAnalyzed": len(res.patents)})

    await _job_store.set_stage(job_id, "clustering")
    await _job_store.update_progress(job_id, "clustersFound", len(res.clusters))
    _job_store.update_job(job_id, clusters=[c.model_dump() for c in res.clusters])
    _emit_event(job_id, "landscape_clustered", f"Found {len(res.clusters)} white-space opportunities", evidence={"clustersFound": len(res.clusters)})

    await _job_store.set_stage(job_id, "inventing")

    session = await _session_service.create_session(
        app_name="ip_matchmaker",
        user_id="web",
        state={SELECTED_CLUSTER_CONTEXT: res.cluster_context},
    )
    prompt = (
        f"Propose, adversarially test, and score a candidate invention for cluster "
        f"'{res.cluster_id}' in domain '{req.domain}', using the selected cluster context provided."
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    seen_candidates: set[str] = set()
    seen_verdict_indices: set[int] = set()
    seen_assessment = False

    last_seen_candidates: list[dict] = []
    last_seen_verdicts: list[dict] = []
    last_seen_scores: list[dict] = []

    async def run() -> None:
        nonlocal seen_assessment, last_seen_candidates, last_seen_verdicts, last_seen_scores
        async for _ in _runner.run_async(user_id="web", session_id=session.id, new_message=msg):
            curr = await _session_service.get_session(app_name="ip_matchmaker", user_id="web", session_id=session.id)
            state = curr.state if curr and curr.state else {}

            cands = _as_list(state.get(CANDIDATE_INVENTIONS))
            if cands:
                val_cands = await _handle_candidate_state(job_id, cands, seen_candidates)
                if val_cands:
                    last_seen_candidates = val_cands

            verdicts = _as_list(state.get(ADVERSARIAL_VERDICTS))
            if verdicts:
                val_verdicts = await _handle_verdict_state(job_id, verdicts, seen_verdict_indices)
                if val_verdicts:
                    last_seen_verdicts = val_verdicts

            scores = _as_list(state.get(SCORED_CANDIDATES))
            if scores:
                val_scores = _validated(ScoreCard, scores)
                if val_scores:
                    last_seen_scores = val_scores
                await _job_store.set_stage(job_id, "governor")
                if not seen_assessment:
                    seen_assessment = True
                    _emit_event(job_id, "assessment_completed", "Final assessment complete", evidence={"scorecardsCount": len(scores)})

    try:
        for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
            try:
                await run()
                break
            except Exception as exc:
                wait = _retry_after_seconds(exc)
                if wait is None or attempt == _MAX_RATE_LIMIT_RETRIES:
                    raise
                logger.info("analyze job %s hit rate limit, retrying in %.1fs", job_id, wait)
                await asyncio.sleep(wait + 0.5)

        final = await _session_service.get_session(app_name="ip_matchmaker", user_id="web", session_id=session.id)
        final_state = final.state if final and final.state else {}

        raw_candidates = last_seen_candidates or _validated(InventionCandidate, final_state.get(CANDIDATE_INVENTIONS))
        raw_verdicts = last_seen_verdicts or _validated(AdversarialVerdict, final_state.get(ADVERSARIAL_VERDICTS))
        raw_scorecards = last_seen_scores or _validated(ScoreCard, final_state.get(SCORED_CANDIDATES))

        telemetry = profiler.get_summary()
        _job_store.update_job(job_id, telemetry_profile=telemetry)
        profiler.print_profile()

        return {
            "candidates": raw_candidates,
            "verdicts": reconcile_candidate_verdicts(raw_verdicts, raw_scorecards),
            "scorecards": raw_scorecards,
            "telemetry_profile": telemetry,
        }
    finally:
        await _session_service.delete_session(app_name="ip_matchmaker", user_id="web", session_id=session.id)


_QUOTA_FRIENDLY_MESSAGE = (
    "This analysis couldn't be completed because the AI service has reached its "
    "current usage limit. Your research has not been lost — please try again "
    "later, once the quota resets."
)


def _classify_error(exc: Exception) -> dict:
    text = str(exc)
    if "RESOURCE_EXHAUSTED" in text and "PerDay" in text:
        return {"error_type": "quota_exhausted", "detail": _QUOTA_FRIENDLY_MESSAGE}
    return {"error_type": "unknown", "detail": text[:300]}


async def _run_job(job_id: str, req: AnalyzeRequest) -> None:
    async with _execution_policy.acquire_execution_slot():
        try:
            result = await asyncio.wait_for(_execute_analysis(job_id, req), timeout=_ANALYZE_TIMEOUT_S)
            await _job_store.set_result(job_id, result)
        except TimeoutError:
            await _job_store.set_error(job_id, f"Agent run exceeded {_ANALYZE_TIMEOUT_S}s.")
            _job_store.update_job(job_id, error_type="timeout", detail=f"Agent run exceeded {_ANALYZE_TIMEOUT_S}s.")
        except Exception as exc:
            logger.exception("analyze job %s failed", job_id)
            err_info = _classify_error(exc)
            await _job_store.set_error(job_id, err_info.get("detail", str(exc)))
            _job_store.update_job(job_id, **err_info)


_ANALYZE_RATE_LIMIT = 3
_ANALYZE_RATE_WINDOW_S = 3600.0
_analyze_request_times: dict[str, list[float]] = {}


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    recent = [t for t in _analyze_request_times.get(client_ip, []) if now - t < _ANALYZE_RATE_WINDOW_S]
    if len(recent) >= _ANALYZE_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: max {_ANALYZE_RATE_LIMIT} analyses per hour per IP.",
        )
    recent.append(now)
    _analyze_request_times[client_ip] = recent


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
