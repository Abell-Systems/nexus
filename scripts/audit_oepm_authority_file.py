#!/usr/bin/env python3
"""Counts the publications of the OEPM Authority File by publication year and compares them with the bibliographic corpus.

The Authority File is the OEPM's inventory of every patent document it has published (number, kind, publication
date, application number, filing date), downloaded from the OpenData catalogue. It has no classification, so it
says how many documents exist, not what they contain. Exploratory: the counts are not part of the published figures.

  python scripts/audit_oepm_authority_file.py ES_Authority_File_20260930.zip [--write FILE]
"""

import argparse
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"

ENTRY = re.compile(r"<afp:AuthorityFileEntry>(.*?)</afp:AuthorityFileEntry>", re.S)
PUBLICATION = re.compile(
    r"<com:PatentDocumentKindCode>(\w+)</com:PatentDocumentKindCode>\s*<com:PublicationDate>(\d{4})\d{4}</com:PublicationDate>"
)
EXCEPTION = re.compile(r"<afp:ExceptionCode>(\w)</afp:ExceptionCode>")


def count_entries(xml: str) -> tuple[Counter[tuple[int, str]], Counter[str]]:
    """Entries by (publication year, 'ep_translation' for T* kinds or 'national'), and by exception code."""
    by_year: Counter[tuple[int, str]] = Counter()
    exceptions: Counter[str] = Counter()
    for entry in ENTRY.findall(xml):
        found = PUBLICATION.search(entry)
        if not found:
            continue
        kind, year = found.group(1), int(found.group(2))
        by_year[(year, "ep_translation" if kind.startswith("T") else "national")] += 1
        code = EXCEPTION.search(entry)
        exceptions[code.group(1) if code else "-"] += 1
    return by_year, exceptions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("authority_file", type=Path)
    parser.add_argument("--write", type=Path, help="also write the table as JSON")
    args = parser.parse_args()

    by_year: Counter[tuple[int, str]] = Counter()
    exceptions: Counter[str] = Counter()
    with zipfile.ZipFile(args.authority_file) as archive:
        for name in archive.namelist():
            if name.endswith(".xml"):
                counted, codes = count_entries(archive.read(name).decode("utf-8", "replace"))
                by_year.update(counted)
                exceptions.update(codes)

    corpus = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))["figures"]["by_publication_year"]
    table = {}
    print("year  authority(T/national)   corpus(T/national)   authority-corpus(T/national)")
    for year in range(2000, 2026):
        ep, national = by_year[(year, "ep_translation")], by_year[(year, "national")]
        c = corpus.get(str(year), {"ep_translations": 0, "national": 0})
        table[year] = {"authority": {"ep_translation": ep, "national": national}, "corpus": c}
        print(
            f"{year}  {ep + national:>6} ({ep}/{national})  {c['ep_translations'] + c['national']:>6} "
            f"({c['ep_translations']}/{c['national']})  {ep + national - c['ep_translations'] - c['national']:>6} "
            f"({ep - c['ep_translations']}/{national - c['national']})"
        )
    print("exception codes (all years):", dict(exceptions))
    if args.write:
        args.write.write_text(
            json.dumps({"by_year": table, "exceptions": dict(exceptions)}, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
