"""Comprehensive unit tests for FastAPI endpoints (infrastructure/api.py) and the
/api/analyze job orchestration helpers (infrastructure/analysis_pipeline.py)."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from domain.models.runtime_schemas import InventionCandidate
from infrastructure import analysis_pipeline as analysis_pipeline_module
from infrastructure.adk.state_keys import (
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    SCORED_CANDIDATES,
)
from infrastructure.analysis_pipeline import (
    _ANALYZE_RATE_LIMIT,
    AnalyzeRequest,
    _analyze_request_times,
    _as_list,
    _check_rate_limit,
    _classify_error,
    _emit_event,
    _execute_analysis,
    _extract_json_object,
    _handle_candidate_state,
    _handle_verdict_state,
    _parse_item_to_dict,
    _retry_after_seconds,
    _run_job,
    _validated,
)
from infrastructure.api import _check_domain_supported, _get_dist_dir, app
from infrastructure.api_dependencies import _demand_datasource, _execution_policy, _job_store

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ("healthy", "ok")


def test_landscape_endpoint_valid_domain():
    response = client.get("/api/landscape", params={"query": "solid electrolyte", "domain": "solid_state_battery"})
    assert response.status_code == 200
    data = response.json()
    assert "patents" in data
    assert "clusters" in data


def test_landscape_endpoint_unsupported_domain():
    response = client.get("/api/landscape", params={"query": "solar panel", "domain": "unsupported_domain_xyz"})
    assert response.status_code == 400


def test_check_domain_supported():
    _check_domain_supported("solid_state_battery")
    with pytest.raises(HTTPException) as exc_info:
        _check_domain_supported("invalid_domain")
    assert exc_info.value.status_code == 400


def test_check_rate_limit():
    ip = "192.168.1.100"
    _analyze_request_times[ip] = []
    for _ in range(_ANALYZE_RATE_LIMIT):
        _check_rate_limit(ip)
    with pytest.raises(HTTPException) as exc_info:
        _check_rate_limit(ip)
    assert exc_info.value.status_code == 429
    _analyze_request_times.pop(ip, None)


def test_retry_after_seconds():
    exc_ms = Exception("Rate limit exceeded, try again in 500ms")
    assert _retry_after_seconds(exc_ms) == 0.5

    exc_s = Exception("Quota exceeded, try again in 12.5s")
    assert _retry_after_seconds(exc_s) == 12.5

    exc_none = Exception("General error without time")
    assert _retry_after_seconds(exc_none) is None


def test_as_list():
    assert _as_list(None) == []
    assert _as_list([1, 2, 3]) == [1, 2, 3]
    assert _as_list({"items": [1, 2]}) == [1, 2]
    assert _as_list({"candidates": ["c1"]}) == ["c1"]
    assert _as_list({"verdicts": ["v1"]}) == ["v1"]
    assert _as_list({"scorecards": ["s1"]}) == ["s1"]
    assert _as_list({"other": "value"}) == [{"other": "value"}]
    assert _as_list("single_string") == ["single_string"]


def test_extract_json_object():
    fenced = "Here is json:\n```json\n{\"key\": \"val\"}\n```\nDone."
    assert _extract_json_object(fenced) == '{"key": "val"}'

    unfenced = "Prefix text {\"a\": 1, \"b\": 2} suffix text"
    assert _extract_json_object(unfenced) == '{"a": 1, "b": 2}'

    invalid = "No json here at all"
    assert _extract_json_object(invalid) is None


def test_extract_json_object_handles_nested_objects():
    """Regression test: a naive "first { .. first }" or "[^}]*" regex truncates
    on the first inner closing brace, dropping real candidate/verdict payloads
    that nest objects (routine for InventionCandidate/AdversarialVerdict/ScoreCard)."""
    nested = (
        "```json\n"
        '{"candidate": {"title": "foo"}, "evidence": {"patents": ["x"]}}\n'
        "```"
    )
    extracted = _extract_json_object(nested)
    assert extracted == '{"candidate": {"title": "foo"}, "evidence": {"patents": ["x"]}}'
    assert json.loads(extracted) == {"candidate": {"title": "foo"}, "evidence": {"patents": ["x"]}}


def test_extract_json_object_ignores_braces_inside_strings():
    tricky = '{"title": "uses {curly} braces in text", "score": 1}'
    extracted = _extract_json_object(tricky)
    assert extracted == tricky
    assert json.loads(extracted) == {"title": "uses {curly} braces in text", "score": 1}


def test_extract_json_object_handles_escaped_quotes_in_strings():
    escaped = r'{"title": "says \"hello\" to you"}'
    extracted = _extract_json_object(escaped)
    assert extracted == escaped
    assert json.loads(extracted) == {"title": 'says "hello" to you'}


def test_extract_json_object_returns_none_when_unbalanced():
    assert _extract_json_object('{"a": 1, "b": {"c": 2}') is None


def test_parse_item_to_dict():
    assert _parse_item_to_dict({"a": 1}, "Test") == {"a": 1}
    assert _parse_item_to_dict('{"a": 1}', "Test") == {"a": 1}
    assert _parse_item_to_dict("```json\n{\"a\": 2}\n```", "Test") == {"a": 2}
    assert _parse_item_to_dict("Not a json", "Test") is None
    assert _parse_item_to_dict(12345, "Test") is None


def test_parse_item_to_dict_extracted_text_still_invalid_json():
    """A '{' is found and the scanner returns a balanced span, but that span still
    isn't valid JSON (e.g. single-quoted keys) — must fail gracefully, not raise."""
    assert _parse_item_to_dict("{'a': 1} is what the model said", "Test") is None


