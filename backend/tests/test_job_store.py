import pytest
from patent_agent.shared.job_store import InMemoryJobStore, get_job_store


@pytest.mark.anyio
async def test_job_store_lifecycle():
    store = InMemoryJobStore()
    job_id = "test_job_123"

    await store.create_job(job_id, {"initial_key": "initial_value"})
    job = await store.get_job(job_id)
    assert job is not None
    assert job["id"] == job_id
    assert job["status"] == "pending"
    assert job["initial_key"] == "initial_value"

    await store.set_stage(job_id, "researching")
    await store.update_progress(job_id, "patentsAnalyzed", 25)
    await store.append_event(job_id, {"type": "test_event", "message": "hello"})

    job = await store.get_job(job_id)
    assert job["stage"] == "researching"
    assert job["progress"]["patentsAnalyzed"] == 25
    assert len(job["events"]) == 1
    assert job["events"][0]["type"] == "test_event"

    await store.set_result(job_id, {"verdicts": ["ok"]})
    job = await store.get_job(job_id)
    assert job["status"] == "done"
    assert job["result"] == {"verdicts": ["ok"]}


@pytest.mark.anyio
async def test_list_jobs_returns_newest_first():
    store = InMemoryJobStore()

    await store.create_job("older", {"created_at": "2026-08-30T10:00:00+00:00"})
    await store.create_job("newer", {"created_at": "2026-08-30T12:00:00+00:00"})

    jobs = await store.list_jobs()

    assert [j["id"] for j in jobs] == ["newer", "older"]


@pytest.mark.anyio
async def test_list_jobs_empty_store():
    store = InMemoryJobStore()
    assert await store.list_jobs() == []
