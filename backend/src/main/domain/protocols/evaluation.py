"""Domain protocols for evaluation dataset loading and verification under ADR 0006."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from domain.models.evaluation import ValidatedDataset


@runtime_checkable
class EvaluationDatasetLoader(Protocol):
    """Port for loading and cryptographically validating evaluation benchmark datasets."""

    def load_validated_dataset(
        self,
        dataset_path: Path,
        checksum_path: Path,
        manifest_path: Path | None = None,
    ) -> ValidatedDataset:
        """Loads dataset from exact paths, verifies byte-exact SHA-256 and manifest, returning ValidatedDataset."""
        ...
