"""Provider Policy abstractions separating model rate-limiting and quota pacing from the agent graph."""

import asyncio
import os
import time
from abc import ABC, abstractmethod


class BaseProviderPolicy(ABC):
    """Abstract rate-limiting policy governing model invocation frequency and token budgeting."""

    @abstractmethod
    async def before_call(self, estimated_tokens: int) -> tuple[float, float]:
        """Paces the call. Returns (gap_wait_seconds, budget_wait_seconds)."""
        pass


class DirectProviderPolicy(BaseProviderPolicy):
    """Zero-overhead policy for enterprise tiers (GCP Vertex / Enterprise OpenAI) and local tests."""

    async def before_call(self, estimated_tokens: int) -> tuple[float, float]:
        return 0.0, 0.0


class GroqFreeTierPolicy(BaseProviderPolicy):
    """Strict RPM + TPM rolling window pacing for Groq Free Tier (8K TPM)."""

    def __init__(
        self,
        min_gap_seconds: float | None = None,
        tpm_budget: int | None = None,
        window_seconds: float | None = None,
    ) -> None:
        self.min_gap = min_gap_seconds if min_gap_seconds is not None else float(os.getenv("RATE_LIMIT_MIN_GAP_SECONDS", "13.0"))
        self.tpm_budget = tpm_budget if tpm_budget is not None else int(os.getenv("RATE_LIMIT_TPM_BUDGET", "6000"))
        self.window_seconds = window_seconds if window_seconds is not None else float(os.getenv("RATE_LIMIT_TPM_WINDOW_SECONDS", "60.0"))
        self._last_call = 0.0
        self._calls: list[tuple[float, int]] = []

    async def before_call(self, estimated_tokens: int) -> tuple[float, float]:
        now = time.monotonic()
        gap_wait = max(0.0, self._last_call + self.min_gap - now)
        if gap_wait > 0:
            await asyncio.sleep(gap_wait)
            now = time.monotonic()

        self._calls = [(t, tok) for t, tok in self._calls if now - t < self.window_seconds]
        used = sum(tok for _, tok in self._calls)
        budget_wait = 0.0
        if self._calls and used + estimated_tokens > self.tpm_budget:
            budget_wait = max(0.0, self.window_seconds - (now - self._calls[0][0]) + 0.5)
            if budget_wait > 0:
                await asyncio.sleep(budget_wait)
                now = time.monotonic()
                self._calls = [(t, tok) for t, tok in self._calls if now - t < self.window_seconds]

        self._last_call = now
        self._calls.append((now, estimated_tokens))
        return gap_wait, budget_wait


class ExecutionPolicy:
    """Controls pipeline-level concurrency, resource quotas, and provider delegation."""

    def __init__(
        self,
        provider_policy: BaseProviderPolicy,
        max_concurrency: int = 1,
    ) -> None:
        self.provider_policy = provider_policy
        self.max_concurrency = max_concurrency
        self.active_runs = 0
        self._lock = None

    def is_busy(self) -> bool:
        """Returns True if maximum concurrent executions are in flight."""
        return self.active_runs >= self.max_concurrency

    class _SlotContext:
        def __init__(self, policy: "ExecutionPolicy"):
            self.policy = policy

        async def __aenter__(self):
            self.policy.active_runs += 1
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.policy.active_runs = max(0, self.policy.active_runs - 1)

    def acquire_execution_slot(self):
        """Async context manager guarding parallel pipeline executions."""
        return self._SlotContext(self)



_default_execution_policy: ExecutionPolicy | None = None


def get_provider_policy() -> BaseProviderPolicy:
    """Factory selecting policy based on active provider configuration."""
    provider = os.getenv("MODEL_PROVIDER", "groq").lower()
    if provider == "groq" and os.getenv("GROQ_TIER", "free").lower() == "free":
        return GroqFreeTierPolicy()
    return DirectProviderPolicy()


from google.adk.plugins.base_plugin import BasePlugin
from .telemetry import PipelineProfiler


class ProviderPacingPlugin(BasePlugin):
    """ADK plugin executing provider rate-limiting and quota pacing."""

    def __init__(
        self,
        policy: BaseProviderPolicy | None = None,
        profiler: PipelineProfiler | None = None,
    ) -> None:
        super().__init__(name="provider_pacing")
        self.policy = policy or get_provider_policy()
        self.profiler = profiler

    @property
    def _min_gap(self) -> float:
        return getattr(self.policy, "min_gap", 0.0)

    @_min_gap.setter
    def _min_gap(self, val: float) -> None:
        if isinstance(self.policy, DirectProviderPolicy):
            self.policy = GroqFreeTierPolicy(min_gap_seconds=val)
        elif hasattr(self.policy, "min_gap"):
            self.policy.min_gap = val

    @property
    def _tpm_budget(self) -> int:
        return getattr(self.policy, "tpm_budget", 100000)

    @_tpm_budget.setter
    def _tpm_budget(self, val: int) -> None:
        if isinstance(self.policy, DirectProviderPolicy):
            self.policy = GroqFreeTierPolicy(tpm_budget=val)
        elif hasattr(self.policy, "tpm_budget"):
            self.policy.tpm_budget = val

    @property
    def _window_seconds(self) -> float:
        return getattr(self.policy, "window_seconds", 60.0)

    @_window_seconds.setter
    def _window_seconds(self, val: float) -> None:
        if isinstance(self.policy, DirectProviderPolicy):
            self.policy = GroqFreeTierPolicy(window_seconds=val)
        elif hasattr(self.policy, "window_seconds"):
            self.policy.window_seconds = val

    @property
    def _calls(self) -> list[tuple[float, int]]:
        return getattr(self.policy, "_calls", [])

    @_calls.setter
    def _calls(self, val: list[tuple[float, int]]) -> None:
        if hasattr(self.policy, "_calls"):
            self.policy._calls = val


    _SAFETY_PAD = 300

    @staticmethod
    def _estimate_tokens(llm_request) -> int:
        try:
            text = str(llm_request.contents) + str(llm_request.config)
        except Exception:
            return 2000
        return max(len(text) // 3, 1) + ProviderPacingPlugin._SAFETY_PAD

    async def before_model_callback(self, *, callback_context, llm_request):
        estimated = self._estimate_tokens(llm_request)
        gap_wait, budget_wait = await self.policy.before_call(estimated)
        if self.profiler:
            self.profiler.record_rate_limit_wait(gap_wait, budget_wait)
        return None


# Backward-compatibility alias
RateLimiter = ProviderPacingPlugin


def get_execution_policy() -> ExecutionPolicy:
    """Factory returning the active execution policy for the current environment."""
    global _default_execution_policy
    if _default_execution_policy is None:
        prov_policy = get_provider_policy()
        max_conc = int(os.getenv("MAX_CONCURRENCY", "1"))
        _default_execution_policy = ExecutionPolicy(
            provider_policy=prov_policy,
            max_concurrency=max_conc,
        )
    return _default_execution_policy


