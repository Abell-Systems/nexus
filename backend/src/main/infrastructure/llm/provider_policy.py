"""Execution policy and pacing plugins for LLM providers."""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from google.adk.plugins import BasePlugin


class ProviderPolicy:
    def __init__(
        self,
        max_requests_per_minute: int = 30,
        max_tokens_per_minute: int = 30000,
        cooldown_seconds: float = 2.0,
    ) -> None:
        self.max_requests_per_minute = max_requests_per_minute
        self.max_tokens_per_minute = max_tokens_per_minute
        self.cooldown_seconds = cooldown_seconds


DirectProviderPolicy = ProviderPolicy
GroqFreeTierPolicy = ProviderPolicy


class ExecutionPolicy:
    def __init__(self, max_concurrency: int = 1) -> None:
        self.max_concurrency = max_concurrency
        self.active_runs = 0
        self.provider_policy = ProviderPolicy()

    def is_busy(self) -> bool:
        return self.active_runs >= self.max_concurrency

    @asynccontextmanager
    async def acquire_execution_slot(self) -> AsyncIterator[None]:
        self.active_runs += 1
        try:
            yield
        finally:
            if self.active_runs > 0:
                self.active_runs -= 1


_EXECUTION_POLICY = ExecutionPolicy()


def get_execution_policy() -> ExecutionPolicy:
    return _EXECUTION_POLICY


class ProviderPacingPlugin(BasePlugin):
    """ADK plugin to pace agent requests according to provider rate limits."""

    def __init__(self, policy: ProviderPolicy | None = None) -> None:
        super().__init__(name="provider_pacing")
        self.policy = policy or ProviderPolicy()
        self._last_call_time: float = 0.0
        self.profiler: Any = None

    async def before_model_call(self, *args: Any, **kwargs: Any) -> None:
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < self.policy.cooldown_seconds:
            await asyncio.sleep(self.policy.cooldown_seconds - elapsed)
        self._last_call_time = time.time()


RateLimiter = ProviderPacingPlugin
