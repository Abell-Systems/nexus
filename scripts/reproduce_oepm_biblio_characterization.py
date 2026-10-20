#!/usr/bin/env python3
"""Reproduces the published figures of the OEPM bibliographic corpus from its hashed source files.

ADR 0036 §11.1: verify the SHA-256 of every file, read the corpus, and show every difference from
`docs/whitespace/oepm-biblio-corpus-characterization.md` (transcribed in
`config/whitespace/oepm_biblio_2000_2025.json`) instead of adjusting it. Sections 4.2 and 7 of that
document are not covered.

  python scripts/reproduce_oepm_biblio_characterization.py [--data-dir data/raw/oepm_open] [--write-figures FILE]

Exit code: 0 all figures reproduced, 1 differences found, 2 source could not be verified.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.corpus_report import build_figures, compare_figures
from domain.protocols.whitespace import SourceIntegrityError
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CONTRACT = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"


def count_figures(figures: object) -> int:
    return sum(count_figures(v) for v in figures.values()) if isinstance(figures, dict) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data" / "raw" / "oepm_open")
    parser.add_argument("--write-figures", type=Path, help="also write the reproduced figures as JSON")
    args = parser.parse_args()

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source = OepmBiblioSource(args.data_dir, {name: f["sha256"] for name, f in contract["files"].items()})
    try:
        figures = build_figures(source.read())
    except SourceIntegrityError as exc:
        print(f"SOURCE NOT VERIFIED: {exc}")
        return 2

    if args.write_figures:
        args.write_figures.write_text(json.dumps(figures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    differences = compare_figures(contract["figures"], figures)
    for line in differences:
        print(line)
    published = count_figures(contract["figures"])
    print(
        f"{len(differences)} difference(s) from {published} published figures"
        if differences
        else f"All {published} published figures reproduced"
    )
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
