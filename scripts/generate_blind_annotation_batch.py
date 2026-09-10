#!/usr/bin/env python3
"""Generates the canonical blinded annotation candidate pool under strict temporal eligibility (PR-E.1)."""

import hashlib
import sys
from pathlib import Path

# Ensure backend/src/main is on sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "backend" / "src" / "main"))

from infrastructure.annotation.blind_export import generate_blinded_annotation_set


def main() -> int:
    benchmark_path = repo_root / "experiments" / "shared" / "dataset_pilot_benchmark.json"
    output_dir = repo_root / "data" / "annotations"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "pilot_strict_annotation_batch.json"
    sidecar_file = output_dir / "pilot_strict_annotation_batch.json.sha256"

    print(f"Loading benchmark from {benchmark_path}...")
    annotation_set = generate_blinded_annotation_set(
        benchmark_path,
        temporal_pool_mode="strict",
        seed=42,
    )

    serialized_json = annotation_set.model_dump_json(indent=2) + "\n"
    output_file.write_text(serialized_json, encoding="utf-8")
    print(f"Emitted canonical batch to {output_file}")

    digest = hashlib.sha256(serialized_json.encode("utf-8")).hexdigest()
    sidecar_content = f"{digest}  {output_file.name}\n"
    sidecar_file.write_text(sidecar_content, encoding="utf-8")
    print(f"Emitted sidecar to {sidecar_file}: {digest}")

    total_candidates = sum(len(d.entries) for d in annotation_set.demands)
    print(f"Validation successful: {len(annotation_set.demands)} demands, {total_candidates} candidate pairs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
