"""Tests for JSON-safe serialization of ComparativeRunReport (PR-E)."""

import json

from application.evaluation.statistics.types import BootstrapCIResult, WilcoxonResult
from domain.models.evaluation import ComparativeRunReport, HypothesisTestResult
from infrastructure.evaluation.comparative_report_serializer import serialize_comparative_report


def _make_report() -> ComparativeRunReport:
    wilcoxon = WilcoxonResult(statistic=0.0, p_value=0.125, n_pairs=3, n_nonzero=2, alternative="greater")
    bootstrap = BootstrapCIResult(
        estimate=0.15, ci_lower=-0.05, ci_upper=0.35, n_bootstrap=10000, confidence_level=0.95, seed=42
    )
    result = HypothesisTestResult(
        hypothesis_id="H01_M0_VS_M1_NDCG10",
        baseline="M0",
        treatment="M1",
        metric="ndcg_at_10",
        scope="strict",
        wilcoxon=wilcoxon,
        bootstrap_ci=bootstrap,
        adjusted_q_value=0.25,
        rejected=False,
        n_paired=3,
        excluded_demand_ids=[],
    )
    return ComparativeRunReport(
        study_protocol_id="NEXUS-M0-VS-M1-PILOT",
        study_protocol_sha256="5c4687e7a88ab86426799f06f03864d6eb1bca3b657289e6ce270f5373240de8",
        study_status="PILOT",
        run_ids={"M0": "run-m0-abc", "M1": "run-m1-def"},
        results=[result],
    )


def test_serialize_comparative_report_is_json_dumpable():
    report = _make_report()
    serialized = serialize_comparative_report(report)
    dumped = json.dumps(serialized)  # raises if anything isn't JSON-safe
    reloaded = json.loads(dumped)
    assert reloaded["study_protocol_id"] == "NEXUS-M0-VS-M1-PILOT"


def test_serialize_comparative_report_preserves_wilcoxon_and_bootstrap_fields():
    report = _make_report()
    serialized = serialize_comparative_report(report)
    result = serialized["results"][0]

    assert result["hypothesis_id"] == "H01_M0_VS_M1_NDCG10"
    assert result["wilcoxon"] == {
        "statistic": 0.0,
        "p_value": 0.125,
        "n_pairs": 3,
        "n_nonzero": 2,
        "alternative": "greater",
    }
    assert result["bootstrap_ci"] == {
        "estimate": 0.15,
        "ci_lower": -0.05,
        "ci_upper": 0.35,
        "n_bootstrap": 10000,
        "confidence_level": 0.95,
        "seed": 42,
    }
    assert result["n_paired"] == 3
    assert result["excluded_demand_ids"] == []


def test_serialize_comparative_report_top_level_fields():
    report = _make_report()
    serialized = serialize_comparative_report(report)

    assert serialized["study_status"] == "PILOT"
    assert serialized["run_ids"] == {"M0": "run-m0-abc", "M1": "run-m1-def"}
    assert len(serialized["results"]) == 1
