"""Base normalizer protocol definition."""

from collections.abc import Iterator
from typing import Protocol

from domain.models.evidence import FieldObservation
from domain.models.patent import PatentDocument
from domain.protocols.sources import RawPayload


class PatentNormalizerProtocol(Protocol):
    """Protocol defining streaming normalization from raw payloads to domain documents."""

    def normalize_stream(
        self, raw_payload: RawPayload
    ) -> Iterator[tuple[PatentDocument, list[FieldObservation]]]:
        """Normalize a raw payload into an iterator of (PatentDocument, list[FieldObservation]) tuples."""
        ...
