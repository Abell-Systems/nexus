import os

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")

from fastapi.testclient import TestClient

from main import app

# Entered (not just constructed) so the ASGI portal's event loop stays alive
# across requests — needed because /api/analyze now spawns a background task
# that must keep running after its own request handler returns.
client = TestClient(app).__enter__()


def test_analyze_rejects_empty_input_before_llm_call(monkeypatch):
    # The real agent graph needs a live Gemini key; skip calling it in unit
    # tests and instead assert the endpoint exists and validates its input.
    response = client.post("/api/analyze", json={"query": "", "domain": "", "cluster_id": ""})
    assert response.status_code == 422  # empty query/domain rejected before an LLM call is made


def test_as_list_normalizes_state_shapes():
    from main import _as_list

    assert _as_list(None) == []
    assert _as_list('{"candidate_id": "c1"}') == [{"candidate_id": "c1"}]
    assert _as_list({"candidate_id": "c1"}) == [{"candidate_id": "c1"}]
    assert _as_list({"scorecards": [{"novelty": 0.9}]}) == [{"novelty": 0.9}]
    assert _as_list("plain adversarial prose") == ["plain adversarial prose"]
    assert _as_list([{"a": 1}]) == [{"a": 1}]


def test_validated_drops_malformed_entries():
    from main import _validated
    from patent_agent.tools.schemas import ScoreCard

    good = {
        "candidate_id": "c1",
        "novelty": 0.9,
        "prior_art_risk": 0.1,
        "differentiation": 0.8,
        "evidence": 0.7,
        "supporting_evidence": ["US-1"],
        "summary": "ok",
        "scope_drift": False,
        "drift_reason": "",
        "obviousness_risk": "low",
        "landscape_quality": "RELEVANT",
        "evaluation_verdict": "REJECTED_ON_PRIOR_ART",
    }
    # free-text agent output and missing required fields must not reach the frontend
    out = _validated(ScoreCard, [good, "prose", {"candidate_id": "c2"}, dict(good, novelty="high")])
    assert out == [good]


def test_validated_recovers_json_wrapped_in_prose_or_fence():
    from main import _validated
    from patent_agent.tools.schemas import AdversarialVerdict

    good = {
        "candidate_id": "c1",
        "verdict": "rejected",
        "rationale": "anticipated",
        "cited_patents": ["US-1"],
    }
    fenced = f"Here is my verdict:\n```json\n{__import__('json').dumps(good)}\n```\nThanks."
    prose_wrapped = f"### Verdict\nSome commentary before. {__import__('json').dumps(good)} and after."
    pure_prose_no_json = "### Verdict\n**Rejected** — no anticipating prior art was cited."

    out = _validated(AdversarialVerdict, [fenced, prose_wrapped, pure_prose_no_json])
    assert out == [good, good]


def test_analyze_rejects_unsupported_domain():
    resp = client.post("/api/analyze", json={"query": "cancer", "domain": "Biotechnology"})
    assert resp.status_code == 422
    assert "battery" in resp.json()["detail"].lower()


def test_landscape_rejects_unsupported_domain():
    resp = client.get("/api/landscape", params={"query": "cancer", "domain": "Biotechnology"})
    assert resp.status_code == 422


def test_landscape_rejects_invalid_params():
    assert client.get("/api/landscape", params={"query": "", "domain": "battery electrolyte"}).status_code == 422
    assert client.get("/api/landscape", params={"query": "q", "domain": ""}).status_code == 422
    assert (
        client.get("/api/landscape", params={"query": "q", "domain": "battery electrolyte", "max_results": 1000}).status_code
        == 422
    )


def test_landscape_single_search_and_valid_clusters():
    from patent_agent.tools.schemas import PatentCluster, PatentRecord

    calls: list[tuple[str, int]] = []

    class SpySource:
        def search_patents(self, query, domain, max_results=20):
            calls.append((query, max_results))
            return [
                PatentRecord(
                    publication_number=f"US-{i}",
                    title=f"t{i}",
                    abstract="a",
                    filing_date="2025-01-01",
                    publication_date="2025-06-01",
                    country_code="US",
                    cpc_codes=["H01M10/0562"],
                )
                for i in range(3)
            ]

    import main

    original = main.get_patents_datasource
    main.get_patents_datasource = lambda: SpySource()
    try:
        response = client.get("/api/landscape", params={"query": "q", "domain": "battery electrolyte"})
    finally:
        main.get_patents_datasource = original
    assert response.status_code == 200
    body = response.json()
    assert len(calls) == 1  # patents searched once, not again for clustering
    assert body["clusters"]
    PatentCluster.model_validate(body["clusters"][0])


