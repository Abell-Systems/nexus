from pathlib import Path
from typing import Any, Protocol
from domain.models.patent import PatentDocument
from domain.models.evidence import FieldObservation
from domain.models.snapshot import DatasetPart


class RawStoreProtocol(Protocol):
    """Protocol for immutable raw payload storage."""

    def store_payload(
        self,
        source_id: str,
        payload_bytes: bytes,
        metadata: dict[str, Any],
        file_ext: str = "json",
    ) -> tuple[Path, str]:
        ...

    def get_payload(self, sha256_digest: str) -> bytes:
        ...

    def verify_payload_integrity(self, sha256_digest: str) -> bool:
        ...


class CanonicalStoreProtocol(Protocol):
    """Protocol for relational canonical storage (Parquet)."""

    def write_batch(
        self,
        dataset_id: str,
        documents: list[PatentDocument],
        observations: list[FieldObservation],
    ) -> None:
        ...

    def seal_dataset(self, dataset_id: str) -> tuple[list[DatasetPart], str]:
        ...


class QueryEngineProtocol(Protocol):
    """Protocol for analytical query engine over canonical datasets."""

    def get_cluster_aggregates(self, cpc_prefix: str) -> dict[str, Any]:
        ...

    def search_by_cpc_prefix(self, cpc_prefix: str) -> list[dict[str, Any]]:
        ...
