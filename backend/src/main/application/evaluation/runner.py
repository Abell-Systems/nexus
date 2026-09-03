"""Clean Architecture EvaluationRunner implementation under ADR 0007.

Invariants:
- Evaluator acts as an independent auditor; contains NO matching or heuristic logic.
- Pure dependency injection: accepts ValidatedDataset, MatchingEngine, MatchingPolicyConfig,
  and EvaluationExecutionContext explicitly via arguments.
- Zero filesystem access: does not open files, discover paths, or query Git.
- Preserves the engine's original candidate ranking order strictly without re-sorting.
- Delegates all mathematical calculations to application.evaluation.metrics.
- Produces a sealed, immutable EvaluationRunReport preserving full provenance audit stamps.
"""

import uuid
from datetime import UTC, datetime

from application.evaluation.metrics import compute_demand_metrics
from domain.models.demand import DemandSignal
from domain.models.evaluation import (
    DemandMetricsReport,
    EvaluationExecutionContext,
    EvaluationRunReport,
    MetricSet,
    RelevanceGrade,
    ValidatedDataset,
)
from domain.models.matching import (
    Candidate,
    CandidatePool,
    MatchingPolicyConfig,
    RetrievalMethod,
)
from domain.protocols.evaluation import EvaluationRunner
from domain.protocols.matching import MatchingEngine


def _macro_average_metric_sets(metric_sets: list[MetricSet]) -> MetricSet:
    """Computes deterministic macro-average across multiple per-demand MetricSets."""
    if not metric_sets:
        return MetricSet(
            precision_at_1=0.0,
            precision_at_3=0.0,
            precision_at_5=0.0,
            recall_at_1=0.0,
            recall_at_3=0.0,
            recall_at_5=0.0,
            mrr=0.0,
            mrr_at_5=0.0,
            ndcg_at_5=0.0,
            judged_at_1=0.0,
            judged_at_3=0.0,
            judged_at_5=0.0,
        )

    n = len(metric_sets)
    return MetricSet(
        precision_at_1=sum(m.precision_at_1 for m in metric_sets) / n,
        precision_at_3=sum(m.precision_at_3 for m in metric_sets) / n,
        precision_at_5=sum(m.precision_at_5 for m in metric_sets) / n,
        recall_at_1=sum(m.recall_at_1 for m in metric_sets) / n,
        recall_at_3=sum(m.recall_at_3 for m in metric_sets) / n,
        recall_at_5=sum(m.recall_at_5 for m in metric_sets) / n,
        mrr=sum(m.mrr for m in metric_sets) / n,
        mrr_at_5=sum(m.mrr_at_5 for m in metric_sets) / n,
        ndcg_at_5=sum(m.ndcg_at_5 for m in metric_sets) / n,
        judged_at_1=sum(m.judged_at_1 for m in metric_sets) / n,
        judged_at_3=sum(m.judged_at_3 for m in metric_sets) / n,
        judged_at_5=sum(m.judged_at_5 for m in metric_sets) / n,
    )


class DefaultEvaluationRunner(EvaluationRunner):
    """Reference implementation of the EvaluationRunner protocol."""

    def run_evaluation(
        self,
        dataset: ValidatedDataset,
        engine: MatchingEngine,
        policy: MatchingPolicyConfig,
        context: EvaluationExecutionContext,
    ) -> EvaluationRunReport:
        """Executes full evaluation run, producing a sealed, reproducible EvaluationRunReport."""
        eval_dataset = dataset.dataset
        manifest = dataset.manifest

        # Map annotations by (demand_id, publication_id) -> RelevanceGrade
        annotations_by_demand: dict[str, dict[str, RelevanceGrade]] = {}
        all_grades: list[RelevanceGrade] = []

        for anno in eval_dataset.annotations:
            if anno.demand_id not in annotations_by_demand:
                annotations_by_demand[anno.demand_id] = {}
            annotations_by_demand[anno.demand_id][anno.publication_id] = anno.grade
            all_grades.append(anno.grade)

        # Sealed candidate universe: all patents in dataset
        universe_candidates = [
            Candidate(publication_id=p.publication_id, retrieval_scores={RetrievalMethod.LEXICAL: 1.0})
            for p in eval_dataset.patents
        ]

        demand_reports: list[DemandMetricsReport] = []

        for eval_demand in eval_dataset.demands:
            d_id = eval_demand.demand_id
            pool = CandidatePool(demand_id=d_id, candidates=universe_candidates)

            demand_signal = DemandSignal(
                demand_id=d_id,
                source_network=eval_demand.provenance.source_authority,
                title=eval_demand.title,
                description=eval_demand.description,
                posted_date=eval_demand.posted_date.isoformat() if eval_demand.posted_date else None,
                classified_cpc_prefixes=eval_demand.target_cpc_prefixes,
            )

            # 1. Evaluate demand using injected MatchingEngine
            assessments = engine.evaluate(
                demand=demand_signal,
                candidates=pool,
                policy=policy,
            )

            # 2. Extract engine ranking strictly preserving original order (ADR 0007 §4)
            ranked_ids = [a.publication_id for a in assessments]

            # 3. Align with judgements and compute per-demand metrics
            judgements = annotations_by_demand.get(d_id, {})
            demand_report = compute_demand_metrics(
                demand_id=d_id,
                ranked_publication_ids=ranked_ids,
                judgements=judgements,
                candidate_universe_size=len(universe_candidates),
            )
            demand_reports.append(demand_report)

        # 4. Compute macro summaries
        macro_strict = _macro_average_metric_sets([r.strict_metrics for r in demand_reports])
        macro_broad = _macro_average_metric_sets([r.broad_metrics for r in demand_reports])

        # 5. Compute global uncertainty rate
        unc_count = sum(1 for g in all_grades if g == RelevanceGrade.UNCERTAIN)
        total_anno = len(all_grades)
        overall_uncertainty_rate = (unc_count / total_anno) if total_anno > 0 else 0.0

        run_id = f"eval-run-{uuid.uuid4().hex[:12]}"

        return EvaluationRunReport(
            run_id=run_id,
            created_at=datetime.now(UTC),
            context=context,
            dataset_id=eval_dataset.dataset_id,
            dataset_version=eval_dataset.dataset_version,
            dataset_sha256=manifest.content_sha256,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_sha256=policy.policy_sha256,
            demand_reports=demand_reports,
            macro_strict=macro_strict,
            macro_broad=macro_broad,
            uncertainty_rate=overall_uncertainty_rate,
        )
