#!/usr/bin/env python3
"""Exports the #104 dense blind-spot annotation batch (JSON) to flat CSV
templates for human annotation -- same columns as the original at-scale
template (demand_id,publication_id,title,abstract,classifications_cpc,
judgment), so the same annotation guide/scale applies unchanged. Writes
three identical blank copies: template, valentin, lydia."""

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIELDNAMES = ["demand_id", "publication_id", "title", "abstract", "classifications_cpc", "judgment"]


def main() -> int:
    in_path = REPO_ROOT / "data" / "annotations" / "ted_dense_blindspot_annotation_batch.json"
    data = json.loads(in_path.read_text(encoding="utf-8"))

    rows = []
    for demand in data["demands"]:
        for entry in demand["entries"]:
            ev = entry["evidence"]
            rows.append({
                "demand_id": demand["demand_id"],
                "publication_id": ev["publication_id"],
                "title": ev["title"],
                "abstract": ev["abstract"],
                "classifications_cpc": "; ".join(ev["classifications_cpc"]),
                "judgment": "",
            })

    for suffix in ("template", "valentin", "lydia"):
        out_path = REPO_ROOT / "data" / "annotations" / f"ted_dense_blindspot_annotation_{suffix}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
