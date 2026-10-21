#!/usr/bin/env python3
"""Observed IPC subclass pairs at two origins, with the counts behind each (data of the descriptive explorer).

The corpus is read through the adapter after its hashes are verified. The result is checked against the versioned
section-density result before it is written: active subclasses, observed pairs and the cells by section pair. Describes
the observed corpus only; an unobserved pair is an absence, not an opportunity, and nothing is ranked.

  python scripts/report_oepm_subclass_pairs.py --corpus-dir data/raw/oepm_open [--write FILE]
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.analysis_records import to_analysis_records
from application.whitespace.subclass_pairs import subclass_pairs
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
DENSITY = REPO_ROOT / "docs" / "whitespace" / "oepm-section-density-results.json"
ORIGINS = [2006, 2022]


def check_against_density(result: dict, density: dict) -> None:
    """Fail loudly if the three invariants of the contract (active, observed, universe) or any cell differ."""
    active, pairs = result["active"], result["pairs"]
    assert len(active) == density["active_subclasses"], "active subclasses differ from the section density"
    assert len(pairs) == density["seen_pairs"], "observed pairs differ from the section density"
    universe = len(active) * (len(active) - 1) // 2
    assert universe - len(pairs) == sum(c["possible_pairs"] - c["seen_pairs"] for c in density["cells"].values())
    per_section = {section: sum(1 for s in active if s[0] == section) for section in sorted({s[0] for s in active})}
    assert per_section == density["active_subclasses_by_section"], "active subclasses by section differ"
    for cell, figures in density["cells"].items():
        x, y = cell
        derived = per_section[x] * (per_section[x] - 1) // 2 if x == y else per_section[x] * per_section[y]
        assert derived == figures["possible_pairs"], f"universe of cell {cell} differs from the section density"
        seen = sum(1 for key in pairs if {key[0], key.split("|")[1][0]} == set(cell))
        assert seen == figures["seen_pairs"], f"cell {cell} differs from the section density"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    files = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))["files"]
    records = to_analysis_records(OepmBiblioSource(args.corpus_dir, {n: f["sha256"] for n, f in files.items()}).read())
    density = json.loads(DENSITY.read_text(encoding="utf-8"))
    report = {}
    for origin in ORIGINS:
        report[str(origin)] = result = subclass_pairs(records, origin)
        check_against_density(result, density[str(origin)])
        n = len(result["active"])
        print(
            origin,
            n,
            "active,",
            len(result["pairs"]),
            "observed,",
            n * (n - 1) // 2 - len(result["pairs"]),
            "not observed",
        )
    if args.write:
        args.write.write_text(json.dumps(report, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
