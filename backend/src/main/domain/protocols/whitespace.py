"""Port for sources of patent publications used by white-space analysis."""

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from domain.models.whitespace import PatentPublication, RejectedRecord


class SourceIntegrityError(Exception):
    """A source file is missing or does not match its expected SHA-256; nothing was read."""


@runtime_checkable
class PatentPublicationSource(Protocol):
    """Yields every record of a source in a deterministic order, rejected ones included.

    Raises ``SourceIntegrityError`` before yielding anything if the source cannot be verified.
    """

    def read(self) -> Iterator[PatentPublication | RejectedRecord]: ...
