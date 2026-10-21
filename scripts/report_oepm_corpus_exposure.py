#!/usr/bin/env python3
"""Exposure of the bibliographic corpus to omissions, from the OEPM Authority File (ADR 0036, O5.1).

Counts, by publication year and kind group, what the OEPM's inventory lists, what the corpus has and what is absent,
and the absences accumulated up to each origin. Measures only; nothing is added to the corpus. The corpus is read
through the adapter after its hashes are verified; the Authority File is an untrusted download identified by SHA-256.

  python scripts/report_oepm_corpus_exposure.py ES_Authority_File_20260930.zip --corpus-dir data/raw/oepm_open [--write FILE]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.corpus_exposure import exposure_table
from domain.models.whitespace import PatentPublication
from infrastructure.sources.patent.oepm_authority import read_authority_file
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
ORIGINS = [2003, 2006, 2010, 2013, 2016, 2019, 2022]  # development, the gap year, confirmatory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("authority_file", type=Path)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    files = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))["files"]
    corpus = OepmBiblioSource(args.corpus_dir, {name: f["sha256"] for name, f in files.items()})
    publications = (p for p in corpus.read() if isinstance(p, PatentPublication))
    report = {
        "authority_file": {
            "name": args.authority_file.name,
            "sha256": hashlib.sha256(args.authority_file.read_bytes()).hexdigest(),
        },
        "exposure": exposure_table(publications, read_authority_file(args.authority_file), ORIGINS),
    }
    print(json.dumps(report["exposure"]["accumulated_up_to_origin"], indent=1))
    if args.write:
        args.write.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
