"""Writes the product demand snapshot from the frozen n39 demand corpus.

The backend must not read from experiments/ (ADR 0026), so the demands the MVP serves are copied once,
verbatim, into data/snapshots/operational_corpus_v1/demands_v1.json together with the sha256 of the source
file. The embedding generation records the same hash, which lets the service check the two belong together.
"""

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    REPO_ROOT / "experiments" / "wpi-demand-patent-matching" / "data" / "dataset_phase2_demand_corpus_n39.json"
)
DEFAULT_OUT = REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1" / "demands_v1.json"


def build_snapshot(demand_corpus_path: Path) -> dict:
    raw_bytes = demand_corpus_path.read_bytes()
    demands = json.loads(raw_bytes.decode("utf-8"))["demands"]
    return {
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "demands": [
            {
                "demand_id": d["demand_id"],
                "title": d["title"],
                "description": d["description"],
                "posted_date": d.get("posted_date"),
                "origin_country": d.get("origin_country"),
                "source_url": (d.get("provenance") or {}).get("source_uri", ""),
            }
            for d in demands
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the product demand snapshot")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    snapshot = build_snapshot(args.source)
    args.out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}: {len(snapshot['demands'])} demands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
