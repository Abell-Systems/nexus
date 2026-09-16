#!/usr/bin/env python3
"""Generates the clean organization-isolated Dev/Test split v2 (N=18).

Instantiates the domain-agnostic organization_aware_split() mechanism
(backend/src/main/application/evaluation/organization_aware_split.py)
against the WPI Phase 2 audited corpus (ADR 0029, ADR 0030), per
experiments/wpi-demand-patent-matching/config/devtest_split_v2.json and
docs/superpowers/specs/2026-09-11-clean-devtest-split-organization-aware-design.md.
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
CONFIG_SHA_NAME = "devtest_split_v2.sha256"

SPLIT_NAME = "devtest_split_n18_v2.json"
SPLIT_SHA_NAME = "devtest_split_n18_v2.sha256"
SPLIT_MANIFEST_NAME = "devtest_split_n18_v2.manifest.json"


def _sha256_file(path: Path) -> str:
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
    computed = _sha256_file(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name, f"{declared_name} != {artifact_path.name}"
    return computed


def main() -> int:
    config_path = CONFIG_DIR / CONFIG_NAME
    config_sha_path = CONFIG_DIR / CONFIG_SHA_NAME
    config_sha = _verify_sidecar(config_path, config_sha_path)

    config = json.loads(config_path.read_text(encoding="utf-8"))

    corpus_path = REPO_ROOT / config["corpus_path"]
    audit_path = REPO_ROOT / config["audit_path"]
    assignments_path = REPO_ROOT / config["assignments_path"]

    corpus_sha = _verify_sidecar(corpus_path, _find_sidecar(corpus_path))
    audit_sha = _verify_sidecar(audit_path, _find_sidecar(audit_path))
    assignments_sha = _verify_sidecar(assignments_path, _find_sidecar(assignments_path))

    assert config["corpus_sha256"] == corpus_sha, "config pinned corpus hash is stale"
    assert config["audit_sha256"] == audit_sha, "config pinned audit hash is stale"
    assert config["assignments_sha256"] == assignments_sha, "config pinned assignments hash is stale"

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assignments = json.loads(assignments_path.read_text(encoding="utf-8"))

    demands = corpus["demands"]
    assert len(demands) == 18, f"Expected 18 audited corpus demands, got {len(demands)}"

    org_map = {e["demand_id"]: e.get("requesting_organization") for e in audit["entries"]}
    status_map = {e["demand_id"]: DemandIndependenceStatus(e["status"]) for e in audit["entries"]}
    sector_map = {a["demand_id"]: a["sector_code"] for a in assignments.get("assignments", [])}

    for d in demands:
        d["requesting_organization"] = org_map.get(d["demand_id"])

    result = organization_aware_split(
        items=demands,
        item_id=lambda d: d["demand_id"],
        org_key=lambda d: d.get("requesting_organization"),
        status_key=lambda d: status_map[d["demand_id"]],
        stratum_key=lambda d: sector_map.get(d["demand_id"], config["missing_stratum"]),
        dev_fraction=config["dev_fraction"],
        base_seed=config["base_seed"],
        unknown_policy=config["unknown_split_policy"],
    )

    dev_ids = list(result.dev.demand_ids)
    test_ids = list(result.test.demand_ids)

    dev_indep_count = sum(1 for did in dev_ids if status_map[did] == DemandIndependenceStatus.INDEPENDENT)
    test_indep_count = sum(1 for did in test_ids if status_map[did] == DemandIndependenceStatus.INDEPENDENT)

    dev_orgs = {org_map[did] for did in dev_ids if status_map[did] == DemandIndependenceStatus.INDEPENDENT}
    test_orgs = {org_map[did] for did in test_ids if status_map[did] == DemandIndependenceStatus.INDEPENDENT}
    org_overlap = bool(dev_orgs & test_orgs)
    assert not org_overlap, f"Cross-partition organization overlap detected: {dev_orgs & test_orgs}"

    split_dataset = {
        "dataset_id": "nexus-phase2-devtest-split-n18-v2",
        "dev": dev_ids,
        "test": test_ids,
    }

    split_path = DATA_DIR / SPLIT_NAME
    split_path.write_text(json.dumps(split_dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    split_sha = _sha256_file(split_path)

    manifest = {
        "split_dataset_id": "nexus-phase2-devtest-split-n18-v2",
        "total_demands": len(demands),
        "independent_demands": result.independent_count,
        "unknown_demands": result.unknown_count,
        "dev_count": len(dev_ids),
        "test_count": len(test_ids),
        "dev_verified_independent_count": dev_indep_count,
        "test_verified_independent_count": test_indep_count,
        "per_stratum_counts": {c.stratum: {"dev": c.dev, "test": c.test} for c in result.per_stratum_counts},
        "split_policy": "organization_aware_stratified",
        "unknown_split_policy": config["unknown_split_policy"],
        "stratification_key": "sector",
        "missing_stratum": config["missing_stratum"],
        "dev_fraction": config["dev_fraction"],
        "base_seed": config["base_seed"],
        "atomic_unit": "demand",
        "organization_isolation": "exact",
        "organization_overlap": org_overlap,
        "content_sha256": split_sha,
        "derived_from": {
            "corpus": corpus_path.name,
            "corpus_sha256": corpus_sha,
            "audit": audit_path.name,
            "audit_sha256": audit_sha,
            "sectors": assignments_path.name,
            "sectors_sha256": assignments_sha,
            "config": config_path.name,
            "config_sha256": config_sha,
        },
    }

    (DATA_DIR / SPLIT_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (DATA_DIR / SPLIT_SHA_NAME).write_text(f"{split_sha}  {SPLIT_NAME}\n", encoding="utf-8")

    print(
        f"Wrote dev={len(dev_ids)} (indep={dev_indep_count}) "
        f"test={len(test_ids)} (indep={test_indep_count}) "
        f"-> {split_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
