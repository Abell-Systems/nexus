"""Clean Architecture implementation of MatchingFeatureExtractor under ADR 0004.

Extracts deterministic alignment features between a demand and a patent publication:
- Lexical similarity signal.
- Dense semantic vector similarity signal.
- CPC taxonomic concordance signal (evaluating maximum hierarchical concordance against policy levels).
- Temporal prior-art validation (delta days between demand posting and patent publication).
- Shared keyword overlap terms.
"""

from datetime import date
from typing import Any

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import (
    MatchFeatures,
    MatchingPolicyConfig,
    PatentCandidateEvidence,
    compute_cpc_symbol_similarity_from_levels,
)


def _parse_iso_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str.split("T")[0])
    except (ValueError, TypeError):
        return None


def extract_demand_context(
    demand: DemandRecord | DemandSignal,
) -> tuple[str, str, str, str | None, str | None]:
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
    raise TypeError(
        f"Expected DemandRecord or DemandSignal, got incompatible object of type {type(demand).__name__}"
    )


class DefaultMatchingFeatureExtractor:
    """Extracts multi-dimensional alignment features between a demand and a candidate patent."""

    def extract_candidate_features(
        self,
        demand: DemandRecord | DemandSignal,
        retrieval_scores: dict[Any, float],
        evidence: PatentCandidateEvidence | None,
        policy: MatchingPolicyConfig,
    ) -> MatchFeatures:
        """Computes MatchFeatures from demand, candidate retrieval scores, and candidate evidence."""
        _demand_id, _d_title, _d_desc, d_date_str, d_cpc_prefix = extract_demand_context(demand)
        d_date = _parse_iso_date(d_date_str)

        # 1. Temporal Prior-Art Evaluation
        p_date_str = evidence.publication_date if evidence else None
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

        s_lex = retrieval_scores.get(RetrievalMethod.LEXICAL, 0.0)
        s_sem = retrieval_scores.get(RetrievalMethod.SEMANTIC, 0.0)
        s_cpc = retrieval_scores.get(RetrievalMethod.CPC, 0.0)

        # 3. Evaluate CPC metadata concordance if present
        concordant_pairs: list[tuple[str, str]] = []
        if d_cpc_prefix and evidence and evidence.classifications_cpc:
            best_sim = 0.0
            best_pair = ("", "")
            for p_cpc in evidence.classifications_cpc:
                sim = compute_cpc_symbol_similarity_from_levels(
                    d_cpc_prefix, p_cpc, policy.cpc_concordance_levels
                )
                if sim > best_sim:
                    best_sim = sim
                    best_pair = (d_cpc_prefix, p_cpc)
            if best_sim > 0.0:
                s_cpc = max(s_cpc, best_sim)
                concordant_pairs.append(best_pair)

        shared_terms = evidence.shared_terms if evidence else ()

        return MatchFeatures(
            lexical_score=round(s_lex, 6),
            semantic_score=round(s_sem, 6),
            cpc_concordance=round(s_cpc, 6),
            temporal_valid=temporal_valid,
            delta_days=delta_days,
            shared_terms=shared_terms,
            concordant_cpc_pairs=tuple(concordant_pairs),
        )
