"""Clean Architecture implementation of MatchingEngine under ADR 0004.

Invariants:
- Evaluates candidate pool against a demand document under MatchingPolicyConfig.
- Decouples feature extraction, sufficiency determination, scoring, and explainable assessment.
- Adheres strictly to single source of truth: weights, concordance levels, and sufficiency rules come from policy.
- Zero in-code policy defaults; zero synthetic fallback inventions.
- Strict determinism: ties broken deterministically by publication_id ASC.
"""

from datetime import date
from typing import Any

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import (
    CandidatePool,
    EvidenceSufficiency,
    MatchAssessment,
    MatchConfidence,
    MatchFeatures,
    MatchingPolicyConfig,
    compute_cpc_symbol_similarity_from_levels,
)
from domain.protocols.matching import MatchingEngine


def _parse_iso_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str.split("T")[0])
    except (ValueError, TypeError):
        return None


def _extract_demand_fields(demand: Any) -> tuple[str, str, str, str | None, str | None]:
    """Extracts (demand_id, title, description, posted_date, cpc_prefix) cleanly."""
    if isinstance(demand, DemandRecord):
        return (
            demand.demand_id,
            demand.title,
            demand.description,
            demand.posted_date,
            demand.cpc_prefix,
        )
    if isinstance(demand, DemandSignal):
        cpc = demand.classified_cpc_prefixes[0] if demand.classified_cpc_prefixes else None
        return (
            demand.demand_id,
            demand.title,
            demand.description,
            demand.posted_date,
            cpc,
        )
    # Generic attribute duck typing
    return (
        getattr(demand, "demand_id", str(getattr(demand, "id", ""))),
        getattr(demand, "title", ""),
        getattr(demand, "description", ""),
        getattr(demand, "posted_date", None),
        getattr(demand, "cpc_prefix", None),
    )


class DefaultMatchingEngine(MatchingEngine):
    """Reference implementation of MatchingEngine protocol."""

    def evaluate(
        self,
        demand: Any,
        candidates: CandidatePool,
        policy: MatchingPolicyConfig,
        patent_metadata: dict[str, dict[str, Any]] | None = None,
    ) -> list[MatchAssessment]:
        """Evaluates each candidate in the pool and produces an explainable MatchAssessment."""
        demand_id, d_title, d_desc, d_date_str, d_cpc_prefix = _extract_demand_fields(demand)
        d_date = _parse_iso_date(d_date_str)
        metadata_lookup = patent_metadata or {}

        assessments: list[MatchAssessment] = []

        for candidate in candidates.candidates:
            pub_id = candidate.publication_id
            scores = candidate.retrieval_scores
            p_meta = metadata_lookup.get(pub_id, {})

            # 1. Temporal Prior-Art Evaluation
            p_date_str = p_meta.get("publication_date")
            p_date = _parse_iso_date(p_date_str)
            delta_days: int | None = None
            temporal_valid = True

            if d_date and p_date:
                delta = (d_date - p_date).days
                delta_days = delta
                if delta <= 0 and policy.sufficiency_rules.require_temporal_validity:
                    temporal_valid = False

            # 2. Extract alignment signals
            from domain.models.matching import RetrievalMethod
            s_lex = scores.get(RetrievalMethod.LEXICAL, 0.0)
            s_sem = scores.get(RetrievalMethod.SEMANTIC, 0.0)
            s_cpc = scores.get(RetrievalMethod.CPC, 0.0)

            # If candidate metadata contains CPCs, compute concordance using policy levels
            p_cpcs = p_meta.get("classifications_cpc", [])
            concordant_pairs: list[tuple[str, str]] = []
            if d_cpc_prefix and p_cpcs:
                best_sim = 0.0
                best_pair = ("", "")
                for p_cpc in p_cpcs:
                    sim = compute_cpc_symbol_similarity_from_levels(
                        d_cpc_prefix, p_cpc, policy.cpc_concordance_levels
                    )
                    if sim > best_sim:
                        best_sim = sim
                        best_pair = (d_cpc_prefix, p_cpc)
                if best_sim > 0.0:
                    s_cpc = max(s_cpc, best_sim)
                    concordant_pairs.append(best_pair)

            shared_terms = tuple(p_meta.get("shared_terms", ()))

            features = MatchFeatures(
                lexical_score=round(s_lex, 6),
                semantic_score=round(s_sem, 6),
                cpc_concordance=round(s_cpc, 6),
                temporal_valid=temporal_valid,
                delta_days=delta_days,
                shared_terms=shared_terms,
                concordant_cpc_pairs=tuple(concordant_pairs),
            )

            # 3. Determine Evidence Sufficiency and Score
            active_signals = sum(1 for s in (s_lex, s_sem, s_cpc) if s > 0.0)

            if not temporal_valid:
                sufficiency = EvidenceSufficiency.INELIGIBLE_TEMPORAL
                overall_score = 0.0
                confidence = MatchConfidence.NONE
                rationale = f"Patent publication date ({p_date_str}) is not prior art for demand date ({d_date_str})"
            elif active_signals < policy.sufficiency_rules.min_active_signals:
                sufficiency = EvidenceSufficiency.INSUFFICIENT_EVIDENCE
                overall_score = 0.0
                confidence = MatchConfidence.NONE
                rationale = "No measurable signals active across lexical, semantic, or taxonomic dimensions"
            else:
                sufficiency = (
                    EvidenceSufficiency.SUFFICIENT if active_signals >= 2 else EvidenceSufficiency.PARTIAL
                )
                w = policy.weights
                raw_score = w.alpha * s_lex + w.beta * s_sem + w.gamma * s_cpc
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
                    f"lex={s_lex:.4f}, sem={s_sem:.4f}, cpc={s_cpc:.4f})"
                )

            assessment = MatchAssessment(
                demand_id=demand_id,
                publication_id=pub_id,
                overall_score=overall_score,
                confidence=confidence,
                sufficiency=sufficiency,
                features=features,
                rationale=rationale,
                policy_id=policy.policy_id,
                policy_version=policy.policy_version,
                policy_sha256=policy.policy_sha256,
            )
            assessments.append(assessment)

        # Deterministic sorting: overall_score DESC, publication_id ASC
        assessments.sort(key=lambda a: (-a.overall_score, a.publication_id))
        return assessments
