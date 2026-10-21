"""Observations for technology white-space analysis (ADR 0036 §5.1).

Raw source values only: nothing here is derived, deduplicated or interpreted. Independent from the
offer-demand matching models on purpose.
"""

import re
from datetime import date
from typing import Literal

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


class ApplicationReference(BaseModel):
    """The application a publication stems from, as the source states it (raw strings, not normalised).

    Not the publication identifier: one application has several publications (for example A1 and B1), and
    sources such as legal status and the pre-2013 citations are keyed by application, not by publication.
    ``country`` and ``kind`` are empty if the source omits them; a reference without a number is not kept.
    """

    model_config = ConfigDict(frozen=True)

    country: str
    number: str
    kind: str


class PatentPublication(BaseModel):
    """One publication by a patent office, as observed in one source file."""

    model_config = ConfigDict(frozen=True)

    country: str
    doc_number: str
    kind: str
    publication_date: date
    application_reference: ApplicationReference | None = None
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


class ApplicationKey(BaseModel):
    """An application in a form comparable across sources: its series and its digits.

    National patents (``P``) and utility models (``U``) are numbered in separate series that share the digit
    space, and European applications (``E``) have their own, so the digits alone do not identify an
    application. No key is ever built by guessing; a source that omits the series gives candidates, not a key.
    """

    model_config = ConfigDict(frozen=True)

    series: Literal["P", "U", "E"]
    number: str


_PREFIXED_NATIONAL = re.compile(r"([PU])(\d+)")


def application_key_from_reference(reference: ApplicationReference | None) -> ApplicationKey | None:
    """Key of a bibliographic record: its application kind is the series, its number must be digits only."""
    if reference is None or reference.kind not in ("P", "U", "E") or not reference.number.isdigit():
        return None
    return ApplicationKey(series=reference.kind, number=reference.number)  # type: ignore[arg-type]


def application_key_from_authority(office: str, text: str) -> ApplicationKey | None:
    """Key of an Authority File entry: ``ES`` numbers carry the series as a letter (``U200502626``), ``EP`` ones are digits."""
    if office == "EP":
        return ApplicationKey(series="E", number=text) if text.isdigit() else None
    match = _PREFIXED_NATIONAL.fullmatch(text) if office == "ES" else None
    return ApplicationKey(series=match.group(1), number=match.group(2)) if match else None  # type: ignore[arg-type]


def application_key_candidates(country: str, number: str) -> tuple[ApplicationKey, ...]:
    """Keys a series-less filing number (as in legal-status data) could be: European, or national patent or utility model."""
    if not number.isdigit():
        return ()
    if country == "EP":
        return (ApplicationKey(series="E", number=number),)
    return (
        (ApplicationKey(series="P", number=number), ApplicationKey(series="U", number=number))
        if country == "ES"
        else ()
    )


class AuthorityEntry(BaseModel):
    """One document of the OEPM's inventory of published documents (Authority File), raw."""

    model_config = ConfigDict(frozen=True)

    publication_number: str
    kind: str
    publication_date: str
    application_office: str
    application_text: str
    filing_date: str

    @property
    def application_key(self) -> ApplicationKey | None:
        return application_key_from_authority(self.application_office, self.application_text)
