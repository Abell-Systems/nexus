#!/usr/bin/env python3
"""Descriptive sensitivity of the base-rate counts at the development origins to perturbations of the corpus (O5.2).

Scenarios are those fixed in ADR 0036, section 8.10; nothing is added to the corpus and no decision changes. The corpus is
read through the adapter after its hashes are verified; the absence rates of scenario S-C come from the exposure table,
which uses the OEPM Authority File (identified by SHA-256).

  python scripts/report_oepm_omission_sensitivity.py ES_Authority_File_20260930.zip --corpus-dir data/raw/oepm_open [--write FILE]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.analysis_records import to_analysis_records
from application.whitespace.corpus_exposure import GROUPS, exposure_table
from application.whitespace.omission_sensitivity import omission_sensitivity
from domain.models.whitespace import PatentPublication
from infrastructure.sources.patent.oepm_authority import read_authority_file
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
ORIGINS = [2003, 2006]
REPLICATIONS = 200


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("authority_file", type=Path)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    files = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))["files"]
    source = OepmBiblioSource(args.corpus_dir, {name: f["sha256"] for name, f in files.items()})
    publications = [p for p in source.read() if isinstance(p, PatentPublication)]
    exposure = exposure_table(publications, read_authority_file(args.authority_file), ORIGINS)
    absence = {
        (int(year), group): cell[group]["absent_share_percent"]
        for year, cell in exposure["by_year"].items()
        for group in GROUPS
    }
    records = [r for r in to_analysis_records(publications) if r.published.year <= max(ORIGINS) + 3]
    report = {
        "authority_file": {
            "name": args.authority_file.name,
            "sha256": hashlib.sha256(args.authority_file.read_bytes()).hexdigest(),
        },
        "scenarios": "ADR 0036 section 8.10",
        "replications": REPLICATIONS,
        "records_in_scope": len(records),
        "sensitivity": omission_sensitivity(records, ORIGINS, absence, replications=REPLICATIONS),
    }
    for origin, scenarios in report["sensitivity"].items():
        print(origin, "S-A", scenarios["S-A"])
    if args.write:
        args.write.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