def test_analyze_returns_202_with_job_id_and_completes(monkeypatch):
    import asyncio

    import main

    async def fake_execute(job_id, req):
        await asyncio.sleep(0)
        return {"candidates": [], "verdicts": [], "scorecards": []}

    monkeypatch.setattr(main, "_execute_analysis", fake_execute)
    resp = client.post("/api/analyze", json={"query": "q", "domain": "battery electrolyte", "cluster_id": "c"})
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    import time

    for _ in range(100):
        body = client.get(f"/api/analyze/{job_id}").json()
        if body["status"] != "running":
            break
        time.sleep(0.05)
    assert body["status"] == "done"


def test_analyze_status_unknown_job_is_404():
    assert client.get("/api/analyze/nope").status_code == 404


def test_list_analyze_jobs_includes_domain_query_and_candidate_count(monkeypatch):
    import asyncio
    import time

    import main

    async def fake_execute(job_id, req):
        await asyncio.sleep(0)
        return {"candidates": [{"candidate_id": "c1"}], "verdicts": [], "scorecards": []}

    monkeypatch.setattr(main, "_execute_analysis", fake_execute)
    resp = client.post("/api/analyze", json={"query": "history-query", "domain": "history-domain-battery-electrolyte"})
    job_id = resp.json()["job_id"]

    for _ in range(100):
        if client.get(f"/api/analyze/{job_id}").json()["status"] != "running":
            break
        time.sleep(0.05)

    listing = client.get("/api/analyze")
    assert listing.status_code == 200
    jobs = listing.json()["jobs"]
    match = next(j for j in jobs if j["job_id"] == job_id)
    assert match["domain"] == "history-domain-battery-electrolyte"
    assert match["query"] == "history-query"
    assert match["status"] == "done"
    assert match["candidate_count"] == 1
    assert match["created_at"] is not None


def test_analyze_rejects_concurrent_runs(monkeypatch):
    import asyncio

    import main

    gate = asyncio.Event()

    class FakeReq:
        query = "q"
        domain = "battery electrolyte"
        cluster_id = "c"

    async def slow_execute(job_id, req):
        await gate.wait()
        return {"candidates": [], "verdicts": [], "scorecards": []}

    monkeypatch.setattr(main, "_execute_analysis", slow_execute)
    first = client.post("/api/analyze", json={"query": "q", "domain": "battery electrolyte", "cluster_id": "c"})
    assert first.status_code == 202
    second = client.post("/api/analyze", json={"query": "q", "domain": "battery electrolyte", "cluster_id": "c2"})
    assert second.status_code == 503
    gate.set()


def test_analyze_status_flattens_result_for_frontend_contract(monkeypatch):
    """GET /api/analyze/{id} must expose candidates/verdicts/scorecards at the
    top level, not nested under "result" -- frontend/src/types/patent.ts's
    JobStatusResponse and ResultsView.tsx both read them flat."""
    import asyncio
    import time

    import main

    async def fake_execute(job_id, req):
        await asyncio.sleep(0)
        return {"candidates": [{"candidate_id": "c1"}], "verdicts": [], "scorecards": []}

    monkeypatch.setattr(main, "_execute_analysis", fake_execute)
    resp = client.post("/api/analyze", json={"query": "q", "domain": "battery electrolyte"})
    job_id = resp.json()["job_id"]

    for _ in range(100):
        body = client.get(f"/api/analyze/{job_id}").json()
        if body["status"] != "running":
            break
        time.sleep(0.05)

    assert body["candidates"] == [{"candidate_id": "c1"}]
    assert "result" not in body
    assert body["job_id"] == job_id


def test_analyze_rate_limits_per_ip(monkeypatch):
    import asyncio

    import main

    async def fake_execute(job_id, req):
        await asyncio.sleep(0)
        return {"candidates": [], "verdicts": [], "scorecards": []}

    monkeypatch.setattr(main, "_execute_analysis", fake_execute)
    for _ in range(main._ANALYZE_RATE_LIMIT):
        resp = client.post("/api/analyze", json={"query": "q", "domain": "battery electrolyte"})
        assert resp.status_code == 202
        for _ in range(100):
            if client.get(f"/api/analyze/{resp.json()['job_id']}").json()["status"] != "running":
                break
            import time

            time.sleep(0.05)

    over_limit = client.post("/api/analyze", json={"query": "q", "domain": "battery electrolyte"})
    assert over_limit.status_code == 429


def test_frontend_root_and_static_assets_serve_200():
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "<!doctype html>" in res_root.text.lower()

    res_index = client.get("/index.html")
    assert res_index.status_code == 200