def test_as_list_fallback_for_non_list_dict_str():
    assert _as_list(("a", "b")) == ["a", "b"]


def test_validated():
    valid_cand = InventionCandidate(
        candidate_id="c1",
        cluster_id="H01M",
        title="Title",
        description="Desc",
        claimed_novelty="Nov",
    )
    # Already a BaseModel
    assert len(_validated(InventionCandidate, [valid_cand])) == 1

    # Valid dict
    dict_cand = {
        "candidate_id": "c2",
        "cluster_id": "H01M",
        "title": "Title 2",
        "description": "Desc 2",
        "claimed_novelty": "Nov 2",
    }
    assert len(_validated(InventionCandidate, [dict_cand])) == 1

    # Valid JSON string
    json_cand = '{"candidate_id": "c3", "cluster_id": "H01M", "title": "T3", "description": "D3", "claimed_novelty": "N3"}'
    assert len(_validated(InventionCandidate, [json_cand])) == 1

    # Invalid dictionary schema
    invalid_dict = {"wrong_key": "val"}
    assert len(_validated(InventionCandidate, [invalid_dict])) == 0


@pytest.mark.asyncio
async def test_handle_candidate_state():
    job_id = "test_cand_job_001"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="test")
    seen = set()

    cands = [
        {
            "candidate_id": "cand_1",
            "cluster_id": "H01M",
            "title": "Solid Battery",
            "description": "Desc",
            "claimed_novelty": "Nov",
        },
        "raw_string_candidate",
    ]
    validated_res = await _handle_candidate_state(job_id, cands, seen)
    assert len(validated_res) == 1
    assert "cand_1" in seen
    assert "raw_string_candidate" in seen


@pytest.mark.asyncio
async def test_handle_candidate_state_with_object_attribute_access():
    """Covers the non-dict, non-string branch: an ADK-emitted object exposing
    .candidate_id/.title as attributes rather than dict keys."""
    job_id = "test_cand_job_002"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="test")
    seen: set[str] = set()

    cand_obj = InventionCandidate(
        candidate_id="cand_obj_1",
        cluster_id="H01M",
        title="Object-form Candidate",
        description="Desc",
        claimed_novelty="Nov",
    )
    await _handle_candidate_state(job_id, [cand_obj], seen)
    assert "cand_obj_1" in seen


@pytest.mark.asyncio
async def test_handle_verdict_state():
    job_id = "test_verdict_job_001"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="test")
    seen = set()

    verdicts = [
        {
            "candidate_id": "c1",
            "verdict": "rejected",
            "rationale": "Prior art exists",
            "cited_patents": ["ES-2849102-B2"],
        },
        {
            "candidate_id": "c2",
            "verdict": "survives",
            "rationale": "Novel and non-obvious",
            "cited_patents": ["ES-2849102-B2"],
        },
        {
            "candidate_id": "c3",
            "verdict": "revised",
            "rationale": "Needs narrower scope",
            "cited_patents": ["ES-1234567-A1"],
        },
    ]
    validated_res = await _handle_verdict_state(job_id, verdicts, seen)
    assert len(validated_res) == 3
    assert len(seen) == 3

    job = _job_store.get_job(job_id)
    assert job["progress"]["candidatesRejected"] == 1
    assert job["progress"]["candidatesSurvived"] == 1
    assert job["progress"]["candidatesRevised"] == 1


