#!/usr/bin/env python3
"""Unobserved IPC subclass pairs at the end of the corpus, with their expected count under independence (data of vertical 3).

The corpus is read through the adapter after its hashes are verified. The result is checked against the versioned
subclass-pairs result by running the same function at the origins that file holds. It states an expected count under
independence within publication years; it is not the study's null model, a score, a ranking or a prediction.

  python scripts/report_oepm_unobserved_pairs.py --corpus-dir data/raw/oepm_open [--write FILE]
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.analysis_records import to_analysis_records
from application.whitespace.subclass_pairs import subclass_pairs
from application.whitespace.unobserved_pairs import unobserved_pairs
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
OBSERVED = REPO_ROOT / "docs" / "whitespace" / "oepm-subclass-pairs-results.json"
ORIGIN = 2025


def check_against_observed(result: dict, observed: dict) -> None:
    """Fail loudly if observed + unobserved is not every pair of active subclasses, or if a listed pair is observed."""
    active = result["active"]
    assert active == observed["active"], (
        "active subclasses differ from the observed-pairs result (identifiers or documents)"
    )
    assert result["counts"]["active"] == len(active)
    assert result["counts"]["pairs"] == len(active) * (len(active) - 1) // 2
    assert sum(len(v) for v in result["pairs"].values()) == result["counts"]["unobserved"]
    for a, row in result["pairs"].items():
        for b, value in row.items():
            assert a < b and a in active and b in active, f"pair {a}|{b} is not between two active subclasses"
            assert value >= 0, f"negative expected count for {a}|{b}"
    observed_pairs = {tuple(key.split("|")) for key in observed["pairs"]}
    listed = {(a, b) for a, row in result["pairs"].items() for b in row}
    assert not listed & observed_pairs, "a listed pair is observed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()

    figures = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))
    files = figures["files"]
    records = to_analysis_records(OepmBiblioSource(args.corpus_dir, {n: f["sha256"] for n, f in files.items()}).read())
    observed = json.loads(OBSERVED.read_text(encoding="utf-8"))
    for origin in (2006, 2022):  # the origins the versioned observed result holds: same function, same totals
        at_origin = unobserved_pairs(records, origin)
        check_against_observed(at_origin, observed[str(origin)])
        assert at_origin["counts"]["unobserved"] == at_origin["counts"]["pairs"] - len(observed[str(origin)]["pairs"])
    result = unobserved_pairs(records, ORIGIN)
    own = subclass_pairs(records, ORIGIN)
    check_against_observed(result, own)
    assert result["counts"]["unobserved"] == result["counts"]["pairs"] - len(own["pairs"])
    result["corpus"] = {"source_id": figures["source_id"], "files": {n: f["sha256"] for n, f in files.items()}}
    c = result["counts"]
    print(ORIGIN, c["active"], "active,", c["pairs"] - c["unobserved"], "observed,", c["unobserved"], "not observed")
    if args.write:
        args.write.write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
