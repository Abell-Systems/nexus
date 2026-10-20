#!/usr/bin/env python3
"""Computes sections 4.2 and 7 of the OEPM bibliographic corpus characterization from its hashed source files.

ADR 0036 §11.1 / C1: derive publication lag and descriptive base rates through the repository's adapter and
show every difference from the printed figures (`config/whitespace/oepm_biblio_lag_base_rates_published.json`)
instead of adjusting either. The published figures are never an input of the computation.

  python scripts/reproduce_oepm_biblio_lag_base_rates.py [--data-dir data/raw/oepm_open] [--write-results FILE]

Exit code: 0 all published figures reproduced, 1 differences found, 2 source could not be verified.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.analysis_records import distinct_publications, to_analysis_records
from application.whitespace.base_rates import base_rates
from application.whitespace.figure_comparison import compare_published
from application.whitespace.publication_lag import lag_figures
from domain.protocols.whitespace import SourceIntegrityError
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

FILES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
PUBLISHED = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_lag_base_rates_published.json"
FULL_ORIGINS = [2006, *range(2012, 2023)]  # 2006: the development origin of §7.1
HIDDEN_ORIGINS, HIDDEN_YEARS = [2013, 2016, 2019], [2007, 2008, 2009, 2011, 2012]
NATIONAL_ORIGINS, FILING_COMPLETE_UNTIL = [2013, 2016, 2019, 2022], 2022


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data" / "raw" / "oepm_open")
    parser.add_argument("--write-results", type=Path, help="also write the reproduced figures as JSON")
    args = parser.parse_args()

    files = json.loads(FILES.read_text(encoding="utf-8"))["files"]
    source = OepmBiblioSource(args.data_dir, {name: f["sha256"] for name, f in files.items()})
    try:
        records = to_analysis_records(source.read())
    except SourceIntegrityError as exc:
        print(f"SOURCE NOT VERIFIED: {exc}")
        return 2

    national = [r for r in records if not r.is_ep_translation]
    lag = lag_figures(records)
    lag["lag_distinct_publications_only"] = lag_figures(distinct_publications(records))["lag"]  # sensitivity, P4
    figures: dict[str, Any] = {
        "lag": lag,
        "full_corpus": base_rates(records, FULL_ORIGINS, hidden_year_origins=HIDDEN_ORIGINS, hidden_years=HIDDEN_YEARS),
        "national": {
            "records": len(national),
            "records_with_two_or_more_subclasses": sum(len(r.subclasses) >= 2 for r in national),
            "origins": base_rates(national, NATIONAL_ORIGINS, filing_outcome_until=FILING_COMPLETE_UNTIL),
        },
    }
    figures["national"]["lag"] = lag_figures(national)["lag"]["national"]

    published = json.loads(PUBLISHED.read_text(encoding="utf-8"))["figures"]
    # the national lag line of §7.2 is the national group of §4.2; the printed value is checked once, in "lag"
    differences = compare_published(published, figures)
    if args.write_results:
        output = {"records_analysed": len(records), "figures": figures, "differences_from_published": differences}
        args.write_results.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for line in differences:
        print(line)
    print(
        f"{len(differences)} difference(s) from the published figures"
        if differences
        else "All published figures reproduced"
    )
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
