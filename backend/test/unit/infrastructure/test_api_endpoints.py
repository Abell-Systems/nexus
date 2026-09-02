"""Unit tests for FastAPI endpoints in infrastructure/api.py."""

from fastapi.testclient import TestClient

from infrastructure.api import app

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
    assert response.status_code in (400, 422)


def test_list_analyze_jobs_endpoint():
    response = client.get("/api/analyze")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


def test_analyze_status_nonexistent_job():
    response = client.get("/api/analyze/nonexistent_job_12345")
    assert response.status_code == 404
