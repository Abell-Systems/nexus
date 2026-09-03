"""Clean Architecture implementation of EvidenceEvaluator under ADR 0004.

Evaluates MatchFeatures under a MatchingPolicyConfig to produce an auditable MatchAssessment:
- Determines EvidenceSufficiency (INELIGIBLE_TEMPORAL, INSUFFICIENT_EVIDENCE, PARTIAL, SUFFICIENT).
- Computes policy-weighted overall compatibility score.
- Categorizes MatchConfidence (STRONG, MODERATE, WEAK, NONE).
- Constructs transparent, explainable rationale.
- Seals provenance with policy_id, policy_version, and policy_sha256.
"""

from domain.models.matching import (
    EvidenceSufficiency,
    MatchAssessment,
    MatchConfidence,
    MatchFeatures,
    MatchingPolicyConfig,
)


class DefaultEvidenceEvaluator:
    """Evaluates extracted alignment features against policy thresholds and sufficiency rules."""

    def evaluate_candidate(
        self,
        demand_id: str,
        publication_id: str,
        features: MatchFeatures,
        policy: MatchingPolicyConfig,
    ) -> MatchAssessment:
        """Constructs an auditable, explainable MatchAssessment from MatchFeatures and policy."""
        active_signals = sum(
            1 for s in (features.lexical_score, features.semantic_score, features.cpc_concordance) if s > 0.0
        )

        if not features.temporal_valid:
            sufficiency = EvidenceSufficiency.INELIGIBLE_TEMPORAL
            overall_score = 0.0
            confidence = MatchConfidence.NONE
            rationale = "Candidate publication date does not establish prior art for demand"
        elif active_signals < policy.sufficiency_rules.min_active_signals:
            sufficiency = EvidenceSufficiency.INSUFFICIENT_EVIDENCE
            overall_score = 0.0
            confidence = MatchConfidence.NONE
            rationale = "No measurable signals active across lexical, semantic, or taxonomic dimensions"
        else:
            is_sufficient = active_signals >= policy.sufficiency_rules.min_signals_for_sufficient
            sufficiency = (
                EvidenceSufficiency.SUFFICIENT if is_sufficient else EvidenceSufficiency.PARTIAL
            )
            w = policy.weights
            raw_score = (
                w.alpha * features.lexical_score
                + w.beta * features.semantic_score
                + w.gamma * features.cpc_concordance
            )
            overall_score = round(raw_score, 6)

            thresh = policy.confidence_thresholds
            if overall_score >= thresh.strong:
                confidence = MatchConfidence.STRONG
            elif overall_score >= thresh.moderate:
                confidence = MatchConfidence.MODERATE
            elif overall_score >= thresh.weak:
                confidence = MatchConfidence.WEAK
            else:
                confidence = MatchConfidence.NONE

            rationale = (
                f"Evidence assessment: overall={overall_score:.4f} (confidence={confidence.value}, "
                f"lex={features.lexical_score:.4f}, sem={features.semantic_score:.4f}, "
                f"cpc={features.cpc_concordance:.4f})"
            )

        return MatchAssessment(
            demand_id=demand_id,
            publication_id=publication_id,
            overall_score=overall_score,
            confidence=confidence,
            sufficiency=sufficiency,
            features=features,
            rationale=rationale,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            policy_sha256=policy.policy_sha256,
        )
