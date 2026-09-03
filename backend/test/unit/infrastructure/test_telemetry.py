"""Unit tests for PipelineProfiler telemetry."""

import time

from infrastructure.telemetry import PipelineProfiler


def test_pipeline_profiler_lifecycle():
    profiler = PipelineProfiler()
    profiler.start_stage("stage_a")
    time.sleep(0.01)
    profiler.start_stage("stage_b")
    time.sleep(0.01)
    profiler.end_stage()

    summary = profiler.get_summary()
    assert "total_duration_seconds" in summary
    assert "stage_a" in summary["stages"]
    assert "stage_b" in summary["stages"]
    assert summary["stages"]["stage_a"] > 0

    # Test print_profile does not raise
    profiler.print_profile()
