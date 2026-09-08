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

    # revalidate_instances="never": disagreements is built from Disagreement
    # instances we construct ourselves right above, never from untrusted input —
    # explicit per Sonar python:S8978, not relying on Pydantic's default.
    model_config = {"arbitrary_types_allowed": True, "revalidate_instances": "never"}


def _weighted_kappa(labels_a: list[int], labels_b: list[int]) -> tuple[float, list[list[int]]]:
    """Linear-weighted Cohen's kappa: penalizes distant disagreements (e.g. 0 vs 3)
    proportionally more than adjacent ones (e.g. 2 vs 3), per PR-E spec §7."""
    n = len(labels_a)
    confusion = [[0] * _NUM_GRADES for _ in range(_NUM_GRADES)]
    for a, b in zip(labels_a, labels_b, strict=True):
        confusion[a][b] += 1

    # n=0, or every judgment sharing the same grade (no expected variance to
    # divide by): kappa is mathematically undefined (0/0), not perfect
    # agreement. Report NaN rather than a misleading 1.0.
    if n == 0:
        return float("nan"), confusion
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
        return float("nan"), confusion
    kappa = 1.0 - (weighted_observed_disagreement / weighted_expected_disagreement)
    return kappa, confusion


def _binary_kappa(labels_a: list[int], labels_b: list[int]) -> float:
    """Simple (unweighted) Cohen's kappa over the derived relevant_binary = grade >= 2 view."""
    n = len(labels_a)
    if n == 0:
        return float("nan")
    bin_a = [1 if g >= 2 else 0 for g in labels_a]
    bin_b = [1 if g >= 2 else 0 for g in labels_b]
    count_a1 = sum(bin_a)
    count_b1 = sum(bin_b)
    observed_agreement = sum(1 for a, b in zip(bin_a, bin_b, strict=True) if a == b) / n

    # expected_agreement == 1.0 (the degenerate case) holds iff p_a1 == p_b1 AND
    # both are exactly 0 or exactly 1 -- i.e. both annotators are constant AND
    # constant at the SAME value (constant-but-different, e.g. A always 0 / B
    # always 1, gives expected_agreement == 0, a well-defined non-degenerate
    # kappa, not this case). Checked on the integer counts rather than the
    # derived float proportions to avoid a floating-point equality comparison
    # (Sonar python:S1244); exact by construction since p_a1/p_b1 are integers
    # divided by n.
    if count_a1 == count_b1 and count_a1 in (0, n):
        return float("nan")

    p_a1 = count_a1 / n
    p_b1 = count_b1 / n
    expected_agreement = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)
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
    if len(keys_a) != len(judgments_a):
        raise ValueError("judgments_a contains duplicate (demand_id, publication_id) judgments")
    if len(keys_b) != len(judgments_b):
        raise ValueError("judgments_b contains duplicate (demand_id, publication_id) judgments")
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
        for k, ga, gb in zip(ordered_keys, labels_a, labels_b, strict=True)
        if ga != gb
    ]

    return IAAReport(
        weighted_kappa=weighted_kappa,
        binary_kappa=binary_kappa,
        confusion_matrix=confusion,
        disagreements=disagreements,
    )
