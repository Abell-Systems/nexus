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
    EvaluationDemand,
    EvaluationExecutionContext,
    EvaluationPatent,
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


def validate_temporal_pool_mode_consistency(temporal_pool_mode: str, require_temporal_validity: bool) -> None:
    """ADR 0018 §2: fails fast on the one invalid combination.

    Pure function over primitives — takes no policy/context object — so the CLI
    bootstrap layer (which already loads the real MatchingPolicyConfig and builds
    the EvaluationExecutionContext) can call it without any new coupling between
    the evaluation runner and matching-domain policy internals: the runner itself
    never reads policy.sufficiency_rules (EvaluationPolicyIdentity intentionally
    exposes only policy_id/policy_version/policy_sha256 for provenance stamping).

    "unconstrained" + require_temporal_validity=True would silently reintroduce
    temporal score-zeroing into what is supposed to be the no-enforcement
    condition RQ3 needs. "strict" is valid regardless of the flag: ineligible
    candidates are already excluded from the pool, so the flag is vacuous, not
    contradictory.
    """
    if temporal_pool_mode == "unconstrained" and require_temporal_validity:
        raise ValueError(
            "temporal_pool_mode='unconstrained' with require_temporal_validity=True "
            "contaminates the unconstrained condition: the evaluator would still zero "
            "scores for temporally-ineligible candidates that remain in the pool. "
            "Use a policy with require_temporal_validity=False for a genuine "
            "unconstrained run, or switch to temporal_pool_mode='strict' (ADR 0018 §2)."
        )


def family_metadata_available(patents: list[EvaluationPatent]) -> bool:
    """ADR 0027: True iff every patent in the given pool carries a non-None family_id.

    A single missing family_id makes the pool's family composition only partially
    known -- treated as fully unavailable, since a partial collapse/exclusion would
    silently distort metrics for the unlabelled patents in a way indistinguishable
    from inventing the metadata.
    """
    return all(p.family_id is not None for p in patents)


def validate_family_policy_feasible(family_policy: str, patents: list[EvaluationPatent]) -> None:
    """ADR 0027 §3: fails fast when the requested policy cannot be honestly applied.

    "allow" never requires family metadata. "collapse" and "exclude_related" require
    it on every patent in the pool being validated -- never silently degrade to
    "allow" and never partially apply the policy.
    """
    if family_policy == "allow":
        return
    if not family_metadata_available(patents):
        raise ValueError(
            f"FAMILY_METADATA_UNAVAILABLE: family_policy='{family_policy}' requires "
            "family_id to be populated on every patent in the candidate universe, "
            "but at least one patent is missing it. Use family_policy='allow', or "
            "supply a dataset with complete family metadata (ADR 0027 §1: family_id "
            "is only ever accepted from the sealed dataset, never inferred here)."
        )


def _apply_family_policy(family_policy: str, patents: list[EvaluationPatent]) -> list[EvaluationPatent]:
    """ADR 0027 §2/§4: pre-ranking pool transform, mirroring _filter_temporally_eligible_patents's
    placement. Caller must have already called validate_family_policy_feasible -- this function
    assumes family_id is populated on every patent when family_policy != "allow".
    """
    if family_policy == "allow":
        return list(patents)

    if family_policy == "collapse":
        best_by_family: dict[str, EvaluationPatent] = {}
        for p in sorted(patents, key=lambda p: p.publication_id):
            family_id = _require_family_id(p)
            if family_id not in best_by_family:
                best_by_family[family_id] = p
        return sorted(best_by_family.values(), key=lambda p: p.publication_id)

    # exclude_related
    family_counts: dict[str, int] = {}
    for p in patents:
        family_id = _require_family_id(p)
        family_counts[family_id] = family_counts.get(family_id, 0) + 1
    return [p for p in patents if family_counts[_require_family_id(p)] == 1]


def _require_family_id(patent: EvaluationPatent) -> str:
    """Narrows EvaluationPatent.family_id (str | None) to str for collapse/exclude_related.

    Precondition enforced here as a real assertion, not just a type-checker hint:
    validate_family_policy_feasible must already have confirmed every patent in the
    pool has a family_id before _apply_family_policy is called for these two policies.
    A caller that skips that check would otherwise silently collapse every
    family_id=None patent into one pseudo-family -- an assertion failure here is the
    correct outcome instead.
    """
    assert patent.family_id is not None, (
        f"_apply_family_policy precondition violated: patent {patent.publication_id} "
        "has no family_id. Caller must call validate_family_policy_feasible first."
    )
    return patent.family_id


def _filter_temporally_eligible_patents(
    demand: EvaluationDemand, patents: list[EvaluationPatent]
) -> list[EvaluationPatent]:
    """ADR 0018 §3: Φ_temporal pool filter — t_pub < t_demand, evaluated per demand.

    Mirrors application.matching.feature_extractor's temporal_valid semantics
    exactly: a patent stays eligible whenever either date is missing (undecidable,
    not excluded) — this function does not introduce a stricter default than the
    existing evaluation-time check it complements.
    """
    d_date = demand.posted_date
    if d_date is None:
        return list(patents)
    return [p for p in patents if p.publication_date is None or p.publication_date < d_date]


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

    return MetricSet.model_validate(macro_values), denominators


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

        # ADR 0027: fail fast, once, on the full sealed universe -- before any
        # per-demand work happens -- if the requested policy cannot be honestly
        # applied to this dataset.
        validate_family_policy_feasible(context.family_policy, patent_universe)

        demand_reports: list[DemandMetricsReport] = []

        for eval_demand in eval_dataset.demands:
            d_id = eval_demand.demand_id

            # 0. ADR 0018 §3: in "strict" mode, Φ_temporal is applied per demand
            #    BEFORE ranking, excluding ineligible patents from the pool entirely —
            #    never inside the adapter/engine/evaluator. "unconstrained" keeps the
            #    full sealed universe, exactly as before ADR 0018.
            if context.temporal_pool_mode == "strict":
                eligible_patents = _filter_temporally_eligible_patents(eval_demand, patent_universe)
            else:
                eligible_patents = patent_universe

            # ADR 0027: family-policy pool transform, applied after temporal
            # eligibility and before ranking -- same insertion point convention
            # ADR 0018 established for _filter_temporally_eligible_patents.
            eligible_patents = _apply_family_policy(context.family_policy, eligible_patents)

            # 1. Delegate ranking to port — receives only evaluation-domain objects,
            #    returns ranked publication_ids in engine's original order.
            ranked_ids = ranking_port.rank_candidates(eval_demand, eligible_patents)

            # 2. Align with expert annotations and compute per-demand metrics
            judgements = annotations_by_demand.get(d_id, {})
            demand_report = compute_demand_metrics(
                demand_id=d_id,
                ranked_publication_ids=ranked_ids,
                judgements=judgements,
                candidate_universe_size=len(eligible_patents),
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
            family_metadata_available=family_metadata_available(patent_universe),
        )
