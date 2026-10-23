#!/usr/bin/env python3
"""Writes a SYNTHETIC demand corpus with the schema of the original N=39 corpus (37 + 2 records).

Every text is invented and every record is marked `synthetic_control` with source_authority "synthetic". It exists
to run the software and the generic conformance check without the original third-party data. It is NOT the study's
corpus: a result obtained on it says nothing about the original study and must not be reported as reproducing it.
Deterministic: same output bytes on every run.

  python synthetic/generate_synthetic_corpus.py [--out DIR]     # default: synthetic/data
"""

import argparse
import hashlib
import json
from pathlib import Path

NAME = "dataset_phase2_demand_corpus_n39"
GROUPS = (("SYNTHETIC-A-", 37), ("SYNTHETIC-B-", 2))
TOPICS = ("coating", "sensor", "membrane", "catalyst", "battery", "filter", "adhesive", "actuator")


def _demand(prefix: str, n: int) -> dict:
    topic = TOPICS[n % len(TOPICS)]
    demand_id = f"{prefix}{n:03d}"
    return {
        "demand_id": demand_id,
        "title": f"Synthetic example {n:03d}: invented request about a {topic}",
        "description": (
            f"This is an invented description number {n:03d} written only to exercise the software. "
            f"It pretends to ask for a {topic} with some fictional property, and it is long enough to pass the "
            "twenty-five word minimum that the conformance check applies to every demand in the corpus."
        ),
        "posted_date": None,
        "target_cpc_prefixes": [],
        "origin_country": "Spain",
        "spanish_origin_level": "level_1_direct_metadata",
        "external_reference": None,
        "provenance": {
            "source_authority": "synthetic",
            "source_uri": f"https://example.invalid/synthetic/{demand_id}",
            "extraction_timestamp": "2000-01-01T00:00:00Z",
            "raw_payload_sha256": hashlib.sha256(demand_id.encode()).hexdigest(),
            "modality": "synthetic_control",
        },
    }


def build() -> tuple[bytes, dict]:
    demands = [_demand(prefix, n) for prefix, count in GROUPS for n in range(1, count + 1)]
    corpus = {
        "dataset_id": "synthetic-demand-corpus-n39",
        "schema_version": "1.0.0",
        "dataset_version": "1.0.0",
        "description": "SYNTHETIC demand corpus (37 + 2 invented records) with the schema of the original N=39 corpus. "
        "Not the study's data.",
        "demands": demands,
    }
    data = (json.dumps(corpus, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    manifest = {
        "dataset_id": corpus["dataset_id"],
        "schema_version": "1.0.0",
        "dataset_version": "1.0.0",
        "source_authorities": ["synthetic"],
        "demand_count": len(demands),
        "patent_count": 0,
        "annotation_count": 0,
        "demand_id_prefix_counts": {prefix: count for prefix, count in GROUPS},
        "content_sha256": hashlib.sha256(data).hexdigest(),
    }
    return data, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "data")
    args = parser.parse_args()
    data, manifest = build()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / f"{NAME}.json").write_bytes(data)
    (args.out / f"{NAME}.sha256").write_text(f"{manifest['content_sha256']}  {NAME}.json\n", encoding="utf-8")
    (args.out / f"{NAME}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote synthetic corpus to {args.out}: {manifest['demand_count']} demands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
