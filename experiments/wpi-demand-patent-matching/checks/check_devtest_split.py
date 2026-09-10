#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 Dev/Test split artifact (#79).

Verifies devtest_split_n13_v1.json against sector_assignments_n24_v1.json (#92) and
devtest_split_v1.json (this experiment's config), per docs/superpowers/specs/
2026-09-10-stratified-devtest-split-design.md. The population is exactly the 13
`assignments` entries -- the 11 `no_sector_coverage` entries (#90/#91) must never
appear in dev or test.

Also recomputes the split in-memory via stratified_split() (same inputs/derivation
as generate_devtest_split.py) and asserts it matches the committed artifact exactly,
proving reproducibility on every run rather than as a one-time manual claim. This
check only reads files and computes in memory -- it never writes to disk.
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

# Expected floor-policy outcome for this run's real per-stratum sizes
# ({1: ENERGY_STORAGE, 2: SANITARY_MATERIALS, 3: METALLURGY, 3: INDUSTRIAL_MACHINERY_IOT,
# 4: BIOTECHNOLOGY}) at dev_fraction=0.40 -- see the plan/spec's floor-policy table.
EXPECTED_STRATUM_SIZE_TO_DEV_TEST = {1: (0, 1), 2: (1, 1), 3: (1, 2), 4: (2, 2)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    assignments_sha = _verify_sidecar(DATA_DIR / ASSIGNMENTS_NAME, DATA_DIR / ASSIGNMENTS_SHA_NAME)
    config_sha = _verify_sidecar(CONFIG_DIR / CONFIG_NAME, CONFIG_DIR / CONFIG_SHA_NAME)
    split_sha = _verify_sidecar(DATA_DIR / SPLIT_NAME, DATA_DIR / SPLIT_SHA_NAME)

    config = json.loads((CONFIG_DIR / CONFIG_NAME).read_text(encoding="utf-8"))
    assert config["assignments_sha256"] == assignments_sha, (
        "devtest_split_v1.json's pinned assignments_sha256 no longer matches "
        "sector_assignments_n24_v1.json -- that input changed underneath this config."
    )

    assignments = json.loads((DATA_DIR / ASSIGNMENTS_NAME).read_text(encoding="utf-8"))
    covered = {a["demand_id"]: a["sector_code"] for a in assignments["assignments"]}
    no_coverage_ids = {e["demand_id"] for e in assignments["no_sector_coverage"]}

    split = json.loads((DATA_DIR / SPLIT_NAME).read_text(encoding="utf-8"))
    manifest = json.loads((DATA_DIR / SPLIT_MANIFEST_NAME).read_text(encoding="utf-8"))

    assert manifest["content_sha256"] == split_sha
    assert manifest["derived_from"]["assignments_sha256"] == assignments_sha
    assert manifest["derived_from"]["config_sha256"] == config_sha
    assert manifest["dev_fraction"] == config["dev_fraction"]
    assert manifest["seed"] == config["seed"]

    dev_ids = split["dev"]
    test_ids = split["test"]

    assert len(dev_ids) == len(set(dev_ids)), "Duplicate demand_id in dev"
    assert len(test_ids) == len(set(test_ids)), "Duplicate demand_id in test"
    assert not (set(dev_ids) & set(test_ids)), "A demand_id appears in both dev and test"
    assert set(dev_ids) | set(test_ids) == set(covered), (
        f"dev + test do not cover exactly the 13 sector-covered demand_ids "
        f"(missing={set(covered) - (set(dev_ids) | set(test_ids))}, "
        f"extra={(set(dev_ids) | set(test_ids)) - set(covered)})"
    )
    assert not (set(dev_ids) & no_coverage_ids), "A no_sector_coverage demand_id leaked into dev"
    assert not (set(test_ids) & no_coverage_ids), "A no_sector_coverage demand_id leaked into test"

    per_stratum: dict[str, dict[str, int]] = {}
    for demand_id, sector in covered.items():
        side = "dev" if demand_id in dev_ids else "test"
        per_stratum.setdefault(sector, {"dev": 0, "test": 0})[side] += 1

    stratum_sizes: dict[str, int] = {}
    for sector in covered.values():
        stratum_sizes[sector] = stratum_sizes.get(sector, 0) + 1

    for sector, size in stratum_sizes.items():
        expected = EXPECTED_STRATUM_SIZE_TO_DEV_TEST.get(size)
        assert expected is not None, (
            f"{sector}: no expected dev/test pair defined for stratum size {size} "
            f"-- update EXPECTED_STRATUM_SIZE_TO_DEV_TEST"
        )
        expected_dev, expected_test = expected
        actual = per_stratum[sector]
        assert (actual["dev"], actual["test"]) == (expected_dev, expected_test), (
            f"{sector} (n={size}): expected dev/test={expected_dev}/{expected_test}, "
            f"got {actual['dev']}/{actual['test']}"
        )

    assert manifest["per_stratum_counts"] == per_stratum

    # Reproducibility: recompute the split in-memory (same derivation as
    # generate_devtest_split.py) and assert it matches the committed artifact exactly.
    recomputed = stratified_split(
        assignments["assignments"],
        stratum_key=lambda a: a[config["stratum_key"]],
        item_id=lambda a: a["demand_id"],
        dev_fraction=config["dev_fraction"],
        seed=config["seed"],
    )
    assert set(recomputed.dev.demand_ids) == set(dev_ids), (
        "Recomputed Dev partition does not match the committed artifact -- "
        "stratified_split() is not reproducing devtest_split_n13_v1.json"
    )
    assert set(recomputed.test.demand_ids) == set(test_ids), (
        "Recomputed Test partition does not match the committed artifact -- "
        "stratified_split() is not reproducing devtest_split_n13_v1.json"
    )

    print(f"OK: dev={len(dev_ids)} test={len(test_ids)} per_stratum={per_stratum}")
    print("OK: recomputed split reproduces the committed artifact exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
