"""Clean Architecture implementation of EvidenceEvaluator under ADR 0004.

Evaluates MatchFeatures under a MatchingPolicyConfig to produce an auditable MatchAssessment:
- Determines EvidenceSufficiency (INELIGIBLE_TEMPORAL, INSUFFICIENT_EVIDENCE, PARTIAL, SUFFICIENT).
- Computes policy-weighted overall compatibility score over ADR 0016 fusion-transformed
  signals (raw features stay raw; the transform is a fusion-time view only).
- Categorizes MatchConfidence (STRONG, MODERATE, WEAK, NONE).
- Constructs transparent, explainable rationale reporting both raw and fused values.
- Seals provenance with policy_id, policy_version, policy_sha256, and fusion_transform_id.
"""

from domain.models.matching import (
    FUSION_LEX_K,
    FUSION_TRANSFORM_ID,
    EvidenceSufficiency,
    MatchAssessment,
    MatchConfidence,
    MatchFeatures,
    MatchingPolicyConfig,
)


def fuse_lexical_score(raw_lexical: float) -> float:
    """ADR 0016 fusion view over raw BM25: x / (x + k), k = 1.0.

    Preserves f(0) = 0 ("no shared terms" stays zero signal), strictly increasing,
    saturating toward 1 without clamping, so high-signal pairs keep their order.
    """
    return raw_lexical / (raw_lexical + FUSION_LEX_K)


def fuse_semantic_score(raw_semantic: float) -> float:
    """ADR 0016 fusion view over raw cosine: (x + 1) / 2.

    Exact affine remap of cosine's true domain [-1, 1] onto [0, 1]; parameter-free.
    Matches the production retriever convention ((cos + 1) / 2).
    """
    return (raw_semantic + 1.0) / 2.0


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
        # ADR 0016 §3: active-signal counting reads RAW features. A raw cosine of
        # 0.0 (orthogonal) must not count as signal even though f_sem(0.0) = 0.5.
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
            # ADR 0016 §1-2: convex combination of [0, 1]-bounded fusion views, so
            # overall_score is structurally in [0, 1] for every possible input.
            # No clamping: bounding is a property of the transform's shape, and
            # ADR 0015 forbids clamping as a substitute for choosing one.
            w = policy.weights
            fused_lex = fuse_lexical_score(features.lexical_score)
            fused_sem = fuse_semantic_score(features.semantic_score)
            overall_score = round(
                w.alpha * fused_lex
                + w.beta * fused_sem
                + w.gamma * features.cpc_concordance,
                6,
            )

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
                f"lex_raw={features.lexical_score:.4f} lex_fused={fused_lex:.4f}, "
                f"sem_raw={features.semantic_score:.4f} sem_fused={fused_sem:.4f}, "
                f"cpc={features.cpc_concordance:.4f}, transform={FUSION_TRANSFORM_ID})"
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
            fusion_transform_id=FUSION_TRANSFORM_ID,
        )
