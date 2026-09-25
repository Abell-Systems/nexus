#!/usr/bin/env python3
"""Retroactive, read-only conformance audit of the frozen v0.1 Minesoft Origin extraction
(experiments/article/minesoft_origin_2000_2025/, commit c7bf50e) against extraction_contract_v1.

Never modifies the audited CSVs. Never regenerates or backfills missing evidence -- a
LEGACY_UNVERIFIABLE finding stays LEGACY_UNVERIFIABLE. Writes a baseline report, not a
certification: its purpose is to make legacy gaps explicit, not to declare v0.1 fully conformant
to a contract it predates.

Usage: python3 audit_minesoft_origin_v0_1.py
Writes: experiments/article/audit/v0.1_conformance_report.json
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_extraction_contract import CONTRACT_VERSION, evaluate_legacy_compound  # noqa: E402

ARTICLE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ARTICLE_DIR / "minesoft_origin_2000_2025"
AUDIT_DIR = ARTICLE_DIR / "audit"


def _compound_display_name(csv_filename: str) -> str:
    # e.g. "01_Brentuximab_vedotin_ids.csv" -> "Brentuximab vedotin"
    stem = csv_filename.removesuffix("_ids.csv")
    _, _, name_part = stem.partition("_")
    return name_part.replace("_", " ")


def _audit_one_csv(csv_path: Path, readme_text: str) -> dict:
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    capped = rows[0]["capped"] == "True"
    total_hits_reported = int(rows[0]["total_hits_reported"])
    compound_display_name = _compound_display_name(csv_path.name)

    findings = evaluate_legacy_compound(
        compound_display_name, rows, capped, total_hits_reported, readme_text,
    )
    return {
        "csv_file": csv_path.name,
        "compound": compound_display_name,
        "findings": [
            {"invariant": f.invariant, "verdict": f.verdict, "detail": f.detail} for f in findings
        ],
    }


def main() -> int:
    readme_text = (DATASET_DIR / "README.md").read_text(encoding="utf-8")
    csv_paths = sorted(DATASET_DIR.glob("*_ids.csv"))
    if not csv_paths:
        print(f"No CSV files found under {DATASET_DIR}", file=sys.stderr)
        return 1

    compounds = {}
    summary = {"PASS": 0, "FAIL": 0, "NOT_APPLICABLE": 0, "LEGACY_UNVERIFIABLE": 0}
    for csv_path in csv_paths:
        result = _audit_one_csv(csv_path, readme_text)
        compounds[result["compound"]] = result
        for finding in result["findings"]:
            summary[finding["verdict"]] += 1

    report = {
        "contract_version": CONTRACT_VERSION,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "minesoft_origin_2000_2025 v0.1 (frozen c7bf50e)",
        "note": (
            "Read-only retroactive baseline. LEGACY_UNVERIFIABLE findings are never backfilled -- "
            "this report documents what the v0.1 artifact can and cannot demonstrate against a "
            "contract it predates, not a certification of full conformance."
        ),
        "compounds": compounds,
        "summary": summary,
    }

    AUDIT_DIR.mkdir(exist_ok=True)
    report_path = AUDIT_DIR / "v0.1_conformance_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"Wrote {report_path}")
    print(f"Summary: {summary}")

    unexpected_fails = [
        (c, f) for c, result in compounds.items() for f in result["findings"]
        if f["verdict"] == "FAIL"
    ]
    if unexpected_fails:
        print(f"\n{len(unexpected_fails)} unexpected FAIL finding(s):", file=sys.stderr)
        for compound, finding in unexpected_fails:
            print(f"  {compound}: {finding['invariant']} -- {finding['detail']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
