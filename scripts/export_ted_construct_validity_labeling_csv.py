#!/usr/bin/env python3
"""Exports the TED construct-validity control sample (JSON manifest) to flat CSV
templates for blind human labeling -- demand_id, description_text, language_code,
judgment (blank). Writes three identical blank copies: template, valentin, lydia.
Annotators label TECHNICAL_PROBLEM / GENERIC_PROCUREMENT / EMPTY_INSUFFICIENT per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md SS3,
independently, blind to each other and to any LLM output."""

import csv
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIELDNAMES = ["demand_id", "description_text", "language_code", "judgment"]


def main() -> int:
    manifest_path = REPO_ROOT / "data" / "annotations" / "ted_construct_validity_control_sample_manifest.json"
    mapped_path = REPO_ROOT / "data" / "experiments" / "phase2_v4" / "candidates_mapped.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mapped_path_bytes = mapped_path.read_bytes()
    actual_mapped_sha256 = hashlib.sha256(mapped_path_bytes).hexdigest()
    if actual_mapped_sha256 != manifest["source_mapped_candidates_sha256"]:
        raise ValueError(
            "candidates_mapped.json has changed since the control sample was built "
            f"(expected sha256 {manifest['source_mapped_candidates_sha256']}, got {actual_mapped_sha256})"
        )
    mapped_by_id = {c["demand_id"]: c for c in json.loads(mapped_path_bytes)}

    rows = []
    for demand_id in manifest["all_ids"]:
        c = mapped_by_id[demand_id]
        rows.append({
            "demand_id": demand_id,
            "description_text": c["description_text"],
            "language_code": c["language_code"],
            "judgment": "",
        })

    for suffix in ("template", "valentin", "lydia"):
        out_path = REPO_ROOT / "data" / "annotations" / f"ted_construct_validity_labeling_{suffix}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
