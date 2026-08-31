import os
from datetime import datetime, timezone

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")

from fastapi.testclient import TestClient

import main
from main import _emit_event, _jobs, app

client = TestClient(app).__enter__()


def test_emit_event_appends_to_job():
    job_id = "test_job_1"
    _jobs[job_id] = {"status": "running", "stage": "queued", "events": []}
    
    _emit_event(job_id, "research_completed", "Researched 20 patents")
    _emit_event(job_id, "landscape_clustered", "Found 3 clusters")
    _emit_event(job_id, "candidate_generated", "Generated Candidate #1", candidate_id="1")
    _emit_event(job_id, "candidate_challenged", "Candidate #1 challenged", candidate_id="1")
    _emit_event(job_id, "candidate_rejected", "Candidate #1 rejected", candidate_id="1")
    _emit_event(job_id, "candidate_revised", "Candidate #1 revised", candidate_id="1")
    _emit_event(job_id, "candidate_survived", "Candidate #1 survived", candidate_id="1")
    _emit_event(job_id, "assessment_completed", "Final assessment complete")

    events = _jobs[job_id]["events"]
    assert len(events) == 8
    
    types = [e["type"] for e in events]
    expected_order = [
        "research_completed",
        "landscape_clustered",
        "candidate_generated",
        "candidate_challenged",
        "candidate_rejected",
        "candidate_revised",
        "candidate_survived",
        "assessment_completed",
    ]
    assert types == expected_order
    
    # Check candidate IDs
    assert events[2]["candidateId"] == "1"
    assert events[3]["candidateId"] == "1"
    assert events[4]["candidateId"] == "1"
    assert events[5]["candidateId"] == "1"
    assert events[6]["candidateId"] == "1"


def test_events_belong_to_correct_job():
    job1 = "job_alpha"
    job2 = "job_beta"
    _jobs[job1] = {"status": "running", "stage": "queued", "events": []}
    _jobs[job2] = {"status": "running", "stage": "queued", "events": []}

    _emit_event(job1, "research_completed", "Job 1 research")
    _emit_event(job2, "research_completed", "Job 2 research")

    assert len(_jobs[job1]["events"]) == 1
    assert _jobs[job1]["events"][0]["message"] == "Job 1 research"

    assert len(_jobs[job2]["events"]) == 1
    assert _jobs[job2]["events"][0]["message"] == "Job 2 research"


def test_malformed_event_or_missing_fields_cannot_crash_status_endpoint():
    job_id = "malformed_job"
    # Inject malformed/incomplete event data
    _jobs[job_id] = {
        "status": "running",
        "stage": "researching",
        "events": [
            None,
            "plain string event",
            {"type": "research_completed"},  # missing timestamp/message
            {"type": "invalid", "timestamp": "2026-08-26T00:00:00Z", "message": "ok"},
        ],
    }

    response = client.get(f"/api/analyze/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert "events" in body
    assert len(body["events"]) == 4


def test_analyze_status_returns_events_in_response(monkeypatch):
    import asyncio

    async def fake_execute(job_id, req):
        await asyncio.sleep(0)
        _emit_event(job_id, "research_completed", "Mock research completed")
        _emit_event(job_id, "candidate_survived", "Candidate #1 survived", candidate_id="1")
        return {"candidates": [], "verdicts": [], "scorecards": [], "events": _jobs[job_id].get("events", [])}

    monkeypatch.setattr(main, "_execute_analysis", fake_execute)
    resp = client.post("/api/analyze", json={"query": "q", "domain": "battery electrolyte", "cluster_id": "c"})
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    import time
    for _ in range(100):
        body = client.get(f"/api/analyze/{job_id}").json()
        if body["status"] != "running":
            break
        time.sleep(0.02)

    assert body["status"] == "done"
    assert "events" in body
    assert len(body["events"]) >= 2
    types = [e["type"] for e in body["events"]]
    assert "research_completed" in types
    assert "candidate_survived" in types
