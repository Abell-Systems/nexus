#!/usr/bin/env python3
"""Exposure gate of vertical 3 on the completeness of the reference year (exit 0 allowed, 1 blocked).

  python scripts/check_vertical3_completeness.py [--exposure FILE]

Reads the versioned exposure result and prints the decision with its reasons. A missing or unreadable file blocks.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.whitespace.completeness_gate import completeness_gate

EXPOSURE = REPO_ROOT / "docs" / "whitespace" / "oepm-corpus-exposure-results.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--exposure", type=Path, default=EXPOSURE)
    args = parser.parse_args()
    try:
        exposure = json.loads(args.exposure.read_text(encoding="utf-8"))
    except (
        OSError,
        ValueError,
        RecursionError,
    ) as error:  # unreadable, not JSON, bad UTF-8 or nested beyond the parser: blocked
        print(f"blocked: {args.exposure} cannot be read as JSON ({type(error).__name__})", file=sys.stderr)
        exposure = {}
    decision = completeness_gate(exposure if isinstance(exposure, dict) else {})
    print(json.dumps(decision, indent=2))
    return 0 if decision["allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
