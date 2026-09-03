"""Pure mathematical unit tests for scientific evaluation metrics under ADR 0007.

Invariants verified:
- Pure functional inputs: ranked item IDs + dict of RelevanceGrades.
- No imports of matching engines, policies, retrievers, or filesystem.
- Strict and broad relevance projection functions.
- Exact precision_at_k, recall_at_k, judged_at_k.
- Epistemic invariant: UNCERTAIN (-1) does not penalize or inflate Precision@K,
  while correctly altering Judged@K coverage and uncertainty_rate.
- Exact nDCG computation with graded relevance (0 to 3).
- Boundary conditions: IDCG=0 -> nDCG=1.0, empty inputs -> 0.0 or 1.0 safely without division by zero.
- Global MRR across full ranking vs rank-truncated MRR@K.
- Deterministic invariance: identical inputs produce identical outputs.
"""

import math

from application.evaluation.metrics import (
    compute_demand_metrics,
    is_relevant_broad,
    is_relevant_strict,
    judged_at_k,
    mrr,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    uncertainty_rate,
)
from domain.models.evaluation import RelevanceGrade


def test_strict_and_broad_relevance_projections():
    # Strict: only GRADE_3 is relevant
    assert is_relevant_strict(RelevanceGrade.GRADE_3) is True
    assert is_relevant_strict(RelevanceGrade.GRADE_2) is False
    assert is_relevant_strict(RelevanceGrade.GRADE_1) is False
    assert is_relevant_strict(RelevanceGrade.GRADE_0) is False
    assert is_relevant_strict(RelevanceGrade.UNCERTAIN) is False

    # Broad: GRADE_2 and GRADE_3 are relevant
    assert is_relevant_broad(RelevanceGrade.GRADE_3) is True
    assert is_relevant_broad(RelevanceGrade.GRADE_2) is True
    assert is_relevant_broad(RelevanceGrade.GRADE_1) is False
    assert is_relevant_broad(RelevanceGrade.GRADE_0) is False
    assert is_relevant_broad(RelevanceGrade.UNCERTAIN) is False


def test_precision_at_k_exact():
    # Ranked sequence: [P1, P2, P3, P4, P5]
    # Relevance: [3, 0, 3, 0, 0]
    # Under strict: [True, False, True, False, False]
    ranking = ["P1", "P2", "P3", "P4", "P5"]
    judgements = {
        "P1": RelevanceGrade.GRADE_3,
        "P2": RelevanceGrade.GRADE_0,
        "P3": RelevanceGrade.GRADE_3,
        "P4": RelevanceGrade.GRADE_0,
        "P5": RelevanceGrade.GRADE_0,
    }

    assert precision_at_k(ranking, judgements, k=1, relevance_fn=is_relevant_strict) == 1.0  # 1/1
    assert math.isclose(precision_at_k(ranking, judgements, k=2, relevance_fn=is_relevant_strict), 0.50)  # 1/2
    assert math.isclose(precision_at_k(ranking, judgements, k=3, relevance_fn=is_relevant_strict), 2 / 3)  # 2/3
    assert math.isclose(precision_at_k(ranking, judgements, k=5, relevance_fn=is_relevant_strict), 2 / 5)  # 2/5


def test_recall_at_k_exact():
    # Universe of relevant items = 3 known relevant items in candidate pool (P1, P3, P7)
    ranking = ["P1", "P2", "P3", "P4", "P5"]
    judgements = {
        "P1": RelevanceGrade.GRADE_3,
        "P2": RelevanceGrade.GRADE_0,
        "P3": RelevanceGrade.GRADE_3,
        "P4": RelevanceGrade.GRADE_0,
        "P5": RelevanceGrade.GRADE_0,
        "P6": RelevanceGrade.GRADE_0,
        "P7": RelevanceGrade.GRADE_3,
    }
    total_relevant = 3  # P1, P3, P7

    assert math.isclose(recall_at_k(ranking, judgements, total_relevant=total_relevant, k=1, relevance_fn=is_relevant_strict), 1 / 3)
    assert math.isclose(recall_at_k(ranking, judgements, total_relevant=total_relevant, k=3, relevance_fn=is_relevant_strict), 2 / 3)
    assert math.isclose(recall_at_k(ranking, judgements, total_relevant=total_relevant, k=5, relevance_fn=is_relevant_strict), 2 / 3)

    # Edge case: total_relevant is 0 -> recall is 1.0 (all relevant items found trivially)
    assert recall_at_k(ranking, judgements, total_relevant=0, k=5, relevance_fn=is_relevant_strict) == 1.0


