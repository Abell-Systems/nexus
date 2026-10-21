#!/usr/bin/env python3
"""Reports how the application number links the bibliographic corpus to the OEPM Authority File and to legal-status data.

Measures only: nothing is added to the corpus and no published figure changes (ADR 0036, O5 and C3 need this
before any other source is considered). The corpus is read through the repository's adapter after its hashes are
verified; the Authority File and the legal-status file are untrusted downloads, identified here by their SHA-256.

  python scripts/report_oepm_application_links.py ES_Authority_File_20260930.zip --corpus-dir data/raw/oepm_open \\
      [--legal-zip LEGAL_2018.zip] [--write FILE]
"""

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.application_links import link_report, resolve_filing_numbers
from domain.models.whitespace import PatentPublication
from infrastructure.sources.patent.oepm_authority import read_authority_file
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
LEGAL_RECORD = re.compile(r"<LR[ >].*?</LR>", re.S)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def legal_filing_numbers(path: Path) -> Iterator[tuple[str, str]]:
    """(country, filing number) of every legal-status record, walking the nested archives; indicator F only."""

    def walk(archive: zipfile.ZipFile) -> Iterator[bytes]:
        for name in archive.namelist():
            if name.endswith(".zip"):
                yield from walk(zipfile.ZipFile(io.BytesIO(archive.read(name))))
            elif name.endswith(".xml"):
                yield archive.read(name)

    for xml in walk(zipfile.ZipFile(path)):
        for record in LEGAL_RECORD.findall(xml.decode("utf-8", "replace")):
            fields = {
                tag: found.group(1)
                for tag in ("L001", "L002", "L003")
                if (found := re.search(f"<{tag}>(.*?)</{tag}>", record))
            }
            if fields.get("L002") == "F" and "L001" in fields and "L003" in fields:
                yield fields["L001"], fields["L003"].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("authority_file", type=Path)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument(
        "--legal-zip", type=Path, help="a yearly legal-status file, to measure how its filing numbers resolve"
    )
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    files = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))["files"]
    corpus = OepmBiblioSource(args.corpus_dir, {name: f["sha256"] for name, f in files.items()})
    publications = (p for p in corpus.read() if isinstance(p, PatentPublication))
    report = {
        "authority_file": {"name": args.authority_file.name, "sha256": sha256(args.authority_file)},
        "links": link_report(publications, read_authority_file(args.authority_file)),
    }
    if args.legal_zip:
        known = {k for e in read_authority_file(args.authority_file) if (k := e.application_key)}
        report["legal_status"] = {
            "file": {"name": args.legal_zip.name, "sha256": sha256(args.legal_zip)},
            "filing_numbers": resolve_filing_numbers(legal_filing_numbers(args.legal_zip), known),
        }
    print(json.dumps(report, indent=2))
    if args.write:
        args.write.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
