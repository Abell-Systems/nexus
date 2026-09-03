"""Unit tests for EvaluationDatasetLoader under ADR 0006.

Invariants verified:
- Byte-exact SHA-256 verification of disk files without re-serialization.
- Fail-fast on missing dataset file (FileNotFoundError).
- Fail-fast on missing .sha256 checksum file (FileNotFoundError).
- Fail-fast on byte-level file tampering (ValueError).
- Fail-fast on malformed .sha256 file format (ValueError).
- Fail-fast on manifest count mismatch (ValueError).
- Working-directory independence: functions identically regardless of process CWD.
- Zero implicit path lookups in cwd or config.
"""

import hashlib
import json
from pathlib import Path

import pytest

from infrastructure.evaluation.dataset_loader import DefaultEvaluationDatasetLoader


@pytest.fixture
def valid_dataset_payload() -> dict:
    return {
        "dataset_id": "eval-bench-test",
        "schema_version": "1.0.0",
        "dataset_version": "1.0.0",
        "description": "Deterministic test evaluation dataset",
        "demands": [
            {
                "demand_id": "INNOGET-TEST-1",
                "title": "Test Demand",
                "description": "Testing drainage fixtures",
                "posted_date": "2023-01-01",
                "target_cpc_prefixes": ["E03C"],
                "is_synthetic": False,
                "provenance": {
                    "source_authority": "innoget",
                    "source_uri": "https://example.com/calls/1",
                    "extraction_timestamp": "2023-01-01T12:00:00Z",
                    "raw_payload_sha256": "1" * 64,
                    "modality": "observed",
                },
            }
        ],
        "patents": [
            {
                "publication_id": "ES-TEST-A1",
                "publication_date": "2022-01-01",
                "classifications_cpc": ["E03C1/00"],
                "title": "Sanitary valve",
                "abstract": "Water mixing valve.",
                "is_synthetic": False,
                "provenance": {
                    "source_authority": "oepm",
                    "source_uri": "https://example.com/patents/ES-TEST-A1",
                    "extraction_timestamp": "2022-01-01T12:00:00Z",
                    "raw_payload_sha256": "2" * 64,
                    "modality": "observed",
                },
            }
        ],
        "annotations": [
            {
                "demand_id": "INNOGET-TEST-1",
                "publication_id": "ES-TEST-A1",
                "grade": 2,
                "annotator_role": "expert_reviewer",
                "notes": "Relevant prior art",
                "modality": "expert_labelled",
            }
        ],
    }


@pytest.fixture
def dataset_bundle(tmp_path: Path, valid_dataset_payload: dict) -> tuple[Path, Path, Path]:
    dataset_file = tmp_path / "dataset.json"
    raw_content = json.dumps(valid_dataset_payload, indent=2).encode("utf-8")
    dataset_file.write_bytes(raw_content)

    digest = hashlib.sha256(raw_content).hexdigest()
    checksum_file = tmp_path / "dataset.sha256"
    checksum_file.write_text(f"{digest}  dataset.json\n", encoding="utf-8")

    manifest_file = tmp_path / "manifest.json"
    manifest_data = {
        "dataset_id": "eval-bench-test",
        "schema_version": "1.0.0",
        "dataset_version": "1.0.0",
        "source_authorities": ["innoget", "oepm"],
        "demand_count": 1,
        "patent_count": 1,
        "annotation_count": 1,
        "content_sha256": digest,
    }
    manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    return dataset_file, checksum_file, manifest_file


def test_loader_success(dataset_bundle):
    dataset_path, checksum_path, manifest_path = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()

    raw_bytes = dataset_path.read_bytes()
    expected_hash = hashlib.sha256(raw_bytes).hexdigest()

    validated = loader.load_validated_dataset(
        dataset_path=dataset_path,
        checksum_path=checksum_path,
        manifest_path=manifest_path,
    )
    assert validated.dataset.dataset_id == "eval-bench-test"
    assert len(validated.dataset.demands) == 1
    assert len(validated.dataset.patents) == 1
    assert len(validated.dataset.annotations) == 1
    assert validated.manifest.content_sha256 == expected_hash


