"""Primary-endpoint alignment tests (PR #44): nDCG@10, exclusion semantics, denominators.

Scope: how we measure, never what is measured. No engine, dataset, label, weight,
threshold, pool, or product contact anywhere below — all inputs are synthetic fixtures.

Covers the brief's boundary battery (IDCG=0, all-irrelevant, perfect, reverse,
fewer-than-10, ties, no-relevant demand, multi-demand) plus the protocol worked
example: every expected number here is hand-derived from the protocol formulas
(DCG = Σ(2^g − 1)/log2(i+1) over the judged sequence; IDCG from the ideal order),
not copied from an implementation run.
"""

import math
from datetime import UTC, date, datetime

from application.evaluation.comparative import evaluate_study_protocol
from application.evaluation.metrics import compute_demand_metrics, ndcg_at_k
from application.evaluation.runner import DefaultEvaluationRunner
from domain.models.evaluation import (
    DataModality,
    DemandMetricsReport,
    EvaluationAnnotation,
    EvaluationDataset,
    EvaluationDatasetManifest,
    EvaluationDemand,
    EvaluationExecutionContext,
    EvaluationPatent,
    EvaluationProvenance,
    EvaluationRunReport,
    MetricSet,
    RelevanceGrade,
    StudyHypothesis,
    StudyProtocol,
    ValidatedDataset,
)

import pytest

_SHA64 = "a" * 64


def _grades(**kwargs: int) -> dict[str, RelevanceGrade]:
    return {pid: RelevanceGrade(g) for pid, g in kwargs.items()}


class ProtocolWorkedExampleTest:
    """Hand-derived nDCG@10 example straight from the protocol formulas."""

    def test_should_match_hand_computed_ndcg_at_10(self) -> None:
        # Ranked: A(3), B(1), C(2), D(0); K=10 (fewer than 10 results is fine).
        # DCG = 7/log2(2) + 1/log2(3) + 3/log2(4) + 0/log2(5)
        #     = 7 + 0.63092975 + 1.5 = 9.13092975
        # IDCG (ideal A,C,B,D) = 7/1 + 3/log2(3) + 1/log2(4) + 0
        #     = 7 + 1.89278926 + 0.5 = 9.39278926
        ranking = ["A", "B", "C", "D"]
        judgements = _grades(A=3, B=1, C=2, D=0)
        expected = (7.0 + 1.0 / math.log2(3) + 3.0 / 2.0) / (7.0 + 3.0 / math.log2(3) + 0.5)
        assert math.isclose(ndcg_at_k(ranking, judgements, k=10), expected, rel_tol=1e-9)

    def test_should_score_perfect_ranking_one(self) -> None:
        ranking = ["A", "B", "C"]
        assert ndcg_at_k(ranking, _grades(A=3, B=2, C=1), k=10) == pytest.approx(1.0)

    def test_should_score_reverse_ranking_below_one(self) -> None:
        judgements = _grades(A=3, B=2, C=0)
        assert ndcg_at_k(["C", "B", "A"], judgements, k=10) < 1.0
        assert ndcg_at_k(["C", "B", "A"], judgements, k=10) > 0.0

    def test_should_score_tied_grades_one_in_any_order(self) -> None:
        judgements = _grades(A=2, B=2, C=0)
        assert ndcg_at_k(["A", "B", "C"], judgements, k=10) == pytest.approx(1.0)
        assert ndcg_at_k(["B", "A", "C"], judgements, k=10) == pytest.approx(1.0)


class ExclusionSemanticsTest:
    def test_should_return_none_and_flag_demand_without_relevant(self) -> None:
        report = compute_demand_metrics(
            demand_id="D-0",
            ranked_publication_ids=["P1", "P2"],
            judgements=_grades(P1=0, P2=0),
            candidate_universe_size=2,
        )
        assert report.has_relevant_judged is False
        assert report.strict_metrics.ndcg_at_10 is None
        assert report.strict_metrics.ndcg_at_5 is None
        assert report.strict_metrics.recall_at_1 is None
        # Defined metrics stay defined: precision and MRR observe genuine zeros.
        assert report.strict_metrics.precision_at_1 == 0.0
        assert report.strict_metrics.mrr == 0.0

    def test_should_flag_demand_with_relevant(self) -> None:
        report = compute_demand_metrics(
            demand_id="D-1",
            ranked_publication_ids=["P1", "P2"],
            judgements=_grades(P1=3, P2=0),
            candidate_universe_size=2,
        )
        assert report.has_relevant_judged is True
        assert report.strict_metrics.ndcg_at_10 == pytest.approx(1.0)
        assert report.strict_metrics.recall_at_1 == 1.0