def test_judged_at_k_exact():
    # Ranked sequence has 1 UNCERTAIN and 1 unannotated item
    ranking = ["P1", "P2", "P3", "P4", "P5"]
    judgements = {
        "P1": RelevanceGrade.GRADE_3,
        "P2": RelevanceGrade.UNCERTAIN,  # unjudged epistemic state
        "P3": RelevanceGrade.GRADE_0,
        "P4": RelevanceGrade.GRADE_2,
        # P5 is absent from judgements dict -> unjudged
    }

    assert judged_at_k(ranking, judgements, k=1) == 1.0  # P1 is judged
    assert judged_at_k(ranking, judgements, k=2) == 0.5  # 1 judged (P1) out of 2
    assert math.isclose(judged_at_k(ranking, judgements, k=3), 2 / 3)  # P1, P3 judged out of 3
    assert math.isclose(judged_at_k(ranking, judgements, k=4), 3 / 4)  # P1, P3, P4 judged out of 4
    assert math.isclose(judged_at_k(ranking, judgements, k=5), 3 / 5)  # 3 judged out of 5


def test_uncertain_does_not_change_precision():
    # Baseline without UNCERTAIN: [P1 (relevant), P2 (irrelevant)] -> P@2 = 1/2 = 0.5
    # Insert UNCERTAIN in between: [P1 (relevant), P_unc (UNCERTAIN), P2 (irrelevant)]
    # Over judged items in top-3: TP=1, FP=1 -> P@3 = 1 / (1 + 1) = 0.5
    ranking = ["P1", "P_unc", "P2"]
    judgements = {
        "P1": RelevanceGrade.GRADE_3,
        "P_unc": RelevanceGrade.UNCERTAIN,
        "P2": RelevanceGrade.GRADE_0,
    }

    prec = precision_at_k(ranking, judgements, k=3, relevance_fn=is_relevant_strict)
    assert math.isclose(prec, 0.5), "UNCERTAIN must NOT be counted as false positive!"


def test_uncertain_changes_judged_coverage():
    ranking = ["P1", "P_unc", "P2"]
    judgements = {
        "P1": RelevanceGrade.GRADE_3,
        "P_unc": RelevanceGrade.UNCERTAIN,
        "P2": RelevanceGrade.GRADE_0,
    }
    # Out of 3 items, exactly 2 are judged
    assert math.isclose(judged_at_k(ranking, judgements, k=3), 2 / 3)


def test_uncertainty_rate_exact():
    all_judgements = [
        RelevanceGrade.GRADE_3,
        RelevanceGrade.GRADE_2,
        RelevanceGrade.GRADE_0,
        RelevanceGrade.UNCERTAIN,
        RelevanceGrade.GRADE_1,
    ]
    # 1 out of 5 is UNCERTAIN
    assert math.isclose(uncertainty_rate(all_judgements), 0.20)

    # Empty judgements -> 0.0 safely
    assert uncertainty_rate([]) == 0.0


