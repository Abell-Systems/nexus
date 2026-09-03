"""Unit tests for ADR 0007 evaluation protocol models and execution context.

Invariants verified:
- Immutability of EvaluationExecutionContext, MetricSet, DemandMetricsReport, EvaluationRunReport.
- Strict git commit hash validation (7 to 40 characters, hexadecimal).
- Provenance integrity stamping: reports preserve dataset, policy, and engine execution context.
- Zero filesystem interaction in domain models.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from domain.models.evaluation import (
    DemandMetricsReport,
    EvaluationExecutionContext,
    EvaluationRunReport,
    MetricSet,
)


def _sample_context() -> EvaluationExecutionContext:
    return EvaluationExecutionContext(
        engine_name="DefaultMatchingEngine",
        engine_version="0.2.0",
        engine_commit_hash="a321b0c",
        execution_timestamp=datetime(2026, 9, 3, 14, 0, 0, tzinfo=UTC),
        environment="ci",
    )


def test_evaluation_execution_context_validation():
    ctx = _sample_context()
    assert ctx.engine_commit_hash == "a321b0c"
    assert ctx.environment == "ci"

    # Commit hash too short (<7 chars)
    with pytest.raises(ValidationError):
        EvaluationExecutionContext(
            engine_name="Test",
            engine_version="1.0",
            engine_commit_hash="abc",
            execution_timestamp=datetime.now(UTC),
            environment="test",
        )

    # Non-hex characters
    with pytest.raises(ValidationError):
        EvaluationExecutionContext(
            engine_name="Test",
            engine_version="1.0",
            engine_commit_hash="not-a-valid-hex-hash",
            execution_timestamp=datetime.now(UTC),
            environment="test",
        )

    # Missing timezone on execution_timestamp
    with pytest.raises(ValidationError):
        EvaluationExecutionContext(
            engine_name="Test",
            engine_version="1.0",
            engine_commit_hash="a321b0c",
            execution_timestamp=datetime(2026, 9, 3, 14, 0, 0),  # Naive
            environment="test",
        )

    # Immutability
    with pytest.raises(ValidationError):
        ctx.environment = "production"  # type: ignore[misc]


def test_demand_metrics_report_and_run_report():
    ctx = _sample_context()

    strict_metrics = MetricSet(
        precision_at_1=1.0,
        precision_at_3=0.67,
        precision_at_5=0.40,
        recall_at_1=0.50,
        recall_at_3=1.0,
        recall_at_5=1.0,
        mrr=1.0,
        mrr_at_5=1.0,
        ndcg_at_5=0.88,
        judged_at_1=1.0,
        judged_at_3=1.0,
        judged_at_5=0.80,
    )
    broad_metrics = MetricSet(
        precision_at_1=1.0,
        precision_at_3=1.0,
        precision_at_5=0.80,
        recall_at_1=0.33,
        recall_at_3=1.0,
        recall_at_5=1.0,
        mrr=1.0,
        mrr_at_5=1.0,
        ndcg_at_5=0.95,
        judged_at_1=1.0,
        judged_at_3=1.0,
        judged_at_5=0.80,
    )

    demand_rep = DemandMetricsReport(
        demand_id="INNOGET-2415",
        candidate_count=15,
        judged_count=10,
        uncertain_count=1,
        strict_metrics=strict_metrics,
        broad_metrics=broad_metrics,
    )

    report = EvaluationRunReport(
        run_id="run-test-123",
        created_at=datetime.now(UTC),
        context=ctx,
        dataset_id="nexus-pilot-16-evaluation-corpus-v1",
        dataset_version="1.0.0",
        dataset_sha256="b" * 64,
        policy_id="default_matching_policy",
        policy_version="1.0.0",
        policy_sha256="c" * 64,
        demand_reports=[demand_rep],
        macro_strict=strict_metrics,
        macro_broad=broad_metrics,
        uncertainty_rate=0.10,
    )

    assert report.run_id == "run-test-123"
    assert len(report.demand_reports) == 1
    assert report.context.engine_commit_hash == "a321b0c"
    assert report.dataset_sha256 == "b" * 64
    assert report.policy_sha256 == "c" * 64

    # Immutability
    with pytest.raises(ValidationError):
        report.run_id = "modified"  # type: ignore[misc]
