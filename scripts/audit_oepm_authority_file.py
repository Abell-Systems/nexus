#!/usr/bin/env python3
"""Counts the publications of the OEPM Authority File by publication year and compares them with the bibliographic corpus.

The Authority File is the OEPM's inventory of every patent document it has published (number, kind, publication
date, application number, filing date), downloaded from the OpenData catalogue. It has no classification, so it
says how many documents exist, not what they contain. Exploratory: the counts are not part of the published figures.

  python scripts/audit_oepm_authority_file.py ES_Authority_File_20260930.zip [--write FILE] [--corpus-dir data/raw/oepm_open]

With --corpus-dir the publications are also matched one by one (publication number, kind code and publication
date) against the records of the bibliographic corpus, which is read through the repository's adapter.
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

REPO_MAIN = REPO_ROOT / "backend" / "src" / "main"
NUMBER = re.compile(r"<pat:PublicationNumber>(\w+)</pat:PublicationNumber>")
DATE = re.compile(r"<com:PublicationDate>(\d{8})</com:PublicationDate>")
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


def publication_keys(xml: str) -> dict[tuple[str, str, str], str]:
    """(publication number, kind code, publication date as YYYYMMDD) of every entry, with its exception code or '-'."""
    keys: dict[tuple[str, str, str], str] = {}
    for entry in ENTRY.findall(xml):
        found, number, date = PUBLICATION.search(entry), NUMBER.search(entry), DATE.search(entry)
        if found and number and date:
            code = EXCEPTION.search(entry)
            keys[(number.group(1), found.group(1), date.group(1))] = code.group(1) if code else "-"
    return keys


def match_corpus(authority: dict[tuple[str, str, str], str], corpus: set[tuple[str, str, str]]) -> dict:
    """Publications in both, only in the authority file (with kind and exception code for 2000-2025) and only in the corpus."""
    by_year: dict[int, Counter[str]] = {}
    missing_exceptions: Counter[str] = Counter()
    missing_kinds: Counter[str] = Counter()
    missing_by_year_kind: dict[int, Counter[str]] = {}
    for key, code in authority.items():
        year = int(key[2][:4])
        counter = by_year.setdefault(year, Counter())
        if key in corpus:
            counter["both"] += 1
        else:
            counter["only_authority"] += 1
            if 2000 <= year <= 2025:
                missing_exceptions[code] += 1
                missing_kinds[key[1]] += 1
                missing_by_year_kind.setdefault(year, Counter())[key[1]] += 1
    for key in corpus - authority.keys():
        by_year.setdefault(int(key[2][:4]), Counter())["only_corpus"] += 1
    return {
        "by_year": {y: dict(c) for y, c in sorted(by_year.items())},
        "missing_by_exception_2000_2025": dict(missing_exceptions),
        "missing_by_kind_2000_2025": dict(missing_kinds.most_common(12)),
        "missing_by_year_and_kind_group": {
            y: {
                "Y": c["Y"],
                "T": sum(v for k, v in c.items() if k.startswith("T")),
                "other": sum(c.values()) - c["Y"] - sum(v for k, v in c.items() if k.startswith("T")),
            }
            for y, c in sorted(missing_by_year_kind.items())
        },
    }


def publication_match(authority_file: Path, corpus_dir: Path) -> dict:
    sys.path.insert(0, str(REPO_MAIN))
    from domain.models.whitespace import PatentPublication
    from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

    authority: dict[tuple[str, str, str], str] = {}
    with zipfile.ZipFile(authority_file) as archive:
        for name in archive.namelist():
            if name.endswith(".xml"):
                authority.update(publication_keys(archive.read(name).decode("utf-8", "replace")))
    files = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))["files"]
    source = OepmBiblioSource(corpus_dir, {name: f["sha256"] for name, f in files.items()})
    corpus = {
        (p.doc_number, p.kind, p.publication_date.strftime("%Y%m%d"))
        for p in source.read()
        if isinstance(p, PatentPublication)
    }
    return match_corpus(authority, corpus)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("authority_file", type=Path)
    parser.add_argument("--write", type=Path, help="also write the table as JSON")
    parser.add_argument(
        "--corpus-dir", type=Path, help="match publications one by one against the bibliographic corpus"
    )
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
    result: dict = {"by_year": table, "exceptions": dict(exceptions)}
    if args.corpus_dir:
        result["publication_match"] = publication_match(args.authority_file, args.corpus_dir)
        print(json.dumps(result["publication_match"], indent=1))
    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
