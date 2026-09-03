"""In-memory and persistent job store for analysis runs."""

import asyncio
import time
from typing import Any


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def create_job(self, job_id: str, domain: str, query: str) -> dict[str, Any]:
        job_data: dict[str, Any] = {
            "job_id": job_id,
            "id": job_id,
            "status": "running",
            "stage": "starting",
            "domain": domain,
            "query": query,
            "created_at": time.time(),
            "updated_at": time.time(),
            "events": [],
            "progress": {},
            "results": None,
            "result": None,
            "error": None,
            "error_type": None,
        }
        self._jobs[job_id] = job_data
        return job_data

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs: Any) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        job.update(kwargs)
        job["updated_at"] = time.time()
        return job

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        sorted_jobs = sorted(self._jobs.values(), key=lambda j: j.get("created_at", 0), reverse=True)
        return sorted_jobs[:limit]

    async def set_stage(self, job_id: str, stage: str) -> None:
        await asyncio.sleep(0)
        self.update_job(job_id, stage=stage)

    async def update_progress(self, job_id: str, key: str, value: Any) -> None:
        await asyncio.sleep(0)
        job = self._jobs.get(job_id)
        if job:
            job.setdefault("progress", {})[key] = value
            job["updated_at"] = time.time()

    async def append_event(self, job_id: str, event: dict[str, Any]) -> None:
        await asyncio.sleep(0)
        job = self._jobs.get(job_id)
        if job:
            job.setdefault("events", []).append(event)
            job["updated_at"] = time.time()

    async def set_result(self, job_id: str, results: dict[str, Any]) -> None:
        await asyncio.sleep(0)
        self.update_job(job_id, status="completed", results=results, result=results)

    async def set_error(self, job_id: str, error: str, error_type: str = "internal") -> None:
        await asyncio.sleep(0)
        self.update_job(job_id, status="failed", error=error, error_type=error_type)


_JOB_STORE_INSTANCE = InMemoryJobStore()


def get_job_store() -> InMemoryJobStore:
    return _JOB_STORE_INSTANCE