def test_mrr_global_vs_mrr_at_k():
    # First relevant item is at rank 4 (index 3)
    ranking = ["P1", "P2", "P3", "P4", "P5"]
    judgements = {
        "P1": RelevanceGrade.GRADE_0,
        "P2": RelevanceGrade.GRADE_0,
        "P3": RelevanceGrade.GRADE_0,
        "P4": RelevanceGrade.GRADE_3,
        "P5": RelevanceGrade.GRADE_3,
    }

    # Global MRR looks across full ranking -> 1/4 = 0.25
    assert math.isclose(mrr(ranking, judgements, relevance_fn=is_relevant_strict), 0.25)

    # MRR@3 cuts off at rank 3 -> first relevant at rank 4 is not found -> 0.0
    assert mrr_at_k(ranking, judgements, k=3, relevance_fn=is_relevant_strict) == 0.0

    # MRR@5 includes rank 4 -> 1/4 = 0.25
    assert math.isclose(mrr_at_k(ranking, judgements, k=5, relevance_fn=is_relevant_strict), 0.25)

    # Edge case: no relevant items anywhere
    irrelevant_judgements = {p: RelevanceGrade.GRADE_0 for p in ranking}
    assert mrr(ranking, irrelevant_judgements, relevance_fn=is_relevant_strict) == 0.0
    assert mrr_at_k(ranking, irrelevant_judgements, k=5, relevance_fn=is_relevant_strict) == 0.0


def test_mrr_preserves_original_system_rank_adversarial():
    # Adversarial test: system places UNCERTAIN items ahead of a relevant item
    # Original ranking:
    # 1. P_unc1 (UNCERTAIN)
    # 2. P_unc2 (UNCERTAIN)
    # 3. P_rel  (GRADE_3)
    # Under ADR 0007 §4, the relevant item was retrieved at original system position 3.
    # Therefore, MRR = 1/3 = ~0.33333, and MRR@2 = 0.0 (cutoff before rank 3), MRR@5 = 1/3
    ranking = ["P_unc1", "P_unc2", "P_rel", "P_other"]
    judgements = {
        "P_unc1": RelevanceGrade.UNCERTAIN,
        "P_unc2": RelevanceGrade.UNCERTAIN,
        "P_rel": RelevanceGrade.GRADE_3,
        "P_other": RelevanceGrade.GRADE_0,
    }

    assert math.isclose(mrr(ranking, judgements, relevance_fn=is_relevant_strict), 1.0 / 3.0)
    assert mrr_at_k(ranking, judgements, k=2, relevance_fn=is_relevant_strict) == 0.0
    assert math.isclose(mrr_at_k(ranking, judgements, k=5, relevance_fn=is_relevant_strict), 1.0 / 3.0)


def test_ndcg_exact():
    # Ranked items: [P1, P2, P3] with grades [3, 2, 0]
    # DCG@3 = (2^3 - 1)/log2(2) + (2^2 - 1)/log2(3) + (2^0 - 1)/log2(4)
    #       = 7 / 1 + 3 / 1.5849625 + 0 = 7 + 1.892789 = 8.892789
    # Ideal ranking: [3, 2, 0] -> IDCG@3 = DCG@3 -> nDCG@3 = 1.0
    ranking = ["P1", "P2", "P3"]
    judgements = {
        "P1": RelevanceGrade.GRADE_3,
        "P2": RelevanceGrade.GRADE_2,
        "P3": RelevanceGrade.GRADE_0,
    }
    assert math.isclose(ndcg_at_k(ranking, judgements, k=3), 1.0)

    # Suboptimal ranking: [P3 (0), P2 (2), P1 (3)]
    # DCG@3 = 0/log2(2) + 3/log2(3) + 7/log2(4) = 0 + 1.892789 + 3.5 = 5.392789
    # IDCG@3 = 8.892789
    # nDCG@3 = 5.392789 / 8.892789 = 0.606423
    suboptimal_ranking = ["P3", "P2", "P1"]
    expected_ndcg = (3 / math.log2(3) + 7 / math.log2(4)) / (7 / math.log2(2) + 3 / math.log2(3))
    actual_ndcg = ndcg_at_k(suboptimal_ranking, judgements, k=3)
    assert math.isclose(actual_ndcg, expected_ndcg, rel_tol=1e-5)