@pytest.mark.asyncio
async def test_handle_verdict_state_skips_non_dict_and_normalizes_revise():
    """Covers: a non-dict entry in the verdicts list (skipped via `continue`), and
    the present-tense "revise" spelling some models emit instead of "revised"."""
    job_id = "test_verdict_job_002"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="test")
    seen: set[int] = set()

    verdicts = [
        "not_a_dict_verdict",
        {
            "candidate_id": "c4",
            "verdict": "revise",
            "rationale": "Needs narrower scope",
            "cited_patents": [],
        },
    ]
    validated_res = await _handle_verdict_state(job_id, verdicts, seen)
    assert validated_res == []
    assert seen == {1}

    job = _job_store.get_job(job_id)
    assert job["progress"]["candidatesRevised"] == 1


def test_classify_error():
    quota_exc = Exception("RESOURCE_EXHAUSTED: Quota exceeded PerDay for project")
    info = _classify_error(quota_exc)
    assert info["error_type"] == "quota_exhausted"

    generic_exc = ValueError("Something unexpected happened")
    info2 = _classify_error(generic_exc)
    assert info2["error_type"] == "unknown"
    assert "Something unexpected happened" in info2["detail"]


def test_emit_event():
    job_id = "event_test_job"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="test")
    _emit_event(job_id, "custom_event", "Message text", candidate_id="c99", evidence={"x": 1})

    job = _job_store.get_job(job_id)
    events = job.get("events", [])
    assert len(events) >= 1
    last_evt = events[-1]
    assert last_evt["type"] == "custom_event"
    assert last_evt["candidateId"] == "c99"
    assert last_evt["evidence"] == {"x": 1}


def test_demands_endpoint():
    # Spanish demands / default
    response = client.get("/api/demands", params={"domain": "solid_state_battery"})
    assert response.status_code == 200
    data = response.json()
    assert "demands" in data

    # Filtered by cluster
    response_cluster = client.get("/api/demands", params={"domain": "solid_state_battery", "cluster_id": "H01M"})
    assert response_cluster.status_code == 200


def test_demands_endpoint_uses_cluster_filter_when_datasource_supports_it():
    """Covers the get_demands_for_cluster branch: only reachable when the configured
    datasource actually exposes that method, which the default test double doesn't."""
    with patch.object(_demand_datasource, "get_demands_for_cluster", return_value=[], create=True):
        response = client.get("/api/demands", params={"domain": "solid_state_battery", "cluster_id": "H01M"})
        assert response.status_code == 200
        assert response.json()["demands"] == []


def test_demands_endpoint_uses_spanish_demands_when_no_cluster_id():
    """Covers the get_spanish_demands branch (no cluster_id, datasource exposes it)."""
    with patch.object(_demand_datasource, "get_spanish_demands", return_value=[], create=True):
        response = client.get("/api/demands", params={"domain": "solid_state_battery"})
        assert response.status_code == 200
        assert response.json()["demands"] == []


