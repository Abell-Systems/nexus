"""Pure mathematical evaluation metrics for scientific matching evaluation under ADR 0007.

Invariants:
- Pure functional inputs: sequences of publication IDs and discrete RelevanceGrade mappings.
- Completely decoupled: NO imports from MatchingEngine, CandidateRetriever, MatchingPolicyConfig,
  filesystem, or Git.
- Epistemological invariant: RelevanceGrade.UNCERTAIN (-1) is strictly filtered and NEVER coerced to 0.
- Dual operational projections: Strict (Grade 3) and Broad (Grades 2 & 3).
- Judged-item Precision@K paired with mandatory Judged@K coverage reporting.
- Deterministic boundary handling: IDCG=0 -> nDCG=1.0.
- Decoupled cutoffs: functions accept generic k, leaving standard (1, 3, 5) aggregation to orchestrators.
"""

import math
from collections.abc import Callable, Sequence

from domain.models.evaluation import (
    DemandMetricsReport,
    MetricSet,
    RelevanceGrade,
)


def is_relevant_strict(grade: RelevanceGrade) -> bool:
    """Strict target alignment projection (ADR 0007 §2): only Grade 3 is relevant."""
    return grade == RelevanceGrade.GRADE_3


def is_relevant_broad(grade: RelevanceGrade) -> bool:
    """Broad technological alignment projection (ADR 0007 §2): Grades 2 and 3 are relevant."""
    return grade in (RelevanceGrade.GRADE_2, RelevanceGrade.GRADE_3)


def is_judged(grade: RelevanceGrade | None) -> bool:
    """Checks whether an item has a definitive expert judgment (not UNCERTAIN or unannotated)."""
    return grade is not None and grade != RelevanceGrade.UNCERTAIN


def precision_at_k(
    ranked_ids: Sequence[str],
    judgements: dict[str, RelevanceGrade],
    k: int,
    relevance_fn: Callable[[RelevanceGrade], bool],
) -> float:
    """Computes Judged-Item Precision@K under ADR 0007 §3: TP_K / (TP_K + FP_K).

    Items with grade UNCERTAIN or missing from judgements are excluded from both numerator and denominator.
    Returns 0.0 if no judged items are present in top-k.
    """
    if k <= 0:
        return 0.0

    cutoff_ids = ranked_ids[:k]
    tp = 0
    fp = 0

    for pub_id in cutoff_ids:
        grade = judgements.get(pub_id)
        if not is_judged(grade):
            continue
        assert grade is not None  # Type narrowing for mypy
        if relevance_fn(grade):
            tp += 1
        else:
            fp += 1

    total_judged = tp + fp
    if total_judged == 0:
        return 0.0
    return tp / total_judged


def recall_at_k(
    ranked_ids: Sequence[str],
    judgements: dict[str, RelevanceGrade],
    total_relevant: int,
    k: int,
    relevance_fn: Callable[[RelevanceGrade], bool],
) -> float:
    """Computes Recall@K over the closed pooled candidate universe under ADR 0007 §1: TP_K / TotalRelevant.

    Boundary condition: if total_relevant == 0, returns 1.0 (all relevant items found trivially).
    """
    if total_relevant <= 0:
        return 1.0
    if k <= 0:
        return 0.0

    cutoff_ids = ranked_ids[:k]
    tp = 0

    for pub_id in cutoff_ids:
        grade = judgements.get(pub_id)
        if not is_judged(grade):
            continue
        assert grade is not None
        if relevance_fn(grade):
            tp += 1

    return min(1.0, tp / total_relevant)


def judged_at_k(
    ranked_ids: Sequence[str],
    judgements: dict[str, RelevanceGrade],
    k: int,
) -> float:
    """Computes Judged Coverage at K under ADR 0007 §3: Judged_K / K."""
    if k <= 0:
        return 0.0

    cutoff_ids = ranked_ids[:k]
    judged_count = sum(1 for pub_id in cutoff_ids if is_judged(judgements.get(pub_id)))
    return judged_count / k


def uncertainty_rate(grades: Sequence[RelevanceGrade]) -> float:
    """Computes overall fraction of items labeled UNCERTAIN under ADR 0007 §3."""
    if not grades:
        return 0.0
    uncertain_count = sum(1 for g in grades if g == RelevanceGrade.UNCERTAIN)
    return uncertain_count / len(grades)


def mrr(
    ranked_ids: Sequence[str],
    judgements: dict[str, RelevanceGrade],
    relevance_fn: Callable[[RelevanceGrade], bool],
) -> float:
    """Computes Global Mean Reciprocal Rank over original system retrieval ranks (ADR 0007 §4).

    The rank is the 1-indexed position in the system's ranked_ids.
    Preceding UNCERTAIN or irrelevant items are not collapsed.
    """
    for idx, pub_id in enumerate(ranked_ids):
        orig_rank = idx + 1
        grade = judgements.get(pub_id)
        if grade is not None and grade != RelevanceGrade.UNCERTAIN and relevance_fn(grade):
            return 1.0 / orig_rank
    return 0.0


