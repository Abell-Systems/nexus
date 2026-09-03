from typing import Any

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import (
    CandidatePool,
    MatchingPolicyConfig,
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
        demand: DemandRecord | DemandSignal,
        *,
        policy: MatchingPolicyConfig,
    ) -> MatchingResult:
        if not isinstance(demand, (DemandRecord, DemandSignal)):
            raise TypeError(
                f"Expected DemandRecord or DemandSignal, got {type(demand).__name__}"
            )
        if policy is None:
            raise ValueError("MatchingPolicyConfig must be explicitly provided to CandidateMatchingService.match()")

        # Operational limit is strictly governed by the injected policy (ADR 0004 / ADR 0005)
        limit = policy.operational_limits.retrieval_limit

        lexical_candidates = self._lexical_retriever.retrieve(demand, limit=limit)
        semantic_candidates = self._semantic_retriever.retrieve(demand, limit=limit)
        cpc_candidates = self._cpc_retriever.retrieve(demand, limit=limit)

        demand_id = demand.demand_id
        pool = CandidatePool.from_retrievals(
            demand_id=demand_id,
            lexical_candidates=lexical_candidates,
            semantic_candidates=semantic_candidates,
            cpc_candidates=cpc_candidates,
        )

        rankings: dict[str, list[RankedCandidate]] = {}
        for strategy_name, ranker in self._rankers.items():
            rankings[strategy_name] = ranker.rank(pool)

        metadata: dict[str, Any] = {
            "retrieval_limit": limit,
            "pool_size": len(pool.candidates),
            "lexical_count": len(lexical_candidates),
            "semantic_count": len(semantic_candidates),
            "cpc_count": len(cpc_candidates),
            "ranker_strategies": list(self._rankers.keys()),
            "policy_id": policy.policy_id,
            "policy_sha256": policy.policy_sha256,
        }

        return MatchingResult(
            demand_id=demand_id,
            pool=pool,
            rankings=rankings,
            metadata=metadata,
        )
