"""Clean Architecture EvaluationRunner implementation under ADR 0007.

Invariants:
- Pure independent auditor: this module imports NOTHING from domain.models.matching,
  domain.protocols.matching, or application.matching. It knows no matching-domain type.
- Zero filesystem access: does not open files, discover paths, or query Git.
- Ranking is delegated entirely to EvaluationRankingPort (implemented by DefaultMatchingAdapter).
  The runner receives a list[str] of ranked publication_ids — nothing more.
- All mathematical calculations are delegated to application.evaluation.metrics.
- The ranked list is accepted as-is; the runner never re-sorts it (ADR 0007 §4).
- Produces a sealed, immutable EvaluationRunReport stamped with provenance.

Dependency graph:
    application.evaluation.runner
        ← domain.models.evaluation   (all inputs/outputs are evaluation-domain types)
        ← domain.protocols.evaluation (EvaluationRankingPort, EvaluationPolicyIdentity)
        ← application.evaluation.metrics (pure math functions)
"""

import uuid
from datetime import UTC, datetime

from application.evaluation.metrics import compute_demand_metrics
from domain.models.evaluation import (
    DemandMetricsReport,
    EvaluationExecutionContext,
    EvaluationRunReport,
    MetricSet,
    RelevanceGrade,
    ValidatedDataset,
)
from domain.protocols.evaluation import (
    EvaluationPolicyIdentity,
    EvaluationRankingPort,
    EvaluationRunner,
)


# MetricSet fields that are always defined (never None): on empty input they fall
# back to 0.0, preserving the pre-PR-#44 all-zero behavior for empty universes.
_ALWAYS_DEFINED_FIELDS = frozenset(
    {
        "precision_at_1",
        "precision_at_3",
        "precision_at_5",
        "mrr",
        "mrr_at_5",
        "judged_at_1",
        "judged_at_3",
        "judged_at_5",
    }
)


def _macro_average_metric_sets(
    metric_sets: list[MetricSet],
) -> tuple[MetricSet, dict[str, int]]:
    """Computes deterministic macro-average across per-demand MetricSets.

    Protocol exclusion rule (PR #44): None (undefined) observations are skipped,
    never imputed. Returns the macro MetricSet (None where no valid observation
    exists) together with explicit per-metric denominators.
    """
    macro_values: dict[str, float | None] = {}
    denominators: dict[str, int] = {}
    for field in MetricSet.model_fields:
        valid = [getattr(m, field) for m in metric_sets if getattr(m, field) is not None]
        denominators[field] = len(valid)
        if valid:
            macro_values[field] = sum(valid) / len(valid)
        elif field in _ALWAYS_DEFINED_FIELDS:
            macro_values[field] = 0.0
        else:
            macro_values[field] = None

    return MetricSet(**macro_values), denominators


class DefaultEvaluationRunner(EvaluationRunner):
    """Reference implementation of the EvaluationRunner protocol.

    The runner is a pure orchestrator:
    1. Iterates over demands in the sealed dataset.
    2. Asks EvaluationRankingPort to rank the candidate patent universe for each demand.
    3. Aligns ranked ids with expert annotations.
    4. Delegates metric computation to metrics.py.
    5. Assembles and stamps EvaluationRunReport.

    The runner never constructs CandidatePool, Candidate, PatentCandidateEvidence, or any
    matching-domain type. That translation is done by the adapter (DefaultMatchingAdapter).
    """

    def run_evaluation(
        self,
        dataset: ValidatedDataset,
        ranking_port: EvaluationRankingPort,
        policy: EvaluationPolicyIdentity,
        context: EvaluationExecutionContext,
    ) -> EvaluationRunReport:
        """Executes full evaluation run, producing a sealed, reproducible EvaluationRunReport."""
        eval_dataset = dataset.dataset
        manifest = dataset.manifest

        # Map annotations by demand_id → {publication_id → RelevanceGrade}
        annotations_by_demand: dict[str, dict[str, RelevanceGrade]] = {}
        all_grades: list[RelevanceGrade] = []

        for anno in eval_dataset.annotations:
            if anno.demand_id not in annotations_by_demand:
                annotations_by_demand[anno.demand_id] = {}
            annotations_by_demand[anno.demand_id][anno.publication_id] = anno.grade
            all_grades.append(anno.grade)

        # Sealed candidate universe: all patents in the dataset
        patent_universe = eval_dataset.patents

        demand_reports: list[DemandMetricsReport] = []

        for eval_demand in eval_dataset.demands:
            d_id = eval_demand.demand_id

            # 1. Delegate ranking to port — receives only evaluation-domain objects,
            #    returns ranked publication_ids in engine's original order.
            ranked_ids = ranking_port.rank_candidates(eval_demand, patent_universe)

            # 2. Align with expert annotations and compute per-demand metrics
            judgements = annotations_by_demand.get(d_id, {})
            demand_report = compute_demand_metrics(
                demand_id=d_id,
                ranked_publication_ids=ranked_ids,
                judgements=judgements,
                candidate_universe_size=len(patent_universe),
            )
            demand_reports.append(demand_report)

        # 3. Compute macro summaries with explicit denominators: undefined (None)
        # per-demand observations are excluded, never imputed (protocol rule).
        # Strict and broad scopes exclude independently (different relevance totals).
        macro_strict, denom_strict = _macro_average_metric_sets([r.strict_metrics for r in demand_reports])
        macro_broad, denom_broad = _macro_average_metric_sets([r.broad_metrics for r in demand_reports])
        macro_denominators = {f"strict.{k}": v for k, v in denom_strict.items()}
        macro_denominators.update({f"broad.{k}": v for k, v in denom_broad.items()})

        # 4. Compute global uncertainty rate
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
            macro_denominators=macro_denominators,
            uncertainty_rate=overall_uncertainty_rate,
        )
