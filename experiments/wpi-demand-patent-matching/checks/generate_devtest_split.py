#!/usr/bin/env python3
"""Instantiates the generic stratified_split() mechanism (backend/src/main/
application/evaluation/stratified_split.py) against the WPI Phase 2 sector
assignments (#92), per experiments/wpi-demand-patent-matching/config/devtest_split_v1.json
and docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md.

Reads only sector_assignments_n24_v1.json's `assignments` list (the 13
sector-covered demands) -- `no_sector_coverage` is never read for membership.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.evaluation.stratified_split import stratified_split  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

ASSIGNMENTS_NAME = "sector_assignments_n24_v1.json"
ASSIGNMENTS_SHA_NAME = "sector_assignments_n24_v1.sha256"
CONFIG_NAME = "devtest_split_v1.json"
CONFIG_SHA_NAME = "devtest_split_v1.sha256"
SPLIT_NAME = "devtest_split_n13_v1.json"
SPLIT_SHA_NAME = "devtest_split_n13_v1.sha256"
SPLIT_MANIFEST_NAME = "devtest_split_n13_v1.manifest.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256_file(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    assignments_sha = _verify_sidecar(DATA_DIR / ASSIGNMENTS_NAME, DATA_DIR / ASSIGNMENTS_SHA_NAME)
    config_sha = _verify_sidecar(CONFIG_DIR / CONFIG_NAME, CONFIG_DIR / CONFIG_SHA_NAME)

    config = json.loads((CONFIG_DIR / CONFIG_NAME).read_text(encoding="utf-8"))
    assert config["assignments_sha256"] == assignments_sha, "config's pinned input hash is stale"

    assignments = json.loads((DATA_DIR / ASSIGNMENTS_NAME).read_text(encoding="utf-8"))
    covered = assignments["assignments"]  # the 13 -- no_sector_coverage deliberately unused

    result = stratified_split(
        covered,
        stratum_key=lambda a: a[config["stratum_key"]],
        item_id=lambda a: a["demand_id"],
        dev_fraction=config["dev_fraction"],
        seed=config["seed"],
    )

    split_dataset = {
        "dataset_id": "nexus-phase2-devtest-split-n13-v1",
        "dev": list(result.dev.demand_ids),
        "test": list(result.test.demand_ids),
    }

    split_path = DATA_DIR / SPLIT_NAME
    split_path.write_text(json.dumps(split_dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    split_sha = _sha256_file(split_path)

    manifest = {
        "dev_count": len(result.dev.demand_ids),
        "test_count": len(result.test.demand_ids),
        "per_stratum_counts": {c.stratum: {"dev": c.dev, "test": c.test} for c in result.per_stratum_counts},
        "dev_fraction": config["dev_fraction"],
        "seed": config["seed"],
        "content_sha256": split_sha,
        "derived_from": {
            "assignments_sha256": assignments_sha,
            "config_sha256": config_sha,
        },
    }
    (DATA_DIR / SPLIT_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (DATA_DIR / SPLIT_SHA_NAME).write_text(f"{split_sha}  {SPLIT_NAME}\n", encoding="utf-8")

    print(
        f"Wrote dev={len(result.dev.demand_ids)} test={len(result.test.demand_ids)} "
        f"-> {split_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
