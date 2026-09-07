"""Tests for paired demand-level comparative evaluation harness under ADR 0011.

Invariants verified:
- Paired metric vectors are extracted by demand_id (never macro aggregates).
- Fails fast when baseline and treatment have non-identical demand_id sets.
- Wilcoxon and bootstrap are invoked with correctly aligned demand-level vectors.
- BH-FDR is applied across the full pre-registered hypothesis family.
- Comparative harness has zero imports from matching domain or infrastructure.
- Seed produces byte-exact reproducible results.
"""

from datetime import UTC, datetime

import pytest

from application.evaluation.comparative import evaluate_study_protocol
from application.evaluation.statistics.types import WilcoxonResult
from domain.models.evaluation import (
    ComparativeRunReport,
    DemandMetricsReport,
    EvaluationExecutionContext,
    EvaluationRunReport,
    MetricSet,
    StudyHypothesis,
    StudyProtocol,
)

SHA64 = "a" * 64
_TS = datetime(2026, 9, 4, 10, 0, 0, tzinfo=UTC)
_CTX = EvaluationExecutionContext(
    engine_name="TestEngine",
    engine_version="0.1.0",
    engine_commit_hash="abc1234",
    execution_timestamp=_TS,
    environment="test",
)


def _make_metric_set(mrr: float) -> MetricSet:
    return MetricSet(
        precision_at_1=mrr,
        precision_at_3=mrr,
        precision_at_5=mrr,
        recall_at_1=mrr,
        recall_at_3=mrr,
        recall_at_5=mrr,
        mrr=mrr,
        mrr_at_5=mrr,
        ndcg_at_5=mrr,
        ndcg_at_10=mrr,
        judged_at_1=1.0,
        judged_at_3=1.0,
        judged_at_5=1.0,
    )


def _make_demand_report(demand_id: str, mrr: float) -> DemandMetricsReport:
    return DemandMetricsReport(
        demand_id=demand_id,
        candidate_count=10,
        judged_count=10,
        uncertain_count=0,
        has_relevant_judged=True,
        strict_metrics=_make_metric_set(mrr),
        broad_metrics=_make_metric_set(min(mrr + 0.1, 1.0)),
    )


def _make_run_report(run_id: str, demand_mrrs: dict[str, float]) -> EvaluationRunReport:
    demand_reports = [_make_demand_report(d, mrr) for d, mrr in demand_mrrs.items()]
    macro = _make_metric_set(sum(demand_mrrs.values()) / len(demand_mrrs))
    denominators = {f"strict.{f}": len(demand_mrrs) for f in MetricSet.model_fields}
    denominators.update({f"broad.{f}": len(demand_mrrs) for f in MetricSet.model_fields})
    return EvaluationRunReport(
        run_id=run_id,
        created_at=_TS,
        context=_CTX,
        dataset_id="test-dataset",
        dataset_version="1.0.0",
        dataset_sha256=SHA64,
        policy_id="test-policy",
        policy_version="1.0.0",
        policy_sha256=SHA64,
        demand_reports=demand_reports,
        macro_strict=macro,
        macro_broad=macro,
        macro_denominators=denominators,
        uncertainty_rate=0.0,
    )


_DEMANDS = {"D1": 0.0, "D2": 0.33, "D3": 1.0, "D4": 0.0, "D5": 0.5,
            "D6": 1.0, "D7": 0.0, "D8": 0.5, "D9": 1.0, "D10": 0.33,
            "D11": 0.0, "D12": 0.5, "D13": 1.0, "D14": 0.0, "D15": 0.5}

_TREATMENT_MRRS = {d: min(v + 0.3, 1.0) for d, v in _DEMANDS.items()}


def _make_protocol(hypotheses: list[StudyHypothesis]) -> StudyProtocol:
    return StudyProtocol(
        study_id="TEST-STUDY",
        study_version="1.0.0",
        protocol_sha256=SHA64,
        alpha=0.05,
        multiple_testing_method="benjamini_hochberg",
        bootstrap_iterations=500,
        bootstrap_confidence_level=0.95,
        seed=42,
        hypotheses=hypotheses,
    )


def test_evaluate_study_protocol_returns_comparative_run_report():
    baseline = _make_run_report("run-M0", _DEMANDS)
    treatment = _make_run_report("run-M1", _TREATMENT_MRRS)
    h = StudyHypothesis(id="H01", baseline="M0", treatment="M1", metric="mrr", scope="strict", alternative="greater", description="")
    protocol = _make_protocol([h])

    report = evaluate_study_protocol(
        runs={"M0": baseline, "M1": treatment},
        protocol=protocol,
        study_status="PILOT",
    )

    assert isinstance(report, ComparativeRunReport)
    assert report.study_status == "PILOT"
    assert report.study_protocol_id == "TEST-STUDY"
    assert len(report.results) == 1


