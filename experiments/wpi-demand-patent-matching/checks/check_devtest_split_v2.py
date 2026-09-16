#!/usr/bin/env python3
"""Independent check gate for clean organization-aware Dev/Test split v2 (ADR 0030).

Verifies devtest_split_n18_v2.json against:
- dataset_phase2_organization_audited_corpus_v1.json (audited corpus, N=18)
- phase2_demand_independence_audit_n24_v1.json (independence audit, N=24)
- sector_assignments_n24_v1.json (sector assignments)
- devtest_split_v2.json (experiment config)
- devtest_split_n13_v1.json (historical split, verifying untouched integrity)

Invariants verified:
1. Sidecar integrity: all .sha256 sidecars match artifact contents.
2. Config hash pins: pinned hashes in devtest_split_v2.json match input hashes.
3. Manifest integrity: devtest_split_n18_v2.manifest.json content_sha256 and counts.
4. Partition invariants:
   - Dev count == 10, Test count == 8, total == 18.
   - Dev and Test are disjoint (Dev ∩ Test = ∅).
   - Dev ∪ Test = Audited Corpus (N=18).
   - Test contains zero UNKNOWN demands (every Test demand is INDEPENDENT).
   - Organizations in Dev (INDEPENDENT) and Test are strictly disjoint.
5. In-memory re-derivation reproducibility:
   Re-running organization_aware_split() reproduces devtest_split_n18_v2.json byte-for-byte.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.evaluation.organization_aware_split import (  # noqa: E402
    organization_aware_split,
)
from domain.models.annotation import DemandIndependenceStatus  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

CONFIG_NAME = "devtest_split_v2.json"
SPLIT_NAME = "devtest_split_n18_v2.json"
SPLIT_MANIFEST_NAME = "devtest_split_n18_v2.manifest.json"
HISTORICAL_SPLIT_NAME = "devtest_split_n13_v1.json"
CORPUS_NAME = "dataset_phase2_organization_audited_corpus_v1.json"
AUDIT_NAME = "phase2_demand_independence_audit_n24_v1.json"
ASSIGNMENTS_NAME = "sector_assignments_n24_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_sidecar(artifact_path: Path) -> Path:
    candidate_exact = artifact_path.with_name(artifact_path.name + ".sha256")
    if candidate_exact.exists():
        return candidate_exact
    candidate_suffix = artifact_path.with_suffix(".sha256")
    if candidate_suffix.exists():
        return candidate_suffix
    raise FileNotFoundError(f"Sidecar not found for {artifact_path}")


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name, f"{declared_name} != {artifact_path.name}"
    return computed


def main() -> int:
    config_path = CONFIG_DIR / CONFIG_NAME
    split_path = DATA_DIR / SPLIT_NAME
    historical_split_path = DATA_DIR / HISTORICAL_SPLIT_NAME
    corpus_path = DATA_DIR / CORPUS_NAME
    audit_path = DATA_DIR / AUDIT_NAME
    assignments_path = DATA_DIR / ASSIGNMENTS_NAME

    # 1. Sidecar integrity verification
    config_sha = _verify_sidecar(config_path, _find_sidecar(config_path))
    split_v2_sha = _verify_sidecar(split_path, _find_sidecar(split_path))
    historical_split_sha = _verify_sidecar(historical_split_path, _find_sidecar(historical_split_path))
    corpus_sha = _verify_sidecar(corpus_path, _find_sidecar(corpus_path))
    audit_sha = _verify_sidecar(audit_path, _find_sidecar(audit_path))
    assignments_sha = _verify_sidecar(assignments_path, _find_sidecar(assignments_path))

    # 2. Config hash pins verification
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["corpus_sha256"] == corpus_sha, "devtest_split_v2.json pinned corpus_sha256 mismatch"
    assert config["audit_sha256"] == audit_sha, "devtest_split_v2.json pinned audit_sha256 mismatch"
    assert config["assignments_sha256"] == assignments_sha, "devtest_split_v2.json pinned assignments_sha256 mismatch"

    # 3. Manifest integrity & counts verification
    manifest = json.loads((DATA_DIR / SPLIT_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["content_sha256"] == split_v2_sha, "Manifest content_sha256 mismatch"
    assert manifest["derived_from"]["corpus_sha256"] == corpus_sha, "Manifest derived corpus_sha256 mismatch"
    assert manifest["derived_from"]["audit_sha256"] == audit_sha, "Manifest derived audit_sha256 mismatch"
    assert manifest["derived_from"]["sectors_sha256"] == assignments_sha, "Manifest derived sectors_sha256 mismatch"
    assert manifest["derived_from"]["config_sha256"] == config_sha, "Manifest derived config_sha256 mismatch"
    assert manifest["total_demands"] == 18, f"Manifest total_demands={manifest['total_demands']} != 18"
    assert manifest["independent_demands"] == 12, f"Manifest independent_demands={manifest['independent_demands']} != 12"
    assert manifest["unknown_demands"] == 6, f"Manifest unknown_demands={manifest['unknown_demands']} != 6"
    assert manifest["dev_count"] == 10, f"Manifest dev_count={manifest['dev_count']} != 10"
    assert manifest["test_count"] == 8, f"Manifest test_count={manifest['test_count']} != 8"
    assert manifest["dev_verified_independent_count"] == 4
    assert manifest["test_verified_independent_count"] == 8
    assert manifest["unknown_split_policy"] == "dev_only"
    assert manifest["organization_overlap"] is False

    # 4. Invariants verification
    split = json.loads(split_path.read_text(encoding="utf-8"))
    dev_ids = split["dev"]
    test_ids = split["test"]

    assert len(dev_ids) == 10, f"Expected 10 dev demands, got {len(dev_ids)}"
    assert len(test_ids) == 8, f"Expected 8 test demands, got {len(test_ids)}"
    assert len(set(dev_ids)) == 10, "Duplicates found in dev partition"
    assert len(set(test_ids)) == 8, "Duplicates found in test partition"

    dev_set = set(dev_ids)
    test_set = set(test_ids)

    # Dev ∩ Test = ∅
    assert not (dev_set & test_set), f"Dev and Test partitions overlap: {dev_set & test_set}"

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    corpus_ids = [d["demand_id"] for d in corpus["demands"]]
    assert len(corpus_ids) == 18, f"Expected 18 demands in audited corpus, got {len(corpus_ids)}"
    corpus_set = set(corpus_ids)

    # Dev ∪ Test = Audited Corpus (N=18)
    assert dev_set | test_set == corpus_set, (
        f"Dev ∪ Test != Audited Corpus. Missing: {corpus_set - (dev_set | test_set)}, "
        f"Extra: {(dev_set | test_set) - corpus_set}"
    )

    # Load audit annotations
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    status_map = {e["demand_id"]: e["status"] for e in audit["entries"]}
    org_map = {e["demand_id"]: e.get("requesting_organization") for e in audit["entries"]}

    # Test ∩ UNKNOWN = ∅ (every Test demand belongs to INDEPENDENT)
    test_unknowns = [did for did in test_ids if status_map[did] == "UNKNOWN"]
    assert not test_unknowns, f"UNKNOWN demands found in Test partition: {test_unknowns}"
    for did in test_ids:
        assert status_map[did] == "INDEPENDENT", (
            f"Test demand {did} status is {status_map[did]}, expected INDEPENDENT"
        )

    # All UNKNOWN demands are in Dev
    dev_unknowns = [did for did in dev_ids if status_map[did] == "UNKNOWN"]
    assert len(dev_unknowns) == 6, f"Expected 6 UNKNOWN demands in Dev, got {len(dev_unknowns)}"

    # Verified organizations in Dev and Test are strictly disjoint
    dev_indep_orgs = {org_map[did] for did in dev_ids if status_map[did] == "INDEPENDENT"}
    test_orgs = {org_map[did] for did in test_ids}
    assert None not in test_orgs and "Anonymous Organization" not in test_orgs, (
        "Test partition contains unverified/anonymous organizations"
    )
    shared_orgs = dev_indep_orgs & test_orgs
    assert not shared_orgs, f"Cross-partition organization leakage detected: {shared_orgs}"

    # 5. In-memory re-derivation reproducibility
    assignments = json.loads(assignments_path.read_text(encoding="utf-8"))
    sector_map = {a["demand_id"]: a["sector_code"] for a in assignments.get("assignments", [])}

    demands_copy = [dict(d) for d in corpus["demands"]]
    for d in demands_copy:
        d["requesting_organization"] = org_map.get(d["demand_id"])

    recomputed = organization_aware_split(
        items=demands_copy,
        item_id=lambda d: d["demand_id"],
        org_key=lambda d: d.get("requesting_organization"),
        status_key=lambda d: DemandIndependenceStatus(status_map[d["demand_id"]]),
        stratum_key=lambda d: sector_map.get(d["demand_id"], config["missing_stratum"]),
        dev_fraction=config["dev_fraction"],
        base_seed=config["base_seed"],
        unknown_policy=config["unknown_split_policy"],
    )

    assert list(recomputed.dev.demand_ids) == dev_ids, (
        f"Recomputed Dev partition mismatch: {list(recomputed.dev.demand_ids)} != {dev_ids}"
    )
    assert list(recomputed.test.demand_ids) == test_ids, (
        f"Recomputed Test partition mismatch: {list(recomputed.test.demand_ids)} != {test_ids}"
    )

    # Verify sector assignments & stratum counts from recomputed stratified split
    expected_manifest_per_stratum = {
        c.stratum: {"dev": c.dev, "test": c.test} for c in recomputed.per_stratum_counts
    }
    assert manifest["per_stratum_counts"] == expected_manifest_per_stratum, (
        f"Manifest per_stratum_counts mismatch: {manifest['per_stratum_counts']} != {expected_manifest_per_stratum}"
    )

    recomputed_dataset = {
        "dataset_id": "nexus-phase2-devtest-split-n18-v2",
        "dev": list(recomputed.dev.demand_ids),
        "test": list(recomputed.test.demand_ids),
    }
    recomputed_json = json.dumps(recomputed_dataset, indent=2, ensure_ascii=False) + "\n"
    actual_json = split_path.read_text(encoding="utf-8")
    assert recomputed_json == actual_json, (
        "Byte-for-byte serialization mismatch against devtest_split_n18_v2.json"
    )

    # Historical split untouched check
    historical_split = json.loads(historical_split_path.read_text(encoding="utf-8"))
    assert len(historical_split["dev"]) + len(historical_split["test"]) == 13, (
        "Historical split devtest_split_n13_v1.json demand count has changed"
    )

    print("================================================================================")
    print("PASS: Clean Organization-Aware Dev/Test Split v2 Check Gate (ADR 0030)")
    print("================================================================================")
    print(f"Sidecars verified: {CONFIG_NAME}, {SPLIT_NAME}, {HISTORICAL_SPLIT_NAME},")
    print(f"                   {CORPUS_NAME}, {AUDIT_NAME}, {ASSIGNMENTS_NAME}")
    print("Config hash pins: VERIFIED")
    print("Manifest integrity & counts: VERIFIED")
    print(f"Partitions: Dev={len(dev_ids)} (4 indep + 6 unknown), Test={len(test_ids)} (8 indep + 0 unknown)")
    print("Invariants:")
    print("  - Dev ∩ Test = ∅")
    print("  - Dev ∪ Test = Audited Corpus (N=18)")
    print("  - Test ∩ UNKNOWN = ∅ (100% verified independent in Test)")
    print("  - orgs(Dev ∩ INDEPENDENT) ∩ orgs(Test) = ∅ (zero cross-partition leakage)")
    print("Reproducibility: in-memory re-derivation matches devtest_split_n18_v2.json byte-for-byte")
    print(f"Historical split: {HISTORICAL_SPLIT_NAME} verified intact (sha256: {historical_split_sha})")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
