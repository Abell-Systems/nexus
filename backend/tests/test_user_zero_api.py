import pytest
from fastapi.testclient import TestClient
from main import app, _jobs

client = TestClient(app)

def test_analyze_job_telemetry():
    response = client.post("/api/analyze", json={
        "domain": "solid-state battery electrolytes",
        "query": "solid electrolyte interphase"
    })
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "running"
    assert data["stage"] in ("queued", "researching")

    job_id = data["job_id"]
    status_resp = client.get(f"/api/analyze/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "stage" in status_data
    assert "progress" in status_data
