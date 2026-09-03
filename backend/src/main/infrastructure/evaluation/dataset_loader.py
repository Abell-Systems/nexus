"""Deterministic EvaluationDatasetLoader under ADR 0006.

Invariants:
- Mandatory explicit Path injection (no relative search or CWD dependence).
- Byte-exact SHA-256 verification directly from file bytes on disk without parsing.
- Fail-fast on missing files (FileNotFoundError) or tampering/corruption (ValueError).
- Full Pydantic validation into immutable EvaluationDataset.
- Validates manifest counts against actual dataset records before returning ValidatedDataset.
"""

import hashlib
import json
import re
from pathlib import Path

from domain.models.evaluation import (
    EvaluationDataset,
    EvaluationDatasetManifest,
    ValidatedDataset,
)
from domain.protocols.evaluation import EvaluationDatasetLoader


def _parse_sha256_file(checksum_path: Path, expected_filename: str) -> str:
    """Extracts expected SHA-256 digest from a standard .sha256 file (<digest>  <filename>).

    Under ADR 0006 §4, format must strictly be: '<64-hex-digest>  <filename>'.
    """
    text = checksum_path.read_text(encoding="utf-8").strip()
    match = re.match(r"^([0-9a-fA-F]{64})\s{2}(.+)$", text)
    if not match:
        raise ValueError(
            f"Malformed .sha256 checksum file format in '{checksum_path}'. "
            "Expected format strictly '<64-hex-digest>  <filename>'"
        )
    digest, filename = match.group(1).lower(), match.group(2).strip()
    if filename != expected_filename:
        raise ValueError(
            f"Checksum file '{checksum_path}' references target filename '{filename}', "
            f"expected '{expected_filename}'"
        )
    return digest


class DefaultEvaluationDatasetLoader(EvaluationDatasetLoader):
    """Reference implementation of EvaluationDatasetLoader protocol."""

    def load_validated_dataset(
        self,
        dataset_path: Path,
        checksum_path: Path,
        manifest_path: Path,
    ) -> ValidatedDataset:
        """Loads and cryptographically verifies an evaluation dataset from disk."""
        if not dataset_path.is_file():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
        if not checksum_path.is_file():
            raise FileNotFoundError(f"Checksum file not found: {checksum_path}")
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        # 1. Byte-Exact Cryptographic Verification (ADR 0006 §4)
        raw_bytes = dataset_path.read_bytes()
        actual_digest = hashlib.sha256(raw_bytes).hexdigest().lower()
        expected_digest = _parse_sha256_file(checksum_path, expected_filename=dataset_path.name)

        if actual_digest != expected_digest:
            raise ValueError(
                f"Cryptographic integrity verification failed for '{dataset_path}'. "
                f"Expected digest: {expected_digest}, computed: {actual_digest}. "
                "Dataset has been tampered with or corrupted."
            )

        # 2. Schema Deserialization and Validation (ADR 0006 §3)
        try:
            raw_json = json.loads(raw_bytes.decode("utf-8"))
        except Exception as err:
            raise ValueError(f"Failed to parse dataset JSON: {err}") from err

        dataset = EvaluationDataset.model_validate(raw_json)

        # 3. Manifest Resolution and Consistency Check (ADR 0006 §3)
        manifest_json = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = EvaluationDatasetManifest.model_validate(manifest_json)
        if manifest.content_sha256.lower() != actual_digest:
            raise ValueError(
                f"Manifest content_sha256 '{manifest.content_sha256}' does not match computed digest '{actual_digest}'"
            )

        return ValidatedDataset(dataset=dataset, manifest=manifest)
