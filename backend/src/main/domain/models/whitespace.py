"""Observations for technology white-space analysis (ADR 0036 §5.1).

Raw source values only: nothing here is derived, deduplicated or interpreted. Independent from the
offer-demand matching models on purpose.
"""

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator


class SourceRecordProvenance(BaseModel):
    """Where a record came from: the hashed source file and the path of the record inside it.

    ``archive_path`` joins the names of nested archives and of the final entry with ``/``. A segment that
    ends in ``.zip`` is an archive to open; what follows the last one is the name of the entry, which may
    itself contain ``/`` (for example ``ES2671175/ES2671175_20190313_B1.xml``).
    """

    model_config = ConfigDict(frozen=True)

    source_file: str
    file_sha256: str
    archive_path: str

    @field_validator("file_sha256")
    @classmethod
    def validate_sha256_format(cls, v: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", v):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v


class SourceAnomaly(BaseModel):
    """An optional field the source states but that cannot be read; the record is kept and the raw value is too.

    For ``encoding`` the raw value is the hexadecimal of the first offending bytes only; the whole original
    record is recoverable from the provenance of the publication.
    """

    model_config = ConfigDict(frozen=True)

    field: str
    raw_value: str
    reason: str


class IpcEntry(BaseModel):
    """One IPC classification entry exactly as the source states it."""

    model_config = ConfigDict(frozen=True)

    section: str
    class_number: str
    subclass: str
    main_group: str | None = None
    subgroup: str | None = None
    version: str | None = None
    level: str | None = None
    value: str | None = None

    @property
    def subclass_symbol(self) -> str:
        """Four-character IPC subclass (derived), for example ``B05C``."""
        return f"{self.section}{self.class_number}{self.subclass}"


class PatentPublication(BaseModel):
    """One publication by a patent office, as observed in one source file."""

    model_config = ConfigDict(frozen=True)

    country: str
    doc_number: str
    kind: str
    publication_date: date
    application_date: date | None = None
    priority_dates: tuple[date, ...] = ()
    title: str = ""
    applicants: tuple[str, ...] = ()
    inventors: tuple[str, ...] = ()
    ipc_entries: tuple[IpcEntry, ...] = ()
    anomalies: tuple[SourceAnomaly, ...] = ()
    provenance: SourceRecordProvenance

    @property
    def has_priority_claim(self) -> bool:
        """True if the source states a priority claim, even when its date could not be read."""
        return bool(self.priority_dates) or any(a.field == "priority_date" for a in self.anomalies)

    @property
    def doc_id(self) -> str:
        """Country, number and kind code. Not unique in the source: repeats are kept, never merged."""
        return f"{self.country}{self.doc_number}{self.kind}"


class RejectedRecord(BaseModel):
    """A source record that could not be read, kept so that it is counted and never silently lost."""

    model_config = ConfigDict(frozen=True)

    provenance: SourceRecordProvenance
    reason: str