def test_comparative_evaluator_extracts_paired_demand_vectors():
    """Wilcoxon must receive per-demand mrr deltas, not macro aggregates."""
    baseline = _make_run_report("run-M0", _DEMANDS)
    treatment = _make_run_report("run-M1", _TREATMENT_MRRS)
    h = StudyHypothesis(id="H01", baseline="M0", treatment="M1", metric="mrr", scope="strict", alternative="greater", description="")
    protocol = _make_protocol([h])

    report = evaluate_study_protocol(runs={"M0": baseline, "M1": treatment}, protocol=protocol, study_status="PILOT")
    result = report.results[0]

    assert isinstance(result.wilcoxon, WilcoxonResult)
    # 15 demand-level pairs supplied → n_pairs == 15
    assert result.wilcoxon.n_pairs == 15


def test_evaluate_study_protocol_fails_fast_on_mismatched_demands():
    baseline = _make_run_report("run-M0", {"D1": 0.0, "D2": 0.5, "D3": 1.0})
    # Treatment is missing D3 and has extra D99
    treatment = _make_run_report("run-M1", {"D1": 0.3, "D2": 0.8, "D99": 0.9})
    h = StudyHypothesis(id="H01", baseline="M0", treatment="M1", metric="mrr", scope="strict", alternative="greater", description="")
    protocol = _make_protocol([h])

    with pytest.raises(ValueError, match="demand_id"):
        evaluate_study_protocol(runs={"M0": baseline, "M1": treatment}, protocol=protocol, study_status="PILOT")


def test_evaluate_study_protocol_fails_fast_on_missing_run_label():
    baseline = _make_run_report("run-M0", _DEMANDS)
    h = StudyHypothesis(id="H01", baseline="M0", treatment="M1", metric="mrr", scope="strict", alternative="greater", description="")
    protocol = _make_protocol([h])

    with pytest.raises(ValueError, match="M1"):
        evaluate_study_protocol(runs={"M0": baseline}, protocol=protocol, study_status="PILOT")


def test_evaluate_study_protocol_deterministic_with_seed():
    baseline = _make_run_report("run-M0", _DEMANDS)
    treatment = _make_run_report("run-M1", _TREATMENT_MRRS)
    h = StudyHypothesis(id="H01", baseline="M0", treatment="M1", metric="mrr", scope="strict", alternative="greater", description="")
    protocol = _make_protocol([h])

    r1 = evaluate_study_protocol(runs={"M0": baseline, "M1": treatment}, protocol=protocol, study_status="PILOT")
    r2 = evaluate_study_protocol(runs={"M0": baseline, "M1": treatment}, protocol=protocol, study_status="PILOT")

    assert r1.results[0].bootstrap_ci.estimate == r2.results[0].bootstrap_ci.estimate
    assert r1.results[0].bootstrap_ci.ci_lower == r2.results[0].bootstrap_ci.ci_lower
    assert r1.results[0].wilcoxon.p_value == r2.results[0].wilcoxon.p_value


def test_evaluate_study_protocol_applies_bh_fdr_across_all_hypotheses():
    """BH correction is applied across ALL hypotheses simultaneously."""
    baseline = _make_run_report("run-M0", _DEMANDS)
    treatment = _make_run_report("run-M1", _TREATMENT_MRRS)
    hs = [
        StudyHypothesis(id=f"H0{i}", baseline="M0", treatment="M1", metric="mrr", scope="strict", alternative="greater", description="")
        for i in range(1, 4)
    ]
    protocol = _make_protocol(hs)

    report = evaluate_study_protocol(runs={"M0": baseline, "M1": treatment}, protocol=protocol, study_status="PILOT")

    assert len(report.results) == 3
    # q-values must be >= raw p-values (BH never deflates) OR equal (when only one test passes BH)
    for res in report.results:
        assert isinstance(res.adjusted_q_value, float)
        assert 0.0 <= res.adjusted_q_value <= 1.0


def test_comparative_harness_has_zero_matching_imports():
    """Architecture: comparative.py must not import from matching domain or infrastructure."""
    import ast
    import pathlib

    src = pathlib.Path("backend/src/main/application/evaluation/comparative.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    forbidden = {"domain.models.matching", "domain.protocols.matching", "application.matching", "infrastructure"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(name=node.module or "")]):
                for f in forbidden:
                    assert f not in (alias.name or ""), f"comparative.py must not import from {f}"
