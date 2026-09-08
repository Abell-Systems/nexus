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
        assert "0.9" not in serialized
        assert "0.7" not in serialized
        assert "0.5" not in serialized

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

    def test_should_produce_byte_identical_serialized_artifact_for_same_seed_and_pool(self):
        """Spec §5 contract 3 literally says 'byte-identical export order' -- test
        the serialized artifact itself, not just the publication_id sequence
        (a weaker property that wouldn't catch e.g. a nondeterministic field
        ordering or value elsewhere in the model)."""
        batch_a = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        batch_b = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        assert batch_a.model_dump_json() == batch_b.model_dump_json()

    def test_should_preserve_the_same_candidate_set_across_different_seeds(self):
        batch_a = build_annotation_batch(_pool(), _demand(), _patents(), seed=1)
        batch_b = build_annotation_batch(_pool(), _demand(), _patents(), seed=2)
        assert {e.publication_id for e in batch_a.entries} == {e.publication_id for e in batch_b.entries}

    def test_should_raise_when_pool_candidate_has_no_matching_patent(self):
        patents = _patents()
        del patents["ES-2"]
        with pytest.raises(KeyError, match="ES-2"):
            build_annotation_batch(_pool(), _demand(), patents, seed=42)

    def test_should_exclude_publication_date_from_export(self):
        """Code review comment on PR #56: publication_date could let an annotator
        reconstruct temporal eligibility and contaminate a relevance judgment that
        is supposed to be purely technical. Uses a real, distinctive date so this
        test actually fails if the date leaks (the default fixture's None wouldn't
        catch a regression that starts passing a real date through)."""
        patents = _patents()
        for patent in patents.values():
            patent.publication_date = "2019-11-20"
        batch = build_annotation_batch(_pool(), _demand(), patents, seed=42)
        serialized = batch.model_dump_json()
        # PatentCandidateEvidence (a shared domain model) still has a
        # publication_date field/key that serializes as null -- the actual
        # boundary property is that the real DATE VALUE never crosses, not that
        # the key is absent.
        assert "2019-11-20" not in serialized
        for entry in batch.entries:
            assert entry.evidence.publication_date is None


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

    def test_should_never_appear_in_annotation_batch_serialization(self):
        """Explicit boundary test (code review comment on PR #56): the temporal
        provenance produced by export_temporal_provenance() must never be
        reachable through AnnotationBatch — not just "happens to be a separate
        function today". Builds a batch and provenance from the SAME pool/reasons
        and confirms none of the provenance's EligibilityReason values leak into
        the annotator-facing batch's serialized form."""
        pool = _pool()
        temporal_reasons = {
            "ES-1": EligibilityReason.ELIGIBLE,
            "ES-2": EligibilityReason.TEMPORAL_UNKNOWN,
            "ES-3": EligibilityReason.ELIGIBLE,
        }

        batch = build_annotation_batch(pool, _demand(), _patents(), seed=42)
        provenance = export_temporal_provenance(temporal_reasons)

        batch_serialized = batch.model_dump_json()
        assert "temporal_unknown" not in batch_serialized
        assert "eligible" not in batch_serialized
        assert "excluded_temporal" not in batch_serialized
        assert provenance not in batch_serialized

        # And structurally: no field on AnnotationBatch or AnnotationCandidateEntry
        # is even shaped to carry an EligibilityReason.
        batch_field_names = set(type(batch).model_fields.keys())
        entry_field_names = set(type(batch.entries[0]).model_fields.keys()) if batch.entries else set()
        assert "temporal_reasons" not in batch_field_names
        assert "eligibility_reason" not in batch_field_names
        assert "temporal_reasons" not in entry_field_names
        assert "eligibility_reason" not in entry_field_names
