"""Two-gate validation check for the TED construct-validity classifier, per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS8. Pure logic, no I/O."""

from dataclasses import dataclass

from domain.models.corpus_expansion import TechnicalProblemClassification


@dataclass(frozen=True)
class GateResult:
    passed: bool
    recall_technical_problem: float
    specificity_generic_procurement: float
    boundary_false_positives: tuple[str, ...]
    reason: str


def evaluate_validation_gate(
    reference_labels: dict[str, TechnicalProblemClassification],
    llm_labels: dict[str, TechnicalProblemClassification],
    boundary_ids: frozenset[str],
    *,
    recall_threshold: float = 0.90,
    specificity_threshold: float = 0.90,
) -> GateResult:
    """Gate A (statistical recall/specificity >= thresholds) AND Gate B (zero
    GENERIC_PROCUREMENT -> TECHNICAL_PROBLEM misclassifications within
    boundary_ids). Both must pass for the overall result to pass."""
    if set(reference_labels) != set(llm_labels):
        raise ValueError("reference_labels and llm_labels must cover the same demand_ids")

    tp_ids = {d for d, c in reference_labels.items() if c == TechnicalProblemClassification.TECHNICAL_PROBLEM}
    gp_ids = {d for d, c in reference_labels.items() if c == TechnicalProblemClassification.GENERIC_PROCUREMENT}

    recall = (
        sum(1 for d in tp_ids if llm_labels[d] == TechnicalProblemClassification.TECHNICAL_PROBLEM) / len(tp_ids)
        if tp_ids else 1.0
    )
    specificity = (
        sum(1 for d in gp_ids if llm_labels[d] != TechnicalProblemClassification.TECHNICAL_PROBLEM) / len(gp_ids)
        if gp_ids else 1.0
    )

    boundary_false_positives = tuple(sorted(
        d for d in gp_ids
        if d in boundary_ids and llm_labels[d] == TechnicalProblemClassification.TECHNICAL_PROBLEM
    ))

    gate_a = recall >= recall_threshold and specificity >= specificity_threshold
    gate_b = len(boundary_false_positives) == 0

    if gate_a and gate_b:
        reason = "Both gates passed: classifier approved for full-population classification."
    elif not gate_b:
        reason = (
            f"Gate B (boundary safety) failed: {len(boundary_false_positives)} "
            f"GENERIC_PROCUREMENT boundary case(s) misclassified as TECHNICAL_PROBLEM: "
            f"{list(boundary_false_positives)}. Escalate to full manual classification."
        )
    else:
        reason = (
            f"Gate A (statistical) failed: recall={recall:.3f} (threshold {recall_threshold}), "
            f"specificity={specificity:.3f} (threshold {specificity_threshold}). "
            "Escalate to full manual classification."
        )

    return GateResult(
        passed=gate_a and gate_b,
        recall_technical_problem=recall,
        specificity_generic_procurement=specificity,
        boundary_false_positives=boundary_false_positives,
        reason=reason,
    )