def test_demand_patents_endpoint():
    # Valid demand signal
    response = client.get(
        "/api/landscape/demand-patents",
        params={"demand_id": "INNOGET-2292", "domain": "solid_state_battery"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "patents" in data

    # Nonexistent demand signal
    response_404 = client.get(
        "/api/landscape/demand-patents",
        params={"demand_id": "NONEXISTENT_SIGNAL_999", "domain": "solid_state_battery"},
    )
    assert response_404.status_code == 404


def test_analyze_endpoint_flow():
    # Start analysis
    response = client.post(
        "/api/analyze",
        json={"domain": "solid_state_battery", "query": "solid electrolyte with sulfide"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Poll status
    poll_resp = client.get(f"/api/analyze/{job_id}")
    assert poll_resp.status_code == 200
    poll_data = poll_resp.json()
    assert poll_data["job_id"] == job_id
    assert "status" in poll_data

    # List jobs
    list_resp = client.get("/api/analyze")
    assert list_resp.status_code == 200
    jobs = list_resp.json()["jobs"]
    assert any(j["job_id"] == job_id for j in jobs)


def test_analyze_endpoint_unsupported_domain():
    response = client.post(
        "/api/analyze",
        json={"domain": "unsupported_domain_999", "query": "test query"},
    )
    assert response.status_code == 400


def test_analyze_status_nonexistent_job():
    response = client.get("/api/analyze/nonexistent_job_12345")
    assert response.status_code == 404


def test_analyze_endpoint_rejects_when_already_busy():
    with patch.object(_execution_policy, "is_busy", return_value=True):
        response = client.post(
            "/api/analyze",
            json={"domain": "solid_state_battery", "query": "test query"},
        )
        assert response.status_code == 503


def test_get_dist_dir_prefers_static_dir_when_present():
    with (
        patch("infrastructure.api.os.path.exists", side_effect=lambda p: p.endswith("static")),
        patch("infrastructure.api.AGENTS_DIR", "/fake/agents/dir"),
    ):
        assert _get_dist_dir() == "/fake/agents/dir/static"


def test_get_dist_dir_falls_back_to_frontend_dist():
    with (
        patch("infrastructure.api.os.path.exists", side_effect=lambda p: p.endswith("frontend/dist")),
        patch("infrastructure.api.AGENTS_DIR", "/fake/agents/dir"),
    ):
        assert _get_dist_dir() == os.path.abspath("/fake/agents/dir/../frontend/dist")


def test_get_dist_dir_returns_none_when_neither_exists():
    with patch("infrastructure.api.os.path.exists", return_value=False):
        assert _get_dist_dir() is None


@pytest.mark.asyncio
async def test_run_job_timeout_handling():
    job_id = "timeout_test_job"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="test")

    with patch("infrastructure.analysis_pipeline._execute_analysis", side_effect=TimeoutError()):
        await _run_job(job_id, MagicMock())

    job = _job_store.get_job(job_id)
    assert job["status"] == "failed"
    assert job["error_type"] == "timeout"


@pytest.mark.asyncio
async def test_run_job_exception_handling():
    job_id = "exc_test_job"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="test")

    with patch("infrastructure.analysis_pipeline._execute_analysis", side_effect=RuntimeError("Engine failure")):
        await _run_job(job_id, MagicMock())

    job = _job_store.get_job(job_id)
    assert job["status"] == "failed"
    assert "Engine failure" in job["error"]


class _FakeSession:
    def __init__(self, session_id: str, state: dict):
        self.id = session_id
        self.state = state


@pytest.mark.asyncio
async def test_execute_analysis_full_flow():
    """Exercises the real _execute_analysis body end to end: research -> clustering ->
    the run() event loop picking up candidates/verdicts/scores from session state as they
    accumulate -> final result assembly. Previously this function was only ever exercised
    via `patch("infrastructure.analysis_pipeline._execute_analysis", ...)` in the _run_job
    tests above, so its entire body (bar the module-level definitions) was unexercised."""
    job_id = "execute_analysis_full_flow_job"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="solid electrolyte")

    research_result = MagicMock()
    research_result.patents = [MagicMock()]
    research_result.clusters = [MagicMock(model_dump=lambda: {"cluster_id": "H01M"})]
    research_result.cluster_id = "H01M"
    research_result.cluster_context = {"summary": "context"}

    candidate = {
        "candidate_id": "cand_1",
        "cluster_id": "H01M",
        "title": "Title",
        "description": "Desc",
        "claimed_novelty": "Novel",
    }
    verdict = {
        "candidate_id": "cand_1",
        "verdict": "survives",
        "rationale": "Rationale",
        "cited_patents": ["ES-2849102-B2"],
    }
    scorecard = {
        "candidate_id": "cand_1",
        "novelty": 0.8,
        "prior_art_risk": 0.2,
        "differentiation": 0.7,
        "evidence": 0.9,
        "supporting_evidence": ["ES-2849102-B2"],
    }

    # Session state grows across three simulated run_async ticks, mirroring how the real
    # ADK session accumulates candidate/verdict/score state as agents in the pipeline run.
    states = [
        {CANDIDATE_INVENTIONS: [candidate]},
        {CANDIDATE_INVENTIONS: [candidate], ADVERSARIAL_VERDICTS: [verdict]},
        {CANDIDATE_INVENTIONS: [candidate], ADVERSARIAL_VERDICTS: [verdict], SCORED_CANDIDATES: [scorecard]},
    ]
    tick = {"n": 0}

    async def fake_get_session(**kwargs):
        idx = min(tick["n"], len(states) - 1)
        tick["n"] += 1
        return _FakeSession(kwargs["session_id"], states[idx])

    async def fake_run_async(**kwargs):
        for _ in states:
            yield object()

    async def fake_create_session(**kwargs):
        return _FakeSession("fake-session-1", kwargs.get("state", {}))

    with (
        patch.object(analysis_pipeline_module, "_research_service", MagicMock(conduct_research=AsyncMock(return_value=research_result))),
        patch.object(analysis_pipeline_module._session_service, "create_session", side_effect=fake_create_session),
        patch.object(analysis_pipeline_module._session_service, "get_session", side_effect=fake_get_session),
        patch.object(analysis_pipeline_module._session_service, "delete_session", new=AsyncMock()),
        patch.object(analysis_pipeline_module._runner, "run_async", side_effect=fake_run_async),
    ):
        result = await _execute_analysis(
            job_id, AnalyzeRequest(domain="solid_state_battery", query="solid electrolyte")
        )

    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["candidate_id"] == "cand_1"
    assert len(result["scorecards"]) == 1
    assert "telemetry_profile" in result

    job = _job_store.get_job(job_id)
    assert job["clusters"] == [{"cluster_id": "H01M"}]


@pytest.mark.asyncio
async def test_execute_analysis_retries_on_rate_limit_then_succeeds():
    """Covers the retry branch: run() raises once with a recognizable rate-limit message,
    _retry_after_seconds parses the wait, and the second attempt succeeds."""
    job_id = "execute_analysis_retry_job"
    _job_store.create_job(job_id=job_id, domain="solid_state_battery", query="solid electrolyte")

    research_result = MagicMock()
    research_result.patents = []
    research_result.clusters = []
    research_result.cluster_id = "H01M"
    research_result.cluster_context = {}

    attempt = {"n": 0}

    async def fake_run_async(**kwargs):
        attempt["n"] += 1
        if attempt["n"] == 1:
            raise RuntimeError("Rate limit exceeded, try again in 10ms")
        return
        yield  # pragma: no cover - makes this an async generator; unreachable on success

    async def fake_create_session(**kwargs):
        return _FakeSession("fake-session-2", kwargs.get("state", {}))

    async def fake_get_session(**kwargs):
        return _FakeSession(kwargs["session_id"], {})

    with (
        patch.object(analysis_pipeline_module, "_research_service", MagicMock(conduct_research=AsyncMock(return_value=research_result))),
        patch.object(analysis_pipeline_module._session_service, "create_session", side_effect=fake_create_session),
        patch.object(analysis_pipeline_module._session_service, "get_session", side_effect=fake_get_session),
        patch.object(analysis_pipeline_module._session_service, "delete_session", new=AsyncMock()),
        patch.object(analysis_pipeline_module._runner, "run_async", side_effect=fake_run_async),
        patch("infrastructure.analysis_pipeline.asyncio.sleep", new=AsyncMock()),
    ):
        result = await _execute_analysis(
            job_id, AnalyzeRequest(domain="solid_state_battery", query="solid electrolyte")
        )

    assert attempt["n"] == 2
    assert result["candidates"] == []


def test_frontend_routes_and_security(tmp_path):
    # API/health routes cannot be served by frontend catchall
    api_miss = client.get("/api/nonexistent_endpoint")
    assert api_miss.status_code == 404

    health_miss = client.get("/health/subpath")
    assert health_miss.status_code == 404

    # Test static file serving when dist exists
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    index_file = dist_dir / "index.html"
    index_file.write_text("<html><body>Test App</body></html>", encoding="utf-8")
    asset_file = dist_dir / "style.css"
    asset_file.write_text("body { color: red; }", encoding="utf-8")

    with patch("infrastructure.api._get_dist_dir", return_value=str(dist_dir)):
        # Root route
        root_resp = client.get("/")
        assert root_resp.status_code == 200
        assert "Test App" in root_resp.text

        # Existing static file
        asset_resp = client.get("/style.css")
        assert asset_resp.status_code == 200
        assert "color: red" in asset_resp.text

        # SPA client routing fallback to index.html
        spa_resp = client.get("/research/cluster-1")
        assert spa_resp.status_code == 200
        assert "Test App" in spa_resp.text

    # When dist does not exist
    with patch("infrastructure.api._get_dist_dir", return_value=None):
        root_404 = client.get("/")
        assert root_404.status_code == 404

        route_404 = client.get("/some/route")
        assert route_404.status_code == 404
