import json

import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, CandidatePool, EligibilityReason, RetrievalMethod
from domain.models.patent import PatentDocument
from infrastructure.annotation.blind_export import build_annotation_batch, export_temporal_provenance


def _pool() -> CandidatePool:
    return CandidatePool(
        demand_id="D1",
        candidates=[
            Candidate(publication_id="ES-1", retrieval_scores={RetrievalMethod.LEXICAL: 0.9}),
            Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.CPC: 0.7}),
            Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.SEMANTIC: 0.5}),
        ],
    )


def _patents() -> dict[str, PatentDocument]:
    return {
        pub_id: PatentDocument(
            publication_id=pub_id,
            country_code="ES",
            doc_number=pub_id.split("-")[1],
            kind_code="A1",
            title=f"Title {pub_id}",
            abstract=f"Abstract {pub_id}",
            classifications_cpc=["C11D1/02"],
        )
        for pub_id in ("ES-1", "ES-2", "ES-3")
    }


def _demand() -> DemandSignal:
    return DemandSignal(demand_id="D1", title="Seeking X", description="Looking for Y")


class BlindExportTest:
    def test_should_exclude_retrieval_scores_from_export(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        serialized = batch.model_dump_json()
        assert "retrieval_scores" not in serialized
        assert "0.9" not in serialized and "0.7" not in serialized and "0.5" not in serialized

    def test_should_exclude_retrieval_method_from_export(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        serialized = batch.model_dump_json()
        assert "lexical" not in serialized
        assert "semantic" not in serialized
        assert "\"cpc\"" not in serialized  # RetrievalMethod.CPC value, not CPC classification codes

    def test_should_exclude_original_ranking_position(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        for entry in batch.entries:
            assert not hasattr(entry, "rank")
            assert not hasattr(entry, "position")

    def test_should_produce_identical_order_for_same_seed_and_pool(self):
        batch_a = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        batch_b = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        assert [e.publication_id for e in batch_a.entries] == [e.publication_id for e in batch_b.entries]

    def test_should_preserve_the_same_candidate_set_across_different_seeds(self):
        batch_a = build_annotation_batch(_pool(), _demand(), _patents(), seed=1)
        batch_b = build_annotation_batch(_pool(), _demand(), _patents(), seed=2)
        assert {e.publication_id for e in batch_a.entries} == {e.publication_id for e in batch_b.entries}

    def test_should_raise_when_pool_candidate_has_no_matching_patent(self):
        patents = _patents()
        del patents["ES-2"]
        with pytest.raises(KeyError, match="ES-2"):
            build_annotation_batch(_pool(), _demand(), patents, seed=42)


class ExportTemporalProvenanceTest:
    def test_should_roundtrip_publication_ids_and_reasons_exactly(self):
        temporal_reasons = {
            "ES-1": EligibilityReason.ELIGIBLE,
            "ES-2": EligibilityReason.TEMPORAL_UNKNOWN,
        }
        serialized = export_temporal_provenance(temporal_reasons)
        roundtripped = json.loads(serialized)
        assert roundtripped == {"ES-1": "eligible", "ES-2": "temporal_unknown"}
        assert set(roundtripped.keys()) == {"ES-1", "ES-2"}