def test_loader_fails_on_missing_dataset(tmp_path):
    loader = DefaultEvaluationDatasetLoader()
    with pytest.raises(FileNotFoundError, match="Dataset file not found"):
        loader.load_validated_dataset(
            dataset_path=tmp_path / "non_existent.json",
            checksum_path=tmp_path / "any.sha256",
            manifest_path=tmp_path / "any.manifest.json",
        )


def test_loader_fails_on_missing_checksum(dataset_bundle, tmp_path):
    dataset_path, _, manifest_path = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()
    with pytest.raises(FileNotFoundError, match="Checksum file not found"):
        loader.load_validated_dataset(
            dataset_path=dataset_path,
            checksum_path=tmp_path / "missing_checksum.sha256",
            manifest_path=manifest_path,
        )


def test_loader_fails_on_missing_manifest(dataset_bundle, tmp_path):
    dataset_path, checksum_path, _ = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()
    with pytest.raises(FileNotFoundError, match="Manifest file not found"):
        loader.load_validated_dataset(
            dataset_path=dataset_path,
            checksum_path=checksum_path,
            manifest_path=tmp_path / "missing_manifest.json",
        )


def test_loader_fails_on_tampered_dataset_bytes(dataset_bundle):
    dataset_path, checksum_path, manifest_path = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()

    # Tamper with 1 byte in the file
    content = bytearray(dataset_path.read_bytes())
    content[10] = ord("X") if content[10] != ord("X") else ord("Y")
    dataset_path.write_bytes(content)

    with pytest.raises(ValueError, match="Cryptographic integrity verification failed"):
        loader.load_validated_dataset(
            dataset_path=dataset_path,
            checksum_path=checksum_path,
            manifest_path=manifest_path,
        )


def test_loader_fails_on_tampered_checksum(dataset_bundle):
    dataset_path, checksum_path, manifest_path = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()

    # Overwrite checksum with bogus digest
    checksum_path.write_text(f"{'f' * 64}  dataset.json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Cryptographic integrity verification failed"):
        loader.load_validated_dataset(
            dataset_path=dataset_path,
            checksum_path=checksum_path,
            manifest_path=manifest_path,
        )


def test_loader_fails_on_malformed_checksum_file(dataset_bundle):
    dataset_path, checksum_path, manifest_path = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()

    checksum_path.write_text("invalid checksum content without hex digest\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed .sha256 checksum file format"):
        loader.load_validated_dataset(
            dataset_path=dataset_path,
            checksum_path=checksum_path,
            manifest_path=manifest_path,
        )


def test_loader_fails_on_checksum_filename_mismatch(dataset_bundle):
    dataset_path, checksum_path, manifest_path = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()

    # Valid digest but points to other_file.json
    raw_bytes = dataset_path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    checksum_path.write_text(f"{digest}  other_file.json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="references target filename 'other_file.json'"):
        loader.load_validated_dataset(
            dataset_path=dataset_path,
            checksum_path=checksum_path,
            manifest_path=manifest_path,
        )


def test_loader_fails_on_manifest_mismatch(dataset_bundle):
    dataset_path, checksum_path, manifest_path = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()

    # Tamper with manifest demand_count
    manifest_data = json.loads(manifest_path.read_text())
    manifest_data["demand_count"] = 5  # Reality is 1
    manifest_path.write_text(json.dumps(manifest_data))

    with pytest.raises(ValueError, match="Manifest demand_count .* does not match dataset"):
        loader.load_validated_dataset(
            dataset_path=dataset_path,
            checksum_path=checksum_path,
            manifest_path=manifest_path,
        )


def test_loader_cwd_independence(dataset_bundle, monkeypatch, tmp_path):
    dataset_path, checksum_path, manifest_path = dataset_bundle
    loader = DefaultEvaluationDatasetLoader()

    # Change current working directory to an unrelated temp dir
    arbitrary_dir = tmp_path / "completely_unrelated_cwd"
    arbitrary_dir.mkdir()
    monkeypatch.chdir(arbitrary_dir)

    validated = loader.load_validated_dataset(
        dataset_path=dataset_path,
        checksum_path=checksum_path,
        manifest_path=manifest_path,
    )
    assert validated.dataset.dataset_id == "eval-bench-test"
