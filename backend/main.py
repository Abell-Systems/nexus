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
from datetime import datetime, timezone

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

from patent_agent.agent import build_invention_pipeline  # noqa: E402
from patent_agent.config import is_supported_domain  # noqa: E402
from patent_agent.provider import LLMProvider  # noqa: E402
from patent_agent.services.research_service import get_research_service  # noqa: E402
from patent_agent.shared.job_store import get_job_store  # noqa: E402
from patent_agent.shared.provider_policy import (  # noqa: E402
    ProviderPacingPlugin,
    get_execution_policy,
)
from patent_agent.shared.state_keys import (  # noqa: E402
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    SCORED_CANDIDATES,
    SELECTED_CLUSTER_CONTEXT,
)
from patent_agent.shared.telemetry import PipelineProfiler  # noqa: E402
from patent_agent.tools.bigquery_patents import get_patents_datasource  # noqa: E402
from patent_agent.tools.clustering import patents_for_demand_signal  # noqa: E402
from patent_agent.tools.demand_sources import get_demand_datasource  # noqa: E402
from patent_agent.tools.schemas import (  # noqa: E402
    AdversarialVerdict,
    AgentEventItem,
    InventionCandidate,
    PatentRecord,
    ScoreCard,
)

logger = logging.getLogger(__name__)

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

# ADK's own origin-check middleware rejects cross-origin requests unless the
# origin is listed here (a plain CORSMiddleware added after the fact does not
# override it). Comma-separated via FRONTEND_ORIGINS so Cloud Run deploys can
# set the real frontend origin without a code change.
_ALLOWED_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",")

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    web=False,
    allow_origins=_ALLOWED_ORIGINS,
)

app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/health"]

_research_service = get_research_service()
_job_store = get_job_store()
_execution_policy = get_execution_policy()
_rate_limiter = ProviderPacingPlugin(policy=_execution_policy.provider_policy)
_session_service = InMemorySessionService()

# Backward compatibility references for tests/inspectors
_jobs = getattr(_job_store, "_jobs", {})


class _AnalyzeLockCompat:
    @property
    def _locked(self) -> bool:
        return _execution_policy.is_busy()

    @_locked.setter
    def _locked(self, val: bool) -> None:
        _execution_policy.active_runs = _execution_policy.max_concurrency if val else 0

    def locked(self) -> bool:
        return _execution_policy.is_busy()


_analyze_lock = _AnalyzeLockCompat()

_analyze_pipeline = build_invention_pipeline()
_runner = Runner(
    agent=_analyze_pipeline,
    app_name="ip_matchmaker",
    session_service=_session_service,
    plugins=[_rate_limiter],
)





@app.get("/health")
def health() -> dict:
    try:
        provider_status = LLMProvider.get_status()
    except Exception as err:
        provider_status = {
            "model_provider": os.getenv("MODEL_PROVIDER", "unknown"),
            "model": "error",
            "error": str(err),
        }
    try:
        patents_datasource_status = get_patents_datasource().get_status()
    except Exception as err:
        patents_datasource_status = {"type": "unknown", "error": str(err)}
    return {
        "status": "ok",
        "use_mock_bigquery": os.getenv("USE_MOCK_BIGQUERY", "true"),
        "patents_datasource": patents_datasource_status,
        **provider_status,
    }


def _check_domain_supported(domain: str) -> None:
    if not is_supported_domain(domain):
        raise HTTPException(
            status_code=422,
            detail=(
                f"This demo's patent data only covers solid-state EV battery electrolytes -- "
                f"'{domain}' is outside that scope and would produce unreliable results."
            ),
        )


@app.get("/api/landscape")
async def get_landscape(
    query: str = Query(min_length=1),
    domain: str = Query(min_length=1),
    max_results: int = Query(20, ge=1, le=100),
) -> dict:
    """Deterministic view of the unified research + clustering pipeline."""
    _check_domain_supported(domain)
    res = await _research_service.conduct_research(query=query, domain=domain, max_patents=max_results)
    return {
        "query": res.query,
        "domain": res.domain,
        "patents": [r.model_dump() for r in res.patents],
        "clusters": [c.model_dump() for c in res.clusters],
    }


@app.get("/api/demand/{signal_id}/patents")
def get_patents_for_demand(
    signal_id: str,
    query: str = Query(min_length=1),
    domain: str = Query(min_length=1),
    max_results: int = Query(20, ge=1, le=100),
) -> dict:
    """Patents related to one demand signal (e.g. an Innoget technology call)."""
    demand_signals = get_demand_datasource().search_demand(query, domain)
    signal = next((s for s in demand_signals if s.id == signal_id), None)
    if signal is None:
        raise HTTPException(status_code=404, detail=f"Demand signal '{signal_id}' not found for that query/domain")
    records = patents_for_demand_signal(signal, domain, max_results)
    return {
        "demand_signal": signal.model_dump(),
        "patents": [r.model_dump() for r in records],
    }


