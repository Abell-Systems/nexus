import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app, _analyze_lock


def test_health_endpoint_details():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "use_mock_bigquery" in data
    assert "model_provider" in data
    assert "api_key_configured" in data
    assert "model" in data


def test_analyze_status_unknown_job_404():
    client = TestClient(app)
    res = client.get("/api/analyze/non_existent_job_12345")
    assert res.status_code == 404
    assert res.json()["detail"] == "Unknown job id."


def test_analyze_concurrent_lock_503():
    client = TestClient(app)
    # Manually acquire the analyze lock to simulate a running job
    _analyze_lock._locked = True
    try:
        res = client.post(
            "/api/analyze",
            json={"query": "solid electrolyte", "domain": "batteries", "cluster_id": "c1"},
        )
        assert res.status_code == 503
        assert res.json()["detail"] == "An analyze run is already in progress."
    finally:
        _analyze_lock._locked = False


def test_landscape_empty_query_422():
    client = TestClient(app)
    res = client.get("/api/landscape?query=&domain=batteries")
    assert res.status_code == 422
