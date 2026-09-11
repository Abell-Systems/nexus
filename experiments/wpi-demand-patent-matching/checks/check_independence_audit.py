#!/usr/bin/env python3
"""Manifest-conformance + re-derivation check for the WPI Phase 2 demand-
independence audit (ADR 0029). Verifies phase2_demand_independence_audit_n24_v1.json
is EXACTLY what application.annotation.demand_independence.derive_independence_groups
produces from the frozen eligible corpus + origin_audit.json, with no drift,
and verifies the Dev/Test leakage audit consistency against devtest_split_n13_v1.json.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.annotation.demand_independence import derive_independence_groups  # noqa: E402
from domain.models.annotation import DemandOrganizationObservation  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
ORIGIN_AUDIT_NAME = "dataset_phase2_demand_corpus_n39.origin_audit.json"
ORIGIN_AUDIT_SHA_NAME = "dataset_phase2_demand_corpus_n39.origin_audit.json.sha256"
DEVTEST_SPLIT_NAME = "devtest_split_n13_v1.json"
DEVTEST_SPLIT_SHA_NAME = "devtest_split_n13_v1.sha256"
AUDIT_NAME = "phase2_demand_independence_audit_n24_v1.json"
AUDIT_SHA_NAME = "phase2_demand_independence_audit_n24_v1.json.sha256"
AUDIT_MANIFEST_NAME = "phase2_demand_independence_audit_n24_v1.manifest.json"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    eligible_sha = _verify_sidecar(DATA_DIR / ELIGIBLE_NAME, DATA_DIR / ELIGIBLE_SHA_NAME)
    origin_audit_sha = _verify_sidecar(DATA_DIR / ORIGIN_AUDIT_NAME, DATA_DIR / ORIGIN_AUDIT_SHA_NAME)
    devtest_split_sha = _verify_sidecar(DATA_DIR / DEVTEST_SPLIT_NAME, DATA_DIR / DEVTEST_SPLIT_SHA_NAME)
    audit_sha = _verify_sidecar(DATA_DIR / AUDIT_NAME, DATA_DIR / AUDIT_SHA_NAME)

    eligible = _load(ELIGIBLE_NAME)
    origin_audit = _load(ORIGIN_AUDIT_NAME)
    devtest_split = _load(DEVTEST_SPLIT_NAME)
    audit = _load(AUDIT_NAME)
    manifest = _load(AUDIT_MANIFEST_NAME)

    assert manifest["content_sha256"] == audit_sha
    assert audit["source_eligible_corpus_sha256"] == eligible_sha
    assert audit["source_origin_audit_sha256"] == origin_audit_sha
    assert audit["historical_devtest_split_leakage_audit"]["source_devtest_split_sha256"] == devtest_split_sha

    org_by_id = {r["demand_id"]: r.get("requesting_organization") for r in origin_audit["records"]}
    eligible_ids = [d["demand_id"] for d in eligible["demands"]]

    non_identifying_values = frozenset(audit["non_identifying_values"])
    observations = [
        DemandOrganizationObservation(demand_id=did, requesting_organization=org_by_id[did])
        for did in eligible_ids
    ]
    expected_entries = derive_independence_groups(observations, non_identifying_values)
    expected = [e.model_dump(mode="json") for e in expected_entries]

    assert audit["entries"] == expected, "Audit entries do not match a fresh re-derivation -- drift detected."

    independent_ids = {e["demand_id"] for e in audit["entries"] if e["status"] == "INDEPENDENT"}
    pseudoreplicate_ids = {e["demand_id"] for e in audit["entries"] if e["status"] == "PSEUDOREPLICATE"}
    assert independent_ids | pseudoreplicate_ids == set(eligible_ids)
    assert not (independent_ids & pseudoreplicate_ids)
    assert len(independent_ids) == 18
    assert len(pseudoreplicate_ids) == 6

    # Verify Dev/Test leakage audit
    leakage = audit["historical_devtest_split_leakage_audit"]
    assert leakage["leakage_status"] == "CONTAMINATED"
    assert leakage["total_split_demands"] == len(devtest_split["dev"]) + len(devtest_split["test"])
    assert "SMAR3TS" in leakage["straddling_organization_groups"]
    assert "Lacer, S.A" in leakage["straddling_organization_groups"]
    assert leakage["straddling_organization_groups"]["SMAR3TS"]["dev_demands"] == ["INNOGET-2404"]
    assert leakage["straddling_organization_groups"]["SMAR3TS"]["test_demands"] == ["INNOGET-2403"]
    assert leakage["straddling_organization_groups"]["Lacer, S.A"]["dev_demands"] == ["INNOGET-2491"]
    assert leakage["straddling_organization_groups"]["Lacer, S.A"]["test_demands"] == ["INNOGET-2492", "INNOGET-2493"]
    assert leakage["contaminated_split_demand_count"] == 5

    for org_data in leakage["straddling_organization_groups"].values():
        for did in org_data["dev_demands"]:
            assert did in devtest_split["dev"]
        for did in org_data["test_demands"]:
            assert did in devtest_split["test"]

    print(
        f"OK: {len(independent_ids)} INDEPENDENT, {len(pseudoreplicate_ids)} PSEUDOREPLICATE "
        f"(re-derivation matches exactly, Dev/Test leakage verified: {leakage['leakage_status']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
