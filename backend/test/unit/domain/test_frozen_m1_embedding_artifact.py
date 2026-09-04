"""Guard tests for ADR 0014: frozen M1 semantic embedding artifact provenance."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from domain.models.evaluation import (
    EvaluationDataset,
    EvaluationDatasetManifest,
    FrozenEmbeddingArtifact,
    ValidatedDataset,
)

_VALID_REVISION = "4328cf26390c98c5e3c738b4460a05b95f4911f5"
_NORM_VEC_A = [0.5, 0.5, 0.5, 0.5]  # ||v||_2 == 1.0 exactly
_NORM_VEC_B = [0.6, 0.8, 0.0, 0.0]  # ||v||_2 == 1.0 exactly


def _make_artifact(**overrides: object) -> FrozenEmbeddingArtifact:
    defaults: dict[str, object] = {
        "artifact_id": "m1_embeddings_pilot_benchmark_v1",
        "frozen_at": date(2026, 9, 4),
        "model_name": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "model_revision": _VALID_REVISION,
        "license": "Apache-2.0",
        "generation_script_path": "scripts/generate_m1_embeddings.py",
        "generation_script_commit": "a" * 40,
        "library_versions": {
            "python": "3.12.3",
            "torch": "2.5.1+cpu",
            "transformers": "4.47.1",
            "sentence-transformers": "3.4.1",
        },
        "generation_device": "cpu",
        "dataset_sha256": "b" * 64,
        "embedding_dimension": 4,
        "normalization": "l2",
        "similarity_metric": "cosine",
        "demand_embeddings": {"D1": _NORM_VEC_A},
        "patent_embeddings": {"P1": _NORM_VEC_B},
        "artifact_sha256": "c" * 64,
    }
    defaults.update(overrides)
    return FrozenEmbeddingArtifact(**defaults)


def _validated_dataset(demand_ids: set[str], patent_ids: set[str], content_sha256: str) -> ValidatedDataset:
    demands = [
        {
            "demand_id": d_id,
            "title": "t",
            "description": "d",
            "provenance": {
                "source_authority": "test",
                "source_uri": "https://example.test/d",
                "extraction_timestamp": "2026-09-04T00:00:00Z",
                "raw_payload_sha256": "d" * 64,
                "modality": "observed",
            },
        }
        for d_id in demand_ids
    ]
    patents = [
        {
            "publication_id": p_id,
            "title": "t",
            "abstract": "a",
            "provenance": {
                "source_authority": "test",
                "source_uri": "https://example.test/p",
                "extraction_timestamp": "2026-09-04T00:00:00Z",
                "raw_payload_sha256": "e" * 64,
                "modality": "observed",
            },
        }
        for p_id in patent_ids
    ]
    dataset = EvaluationDataset(
        dataset_id="test_dataset",
        schema_version="1.0",
        dataset_version="1.0",
        description="test",
        demands=demands,
        patents=patents,
        annotations=[],
    )
    manifest = EvaluationDatasetManifest(
        dataset_id="test_dataset",
        schema_version="1.0",
        dataset_version="1.0",
        source_authorities=["test"],
        demand_count=len(demands),
        patent_count=len(patents),
        annotation_count=0,
        content_sha256=content_sha256,
    )
    return ValidatedDataset(dataset=dataset, manifest=manifest)


class FrozenM1EmbeddingArtifactTest:
    """Guards for FrozenEmbeddingArtifact (ADR 0014): the frozen artifact is the authority
    for M1 embeddings; verify_source_dataset checks it against an already-loaded,
    independently-verified ValidatedDataset — never the reverse.
    """

    def test_should_construct_when_valid(self) -> None:
        artifact = _make_artifact()
        assert artifact.embedding_dimension == 4
        assert artifact.generation_device == "cpu"

    def test_should_reject_when_model_revision_is_not_full_hex_sha(self) -> None:
        with pytest.raises(ValidationError, match="model_revision"):
            _make_artifact(model_revision="not-a-sha")

    def test_should_reject_when_generation_device_is_not_cpu(self) -> None:
        with pytest.raises(ValidationError):
            _make_artifact(generation_device="cuda")

    def test_should_reject_when_embedding_dimension_mismatches_stored_vector(self) -> None:
        with pytest.raises(ValidationError, match="dimension"):
            _make_artifact(demand_embeddings={"D1": [0.1, 0.2]})

    def test_should_reject_when_embedding_contains_non_finite_value(self) -> None:
        with pytest.raises(ValidationError, match="non-finite"):
            _make_artifact(demand_embeddings={"D1": [0.5, 0.5, float("nan"), 0.5]})

    def test_should_reject_when_embedding_is_not_l2_normalized(self) -> None:
        with pytest.raises(ValidationError, match="L2 norm"):
            _make_artifact(demand_embeddings={"D1": [1.0, 1.0, 1.0, 1.0]})

    def test_should_round_trip_through_load_from_json_when_hash_matches(self, tmp_path: Path) -> None:
        artifact = _make_artifact()
        payload = json.loads(artifact.model_dump_json())
        import hashlib

        payload.pop("artifact_sha256")
        canonical = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
        payload["artifact_sha256"] = hashlib.sha256(canonical).hexdigest()

        path = tmp_path / "artifact.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        loaded = FrozenEmbeddingArtifact.load_from_json(path)
        assert loaded.artifact_id == artifact.artifact_id

    def test_should_reject_artifact_when_tampered(self, tmp_path: Path) -> None:
        artifact = _make_artifact()
        payload = json.loads(artifact.model_dump_json())
        payload["artifact_sha256"] = "f" * 64  # wrong on purpose
        path = tmp_path / "tampered.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

        with pytest.raises(ValueError, match="integrity verification failed"):
            FrozenEmbeddingArtifact.load_from_json(path)

    def test_should_verify_source_dataset_when_hashes_and_ids_match(self) -> None:
        artifact = _make_artifact(dataset_sha256="b" * 64)
        dataset = _validated_dataset(demand_ids={"D1"}, patent_ids={"P1"}, content_sha256="b" * 64)
        artifact.verify_source_dataset(dataset)  # must not raise

    def test_should_reject_when_dataset_sha256_has_drifted(self) -> None:
        artifact = _make_artifact(dataset_sha256="b" * 64)
        dataset = _validated_dataset(demand_ids={"D1"}, patent_ids={"P1"}, content_sha256="0" * 64)

        with pytest.raises(ValueError, match="Source dataset drift detected"):
            artifact.verify_source_dataset(dataset)

    def test_should_reject_when_demand_ids_do_not_match_dataset(self) -> None:
        artifact = _make_artifact(dataset_sha256="b" * 64, demand_embeddings={"D_STALE": _NORM_VEC_A})
        dataset = _validated_dataset(demand_ids={"D1"}, patent_ids={"P1"}, content_sha256="b" * 64)

        with pytest.raises(ValueError, match="demand_embeddings keys"):
            artifact.verify_source_dataset(dataset)

    def test_should_reject_when_patent_ids_do_not_match_dataset(self) -> None:
        artifact = _make_artifact(dataset_sha256="b" * 64, patent_embeddings={"P_STALE": _NORM_VEC_B})
        dataset = _validated_dataset(demand_ids={"D1"}, patent_ids={"P1"}, content_sha256="b" * 64)

        with pytest.raises(ValueError, match="patent_embeddings keys"):
            artifact.verify_source_dataset(dataset)