def test_ndcg_idcg_zero_boundary():
    # Case A: Demand where all judged candidates are Grade 0 (no relevant items exist)
    ranking = ["P1", "P2", "P3"]
    all_zero_judgements = {
        "P1": RelevanceGrade.GRADE_0,
        "P2": RelevanceGrade.GRADE_0,
        "P3": RelevanceGrade.GRADE_0,
    }
    # IDCG is 0 and DCG is 0 -> mathematically non-informative -> 1.0 by ADR 0007 §4
    assert ndcg_at_k(ranking, all_zero_judgements, k=3) == 1.0

    # Case B: All candidates are UNCERTAIN (0 judged relevant items)
    all_uncertain_judgements = {
        "P1": RelevanceGrade.UNCERTAIN,
        "P2": RelevanceGrade.UNCERTAIN,
    }
    assert ndcg_at_k(ranking, all_uncertain_judgements, k=3) == 1.0

    # Case C: Mixture of UNCERTAIN and Grade 0 (0 relevant items)
    mixed_judgements = {
        "P1": RelevanceGrade.UNCERTAIN,
        "P2": RelevanceGrade.GRADE_0,
    }
    assert ndcg_at_k(ranking, mixed_judgements, k=3) == 1.0

    # Case D: Empty candidate ranking
    assert ndcg_at_k([], {}, k=3) == 1.0


def test_ndcg_with_uncertain_filters_before_discount():
    # Ranking: [P_unc, P1 (3), P2 (2)]
    # Filtered judged sequence: [P1 (3), P2 (2)]
    # Under ADR 0007, discount is applied to the resulting judged sequence:
    # Position 1 in judged sequence: P1 (3) -> (2^3-1)/log2(2) = 7/1 = 7
    # Position 2 in judged sequence: P2 (2) -> (2^2-1)/log2(3) = 3/1.5849 = 1.892789
    # DCG = 8.892789, IDCG = 8.892789 -> nDCG = 1.0
    ranking = ["P_unc", "P1", "P2"]
    judgements = {
        "P_unc": RelevanceGrade.UNCERTAIN,
        "P1": RelevanceGrade.GRADE_3,
        "P2": RelevanceGrade.GRADE_2,
    }
    assert math.isclose(ndcg_at_k(ranking, judgements, k=2), 1.0)


def test_compute_demand_metrics_deterministic_invariance():
    ranking = ["P1", "P2", "P3", "P4", "P5"]
    judgements = {
        "P1": RelevanceGrade.GRADE_3,
        "P2": RelevanceGrade.GRADE_2,
        "P3": RelevanceGrade.UNCERTAIN,
        "P4": RelevanceGrade.GRADE_0,
        "P5": RelevanceGrade.GRADE_1,
    }

    report1 = compute_demand_metrics(
        demand_id="D-1",
        ranked_publication_ids=ranking,
        judgements=judgements,
        candidate_universe_size=5,
    )
    report2 = compute_demand_metrics(
        demand_id="D-1",
        ranked_publication_ids=ranking,
        judgements=judgements,
        candidate_universe_size=5,
    )

    # Determinism: exact equality across runs
    assert report1 == report2
    assert report1.demand_id == "D-1"
    assert report1.candidate_count == 5
    assert report1.judged_count == 4
    assert report1.uncertain_count == 1

    # Strict: only P1 is relevant (1 total in universe)
    assert report1.strict_metrics.precision_at_1 == 1.0
    assert report1.strict_metrics.recall_at_1 == 1.0
    assert report1.strict_metrics.mrr == 1.0

    # Broad: P1 and P2 are relevant (2 total in universe)
    assert report1.broad_metrics.precision_at_1 == 1.0
    assert report1.broad_metrics.precision_at_3 == 1.0  # P1, P2 judged relevant, P3 is UNCERTAIN (filtered) -> 2/2 = 1.0
    assert report1.broad_metrics.judged_at_3 == 2 / 3
    assert report1.broad_metrics.recall_at_1 == 0.5
    assert report1.broad_metrics.recall_at_3 == 1.0
