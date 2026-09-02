"""In-memory and persistent job store for analysis runs."""

import time
from typing import Any


class InMemoryJobStore:
    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}

    def create_job(self, job_id: str, domain: str, query: str) -> dict[str, Any]:
        job_data = {
            "job_id": job_id,
            "status": "running",
            "stage": "starting",
            "domain": domain,
            "query": query,
            "created_at": time.time(),
            "updated_at": time.time(),
            "events": [],
            "results": None,
            "error": None,
            "error_type": None,
        }
        self._jobs[job_id] = job_data
        return job_data

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        job.update(kwargs)
        job["updated_at"] = time.time()
        return job

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        sorted_jobs = sorted(self._jobs.values(), key=lambda j: j.get("created_at", 0), reverse=True)
        return sorted_jobs[:limit]


_JOB_STORE_INSTANCE = InMemoryJobStore()


def get_job_store() -> InMemoryJobStore:
    return _JOB_STORE_INSTANCE
