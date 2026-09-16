#!/usr/bin/env python3
"""CLI gate for a FUTURE Minesoft extraction run against extraction_contract_v1.

Usage: python3 check_extraction_run.py <run_bundle.json>

<run_bundle.json> is a single JSON file describing one compound's extraction run:
{
  "extraction_run_id": "...", "compound": "...", "capped": false, "extraction_cap": null,
  "total_hits_reported": 1234, "page_size": 50, "pagination_mode": "sequential_single_run",
  "pages": [{"page_number": 0, "raw_response_path": "raw/page_0.json", "content_sha256": "<hex>", ...}],
  "rows": [{"publication_id": "...", "extraction_run_id": "...", "page_number": 0, "row_index": 0}]
}

raw_response_path in each page is resolved relative to the bundle file's own directory; this script
reads each referenced raw file and verifies its actual sha256 against the page's declared
content_sha256 (evaluate_future_run stays pure by taking these pre-computed hashes as input).

Hard-fails (non-zero exit) on any FAIL finding. Never patches, fills in, or silently accepts
missing/partial data.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_extraction_contract import CONTRACT_VERSION, FAIL, evaluate_future_run  # noqa: E402


def _compute_page_hashes(bundle_dir: Path, pages: list[dict]) -> dict[int, str]:
    hashes: dict[int, str] = {}
    for page in pages:
        raw_path = page.get("raw_response_path")
        if not raw_path:
            continue
        full_path = bundle_dir / raw_path
        if not full_path.is_file():
            continue
        hashes[page["page_number"]] = hashlib.sha256(full_path.read_bytes()).hexdigest()
    return hashes


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: check_extraction_run.py <run_bundle.json>", file=sys.stderr)
        return 2

    bundle_path = Path(argv[1]).resolve()
    if not bundle_path.is_file():
        print(f"Run bundle not found: {bundle_path}", file=sys.stderr)
        return 2

    run = json.loads(bundle_path.read_text(encoding="utf-8"))

    bundle_contract_version = run.get("contract_version", CONTRACT_VERSION)
    if bundle_contract_version != CONTRACT_VERSION:
        print(
            f"contract_version mismatch: bundle declares {bundle_contract_version!r}, "
            f"validator implements {CONTRACT_VERSION!r}",
            file=sys.stderr,
        )
        return 2

    computed_hashes = _compute_page_hashes(bundle_path.parent, run.get("pages", []))
    findings = evaluate_future_run(run, computed_hashes=computed_hashes)

    for finding in findings:
        print(f"{finding.invariant}: {finding.verdict} -- {finding.detail}")

    failures = [f for f in findings if f.verdict == FAIL]
    if failures:
        print(f"\n{len(failures)} invariant(s) FAILED. Run does not conform to {CONTRACT_VERSION}.", file=sys.stderr)
        return 1

    print(f"\nAll invariants satisfied for {CONTRACT_VERSION}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
