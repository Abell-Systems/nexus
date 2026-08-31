"""Fine-grained latency span tracer and bottleneck profiler for the IP pipeline."""

import asyncio
import time
from contextlib import contextmanager, asynccontextmanager
from typing import Any


class SpanRecord:
    def __init__(self, name: str, category: str, start_time: float, metadata: dict | None = None) -> None:
        self.name = name
        self.category = category
        self.start_time = start_time
        self.end_time: float | None = None
        self.duration_seconds: float = 0.0
        self.metadata = metadata or {}

    def finish(self) -> None:
        self.end_time = time.monotonic()
        self.duration_seconds = max(0.0, self.end_time - self.start_time)


class PipelineProfiler:
    """Collects and aggregates latency spans across pipeline stages and rate limiter waits."""

    def __init__(self) -> None:
        self.spans: list[SpanRecord] = []
        self._rate_limit_gap_wait: float = 0.0
        self._rate_limit_budget_wait: float = 0.0

    @contextmanager
    def span(self, name: str, category: str = "general", **metadata: Any):
        rec = SpanRecord(name, category, time.monotonic(), metadata)
        self.spans.append(rec)
        try:
            yield rec
        finally:
            rec.finish()

    @asynccontextmanager
    async def async_span(self, name: str, category: str = "general", **metadata: Any):
        rec = SpanRecord(name, category, time.monotonic(), metadata)
        self.spans.append(rec)
        try:
            yield rec
        finally:
            rec.finish()

    def record_rate_limit_wait(self, gap_wait: float = 0.0, budget_wait: float = 0.0) -> None:
        if gap_wait > 0:
            self._rate_limit_gap_wait += gap_wait
        if budget_wait > 0:
            self._rate_limit_budget_wait += budget_wait

    def get_summary(self) -> dict[str, Any]:
        categories: dict[str, float] = {}
        for s in self.spans:
            categories[s.category] = categories.get(s.category, 0.0) + s.duration_seconds

        total_wait = self._rate_limit_gap_wait + self._rate_limit_budget_wait
        total_time = sum(s.duration_seconds for s in self.spans)

        return {
            "total_span_time_seconds": round(total_time, 2),
            "rate_limit_total_wait_seconds": round(total_wait, 2),
            "rate_limit_gap_wait_seconds": round(self._rate_limit_gap_wait, 2),
            "rate_limit_budget_wait_seconds": round(self._rate_limit_budget_wait, 2),
            "by_category_seconds": {k: round(v, 2) for k, v in categories.items()},
            "spans": [
                {
                    "name": s.name,
                    "category": s.category,
                    "duration_seconds": round(s.duration_seconds, 2),
                    "metadata": s.metadata,
                }
                for s in self.spans
            ],
        }

    def print_profile(self) -> None:
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print(" PIPELINE LATENCY PROFILE & BOTTLENECK ANALYSIS")
        print("=" * 60)
        for s in self.spans:
            print(f"  [{s.category:<16}] {s.name:<30} : {s.duration_seconds:6.2f}s")
        print("-" * 60)
        print(f"  Rate-Limit Artificial Wait (RPM gap) : {summary['rate_limit_gap_wait_seconds']:6.2f}s")
        print(f"  Rate-Limit Artificial Wait (TPM bud) : {summary['rate_limit_budget_wait_seconds']:6.2f}s")
        print(f"  Total Artificial Pacing Overhead     : {summary['rate_limit_total_wait_seconds']:6.2f}s")
        print(f"  Total Active Processing Time         : {summary['total_span_time_seconds']:6.2f}s")
        print("=" * 60 + "\n")

