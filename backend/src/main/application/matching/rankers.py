from domain.models.matching import (
    CandidatePool,
    RankedCandidate,
    RankerWeights,
    RetrievalMethod,
)
from domain.protocols.matching import CandidateRanker

from .normalization import min_max_normalize


def _build_ranked_list(
    scored_items: list[tuple[str, float, dict[str, float]]],
) -> list[RankedCandidate]:
    """Sorts items deterministically by (score DESC, publication_id ASC) and assigns 1-based ranks."""
    sorted_items = sorted(scored_items, key=lambda item: (-item[1], item[0]))
    return [
        RankedCandidate(
            publication_id=pub_id,
            rank=idx + 1,
            score=score,
            components=components,
        )
        for idx, (pub_id, score, components) in enumerate(sorted_items)
    ]


class LexicalRanker(CandidateRanker):
    """Ranks candidates in the pool exclusively by their lexical retrieval score."""

    def rank(self, pool: CandidatePool) -> list[RankedCandidate]:
        raw_scores = {
            c.publication_id: c.retrieval_scores.get(RetrievalMethod.LEXICAL, 0.0)
            for c in pool.candidates
        }
        normalized = min_max_normalize(raw_scores)
        scored_items = [
            (
                c.publication_id,
                normalized[c.publication_id],
                {
                    "raw_lexical": raw_scores[c.publication_id],
                    "norm_lexical": normalized[c.publication_id],
                },
            )
            for c in pool.candidates
        ]
        return _build_ranked_list(scored_items)


class SemanticRanker(CandidateRanker):
    """Ranks candidates in the pool exclusively by their semantic retrieval score."""

    def rank(self, pool: CandidatePool) -> list[RankedCandidate]:
        scored_items = [
            (
                c.publication_id,
                c.retrieval_scores.get(RetrievalMethod.SEMANTIC, 0.0),
                {"semantic": c.retrieval_scores.get(RetrievalMethod.SEMANTIC, 0.0)},
            )
            for c in pool.candidates
        ]
        return _build_ranked_list(scored_items)


class CPCRanker(CandidateRanker):
    """Ranks candidates in the pool exclusively by their taxonomic CPC concordance score."""

    def rank(self, pool: CandidatePool) -> list[RankedCandidate]:
        scored_items = [
            (
                c.publication_id,
                c.retrieval_scores.get(RetrievalMethod.CPC, 0.0),
                {"cpc": c.retrieval_scores.get(RetrievalMethod.CPC, 0.0)},
            )
            for c in pool.candidates
        ]
        return _build_ranked_list(scored_items)


class HybridRanker(CandidateRanker):
    """Ranks candidates in the pool via linear combination: S_hybrid = alpha*S_lex + beta*S_sem + gamma*S_cpc.

    Invariants:
    - S_lex is min-max normalized across the candidate pool.
    - Missing retrieval signals default strictly to 0.0.
    - Ties broken deterministically by publication_id ASC.
    """

    def __init__(self, weights: RankerWeights) -> None:
        self._weights = weights

    @property
    def weights(self) -> RankerWeights:
        return self._weights

    def rank(self, pool: CandidatePool) -> list[RankedCandidate]:
        raw_lexical = {
            c.publication_id: c.retrieval_scores.get(RetrievalMethod.LEXICAL, 0.0)
            for c in pool.candidates
        }
        norm_lexical = min_max_normalize(raw_lexical)

        scored_items: list[tuple[str, float, dict[str, float]]] = []
        for c in pool.candidates:
            pub_id = c.publication_id
            s_lex = norm_lexical.get(pub_id, 0.0)
            s_sem = c.retrieval_scores.get(RetrievalMethod.SEMANTIC, 0.0)
            s_cpc = c.retrieval_scores.get(RetrievalMethod.CPC, 0.0)

            hybrid_score = (
                self._weights.alpha * s_lex
                + self._weights.beta * s_sem
                + self._weights.gamma * s_cpc
            )

            components = {
                "alpha": self._weights.alpha,
                "beta": self._weights.beta,
                "gamma": self._weights.gamma,
                "norm_lexical": s_lex,
                "semantic": s_sem,
                "cpc": s_cpc,
            }
            scored_items.append((pub_id, round(hybrid_score, 6), components))

        return _build_ranked_list(scored_items)
