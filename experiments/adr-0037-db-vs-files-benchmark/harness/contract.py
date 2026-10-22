"""Contract between the harness and a storage alternative (pre-registration §1, §3).

A store changes only the storage mechanism. Everything else (rows, report code, comparisons) is shared.
Return codes of run_benchmark: 0 = ran and every acceptance check passed; 1 = ran and at least one check failed;
2 = refused to run (protocol not authorised, bad arguments); 3 = environment incident (nothing is graded).
"""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from application.whitespace.analysis_records import AnalysisRecord

AlterKind = Literal["change_subclass", "flip_byte", "delete_object", "swap_rows"]
EXIT_PASS, EXIT_FAIL, EXIT_REFUSED, EXIT_INCIDENT = 0, 1, 2, 3


class IntegrityError(Exception):
    """Raised by verify(): explicit failure, nothing served. A warning that lets a run continue does not count as detection."""


@dataclass(frozen=True)
class VerifyResult:
    version: str
    manifest_digest: str


class Store(Protocol):
    """One isolated instance per alternative: its own directory / schema namespace, nothing shared with the other."""

    name: str

    def prepare(self, version: str, rows: dict[str, list[tuple]]) -> VerifyResult:
        """Build `version` from the shared rows in a location independent of any other version; write its manifest."""

    def verify(self, version: str) -> VerifyResult:
        """Recompute integrity against the version's manifest. Raises IntegrityError on any mismatch or absence."""

    def read_records(self, version: str) -> list[AnalysisRecord]:
        """All records in record order, subclasses ordered by code point (contract of ADR 0037 §3.8)."""

    def alter(self, version: str, kind: AlterKind) -> None:
        """Apply one pre-registered alteration to the stored copy of `version` (never to the shared rows)."""

    def backup(self, version: str, destination: Path) -> None: ...

    def restore(self, source: Path, version: str) -> None:
        """Restore into `version`, which must not exist (no overwrite)."""

    def drop(self, version: str) -> None: ...

    def size_bytes(self, version: str) -> int: ...

    def configuration(self) -> dict:
        """Exact versions and parameters that can affect results (engine version, compression, collation, settings)."""


Clock = Callable[[], float]


def analysis_record(doc_id, kind, published, application_date, min_priority, subclasses) -> AnalysisRecord:
    """Same construction for both stores (mirrors application.whitespace.analysis_records.to_analysis_records)."""
    from application.whitespace.corpus_report import kind_group

    dates = [d for d in (min_priority, application_date) if d]
    return AnalysisRecord(doc_id, published, kind_group(kind), min(dates).year if dates else None, tuple(subclasses), kind)
