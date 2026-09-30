import numpy as np
import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import RetrievalMethod
from domain.models.patent import PatentDocument
from infrastructure.embeddings.embedding_texts import demand_embedding_text
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder, UnknownEmbeddingTextError
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy
from infrastructure.matching.numpy_dense import NumpyDenseRetriever


def _patent(pub_id: str, country: str = "ES", published: str = "2020-01-01") -> PatentDocument:
    return PatentDocument(
        publication_id=pub_id,
        country_code=country,
        doc_number=pub_id.split("-")[1],
        kind_code="A1",
        title=f"Title {pub_id}",
        abstract=f"Abstract {pub_id}",
        publication_date=published,
    )


def _demand(posted_date: str | None = "2022-01-01") -> DemandSignal:
    return DemandSignal(
        demand_id="INNOGET-1",
        title="Lighter vehicles",
        description="Seeking new materials",
        posted_date=posted_date,
    )


def _retriever(patents, matrix, demand_vector, demand=None):
    demand = demand or _demand()
    text = demand_embedding_text(demand.title, demand.description)
    return NumpyDenseRetriever(
        patents=patents,
        matrix=np.asarray(matrix, dtype=np.float32),
        embedder=PrecomputedEmbedder({text: demand_vector}),
        eligibility_policy=DefaultPatentEligibilityPolicy(target_jurisdiction="ES"),
    )


ROWS = [[1.0, 0.0], [0.0, 1.0], [0.6, 0.8]]


class NumpyDenseRetrieverTest:
    def test_should_rank_by_cosine_descending_when_demand_aligned_with_one_patent(self):
        patents = [_patent("ES-1-A1"), _patent("ES-2-A1"), _patent("ES-3-A1")]
        result = _retriever(patents, ROWS, [0.0, 1.0]).retrieve(_demand(), limit=3)
        assert [c.publication_id for c in result] == ["ES-2-A1", "ES-3-A1", "ES-1-A1"]

    def test_should_score_as_half_cosine_plus_half_when_ranking(self):
        patents = [_patent("ES-1-A1"), _patent("ES-2-A1"), _patent("ES-3-A1")]
        result = _retriever(patents, ROWS, [0.0, 1.0]).retrieve(_demand(), limit=3)
        scores = {c.publication_id: c.retrieval_scores[RetrievalMethod.SEMANTIC] for c in result}
        assert scores["ES-2-A1"] == pytest.approx(1.0)
        assert scores["ES-3-A1"] == pytest.approx(round((0.8 + 1.0) / 2.0, 6))
        assert scores["ES-1-A1"] == pytest.approx(0.5)

    def test_should_break_ties_by_publication_id_ascending_when_scores_are_equal(self):
        patents = [_patent("ES-9-A1"), _patent("ES-2-A1")]
        result = _retriever(patents, [[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0]).retrieve(_demand(), limit=2)
        assert [c.publication_id for c in result] == ["ES-2-A1", "ES-9-A1"]

    def test_should_return_identical_ranking_when_called_twice(self):
        patents = [_patent("ES-1-A1"), _patent("ES-2-A1"), _patent("ES-3-A1")]
        retriever = _retriever(patents, ROWS, [0.6, 0.8])
        assert retriever.retrieve(_demand(), limit=3) == retriever.retrieve(_demand(), limit=3)

    def test_should_truncate_to_limit_when_more_eligible_patents_than_limit(self):
        patents = [_patent("ES-1-A1"), _patent("ES-2-A1"), _patent("ES-3-A1")]
        result = _retriever(patents, ROWS, [0.0, 1.0]).retrieve(_demand(), limit=2)
        assert len(result) == 2

    def test_should_exclude_non_es_jurisdiction_when_country_is_ep(self):
        patents = [_patent("EP-1-A1", country="EP"), _patent("ES-2-A1")]
        result = _retriever(patents, [[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0]).retrieve(_demand(), limit=5)
        assert [c.publication_id for c in result] == ["ES-2-A1"]

    def test_should_exclude_patents_published_after_demand_when_temporal_rule_applies(self):
        patents = [_patent("ES-1-A1", published="2023-05-01"), _patent("ES-2-A1", published="2021-05-01")]
        result = _retriever(patents, [[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0]).retrieve(_demand("2022-01-01"), limit=5)
        assert [c.publication_id for c in result] == ["ES-2-A1"]

    def test_should_return_empty_list_when_no_patent_is_eligible(self):
        patents = [_patent("ES-1-A1", published="2024-01-01")]
        assert _retriever(patents, [[1.0, 0.0]], [1.0, 0.0]).retrieve(_demand("2022-01-01"), limit=5) == []

    def test_should_return_fewer_than_limit_when_eligible_set_is_small(self):
        patents = [_patent("ES-1-A1"), _patent("EP-2-A1", country="EP")]
        result = _retriever(patents, [[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0]).retrieve(_demand(), limit=5)
        assert len(result) == 1

    def test_should_raise_value_error_when_patent_count_and_matrix_rows_differ(self):
        with pytest.raises(ValueError, match="rows"):
            _retriever([_patent("ES-1-A1")], ROWS, [1.0, 0.0])

    def test_should_raise_value_error_when_demand_vector_dimension_differs_from_matrix(self):
        patents = [_patent("ES-1-A1")]
        with pytest.raises(ValueError, match="dimension"):
            _retriever(patents, [[1.0, 0.0]], [1.0, 0.0, 0.0]).retrieve(_demand(), limit=5)

    def test_should_raise_unknown_text_when_demand_was_not_embedded_offline(self):
        patents = [_patent("ES-1-A1")]
        retriever = _retriever(patents, [[1.0, 0.0]], [1.0, 0.0])
        other = DemandSignal(demand_id="X", title="Free text", description="typed by a user", posted_date="2022-01-01")
        with pytest.raises(UnknownEmbeddingTextError):
            retriever.retrieve(other, limit=5)

    def test_should_return_empty_list_when_demand_text_is_blank(self):
        patents = [_patent("ES-1-A1")]
        retriever = NumpyDenseRetriever(
            patents=patents,
            matrix=np.asarray([[1.0, 0.0]], dtype=np.float32),
            embedder=PrecomputedEmbedder({"unused": [1.0, 0.0]}),
            eligibility_policy=DefaultPatentEligibilityPolicy(target_jurisdiction="ES"),
        )
        blank = DemandSignal(demand_id="B", title=" ", description="", posted_date="2022-01-01")
        assert retriever.retrieve(blank, limit=5) == []
