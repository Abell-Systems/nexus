import pytest

from application.matching.rankers import (
    CPCRanker,
    HybridRanker,
    LexicalRanker,
    SemanticRanker,
)
from application.matching.service import CandidateMatchingService
from domain.models.demand import DemandSignal
from domain.models.matching import (
    Candidate,
    CandidatePool,
    RankedCandidate,
    RankerWeights,
    RetrievalMethod,
)
from domain.protocols.matching import (
    CandidateRanker,
    PatentCandidateRetriever,
)


class StubCandidateRetriever(PatentCandidateRetriever):
    """Stub returning a pre-configured list of candidates."""

    def __init__(self, candidates: list[Candidate]) -> None:
        self.candidates = candidates
        self.retrieve_call_count = 0
        self.received_demand: DemandSignal | None = None

    def retrieve(self, demand: DemandSignal, *, limit: int = 100) -> list[Candidate]:
        self.retrieve_call_count += 1
        self.received_demand = demand
        return self.candidates


class RecordingRanker(CandidateRanker):
    """Stub ranker recording the pool instance it received."""

    def __init__(self) -> None:
        self.received_pools: list[CandidatePool] = []

    def rank(self, pool: CandidatePool) -> list[RankedCandidate]:
        self.received_pools.append(pool)
        return [
            RankedCandidate(publication_id=c.publication_id, rank=idx + 1, score=1.0)
            for idx, c in enumerate(pool.candidates)
        ]


def test_matching_service_requires_all_retrievers_and_strategies():
    lex_stub = StubCandidateRetriever([])
    sem_stub = StubCandidateRetriever([])
    cpc_stub = StubCandidateRetriever([])

    # Missing a required strategy (e.g., hybrid)
    with pytest.raises(ValueError, match="Missing required ranking strategies"):
        CandidateMatchingService(
            lexical_retriever=lex_stub,
            semantic_retriever=sem_stub,
            cpc_retriever=cpc_stub,
            rankers={"lexical": RecordingRanker(), "semantic": RecordingRanker()},
        )


def test_matching_service_orchestrates_shared_pool_and_passes_identical_pool_to_all_rankers():
    c_lex1 = Candidate(publication_id="ES-1", retrieval_scores={RetrievalMethod.LEXICAL: 10.0})
    c_lex2 = Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.LEXICAL: 5.0})

    c_sem2 = Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.SEMANTIC: 0.9})
    c_sem3 = Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.SEMANTIC: 0.8})

    c_cpc3 = Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.CPC: 1.0})
    c_cpc4 = Candidate(publication_id="ES-4", retrieval_scores={RetrievalMethod.CPC: 0.5})

    lex_stub = StubCandidateRetriever([c_lex1, c_lex2])
    sem_stub = StubCandidateRetriever([c_sem2, c_sem3])
    cpc_stub = StubCandidateRetriever([c_cpc3, c_cpc4])

    lex_ranker = RecordingRanker()
    sem_ranker = RecordingRanker()
    cpc_ranker = RecordingRanker()
    hyb_ranker = RecordingRanker()

    service = CandidateMatchingService(
        lexical_retriever=lex_stub,
        semantic_retriever=sem_stub,
        cpc_retriever=cpc_stub,
        rankers={
            "lexical": lex_ranker,
            "semantic": sem_ranker,
            "cpc": cpc_ranker,
            "hybrid": hyb_ranker,
        },
    )

    demand = DemandSignal(
        demand_id="INNOGET-2292",
        source_network="InnoGet",
        title="Detergent Demand",
        description="Seeking biodegradable low temperature detergent",
        posted_date="2022-01-01",
    )

    result = service.match(demand)

    # Assert 1: Exactly 3 retriever calls with identical demand
    assert lex_stub.retrieve_call_count == 1
    assert sem_stub.retrieve_call_count == 1
    assert cpc_stub.retrieve_call_count == 1
    assert lex_stub.received_demand == demand
    assert sem_stub.received_demand == demand
    assert cpc_stub.received_demand == demand

    # Assert 2: CandidatePool is properly deduplicated into exactly 4 candidates
    assert len(result.pool.candidates) == 4
    expected_ids = ["ES-1", "ES-2", "ES-3", "ES-4"]
    assert [c.publication_id for c in result.pool.candidates] == expected_ids

    # Assert 3: All 4 rankers receive identical CandidatePool instance and IDs
    for ranker in (lex_ranker, sem_ranker, cpc_ranker, hyb_ranker):
        assert len(ranker.received_pools) == 1
        assert [c.publication_id for c in ranker.received_pools[0].candidates] == expected_ids

    # Assert 4: MatchingResult contains all 4 rankings
    for strat in ("lexical", "semantic", "cpc", "hybrid"):
        assert strat in result.rankings
        assert len(result.rankings[strat]) == 4


def test_real_rankers_on_shared_pool_with_missing_signals_and_ties():
    c1 = Candidate(
        publication_id="ES-A",
        retrieval_scores={RetrievalMethod.LEXICAL: 10.0, RetrievalMethod.SEMANTIC: 0.6},
    )
    c2 = Candidate(
        publication_id="ES-B",
        retrieval_scores={RetrievalMethod.SEMANTIC: 0.8, RetrievalMethod.CPC: 0.5},
    )
    c3 = Candidate(
        publication_id="ES-C",
        retrieval_scores={RetrievalMethod.CPC: 1.0},
    )
    pool = CandidatePool(demand_id="D1", candidates=[c1, c2, c3])

    weights = RankerWeights(alpha=0.35, beta=0.45, gamma=0.20)
    hybrid_ranker = HybridRanker(weights=weights)
    lex_ranker = LexicalRanker()
    sem_ranker = SemanticRanker()
    cpc_ranker = CPCRanker()

    lex_ranked = lex_ranker.rank(pool)
    sem_ranked = sem_ranker.rank(pool)
    cpc_ranked = cpc_ranker.rank(pool)
    hybrid_ranked = hybrid_ranker.rank(pool)

    # Lexical: ES-A has raw 10.0, others have 0.0 -> normalized: ES-A=1.0, ES-B=0.0, ES-C=0.0
    assert [r.publication_id for r in lex_ranked] == ["ES-A", "ES-B", "ES-C"]
    assert lex_ranked[0].score == 1.0
    assert lex_ranked[1].score == 0.0

    # Semantic: ES-B has 0.8, ES-A has 0.6, ES-C has 0.0
    assert [r.publication_id for r in sem_ranked] == ["ES-B", "ES-A", "ES-C"]
    assert sem_ranked[0].score == 0.8

    # CPC: ES-C has 1.0, ES-B has 0.5, ES-A has 0.0
    assert [r.publication_id for r in cpc_ranked] == ["ES-C", "ES-B", "ES-A"]

    # Hybrid:
    # ES-A: 0.35*1.0 + 0.45*0.6 + 0.20*0.0 = 0.35 + 0.27 + 0 = 0.62
    # ES-B: 0.35*0.0 + 0.45*0.8 + 0.20*0.5 = 0.00 + 0.36 + 0.10 = 0.46
    # ES-C: 0.35*0.0 + 0.45*0.0 + 0.20*1.0 = 0.00 + 0.00 + 0.20 = 0.20
    assert [r.publication_id for r in hybrid_ranked] == ["ES-A", "ES-B", "ES-C"]
    assert hybrid_ranked[0].score == 0.62
    assert hybrid_ranked[1].score == 0.46
    assert hybrid_ranked[2].score == 0.20
    assert hybrid_ranked[0].components["norm_lexical"] == 1.0
    assert hybrid_ranked[0].components["cpc"] == 0.0
