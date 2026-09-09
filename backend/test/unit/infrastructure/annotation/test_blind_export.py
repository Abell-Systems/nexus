import json
import re
from pathlib import Path

import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, CandidatePool, EligibilityReason, RetrievalMethod
from domain.models.patent import PatentDocument
from infrastructure.annotation.blind_export import (
    BlindedAnnotationSet,
    build_annotation_batch,
    export_temporal_provenance,
    generate_blinded_annotation_set,
)


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


class BlindExportOrderingTest:
    def test_should_produce_identical_batch_regardless_of_candidate_input_order(self):
        pool_forward = CandidatePool(
            demand_id="D1",
            candidates=[
                Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.LEXICAL: 0.5}),
                Candidate(publication_id="ES-1", retrieval_scores={RetrievalMethod.LEXICAL: 0.9}),
                Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.LEXICAL: 0.7}),
            ],
        )
        pool_reverse = CandidatePool(
            demand_id="D1",
            candidates=[
                Candidate(publication_id="ES-1", retrieval_scores={RetrievalMethod.LEXICAL: 0.9}),
                Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.LEXICAL: 0.7}),
                Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.LEXICAL: 0.5}),
            ],
        )
        batch_a = build_annotation_batch(pool_forward, _demand(), _patents(), seed=42)
        batch_b = build_annotation_batch(pool_reverse, _demand(), _patents(), seed=42)
        assert [e.publication_id for e in batch_a.entries] == [e.publication_id for e in batch_b.entries]
        assert batch_a.model_dump_json() == batch_b.model_dump_json()


class BlindedAnnotationSetModelTest:
    def test_should_require_explicit_schema_version_and_mandatory_provenance(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        annotation_set = BlindedAnnotationSet(
            schema_version="1.0.0",
            dataset_id="nexus-pilot-16-evaluation-corpus-v1",
            dataset_sha256="bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453",
            temporal_pool_mode="strict",
            seed=42,
            demands=[batch],
        )
        assert annotation_set.schema_version == "1.0.0"
        assert annotation_set.temporal_pool_mode == "strict"
        assert len(annotation_set.demands) == 1
        assert not hasattr(annotation_set, "created_at")

    def test_should_reject_empty_schema_version_or_mismatched_sha_length(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        with pytest.raises(ValueError):
            BlindedAnnotationSet(
                schema_version="",
                dataset_id="nexus-pilot-16-evaluation-corpus-v1",
                dataset_sha256="bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453",
                temporal_pool_mode="strict",
                seed=42,
                demands=[batch],
            )
        with pytest.raises(ValueError):
            BlindedAnnotationSet(
                schema_version="1.0.0",
                dataset_id="nexus-pilot-16-evaluation-corpus-v1",
                dataset_sha256="short_hash",
                temporal_pool_mode="strict",
                seed=42,
                demands=[batch],
            )


class GenerateBlindedAnnotationSetTest:
    def test_should_fail_fast_if_benchmark_does_not_exist(self, tmp_path: Path):
        non_existent = tmp_path / "missing.json"
        with pytest.raises(FileNotFoundError, match="Benchmark dataset file not found"):
            generate_blinded_annotation_set(non_existent, temporal_pool_mode="strict", seed=42)

    def test_should_fail_fast_if_temporal_pool_mode_not_strict(self, tmp_path: Path):
        benchmark_file = tmp_path / "dummy.json"
        benchmark_file.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match="temporal_pool_mode must be 'strict'"):
            generate_blinded_annotation_set(benchmark_file, temporal_pool_mode="unconstrained", seed=42)

    def test_should_fail_fast_if_benchmark_sha256_mismatch(self, tmp_path: Path):
        benchmark_file = tmp_path / "corrupted.json"
        benchmark_file.write_text('{"dataset_id": "nexus-pilot-16"}', encoding="utf-8")
        with pytest.raises(ValueError, match="SHA-256 digest mismatch"):
            generate_blinded_annotation_set(
                benchmark_file,
                temporal_pool_mode="strict",
                seed=42,
                expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            )

    def test_should_derive_exact_eligible_sets_from_real_pilot_benchmark(self):
        real_benchmark = Path("data/evaluation/dataset_pilot_benchmark.json")
        if not real_benchmark.exists():
            pytest.skip("Benchmark file not present")

        result = generate_blinded_annotation_set(real_benchmark, temporal_pool_mode="strict", seed=42)

        assert result.schema_version == "1.0.0"
        assert result.dataset_id == "nexus-pilot-16-evaluation-corpus-v1"
        assert result.temporal_pool_mode == "strict"
        assert result.seed == 42
        assert len(result.demands) == 3

        demands_by_id = {d.demand_id: d for d in result.demands}
        assert set(demands_by_id.keys()) == {"INNOGET-2415", "INNOGET-2292", "INNOGET-2501"}

        # Exact candidate counts per demand
        assert len(demands_by_id["INNOGET-2415"].entries) == 12
        assert len(demands_by_id["INNOGET-2292"].entries) == 13
        assert len(demands_by_id["INNOGET-2501"].entries) == 13

        # Total candidate pairs = 38
        total_candidates = sum(len(d.entries) for d in result.demands)
        assert total_candidates == 38

        # Invariant: excluded publications must never appear
        pub_2415 = {e.publication_id for e in demands_by_id["INNOGET-2415"].entries}
        assert "ES-2856789-A1" not in pub_2415
        assert "ES-2895412-B1" not in pub_2415
        assert "ES-2901234-A1" not in pub_2415

        pub_2292 = {e.publication_id for e in demands_by_id["INNOGET-2292"].entries}
        assert "ES-2856789-A1" not in pub_2292
        assert "ES-2901234-A1" not in pub_2292
        assert "ES-2895412-B1" in pub_2292  # Eligible for 2292 (pub 2023-01-15 < demand 2023-02-15)

        pub_2501 = {e.publication_id for e in demands_by_id["INNOGET-2501"].entries}
        assert "ES-2856789-A1" not in pub_2501
        assert "ES-2901234-A1" not in pub_2501
        assert "ES-2895412-B1" in pub_2501


class StructuralBlindnessInvariantTest:
    def test_serialized_json_payload_must_not_contain_forbidden_keys(self):
        real_benchmark = Path("data/evaluation/dataset_pilot_benchmark.json")
        annotation_set = generate_blinded_annotation_set(real_benchmark, temporal_pool_mode="strict", seed=42)
        serialized = annotation_set.model_dump_json(indent=2)
        parsed = json.loads(serialized)

        forbidden_patterns = [
            r'"score"',
            r'"retrieval_scores"',
            r'"rank"',
            r'"position"',
            r'"retriever_id"',
            r'"retrieval_method"',
            r'"method"',
            r'"publication_date":\s*"[^"]+"',  # Non-null publication date string
        ]

        for pattern in forbidden_patterns:
            assert not re.search(pattern, serialized, re.IGNORECASE), f"Forbidden pattern {pattern} found in serialized JSON"

        # Verify entry structure
        for demand_batch in parsed["demands"]:
            assert "demand_id" in demand_batch
            assert "demand_title" in demand_batch
            assert "demand_description" in demand_batch
            for entry in demand_batch["entries"]:
                assert set(entry.keys()) == {"publication_id", "evidence"}
                evidence = entry["evidence"]
                assert "title" in evidence
                assert "abstract" in evidence
                assert "classifications_cpc" in evidence
                assert evidence.get("publication_date") is None

