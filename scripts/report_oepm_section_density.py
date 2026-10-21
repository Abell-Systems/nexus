#!/usr/bin/env python3
"""Share of IPC subclass pairs already seen together, by pair of sections, at two origins (descriptive map).

The corpus is read through the adapter after its hashes are verified. Describes the observed corpus only; an unseen pair
is an absence, not an opportunity, and nothing is ranked.

  python scripts/report_oepm_section_density.py --corpus-dir data/raw/oepm_open [--write FILE]
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.analysis_records import to_analysis_records
from application.whitespace.section_density import section_density
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
ORIGINS = [2006, 2022]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    files = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))["files"]
    records = to_analysis_records(OepmBiblioSource(args.corpus_dir, {n: f["sha256"] for n, f in files.items()}).read())
    report = {str(origin): section_density(records, origin) for origin in ORIGINS}
    for origin, density in report.items():
        print(origin, density["active_subclasses"], "active subclasses,", density["seen_pairs"], "seen pairs")
    if args.write:
        args.write.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