def _prov() -> EvaluationProvenance:
    return EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="f" * 64,
        modality=DataModality.OBSERVED,
    )


def _two_demand_dataset() -> ValidatedDataset:
    prov = _prov()
    demands = [
        EvaluationDemand(
            demand_id="D-VALID",
            title="t",
            description="d",
            posted_date=date(2023, 1, 1),
            target_cpc_prefixes=["E03C"],
            provenance=prov,
        ),
        EvaluationDemand(
            demand_id="D-EMPTY",
            title="t",
            description="d",
            posted_date=date(2023, 1, 1),
            target_cpc_prefixes=["E03C"],
            provenance=prov,
        ),
    ]
    patents = [
        EvaluationPatent(
            publication_id=f"P-{i}",
            publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"],
            title=f"Patent {i}",
            abstract=f"Abstract {i}",
            provenance=prov,
        )
        for i in range(1, 4)
    ]
    annotations = [
        EvaluationAnnotation(
            demand_id="D-VALID", publication_id="P-1", grade=RelevanceGrade.GRADE_3,
            annotator_role="expert", modality=DataModality.EXPERT_LABELLED,
        ),
        EvaluationAnnotation(
            demand_id="D-VALID", publication_id="P-2", grade=RelevanceGrade.GRADE_0,
            annotator_role="expert", modality=DataModality.EXPERT_LABELLED,
        ),
        EvaluationAnnotation(
            demand_id="D-EMPTY", publication_id="P-1", grade=RelevanceGrade.GRADE_0,
            annotator_role="expert", modality=DataModality.EXPERT_LABELLED,
        ),
        EvaluationAnnotation(
            demand_id="D-EMPTY", publication_id="P-2", grade=RelevanceGrade.GRADE_0,
            annotator_role="expert", modality=DataModality.EXPERT_LABELLED,
        ),
    ]
    dataset = EvaluationDataset(
        dataset_id="endpoint-test", schema_version="1.0.0", dataset_version="1.0.0",
        description="t", demands=demands, patents=patents, annotations=annotations,
    )
    manifest = EvaluationDatasetManifest(
        dataset_id="endpoint-test", schema_version="1.0.0", dataset_version="1.0.0",
        source_authorities=["oepm"], demand_count=2, patent_count=3, annotation_count=4,
        content_sha256=_SHA64,
    )
    return ValidatedDataset(dataset=dataset, manifest=manifest)


class _FixedPort:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    def rank_candidates(self, demand, patents):
        ids = {p.publication_id for p in patents}
        return [pid for pid in self.order if pid in ids]


def _context() -> EvaluationExecutionContext:
    return EvaluationExecutionContext(
        engine_name="TestEngine",
        engine_version="0.1.0",
        engine_commit_hash="abc1234",
        execution_timestamp=datetime(2026, 9, 4, tzinfo=UTC),
        environment="test",
    )


def _policy_identity():
    from domain.models.matching import MatchingPolicyConfig

    return MatchingPolicyConfig(
        policy_id="p",
        policy_version="1.0.0",
        description="t",
        weights={"alpha": 0.35, "beta": 0.45, "gamma": 0.20},
        operational_limits={"retrieval_limit": 100, "max_candidate_pool_size": 300},
        cpc_concordance_levels={
            "subgroup": 1.0, "main_group": 0.8, "subclass": 0.5, "section": 0.2, "none": 0.0
        },
        confidence_thresholds={"strong": 0.75, "moderate": 0.50, "weak": 0.25},
        sufficiency_rules={
            "min_active_signals": 1, "min_signals_for_sufficient": 2,
            "require_temporal_validity": True,
        },
        concept_to_cpc_taxonomy={},
        policy_sha256=_SHA64,
    )