def mrr_at_k(
    ranked_ids: Sequence[str],
    judgements: dict[str, RelevanceGrade],
    k: int,
    relevance_fn: Callable[[RelevanceGrade], bool],
) -> float:
    """Computes Rank-Truncated Reciprocal Rank within top-k original system positions (ADR 0007 §4)."""
    if k <= 0:
        return 0.0

    for idx, pub_id in enumerate(ranked_ids[:k]):
        orig_rank = idx + 1
        grade = judgements.get(pub_id)
        if grade is not None and grade != RelevanceGrade.UNCERTAIN and relevance_fn(grade):
            return 1.0 / orig_rank
    return 0.0


def ndcg_at_k(
    ranked_ids: Sequence[str],
    judgements: dict[str, RelevanceGrade],
    k: int,
) -> float:
    """Computes normalized Discounted Cumulative Gain at K under ADR 0007 §4.

    Invariants:
    - Items with grade UNCERTAIN are filtered out before applying logarithmic discount.
    - Uses gain formulation: 2^g - 1 for discrete grade g in {0, 1, 2, 3}.
    - Boundary condition: if IDCG == 0.0 (no judged relevant items exist for demand), returns 1.0.
    """
    if k <= 0:
        return 0.0

    # 1. Filter out UNCERTAIN / unjudged items to produce judged ranking
    judged_grades: list[int] = []
    for pub_id in ranked_ids:
        grade = judgements.get(pub_id)
        if is_judged(grade):
            assert grade is not None
            judged_grades.append(grade.value)

    # 2. Extract top-k judged grades
    top_k_grades = judged_grades[:k]

    # 3. Compute DCG@k
    dcg = 0.0
    for idx, g in enumerate(top_k_grades):
        gain = (2.0**g) - 1.0
        discount = math.log2(idx + 2.0)  # log2(rank + 1) where rank = idx + 1
        dcg += gain / discount

    # 4. Compute IDCG@k from all known judged grades for this demand
    all_known_grades = [g.value for g in judgements.values() if is_judged(g)]
    sorted_ideal = sorted(all_known_grades, reverse=True)[:k]

    idcg = 0.0
    for idx, g in enumerate(sorted_ideal):
        gain = (2.0**g) - 1.0
        discount = math.log2(idx + 2.0)
        idcg += gain / discount

    # Boundary handling (ADR 0007 §4)
    if idcg <= 0.0:
        return 1.0

    return min(1.0, dcg / idcg)


def _build_metric_set(
    ranked_ids: Sequence[str],
    judgements: dict[str, RelevanceGrade],
    total_relevant: int,
    relevance_fn: Callable[[RelevanceGrade], bool],
) -> MetricSet:
    """Constructs an immutable MetricSet for a specific relevance projection function."""
    return MetricSet(
        precision_at_1=precision_at_k(ranked_ids, judgements, k=1, relevance_fn=relevance_fn),
        precision_at_3=precision_at_k(ranked_ids, judgements, k=3, relevance_fn=relevance_fn),
        precision_at_5=precision_at_k(ranked_ids, judgements, k=5, relevance_fn=relevance_fn),
        recall_at_1=recall_at_k(ranked_ids, judgements, total_relevant=total_relevant, k=1, relevance_fn=relevance_fn),
        recall_at_3=recall_at_k(ranked_ids, judgements, total_relevant=total_relevant, k=3, relevance_fn=relevance_fn),
        recall_at_5=recall_at_k(ranked_ids, judgements, total_relevant=total_relevant, k=5, relevance_fn=relevance_fn),
        mrr=mrr(ranked_ids, judgements, relevance_fn=relevance_fn),
        mrr_at_5=mrr_at_k(ranked_ids, judgements, k=5, relevance_fn=relevance_fn),
        ndcg_at_5=ndcg_at_k(ranked_ids, judgements, k=5),
        judged_at_1=judged_at_k(ranked_ids, judgements, k=1),
        judged_at_3=judged_at_k(ranked_ids, judgements, k=3),
        judged_at_5=judged_at_k(ranked_ids, judgements, k=5),
    )


def compute_demand_metrics(
    demand_id: str,
    ranked_publication_ids: Sequence[str],
    judgements: dict[str, RelevanceGrade],
    candidate_universe_size: int,
) -> DemandMetricsReport:
    """Computes deterministic DemandMetricsReport across strict and broad projections."""
    judged_count = sum(1 for g in judgements.values() if is_judged(g))
    uncertain_count = sum(1 for g in judgements.values() if g == RelevanceGrade.UNCERTAIN)

    total_strict_relevant = sum(
        1 for g in judgements.values() if is_judged(g) and is_relevant_strict(g)
    )
    total_broad_relevant = sum(
        1 for g in judgements.values() if is_judged(g) and is_relevant_broad(g)
    )

    strict_metrics = _build_metric_set(
        ranked_ids=ranked_publication_ids,
        judgements=judgements,
        total_relevant=total_strict_relevant,
        relevance_fn=is_relevant_strict,
    )
    broad_metrics = _build_metric_set(
        ranked_ids=ranked_publication_ids,
        judgements=judgements,
        total_relevant=total_broad_relevant,
        relevance_fn=is_relevant_broad,
    )

    return DemandMetricsReport(
        demand_id=demand_id,
        candidate_count=candidate_universe_size,
        judged_count=judged_count,
        uncertain_count=uncertain_count,
        strict_metrics=strict_metrics,
        broad_metrics=broad_metrics,
    )
