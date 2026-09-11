"""Paired demand-level comparative evaluation harness under ADR 0011.

Invariants:
- Extracts paired per-demand metric vectors from EvaluationRunReport.demand_reports.
  Statistical tests operate on demand-level observations, NEVER on macro aggregates.
- Fails fast with ValueError if baseline and treatment demand_id sets differ.
- Fails fast with ValueError if a required run label is absent from the runs dict.
- Applies BH-FDR across the full pre-registered hypothesis family simultaneously.
- Zero imports from matching domain, infrastructure, or provider SDKs.

Dependency graph:
    application.evaluation.comparative
        ← domain.models.evaluation  (EvaluationRunReport, StudyProtocol, hypothesis models)
        ← application.evaluation.statistics  (wilcoxon, bootstrap, multiple_testing)
"""

from application.evaluation.statistics import (
    adjust_benjamini_hochberg,
    paired_bootstrap_ci,
    paired_wilcoxon_test,
)
from application.evaluation.statistics.types import BootstrapCIResult, WilcoxonResult
from domain.models.evaluation import (
    ComparativeRunReport,
    EvaluationRunReport,
    HypothesisTestResult,
    MetricSet,
    StudyHypothesis,
    StudyProtocol,
)


def _extract_metric(metric_set: MetricSet, metric: str) -> float | None:
    """Extract a scalar metric value by name from a MetricSet.

    Returns None when the metric is undefined for that demand (protocol exclusion
    semantics, PR #44) so the caller can exclude the pair instead of imputing.
    """
    if metric not in MetricSet.model_fields:
        raise ValueError(
            f"Metric '{metric}' not found in MetricSet. "
            f"Available metrics: {list(MetricSet.model_fields.keys())}"
        )
    value = getattr(metric_set, metric)
    return None if value is None else float(value)


def _extract_paired_vectors(
    baseline_run: EvaluationRunReport,
    treatment_run: EvaluationRunReport,
    hypothesis: StudyHypothesis,
) -> tuple[list[float], list[float], list[str]]:
    """Extract aligned per-demand metric vectors from two EvaluationRunReports.

    The paired vectors are ordered by the sorted set of demand_ids to guarantee
    deterministic alignment across independent runs. Demands where the hypothesis
    metric is undefined (None) on either side are excluded as a pair and returned
    as the third element, per the protocol exclusion rule — never imputed.

    Raises:
        ValueError: if demand_id sets differ between baseline and treatment runs.
    """
    baseline_by_demand = {r.demand_id: r for r in baseline_run.demand_reports}
    treatment_by_demand = {r.demand_id: r for r in treatment_run.demand_reports}

    baseline_ids = set(baseline_by_demand.keys())
    treatment_ids = set(treatment_by_demand.keys())

    if baseline_ids != treatment_ids:
        only_baseline = baseline_ids - treatment_ids
        only_treatment = treatment_ids - baseline_ids
        msg_parts = []
        if only_baseline:
            msg_parts.append(f"demand_id(s) only in baseline: {sorted(only_baseline)}")
        if only_treatment:
            msg_parts.append(f"demand_id(s) only in treatment: {sorted(only_treatment)}")
        raise ValueError(
            f"Demand ID mismatch between baseline '{baseline_run.run_id}' "
            f"and treatment '{treatment_run.run_id}'. "
            + "; ".join(msg_parts)
        )

    ordered_ids = sorted(baseline_ids)
    scope_attr = "strict_metrics" if hypothesis.scope == "strict" else "broad_metrics"

    baseline_values: list[float] = []
    treatment_values: list[float] = []
    excluded_demand_ids: list[str] = []

    for demand_id in ordered_ids:
        b_report = baseline_by_demand[demand_id]
        t_report = treatment_by_demand[demand_id]
        b_metrics: MetricSet = getattr(b_report, scope_attr)
        t_metrics: MetricSet = getattr(t_report, scope_attr)
        b_value = _extract_metric(b_metrics, hypothesis.metric)
        t_value = _extract_metric(t_metrics, hypothesis.metric)
        if b_value is None or t_value is None:
            excluded_demand_ids.append(demand_id)
            continue
        baseline_values.append(b_value)
        treatment_values.append(t_value)

    return baseline_values, treatment_values, excluded_demand_ids


def _validate_paired_run_identity(
    baseline_run: EvaluationRunReport, treatment_run: EvaluationRunReport, hypothesis_id: str
) -> None:
    """ADR 0018 Enforcement #6 / ADR 0027 Enforcement #6 / ADR 0028: two runs built
    under different pool-construction or denominator semantics are not a like-for-like
    ranking comparison. Pairing them would silently attribute a pool-composition or
    denominator-definition difference to the ranking engine under test, contaminating
    the very hypothesis test this harness exists to run honestly.
    """
    if baseline_run.context.temporal_pool_mode != treatment_run.context.temporal_pool_mode:
        raise ValueError(
            f"Hypothesis '{hypothesis_id}': baseline and treatment runs use different "
            f"temporal_pool_mode ('{baseline_run.context.temporal_pool_mode}' vs "
            f"'{treatment_run.context.temporal_pool_mode}') -- not a like-for-like "
            "comparison (ADR 0018 Enforcement #6)."
        )
    if baseline_run.context.family_policy != treatment_run.context.family_policy:
        raise ValueError(
            f"Hypothesis '{hypothesis_id}': baseline and treatment runs use different "
            f"family_policy ('{baseline_run.context.family_policy}' vs "
            f"'{treatment_run.context.family_policy}') -- not a like-for-like "
            "comparison (ADR 0027 Enforcement #6)."
        )
    if baseline_run.denominator_semantics != treatment_run.denominator_semantics:
        raise ValueError(
            f"Hypothesis '{hypothesis_id}': baseline and treatment runs use different "
            f"denominator_semantics ('{baseline_run.denominator_semantics}' vs "
            f"'{treatment_run.denominator_semantics}') -- comparing runs computed under "
            "different Recall/nDCG denominator definitions is scientifically invalid (ADR 0028)."
        )