class MacroExclusionTest:
    def test_should_exclude_undefined_demands_with_explicit_denominators(self) -> None:
        # Fixed order P-1, P-2, P-3 for both demands. D-VALID has one strict
        # relevant (P-1 at rank 1): nDCG@10 = 1.0, recall = 1.0. D-EMPTY has
        # none: both undefined and excluded.
        report = DefaultEvaluationRunner().run_evaluation(
            dataset=_two_demand_dataset(),
            ranking_port=_FixedPort(["P-1", "P-2", "P-3"]),
            policy=_policy_identity(),
            context=_context(),
        )
        assert report.macro_denominators["strict.ndcg_at_10"] == 1
        assert report.macro_denominators["broad.ndcg_at_10"] == 1
        assert report.macro_denominators["strict.mrr"] == 2
        assert report.macro_strict.ndcg_at_10 == pytest.approx(1.0)
        assert report.macro_strict.recall_at_1 == pytest.approx(1.0)
        assert report.macro_denominators["strict.recall_at_1"] == 1
        by_id = {r.demand_id: r for r in report.demand_reports}
        assert by_id["D-EMPTY"].has_relevant_judged is False
        assert by_id["D-EMPTY"].strict_metrics.ndcg_at_10 is None


def _metric_set(**overrides):
    base = {
        "precision_at_1": 1.0, "precision_at_3": 1.0, "precision_at_5": 1.0,
        "recall_at_1": 1.0, "recall_at_3": 1.0, "recall_at_5": 1.0,
        "mrr": 0.5, "mrr_at_5": 0.5, "ndcg_at_5": 0.8, "ndcg_at_10": 0.9,
        "judged_at_1": 1.0, "judged_at_3": 1.0, "judged_at_5": 1.0,
    }
    base.update(overrides)
    return MetricSet(**base)


def _run(run_id: str, values: dict[str, float | None]) -> EvaluationRunReport:
    reports = [
        DemandMetricsReport(
            demand_id=d, candidate_count=3, judged_count=2, uncertain_count=0,
            has_relevant_judged=v is not None,
            strict_metrics=_metric_set(ndcg_at_10=v, recall_at_1=v),
            broad_metrics=_metric_set(ndcg_at_10=v, recall_at_1=v),
        )
        for d, v in values.items()
    ]
    n = len(values)
    macro = _metric_set()
    denominators = {f"strict.{f}": n for f in MetricSet.model_fields}
    denominators.update({f"broad.{f}": n for f in MetricSet.model_fields})
    return EvaluationRunReport(
        run_id=run_id, created_at=datetime(2026, 9, 4, tzinfo=UTC), context=_context(),
        dataset_id="t", dataset_version="1.0.0", dataset_sha256=_SHA64,
        policy_id="p", policy_version="1.0.0", policy_sha256=_SHA64,
        demand_reports=reports, macro_strict=macro, macro_broad=macro,
        macro_denominators=denominators, uncertainty_rate=0.0,
    )


def _protocol(hypothesis: StudyHypothesis) -> StudyProtocol:
    return StudyProtocol(
        study_id="T", study_version="1.0.0", protocol_sha256=_SHA64, alpha=0.05,
        multiple_testing_method="benjamini_hochberg", bootstrap_iterations=500,
        bootstrap_confidence_level=0.95, seed=42, hypotheses=[hypothesis],
    )


class PairedExclusionTest:
    def test_should_exclude_undefined_pairs_with_explicit_accounting(self) -> None:
        baseline = _run("b", {"D1": 0.4, "D2": None, "D3": 0.8, "D4": 0.3})
        treatment = _run("t", {"D1": 0.6, "D2": 0.5, "D3": None, "D4": 0.7})
        h = StudyHypothesis(
            id="H", baseline="b", treatment="t", metric="ndcg_at_10",
            scope="strict", alternative="greater", description="",
        )
        result = evaluate_study_protocol(
            runs={"b": baseline, "t": treatment}, protocol=_protocol(h), study_status="PILOT"
        ).results[0]
        # Only D1 and D4 are defined on both sides.
        assert result.n_paired == 2
        assert result.excluded_demand_ids == ["D2", "D3"]

    def test_should_fail_fast_when_no_valid_pair_exists(self) -> None:
        baseline = _run("b", {"D1": None})
        treatment = _run("t", {"D1": None})
        h = StudyHypothesis(
            id="H", baseline="b", treatment="t", metric="ndcg_at_10",
            scope="strict", alternative="greater", description="",
        )
        with pytest.raises(ValueError, match="no valid paired observations"):
            evaluate_study_protocol(
                runs={"b": baseline, "t": treatment}, protocol=_protocol(h), study_status="PILOT"
            )
