import duckdb
import pytest

from application.matching.candidate_pool_builder import CandidatePoolBuilder
from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, EligibilityReason, RetrievalMethod
from domain.protocols.matching import PatentEligibilityPolicy


class _FakeRetriever:
    def __init__(self, method: RetrievalMethod, results: dict[str, float]):
        self._method = method
        self._results = results

    def retrieve(self, demand, *, limit: int = 100) -> list[Candidate]:
        return [
            Candidate(publication_id=pub_id, retrieval_scores={self._method: score})
            for pub_id, score in list(self._results.items())[:limit]
        ]


class _AllEligiblePolicy(PatentEligibilityPolicy):
    def evaluate(self, patent, demand):
        from domain.models.matching import EligibilityResult

        return EligibilityResult(
            publication_id=patent.publication_id,
            is_eligible=True,
            reason=EligibilityReason.ELIGIBLE,
        )


class _ExcludeOnePolicy(PatentEligibilityPolicy):
    def __init__(self, excluded_id: str):
        self._excluded_id = excluded_id

    def evaluate(self, patent, demand):
        from domain.models.matching import EligibilityResult

        if patent.publication_id == self._excluded_id:
            return EligibilityResult(
                publication_id=patent.publication_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_TEMPORAL,
            )
        return EligibilityResult(
            publication_id=patent.publication_id,
            is_eligible=True,
            reason=EligibilityReason.ELIGIBLE,
        )


class _UnknownForOnePolicy(PatentEligibilityPolicy):
    def __init__(self, unknown_id: str):
        self._unknown_id = unknown_id

    def evaluate(self, patent, demand):
        from domain.models.matching import EligibilityResult

        reason = (
            EligibilityReason.TEMPORAL_UNKNOWN
            if patent.publication_id == self._unknown_id
            else EligibilityReason.ELIGIBLE
        )
        return EligibilityResult(publication_id=patent.publication_id, is_eligible=True, reason=reason)


@pytest.fixture
def memory_duckdb_two_patents():
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE patents (
            publication_id VARCHAR PRIMARY KEY,
            country_code VARCHAR,
            doc_number VARCHAR,
            kind_code VARCHAR,
            title VARCHAR,
            abstract VARCHAR,
            publication_date VARCHAR
        )
        """
    )
    con.execute(
        "INSERT INTO patents VALUES "
        "('ES-3001', 'ES', '3001', 'A1', 'Title A', 'Abstract A', '2021-01-01'), "
        "('ES-3002', 'ES', '3002', 'A1', 'Title B', 'Abstract B', '2021-02-01')"
    )
    yield con
    con.close()


class CandidatePoolBuilderTest:
    def test_should_union_candidates_across_retrievers_without_duplicating(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9, "ES-3002": 0.5})
        cpc = _FakeRetriever(RetrievalMethod.CPC, {"ES-3001": 0.7})
        builder = CandidatePoolBuilder(
            retrievers=[bm25, cpc],
            eligibility_policy=_AllEligiblePolicy(),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D1", title="t", description="d"))
        assert {c.publication_id for c in result.pool.candidates} == {"ES-3001", "ES-3002"}

    def test_should_merge_retrieval_scores_from_multiple_methods_for_same_candidate(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9})
        cpc = _FakeRetriever(RetrievalMethod.CPC, {"ES-3001": 0.7})
        builder = CandidatePoolBuilder(
            retrievers=[bm25, cpc],
            eligibility_policy=_AllEligiblePolicy(),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D1", title="t", description="d"))
        merged = next(c for c in result.pool.candidates if c.publication_id == "ES-3001")
        assert merged.retrieval_scores == {RetrievalMethod.LEXICAL: 0.9, RetrievalMethod.CPC: 0.7}

    def test_should_tag_temporal_reason_per_candidate(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9, "ES-3002": 0.5})
        builder = CandidatePoolBuilder(
            retrievers=[bm25],
            eligibility_policy=_UnknownForOnePolicy(unknown_id="ES-3002"),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D1", title="t", description="d"))
        assert result.temporal_reasons["ES-3001"] == EligibilityReason.ELIGIBLE
        assert result.temporal_reasons["ES-3002"] == EligibilityReason.TEMPORAL_UNKNOWN

    def test_should_exclude_excluded_temporal_candidate_from_final_pool(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9, "ES-3002": 0.5})
        builder = CandidatePoolBuilder(
            retrievers=[bm25],
            eligibility_policy=_ExcludeOnePolicy(excluded_id="ES-3002"),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D1", title="t", description="d"))
        assert {c.publication_id for c in result.pool.candidates} == {"ES-3001"}
        assert "ES-3002" not in result.temporal_reasons
        assert result.temporal_reasons["ES-3001"] == EligibilityReason.ELIGIBLE

    def test_should_reject_empty_retriever_list(self, memory_duckdb_two_patents):
        with pytest.raises(ValueError, match="at least one retriever"):
            CandidatePoolBuilder(
                retrievers=[],
                eligibility_policy=_AllEligiblePolicy(),
                connection=memory_duckdb_two_patents,
            )

    def test_should_fail_fast_when_retriever_returns_id_missing_from_patents_table(
        self, memory_duckdb_two_patents
    ):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-9999": 0.9})
        builder = CandidatePoolBuilder(
            retrievers=[bm25],
            eligibility_policy=_AllEligiblePolicy(),
            connection=memory_duckdb_two_patents,
        )
        with pytest.raises(ValueError, match="ES-9999"):
            builder.build(DemandSignal(demand_id="D1", title="t", description="d"))

    def test_should_stamp_demand_id_on_pool(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9})
        builder = CandidatePoolBuilder(
            retrievers=[bm25],
            eligibility_policy=_AllEligiblePolicy(),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D42", title="t", description="d"))
        assert result.pool.demand_id == "D42"
