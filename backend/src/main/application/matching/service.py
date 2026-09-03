from typing import Any

from domain.models.demand import DemandSignal
from domain.models.matching import (
    CandidatePool,
    MatchingResult,
    RankedCandidate,
)
from domain.protocols.matching import (
    CandidateRanker,
    PatentCandidateRetriever,
)

REQUIRED_RANKER_STRATEGIES = {"lexical", "semantic", "cpc", "hybrid"}


class CandidateMatchingService:
    """Orchestrates Stage 1 Retrieval into a shared candidate pool and Stage 2 Ranking over that fixed pool."""

    def __init__(
        self,
        lexical_retriever: PatentCandidateRetriever,
        semantic_retriever: PatentCandidateRetriever,
        cpc_retriever: PatentCandidateRetriever,
        rankers: dict[str, CandidateRanker],
    ) -> None:
        if not lexical_retriever or not semantic_retriever or not cpc_retriever:
            raise ValueError("All three retrievers (lexical, semantic, cpc) must be provided")

        missing_strategies = REQUIRED_RANKER_STRATEGIES - set(rankers.keys())
        if missing_strategies:
            raise ValueError(f"Missing required ranking strategies: {missing_strategies}")

        self._lexical_retriever = lexical_retriever
        self._semantic_retriever = semantic_retriever
        self._cpc_retriever = cpc_retriever
        self._rankers = rankers

    def match(
        self,
        demand: DemandSignal,
        *,
        retrieval_limit: int = 100,
    ) -> MatchingResult:
        lexical_candidates = self._lexical_retriever.retrieve(demand, limit=retrieval_limit)
        semantic_candidates = self._semantic_retriever.retrieve(demand, limit=retrieval_limit)
        cpc_candidates = self._cpc_retriever.retrieve(demand, limit=retrieval_limit)

        pool = CandidatePool.from_retrievals(
            demand_id=demand.demand_id,
            lexical_candidates=lexical_candidates,
            semantic_candidates=semantic_candidates,
            cpc_candidates=cpc_candidates,
        )

        rankings: dict[str, list[RankedCandidate]] = {}
        for strategy_name, ranker in self._rankers.items():
            rankings[strategy_name] = ranker.rank(pool)

        metadata: dict[str, Any] = {
            "retrieval_limit": retrieval_limit,
            "pool_size": len(pool.candidates),
            "lexical_count": len(lexical_candidates),
            "semantic_count": len(semantic_candidates),
            "cpc_count": len(cpc_candidates),
            "ranker_strategies": list(self._rankers.keys()),
        }

        return MatchingResult(
            demand_id=demand.demand_id,
            pool=pool,
            rankings=rankings,
            metadata=metadata,
        )
