"""Base normalizer protocol definition."""

from typing import Iterator, Protocol
from nexus.domain.models.patent import PatentDocument
from nexus.domain.models.evidence import FieldObservation
from nexus.domain.protocols.sources import RawPayload


class PatentNormalizerProtocol(Protocol):
    """Protocol defining streaming normalization from raw payloads to domain documents."""

    def normalize_stream(
        self, raw_payload: RawPayload
    ) -> Iterator[tuple[PatentDocument, list[FieldObservation]]]:
        """Normalize a raw payload into an iterator of (PatentDocument, list[FieldObservation]) tuples."""
        ...
