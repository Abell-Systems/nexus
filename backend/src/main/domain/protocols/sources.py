import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class RawPayload(BaseModel):
    """Raw payload chunk ingested directly from an external authority source."""

    source_id: str
    batch_id: str
    payload_bytes: bytes
    metadata: dict[str, Any] = Field(default_factory=dict)
    retrieval_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def payload_sha256(self) -> str:
        return hashlib.sha256(self.payload_bytes).hexdigest()


@runtime_checkable
class PatentSourceProtocol(Protocol):
    """Protocol for patent data sources yielding streaming raw batches."""

    def fetch_batches(self) -> Iterator[RawPayload]:
        ...


@runtime_checkable
class DemandSourceProtocol(Protocol):
    """Protocol for technological demand data sources."""

    def fetch_demands(self) -> Iterator[Any]:
        ...

