"""Pipeline profiling and telemetry utilities."""

import time
from typing import Any


class PipelineProfiler:
    def __init__(self) -> None:
        self.start_time = time.time()
        self.stage_timings: dict[str, float] = {}
        self._current_stage: str | None = None
        self._stage_start: float | None = None

    def start_stage(self, stage_name: str) -> None:
        now = time.time()
        if self._current_stage and self._stage_start:
            self.stage_timings[self._current_stage] = now - self._stage_start
        self._current_stage = stage_name
        self._stage_start = now

    def end_stage(self) -> None:
        now = time.time()
        if self._current_stage and self._stage_start:
            self.stage_timings[self._current_stage] = now - self._stage_start
            self._current_stage = None
            self._stage_start = None

    def get_summary(self) -> dict[str, Any]:
        self.end_stage()
        total_duration = time.time() - self.start_time
        return {
            "total_duration_seconds": round(total_duration, 3),
            "stages": {k: round(v, 3) for k, v in self.stage_timings.items()},
        }

    def print_profile(self) -> None:
        summary = self.get_summary()
        print(f"[Profiler] Total Duration: {summary['total_duration_seconds']}s")
        for stage, duration in summary.get("stages", {}).items():
            print(f"  - {stage}: {duration}s")
