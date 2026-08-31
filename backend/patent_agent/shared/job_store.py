"""Job Persistence Layer for IP-Matchmaker.

Abstracts job state management from the API entrypoint. Supports:
- InMemoryJobStore (single instance / development / tests)
- Extensible to PersistentJobStore (Firestore, PostgreSQL, Redis)
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseJobStore(ABC):
    """Abstract interface for storing and retrieving pipeline job states."""

    @abstractmethod
    async def create_job(self, job_id: str, initial_data: dict) -> None:
        """Initialize a new job with given data."""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[dict]:
        """Fetch job data by ID."""
        pass

    @abstractmethod
    async def update_job(self, job_id: str, updates: dict) -> None:
        """Merge update dictionary into existing job data."""
        pass

    @abstractmethod
    async def append_event(self, job_id: str, event: dict) -> None:
        """Append an event log to the job."""
        pass

    @abstractmethod
    async def set_stage(self, job_id: str, stage: str) -> None:
        """Update current execution stage."""
        pass

    @abstractmethod
    async def update_progress(self, job_id: str, key: str, value: Any) -> None:
        """Update a specific progress counter."""
        pass

    @abstractmethod
    async def set_result(self, job_id: str, result: dict) -> None:
        """Mark job done and save final result."""
        pass

    @abstractmethod
    async def set_error(self, job_id: str, error_message: str) -> None:
        """Mark job errored and save error message."""
        pass

    @abstractmethod
    async def list_jobs(self) -> list[dict]:
        """List all known jobs, newest first."""
        pass


class InMemoryJobStore(BaseJobStore):
    """In-memory thread-safe implementation of BaseJobStore."""

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, job_id: str, initial_data: dict) -> None:
        async with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": "pending",
                "stage": "pending",
                "progress": {},
                "events": [],
                "clusters": [],
                "result": None,
                "error": None,
                **initial_data,
            }

    async def get_job(self, job_id: str) -> Optional[dict]:
        async with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job is not None else None

    async def update_job(self, job_id: str, updates: dict) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)

    async def append_event(self, job_id: str, event: dict) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].setdefault("events", []).append(event)

    async def set_stage(self, job_id: str, stage: str) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["stage"] = stage

    async def update_progress(self, job_id: str, key: str, value: Any) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].setdefault("progress", {})[key] = value

    async def set_result(self, job_id: str, result: dict) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "done"
                self._jobs[job_id]["stage"] = "done"
                self._jobs[job_id]["result"] = result

    async def set_error(self, job_id: str, error_message: str) -> None:
        async with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "error"
                self._jobs[job_id]["stage"] = "error"
                self._jobs[job_id]["error"] = error_message

    async def list_jobs(self) -> list[dict]:
        async with self._lock:
            jobs = [dict(job) for job in self._jobs.values()]
        jobs.sort(key=lambda j: j.get("created_at") or "", reverse=True)
        return jobs


_default_job_store: Optional[BaseJobStore] = None


def get_job_store() -> BaseJobStore:
    """Singleton getter for the configured JobStore."""
    global _default_job_store
    if _default_job_store is None:
        _default_job_store = InMemoryJobStore()
    return _default_job_store
