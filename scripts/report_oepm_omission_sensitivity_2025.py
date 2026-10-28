#!/usr/bin/env python3
"""Descriptive sensitivity of the 2025 unobserved pairs (protocol: docs/whitespace/oepm-omission-sensitivity-2025-protocol.md).

Aggregate output only: no pair and no identifier is written. Stops if S-A does not reproduce 621 / 192,510 / 149,048.

  python scripts/report_oepm_omission_sensitivity_2025.py --corpus-dir data/raw/oepm_open --write FILE
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.analysis_records import to_analysis_records
from application.whitespace.omission_sensitivity_2025 import (
    compare,
    o4_years,
    remove_units,
    stratified_sample,
    units_of_year,
    units_per_year,
)
from application.whitespace.unobserved_pairs import unobserved_pairs
from domain.models.whitespace import RejectedRecord
from infrastructure.sources.patent.oepm_biblio import OepmBiblioSource

CORPUS_FIGURES = REPO_ROOT / "config" / "whitespace" / "oepm_biblio_2000_2025.json"
ORIGIN = 2025
EXPECTED_S_A = {"active": 621, "pairs": 192510, "unobserved": 149048}
SEEDS = (20261101, 20261102, 20261103, 20261104, 20261105)
THRESHOLDS = (10, 40)


def run(records, min_documents=20):
    return unobserved_pairs(records, ORIGIN, min_documents)


def say(text):
    print(f"[{time.strftime('%H:%M:%S')}] {text}", flush=True)


def summary(rows):
    values = [r["spearman_E"] for r in rows if r["spearman_E"] is not None]
    return {"min": min(values), "median": statistics.median(values), "max": max(values)} if values else None


def checked(stats):
    assert stats["became_observed"] == 0, "removal created a co-classification: invariant of amendment 1 failed"
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()

    figures = json.loads(CORPUS_FIGURES.read_text(encoding="utf-8"))
    files = {n: f["sha256"] for n, f in figures["files"].items()}
    outcomes = list(OepmBiblioSource(args.corpus_dir, files).read())
    rejected = sum(isinstance(o, RejectedRecord) for o in outcomes)
    records = to_analysis_records(outcomes)
    units = o4_years(records)
    expected = figures["figures"]  # the published manifest: accepted records, rejected records, distinct identifiers (O4 units)
    assert (len(records), rejected, len(units)) == (expected["records"], expected["rejected"], expected["distinct_doc_ids"]), (
        "record counts differ from the corpus manifest"
    )
    per_year = units_per_year(units)
    out = {
        "protocol": "docs/whitespace/oepm-omission-sensitivity-2025-protocol.md (with amendment 1)",
        "corpus": {"source_id": figures["source_id"], "files": files},
        "units": {"records_read": len(outcomes), "records_rejected": rejected, "records_accepted": len(records), "o4_units": len(units), "o4_units_per_year": {str(y): n for y, n in per_year.items()}},
    }
    say(f"read {len(outcomes)}, rejected {rejected}, accepted {len(records)}, O4 units {len(units)}")

    base = run(records)
    if base["counts"] != EXPECTED_S_A:
        say(f"S-A DOES NOT REPRODUCE: {base['counts']}; stopping")
        return 1
    out["S-A"] = base["counts"]
    say("S-A reproduces")

    b1 = {}
    for year in per_year:
        if year == 2010:
            continue
        b1[str(year)] = checked(compare(base, run(remove_units(records, units_of_year(units, year)))))
        say(f"S-B1 {year}")
    out["S-B1"] = {"per_year": b1, "spearman_E": summary(list(b1.values()))}

    c = {}
    for seed in SEEDS:
        removed = stratified_sample(units, seed)
        c[str(seed)] = checked(compare(base, run(remove_units(records, removed))))
        c[str(seed)]["removed_units"] = len(removed)
        say(f"S-C seed {seed}")
    again = compare(base, run(remove_units(records, stratified_sample(units, SEEDS[0]))))
    assert {k: v for k, v in c[str(SEEDS[0])].items() if k != "removed_units"} == again, "same seed gave a different result"
    out["S-C"] = {"per_seed": c, "spearman_E": summary(list(c.values()))}

    out["S-D"] = {}
    for threshold in THRESHOLDS:
        out["S-D"][str(threshold)] = compare(base, run(records, threshold))
        say(f"S-D {threshold}")

    args.write.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    say(f"written {args.write}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