def evaluate_study_protocol(
    runs: dict[str, EvaluationRunReport],
    protocol: StudyProtocol,
    study_status: str = "PILOT",
) -> ComparativeRunReport:
    """Execute all pre-registered hypotheses against their paired run reports.

    Invariants:
    - Every hypothesis in protocol.hypotheses must reference model labels present in `runs`.
    - BH-FDR is applied across the closed family of all hypotheses simultaneously.
    - Seed is taken from the protocol to guarantee byte-exact reproducibility.

    Args:
        runs:         Mapping of model label → EvaluationRunReport (one per model variant).
        protocol:     Sealed, pre-registered study protocol (ADR 0011 §2).
        study_status: "PILOT" or "FINAL". Must be "FINAL" only after benchmark freeze.

    Returns:
        ComparativeRunReport stamped with protocol provenance and BH-adjusted results.

    Raises:
        ValueError: if any model label referenced by a hypothesis is absent from `runs`.
        ValueError: if demand_id sets differ between baseline and treatment runs.
    """
    # Step 1: Validate that all model labels are present
    for hypothesis in protocol.hypotheses:
        for label in (hypothesis.baseline, hypothesis.treatment):
            if label not in runs:
                raise ValueError(
                    f"Model label '{label}' referenced in hypothesis '{hypothesis.id}' "
                    f"not found in runs. Available labels: {sorted(runs.keys())}"
                )

    # Step 2: Run paired tests for each hypothesis, collecting raw p-values
    raw_results: list[tuple[StudyHypothesis, WilcoxonResult, BootstrapCIResult, int, list[str]]] = []
    raw_p_values: list[float] = []

    for hypothesis in protocol.hypotheses:
        baseline_run = runs[hypothesis.baseline]
        treatment_run = runs[hypothesis.treatment]
        _validate_paired_run_identity(baseline_run, treatment_run, hypothesis.id)

        baseline_vec, treatment_vec, excluded_ids = _extract_paired_vectors(
            baseline_run, treatment_run, hypothesis
        )
        if not baseline_vec:
            raise ValueError(
                f"Hypothesis '{hypothesis.id}' has no valid paired observations for metric "
                f"'{hypothesis.metric}' ({hypothesis.scope} scope): every demand was excluded "
                f"as undefined. Cannot test on zero pairs."
            )

        wilcoxon_result: WilcoxonResult = paired_wilcoxon_test(
            baseline=baseline_vec,
            treatment=treatment_vec,
            alternative=hypothesis.alternative,
        )

        bootstrap_result: BootstrapCIResult = paired_bootstrap_ci(
            baseline=baseline_vec,
            treatment=treatment_vec,
            n_bootstrap=protocol.bootstrap_iterations,
            confidence_level=protocol.bootstrap_confidence_level,
            seed=protocol.seed,
        )

        raw_results.append(
            (hypothesis, wilcoxon_result, bootstrap_result, len(baseline_vec), excluded_ids)
        )
        raw_p_values.append(wilcoxon_result.p_value)

    # Step 3: BH-FDR across the closed family of hypotheses
    bh = adjust_benjamini_hochberg(p_values=raw_p_values, alpha=protocol.alpha)

    # Step 4: Assemble HypothesisTestResult per hypothesis
    hypothesis_results: list[HypothesisTestResult] = []
    for i, (hypothesis, wilcoxon_result, bootstrap_result, n_paired, excluded_ids) in enumerate(raw_results):
        hypothesis_results.append(
            HypothesisTestResult(
                hypothesis_id=hypothesis.id,
                baseline=hypothesis.baseline,
                treatment=hypothesis.treatment,
                metric=hypothesis.metric,
                scope=hypothesis.scope,
                wilcoxon=wilcoxon_result,
                bootstrap_ci=bootstrap_result,
                adjusted_q_value=bh.adjusted_p_values[i],
                rejected=bh.rejected[i],
                n_paired=n_paired,
                excluded_demand_ids=excluded_ids,
            )
        )

    # Step 5: Assemble sealed ComparativeRunReport
    run_ids = {label: report.run_id for label, report in runs.items()}

    return ComparativeRunReport(
        study_protocol_id=protocol.study_id,
        study_protocol_sha256=protocol.protocol_sha256,
        study_status=study_status,
        run_ids=run_ids,
        results=hypothesis_results,
    )
