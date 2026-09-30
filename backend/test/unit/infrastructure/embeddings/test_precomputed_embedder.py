import pytest

from infrastructure.embeddings.embedding_texts import demand_embedding_text, patent_embedding_text
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder, UnknownEmbeddingTextError


class EmbeddingTextsTest:
    def test_should_join_title_and_description_with_single_space_when_both_present(self):
        assert demand_embedding_text("Lighter vehicles", "Seeking new materials") == "Lighter vehicles Seeking new materials"

    def test_should_strip_outer_whitespace_when_description_is_empty(self):
        assert demand_embedding_text("Lighter vehicles", "") == "Lighter vehicles"

    def test_should_return_empty_string_when_title_and_description_are_blank(self):
        assert demand_embedding_text("  ", "") == ""

    def test_should_join_title_and_abstract_when_both_present(self):
        assert patent_embedding_text("Smart sink", "Sensor and thermal control") == "Smart sink Sensor and thermal control"


class PrecomputedEmbedderTest:
    def test_should_return_stored_vector_when_text_is_known(self):
        embedder = PrecomputedEmbedder({"alpha text": [1.0, 0.0], "beta text": [0.0, 1.0]})
        assert embedder.embed("alpha text") == [1.0, 0.0]

    def test_should_return_copy_when_caller_mutates_result(self):
        embedder = PrecomputedEmbedder({"alpha text": [1.0, 0.0]})
        embedder.embed("alpha text").append(9.9)
        assert embedder.embed("alpha text") == [1.0, 0.0]

    def test_should_raise_unknown_text_when_text_differs_by_one_trailing_space(self):
        embedder = PrecomputedEmbedder({"alpha text": [1.0, 0.0]})
        with pytest.raises(UnknownEmbeddingTextError):
            embedder.embed("alpha text ")

    def test_should_raise_unknown_text_when_text_was_never_stored(self):
        embedder = PrecomputedEmbedder({"alpha text": [1.0, 0.0]})
        with pytest.raises(UnknownEmbeddingTextError):
            embedder.embed("free text typed by a user")

    def test_should_reject_construction_when_no_vectors_given(self):
        with pytest.raises(ValueError):
            PrecomputedEmbedder({})
