"""Tests for comparative evaluation domain models under ADR 0011.

Invariants verified:
- StudyHypothesis enforces stable identifier, pre-registered metric, scope, and alternative.
- StudyProtocol enforces seed, alpha, confidence level, and non-empty hypothesis family.
- HypothesisTestResult carries both statistical and BH-adjusted results.
- ComparativeRunReport preserves full provenance including study_protocol_id and sha256.
"""

import pytest
from pydantic import ValidationError

from application.evaluation.statistics.types import BootstrapCIResult, WilcoxonResult
from domain.models.evaluation import (
    ComparativeRunReport,
    HypothesisTestResult,
    StudyHypothesis,
    StudyProtocol,
)


def test_study_hypothesis_valid():
    h = StudyHypothesis(
        id="H01_M1_vs_M0_MRR",
        baseline="M0",
        treatment="M1",
        metric="mrr",
        scope="strict",
        alternative="greater",
        description="M1 improves strict MRR over M0",
    )
    assert h.id == "H01_M1_vs_M0_MRR"
    assert h.baseline == "M0"
    assert h.treatment == "M1"
    assert h.metric == "mrr"
    assert h.scope == "strict"
    assert h.alternative == "greater"


def test_study_hypothesis_validates_scope():
    with pytest.raises(ValidationError):
        StudyHypothesis(
            id="bad",
            baseline="M0",
            treatment="M1",
            metric="mrr",
            scope="invalid_scope",
            alternative="greater",
            description="",
        )


def test_study_hypothesis_validates_alternative():
    with pytest.raises(ValidationError):
        StudyHypothesis(
            id="bad",
            baseline="M0",
            treatment="M1",
            metric="mrr",
            scope="strict",
            alternative="invalid",
            description="",
        )


def test_study_protocol_requires_nonzero_hypotheses():
    with pytest.raises(ValidationError):
        StudyProtocol(
            study_id="TEST",
            study_version="1.0.0",
            protocol_sha256="a" * 64,
            alpha=0.05,
            multiple_testing_method="benjamini_hochberg",
            bootstrap_iterations=1000,
            bootstrap_confidence_level=0.95,
            seed=42,
            hypotheses=[],
        )


def test_study_protocol_valid():
    h = StudyHypothesis(
        id="H01",
        baseline="M0",
        treatment="M1",
        metric="mrr",
        scope="strict",
        alternative="greater",
        description="test",
    )
    p = StudyProtocol(
        study_id="S1",
        study_version="1.0.0",
        protocol_sha256="a" * 64,
        alpha=0.05,
        multiple_testing_method="benjamini_hochberg",
        bootstrap_iterations=1000,
        bootstrap_confidence_level=0.95,
        seed=42,
        hypotheses=[h],
    )
    assert len(p.hypotheses) == 1
    assert p.alpha == 0.05


def test_hypothesis_test_result_carries_statistical_outputs():
    w = WilcoxonResult(statistic=10.0, p_value=0.03, alternative="greater", n_pairs=10, n_nonzero=10)
    ci = BootstrapCIResult(estimate=0.15, ci_lower=0.02, ci_upper=0.30, n_bootstrap=1000, confidence_level=0.95, seed=42)
    r = HypothesisTestResult(
        hypothesis_id="H01",
        baseline="M0",
        treatment="M1",
        metric="mrr",
        scope="strict",
        wilcoxon=w,
        bootstrap_ci=ci,
        adjusted_q_value=0.12,
        rejected=False,
        n_paired=10,
    )
    assert r.hypothesis_id == "H01"
    assert r.wilcoxon.p_value == 0.03
    assert r.bootstrap_ci.estimate == 0.15
    assert not r.rejected


def test_comparative_run_report_stamps_protocol_provenance():
    w = WilcoxonResult(statistic=10.0, p_value=0.03, alternative="greater", n_pairs=10, n_nonzero=10)
    ci = BootstrapCIResult(estimate=0.15, ci_lower=0.02, ci_upper=0.30, n_bootstrap=1000, confidence_level=0.95, seed=42)
    result = HypothesisTestResult(
        hypothesis_id="H01",
        baseline="M0",
        treatment="M1",
        metric="mrr",
        scope="strict",
        wilcoxon=w,
        bootstrap_ci=ci,
        adjusted_q_value=0.12,
        rejected=False,
        n_paired=10,
        excluded_demand_ids=["D9"],
    )
    report = ComparativeRunReport(
        study_protocol_id="NEXUS-PHASE2-ABLATION-M0-M6",
        study_protocol_sha256="c" * 64,
        study_status="PILOT",
        run_ids={"M0": "run-aaa", "M1": "run-bbb"},
        results=[result],
    )
    assert report.study_protocol_id == "NEXUS-PHASE2-ABLATION-M0-M6"
    assert len(report.study_protocol_sha256) == 64
    assert report.study_status == "PILOT"
    assert len(report.results) == 1
