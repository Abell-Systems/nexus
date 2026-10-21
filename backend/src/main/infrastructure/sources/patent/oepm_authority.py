"""Reader of the OEPM Authority File: the inventory of every patent document the office has published.

It holds numbers and dates only, no classification, and it is rebuilt every month, so no hash is pinned: the caller
records the file name and its SHA-256 with whatever it reports. The XML is read with regular expressions, one entry
at a time, so no entity or external reference is ever resolved.
"""

import re
import zipfile
from collections.abc import Iterator
from pathlib import Path

from domain.models.whitespace import AuthorityEntry

_ENTRY = re.compile(r"<afp:AuthorityFileEntry>(.*?)</afp:AuthorityFileEntry>", re.S)


def _field(pattern: str, entry: str) -> str:
    found = re.search(pattern, entry)
    return found.group(1) if found else ""


def read_authority_file(path: Path) -> Iterator[AuthorityEntry]:
    """Every entry with a publication number, kind and date, in archive order."""
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".xml"):
                continue
            for entry in _ENTRY.findall(archive.read(name).decode("utf-8", "replace")):
                number = _field(r"<pat:PublicationNumber>(\w+)<", entry)
                kind = _field(r"<com:PatentDocumentKindCode>(\w+)<", entry)
                date = _field(r"<com:PublicationDate>(\d{8})<", entry)
                if number and kind and date:
                    yield AuthorityEntry(
                        publication_number=number,
                        kind=kind,
                        publication_date=date,
                        application_office=_field(r"<pat:ApplicationIdentification>\s*<com:IPOfficeCode>(\w+)<", entry),
                        application_text=_field(r"<com:ApplicationNumberText>([^<]*)<", entry).strip(),
                        filing_date=_field(r"<pat:FilingDate>(\d{8})<", entry),
                    )
