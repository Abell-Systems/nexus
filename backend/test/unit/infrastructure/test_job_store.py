"""Unit tests for InMemoryJobStore."""

import pytest

from infrastructure.storage.job_store import InMemoryJobStore


@pytest.mark.asyncio
async def test_job_store_lifecycle():
    store = InMemoryJobStore()
    job = store.create_job("j1", "solid_state_battery", "electrolyte")
    assert job["job_id"] == "j1"
    assert job["status"] == "running"

    await store.set_stage("j1", "clustering")
    assert store.get_job("j1")["stage"] == "clustering"

    await store.update_progress("j1", "clustersFound", 3)
    assert store.get_job("j1")["progress"]["clustersFound"] == 3

    await store.append_event("j1", {"type": "cluster_found", "message": "found 3 clusters"})
    assert len(store.get_job("j1")["events"]) == 1

    await store.set_result("j1", {"candidates": []})
    assert store.get_job("j1")["status"] == "completed"

    jobs = store.list_jobs(limit=10)
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "j1"


@pytest.mark.asyncio
async def test_job_store_error_handling():
    store = InMemoryJobStore()
    store.create_job("j2", "solid_state_battery", "electrolyte")
    await store.set_error("j2", "Failed calculation", error_type="math_error")
    job = store.get_job("j2")
    assert job["status"] == "failed"
    assert job["error"] == "Failed calculation"
    assert job["error_type"] == "math_error"