class AnalyzeRequest(BaseModel):
    domain: str = Field(min_length=1)
    query: str = Field(default="solid electrolyte interphase")
    cluster_id: str | None = None


def _as_list(value) -> list:
    """Normalize one state entry to a JSON-friendly list."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return [value]
    if isinstance(value, dict):
        for key in ("candidate", "scorecards"):
            if key in value:
                return _as_list(value[key])
        return [value]
    return list(value)


def _extract_json_object(text: str) -> str | None:
    """Best-effort recovery of a JSON object from text that isn't pure JSON --
    e.g. wrapped in a ```json fence, or with stray prose around it (an LLM
    without a schema-enforced output can ignore a "JSON only" instruction)."""
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        return text[first : last + 1]
    return None


def _validated(model_cls, items) -> list[dict]:
    """Keep only entries that match the shared schema; drop the rest."""
    out = []
    for item in _as_list(items):
        if isinstance(item, model_cls):
            out.append(item.model_dump())
            continue
        if isinstance(item, str):
            try:
                item = json.loads(item)
            except Exception:
                extracted = _extract_json_object(item)
                try:
                    if extracted is None:
                        raise ValueError("no JSON object found in text")
                    item = json.loads(extracted)
                except Exception as exc:
                    logger.warning("_validated(%s): couldn't parse item as JSON (%s): %r", model_cls.__name__, exc, item[:300])
                    continue
        if not isinstance(item, dict):
            logger.warning("_validated(%s): item is not a dict after parsing: %r", model_cls.__name__, item)
            continue
        try:
            out.append(model_cls(**item).model_dump())
        except ValidationError as exc:
            logger.warning("_validated(%s): item failed schema validation: %s | item=%r", model_cls.__name__, exc, item)
    return out


# Cloud Run's request timeout default is 300s; keep the background loop bounded.
_ANALYZE_TIMEOUT_S = 600.0


def _emit_event(
    job_id: str,
    event_type: str,
    message: str,
    candidate_id: str | None = None,
    evidence: dict | None = None,
) -> None:
    """Append a structured, typed event to the job's event log."""
    ts = datetime.now(timezone.utc).isoformat()
    evt = {
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


def reconcile_candidate_verdicts(
    verdicts: list[dict], scorecards: list[dict]
) -> list[dict]:
    """Ensures backend produces authoritative verdict: if governor scorecard finds
    direct anticipation or blocking prior art, force verdict to 'rejected'."""
    reconciled = []
    for v in verdicts:
        v_copy = dict(v)
        cand_id = v_copy.get("candidate_id")
        sc = next((s for s in scorecards if isinstance(s, dict) and s.get("candidate_id") == cand_id), None)
        if sc:
            summary = (sc.get("summary") or "").lower()
            if (
                "directly anticipated" in summary
                or "no room for novelty" in summary
                or "cannot be recommended" in summary
            ):
                v_copy["verdict"] = "rejected"
        reconciled.append(v_copy)
    return reconciled


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
    _emit_event(
        job_id,
        "research_completed",
        f"Researched {len(res.patents)} patents",
        evidence={"patentsAnalyzed": len(res.patents)},
    )

    await _job_store.set_stage(job_id, "clustering")
    await _job_store.update_progress(job_id, "clustersFound", len(res.clusters))
    await _job_store.update_job(job_id, {"clusters": [c.model_dump() for c in res.clusters]})
    _emit_event(
        job_id,
        "landscape_clustered",
        f"Found {len(res.clusters)} white-space opportunities",
        evidence={"clustersFound": len(res.clusters)},
    )

    cluster_id = res.cluster_id
    cluster_context = res.cluster_context

    await _job_store.set_stage(job_id, "inventing")

    session = await _session_service.create_session(
        app_name="ip_matchmaker",
        user_id="web",
        state={SELECTED_CLUSTER_CONTEXT: cluster_context},
    )
    prompt = (
        f"Propose, adversarially test, and score a candidate invention for cluster "
        f"'{cluster_id}' in domain '{req.domain}', using the selected cluster context provided."
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    seen_candidates: set[str] = set()
    seen_verdict_indices: set[int] = set()
    seen_assessment = False

    # ADK can leave session state empty on the *final* get_session() call even
    # after a mid-run checkpoint saw real data: an LlmAgent with output_schema
    # skips writing state_delta on a trailing empty streaming chunk (see
    # google.adk.agents.llm_agent.LlmAgent.__maybe_save_output_to_state --
    # "this is an empty final chunk of a stream. Do not attempt to parse it"),
    # so a value set on an earlier chunk of the same turn can end up not
    # persisted by the time we re-fetch. Track the latest *validated* snapshot
    # of each state key here instead of trusting a fresh get_session() after
    # the loop -- confirmed reproducing this against production three times
    # in a row (see docs/roadmap.md open risks, 2026-08-30). Deliberately keyed
    # on "validates successfully", not "non-empty": a later loop iteration
    # producing unparseable text (e.g. adversarial_agent without an
    # output_schema) must not clobber an earlier good snapshot.
    last_seen_candidates: list[dict] = []
    last_seen_verdicts: list[dict] = []
    last_seen_scores: list[dict] = []

    async def run() -> None:
        nonlocal seen_assessment, last_seen_candidates, last_seen_verdicts, last_seen_scores
        async for _ in _runner.run_async(user_id="web", session_id=session.id, new_message=msg):
            curr = await _session_service.get_session(
                app_name="ip_matchmaker", user_id="web", session_id=session.id
            )
            state = curr.state or {}

            cands = _as_list(state.get(CANDIDATE_INVENTIONS))
            if cands:
                validated_cands = _validated(InventionCandidate, cands)
                if validated_cands:
                    last_seen_candidates = validated_cands
                await _job_store.update_progress(job_id, "candidatesGenerated", len(cands))
                for cand in cands:
                    cand_id = "unknown"
                    cand_title = ""
                    if isinstance(cand, dict):
                        cand_id = str(cand.get("candidate_id", "unknown"))
                        cand_title = cand.get("title", "")
                    elif hasattr(cand, "candidate_id"):
                        cand_id = str(getattr(cand, "candidate_id"))
                        cand_title = getattr(cand, "title", "")
                    else:
                        cand_id = str(cand)

                    if cand_id not in seen_candidates:
                        seen_candidates.add(cand_id)
                        _emit_event(
                            job_id,
                            "candidate_generated",
                            f"Generated Candidate #{cand_id}" + (f": {cand_title}" if cand_title else ""),
                            candidate_id=cand_id,
                            evidence=cand if isinstance(cand, (dict, list, str, int, float)) else str(cand),
                        )

            verdicts = _as_list(state.get(ADVERSARIAL_VERDICTS))
            if verdicts:
                validated_verdicts = _validated(AdversarialVerdict, verdicts)
                if validated_verdicts:
                    last_seen_verdicts = validated_verdicts
                await _job_store.set_stage(job_id, "adversarial")
                rej = 0
                surv = 0
                rev = 0
                for idx, v in enumerate(verdicts):
                    if isinstance(v, dict):
                        v_str = str(v.get("verdict", "")).lower()
                        if v_str == "rejected":
                            rej += 1
                        elif v_str == "survives":
                            surv += 1
                        elif v_str in ("revised", "revise"):
                            rev += 1

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
                                _emit_event(
                                    job_id,
                                    "candidate_rejected",
                                    f"Candidate #{v_cand_id} rejected",
                                    candidate_id=v_cand_id,
                                    evidence=v,
                                )
                            elif v_str in ("revised", "revise"):
                                _emit_event(
                                    job_id,
                                    "candidate_revised",
                                    f"Candidate #{v_cand_id} revised",
                                    candidate_id=v_cand_id,
                                    evidence=v,
                                )
                            elif v_str == "survives":
                                _emit_event(
                                    job_id,
                                    "candidate_survived",
                                    f"Candidate #{v_cand_id} survived",
                                    candidate_id=v_cand_id,
                                    evidence=v,
                                )

                await _job_store.update_progress(job_id, "candidatesRejected", rej)
                await _job_store.update_progress(job_id, "candidatesRevised", rev)
                await _job_store.update_progress(job_id, "candidatesSurvived", surv)

            scores = _as_list(state.get(SCORED_CANDIDATES))
            if scores:
                validated_scores = _validated(ScoreCard, scores)
                if validated_scores:
                    last_seen_scores = validated_scores
                await _job_store.set_stage(job_id, "governor")
                if not seen_assessment:
                    seen_assessment = True
                    _emit_event(
                        job_id,
                        "assessment_completed",
                        "Final assessment complete",
                        evidence={"scorecardsCount": len(scores)},
                    )

    try:
        for attempt in range(_MAX_RATE_LIMIT_RETRIES + 1):
            try:
                await run()
                break
            except Exception as exc:
                wait = _retry_after_seconds(exc)
                if wait is None or attempt == _MAX_RATE_LIMIT_RETRIES:
                    raise
                logger.info(
                    "analyze job %s hit a rate limit, retrying in %.1fs (attempt %d/%d)",
                    job_id, wait, attempt + 1, _MAX_RATE_LIMIT_RETRIES,
                )
                await asyncio.sleep(wait + 0.5)

        # Prefer the last validated snapshot seen during the run over a fresh
        # get_session() call -- see the last_seen_* comment above `run()` for
        # why the final session state can come back empty even though the
        # data genuinely existed mid-run. last_seen_* are already validated
        # (list[dict]); fall back to a fresh fetch only if the run somehow
        # never saw a valid snapshot of that key at all.
        final = await _session_service.get_session(
            app_name="ip_matchmaker", user_id="web", session_id=session.id
        )
        final_state = final.state or {}
        logger.warning(
            "analyze job %s pre-return snapshot: last_seen_candidates=%r final_state[CANDIDATE_INVENTIONS]=%r "
            "last_seen_verdicts=%r final_state[ADVERSARIAL_VERDICTS]=%r "
            "last_seen_scores=%r final_state[SCORED_CANDIDATES]=%r",
            job_id,
            last_seen_candidates,
            final_state.get(CANDIDATE_INVENTIONS),
            last_seen_verdicts,
            final_state.get(ADVERSARIAL_VERDICTS),
            last_seen_scores,
            final_state.get(SCORED_CANDIDATES),
        )
        raw_candidates = last_seen_candidates or _validated(InventionCandidate, final_state.get(CANDIDATE_INVENTIONS))
        raw_verdicts = last_seen_verdicts or _validated(AdversarialVerdict, final_state.get(ADVERSARIAL_VERDICTS))
        raw_scorecards = last_seen_scores or _validated(ScoreCard, final_state.get(SCORED_CANDIDATES))

        telemetry = profiler.get_summary()
        await _job_store.update_job(job_id, {"telemetry_profile": telemetry})
        profiler.print_profile()

        return {
            "candidates": raw_candidates,
            "verdicts": reconcile_candidate_verdicts(raw_verdicts, raw_scorecards),
            "scorecards": raw_scorecards,
            "telemetry_profile": telemetry,
        }
    finally:
        await _session_service.delete_session(
            app_name="ip_matchmaker", user_id="web", session_id=session.id
        )


_QUOTA_FRIENDLY_MESSAGE = (
    "This analysis couldn't be completed because the AI service has reached its "
    "current usage limit. Your research has not been lost — please try again "
    "later, once the quota resets."
)


def _classify_error(exc: Exception) -> dict:
    """Map a raw exception to a user-facing error_type + message."""
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
            await _job_store.update_job(job_id, {"error_type": "timeout", "detail": f"Agent run exceeded {_ANALYZE_TIMEOUT_S}s."})
        except Exception as exc:
            logger.exception("analyze job %s failed", job_id)
            err_info = _classify_error(exc)
            await _job_store.set_error(job_id, err_info.get("detail", str(exc)))
            await _job_store.update_job(job_id, err_info)


_ANALYZE_RATE_LIMIT = 3
_ANALYZE_RATE_WINDOW_S = 3600.0
# ponytail: per-process in-memory counter, no new infra -- valid because Cloud
# Run is pinned to --max-instances=1 (same reasoning as the in-memory job store).
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
    await _job_store.create_job(
        job_id,
        {
            "status": "running",
            "stage": "queued",
            "domain": req.domain,
            "query": req.query,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    asyncio.create_task(_run_job(job_id, req))
    return {"job_id": job_id, "status": "running", "stage": "queued"}



@app.get("/api/analyze")
async def list_analyze_jobs() -> dict:
    """Lists past/in-progress analyze jobs (in-memory, this process only), newest first.

    Summary only -- open a specific job via GET /api/analyze/{job_id} for the
    full result (candidates/verdicts/scorecards), which is already served from
    the job store without re-running anything.
    """
    jobs = await _job_store.list_jobs()
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
    """Poll endpoint for a background analyze run.

    The job store keeps the final result nested under job["result"], but the
    frontend's JobStatusResponse (frontend/src/types/patent.ts) expects
    candidates/verdicts/scorecards flat on the response -- flatten here
    rather than changing the frontend or the job store's internal shape.
    """
    job = await _job_store.get_job(job_id)
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
    if full_path.startswith("api/") or full_path.startswith("health"):
        raise HTTPException(status_code=404, detail="API route not found.")
    dist_dir = _get_dist_dir()
    if dist_dir:
        target_file = os.path.join(dist_dir, full_path)
        if os.path.isfile(target_file):
            return FileResponse(target_file)
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend route not found.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
