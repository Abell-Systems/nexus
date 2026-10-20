"""Reader for the OEPM OpenData bibliographic files: ST36 XML inside nested ZIP archives (ADR 0036 §11.1).

Verifies the SHA-256 of every expected file before reading any of them, keeps every record (repeated
identifiers included), and returns records the XML parser cannot read as ``RejectedRecord`` instead of
dropping them. Dates are taken from each record, never from the name of the file that holds it.
"""

import hashlib
import io
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterator, Mapping
from datetime import date, datetime
from pathlib import Path

from domain.models.whitespace import IpcEntry, PatentPublication, RejectedRecord, SourceRecordProvenance
from domain.protocols.whitespace import SourceIntegrityError

_DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>")
_XML_ILLEGAL_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _to_date(text: str | None, field: str) -> date:
    if not text:
        raise ValueError(f"missing {field}")
    try:
        return datetime.strptime(text, "%Y%m%d").date()
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {text!r}") from exc


def _party_names(root: ET.Element, tag: str) -> tuple[str, ...]:
    names = []
    for party in root.iter(tag):
        name = party.findtext("addressbook/name") or ", ".join(
            part for part in (party.findtext("addressbook/last-name"), party.findtext("addressbook/first-name")) if part
        )
        if name:
            names.append(name)
    return tuple(names)


def _ipc_entry(node: ET.Element) -> IpcEntry:
    section, class_number, subclass = (node.findtext(tag) for tag in ("section", "class", "subclass"))
    if not (section and class_number and subclass):
        raise ValueError("incomplete IPC entry")
    return IpcEntry(
        section=section,
        class_number=class_number,
        subclass=subclass,
        main_group=node.findtext("main-group"),
        subgroup=node.findtext("subgroup"),
        version=node.findtext("ipc-version-indicator/date"),
        level=node.findtext("classification-level"),
        value=node.findtext("classification-value"),
    )


def _publication(raw: bytes, provenance: SourceRecordProvenance) -> PatentPublication:
    # The DOCTYPE (and with it any entity declaration) is removed before parsing, so entities cannot expand.
    text = _DOCTYPE.sub("", raw.decode("utf-8", "replace"))
    root = ET.fromstring(_XML_ILLEGAL_CONTROL.sub("", text))
    if root.tag != "es-patent-document":
        raise ValueError(f"unexpected root element {root.tag!r}")
    application = root.findtext(".//application-reference/document-id/date")
    return PatentPublication(
        country=root.get("country") or "",
        doc_number=root.get("doc-number") or "",
        kind=root.get("kind") or "",
        publication_date=_to_date(root.get("date-publ"), "publication date"),
        application_date=_to_date(application, "application date") if application else None,
        priority_dates=tuple(
            _to_date(claim.findtext(".//date"), "priority date")
            for claim in root.iter("priority-claim")
            if claim.findtext(".//date")
        ),
        title=root.findtext(".//invention-title") or "",
        applicants=_party_names(root, "applicant"),
        inventors=_party_names(root, "inventor"),
        ipc_entries=tuple(_ipc_entry(node) for node in root.iter("classification-ipcr")),
        provenance=provenance,
    )


def _parse_record(raw: bytes, provenance: SourceRecordProvenance) -> PatentPublication | RejectedRecord:
    try:
        return _publication(raw, provenance)
    except (ET.ParseError, ValueError) as exc:
        return RejectedRecord(provenance=provenance, reason=f"{type(exc).__name__}: {exc}")


def _walk(
    archive: zipfile.ZipFile, source_file: str, file_sha: str, prefix: str
) -> Iterator[PatentPublication | RejectedRecord]:
    for name in sorted(archive.namelist()):
        provenance = SourceRecordProvenance(source_file=source_file, file_sha256=file_sha, archive_path=prefix + name)
        if name.endswith(".zip"):
            try:
                nested = zipfile.ZipFile(io.BytesIO(archive.read(name)))
            except zipfile.BadZipFile as exc:
                yield RejectedRecord(provenance=provenance, reason=f"BadZipFile: {exc}")
                continue
            yield from _walk(nested, source_file, file_sha, f"{prefix}{name}/")
        elif name.endswith(".xml"):
            yield _parse_record(archive.read(name), provenance)


class OepmBiblioSource:
    """``PatentPublicationSource`` over a directory of ``BIBLIO_*.zip`` files with known SHA-256 digests."""

    def __init__(self, directory: Path | str, expected_sha256: Mapping[str, str]) -> None:
        self._directory = Path(directory)
        self._expected = dict(expected_sha256)

    def verify(self) -> None:
        for name in sorted(self._expected):
            path = self._directory / name
            if not path.is_file():
                raise SourceIntegrityError(f"{name}: file is missing")
            actual = file_sha256(path)
            if actual != self._expected[name]:
                raise SourceIntegrityError(f"{name}: SHA-256 is {actual}, expected {self._expected[name]}")

    def read(self) -> Iterator[PatentPublication | RejectedRecord]:
        self.verify()
        for name in sorted(self._expected):
            with zipfile.ZipFile(self._directory / name) as archive:
                yield from _walk(archive, name, self._expected[name], "")
