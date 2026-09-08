from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel

from domain.models.annotation import AnnotationJudgment

_NUM_GRADES = 4  # RelevanceGrade 0..3; UNCERTAIN is already rejected by AnnotationJudgment


@dataclass(frozen=True)
class Disagreement:
    demand_id: str
    publication_id: str
    grade_a: int
    grade_b: int


class IAAReport(BaseModel):
    weighted_kappa: float
    binary_kappa: float
    confusion_matrix: list[list[int]]
    disagreements: list[Disagreement]

    model_config = {"arbitrary_types_allowed": True}


def _weighted_kappa(labels_a: list[int], labels_b: list[int]) -> tuple[float, list[list[int]]]:
    """Linear-weighted Cohen's kappa: penalizes distant disagreements (e.g. 0 vs 3)
    proportionally more than adjacent ones (e.g. 2 vs 3), per PR-E spec §7."""
    n = len(labels_a)
    confusion = [[0] * _NUM_GRADES for _ in range(_NUM_GRADES)]
    for a, b in zip(labels_a, labels_b):
        confusion[a][b] += 1
    observed = np.array(confusion, dtype=float)

    row_marginals = observed.sum(axis=1)
    col_marginals = observed.sum(axis=0)
    expected = np.outer(row_marginals, col_marginals) / n

    weights = np.array(
        [[abs(i - j) / (_NUM_GRADES - 1) for j in range(_NUM_GRADES)] for i in range(_NUM_GRADES)]
    )

    weighted_observed_disagreement = float((weights * observed).sum())
    weighted_expected_disagreement = float((weights * expected).sum())
    if weighted_expected_disagreement == 0:
        return 1.0, confusion
    kappa = 1.0 - (weighted_observed_disagreement / weighted_expected_disagreement)
    return kappa, confusion


def _binary_kappa(labels_a: list[int], labels_b: list[int]) -> float:
    """Simple (unweighted) Cohen's kappa over the derived relevant_binary = grade >= 2 view."""
    n = len(labels_a)
    bin_a = [1 if g >= 2 else 0 for g in labels_a]
    bin_b = [1 if g >= 2 else 0 for g in labels_b]
    observed_agreement = sum(1 for a, b in zip(bin_a, bin_b) if a == b) / n

    p_a1 = sum(bin_a) / n
    p_b1 = sum(bin_b) / n
    expected_agreement = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)

    if expected_agreement == 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def compute_iaa(
    judgments_a: list[AnnotationJudgment],
    judgments_b: list[AnnotationJudgment],
) -> IAAReport:
    if not judgments_a or not judgments_b:
        raise ValueError("compute_iaa requires both judgments_a and judgments_b to be non-empty")

    annotators_a = {j.annotator_id for j in judgments_a}
    annotators_b = {j.annotator_id for j in judgments_b}
    if len(annotators_a) == 1 and annotators_a == annotators_b:
        raise ValueError(
            f"judgments_a and judgments_b are both from the same single annotator "
            f"({next(iter(annotators_a))!r}) — IAA requires two independent annotators"
        )

    keys_a = {(j.demand_id, j.publication_id) for j in judgments_a}
    keys_b = {(j.demand_id, j.publication_id) for j in judgments_b}
    if keys_a != keys_b:
        raise ValueError(
            "Both annotators must judge the same set of (demand_id, publication_id) pairs — "
            f"got {len(keys_a)} vs {len(keys_b)} pairs, symmetric difference: {keys_a ^ keys_b}"
        )

    by_key_a = {(j.demand_id, j.publication_id): j for j in judgments_a}
    by_key_b = {(j.demand_id, j.publication_id): j for j in judgments_b}

    ordered_keys = sorted(keys_a)
    labels_a = [int(by_key_a[k].grade) for k in ordered_keys]
    labels_b = [int(by_key_b[k].grade) for k in ordered_keys]

    weighted_kappa, confusion = _weighted_kappa(labels_a, labels_b)
    binary_kappa = _binary_kappa(labels_a, labels_b)

    disagreements = [
        Disagreement(demand_id=k[0], publication_id=k[1], grade_a=ga, grade_b=gb)
        for k, ga, gb in zip(ordered_keys, labels_a, labels_b)
        if ga != gb
    ]

    return IAAReport(
        weighted_kappa=weighted_kappa,
        binary_kappa=binary_kappa,
        confusion_matrix=confusion,
        disagreements=disagreements,
    )
