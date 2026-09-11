#!/usr/bin/env python3
"""Derives the WPI Phase 2 demand-independence audit (ADR 0029) for the N=24
eligible corpus: for each eligible demand, join its already-frozen
requesting_organization value (from dataset_phase2_demand_corpus_n39.origin_audit.json,
extracted at acquisition time -- never inferred here) and classify it via
Nexus's generic exact-match grouping rule
(application.annotation.demand_independence.derive_independence_groups).

Also audits whether repeated organizations straddle the frozen Dev/Test split
(devtest_split_n13_v1.json), quantifying and encoding any organization-level
leakage across the boundary.

This is experiment tooling: it supplies the concrete non_identifying_values
exclusion list (a literal, documented property of the InnoGet source data, not
a general rule) and persists the resulting frozen artifact. It does not
implement the grouping rule itself -- that lives in backend/src/main and is
covered by generic, synthetic-fixture unit tests
(backend/test/unit/application/test_demand_independence.py).
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

NON_IDENTIFYING_VALUES = frozenset({"Anonymous Organization"})


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256_file(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, (
        f"{artifact_path.name}: bytes do not match {sidecar_path.name} -- refusing to derive "
        "from a modified input. Investigate before regenerating."
    )
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    eligible_sha = _verify_sidecar(DATA_DIR / ELIGIBLE_NAME, DATA_DIR / ELIGIBLE_SHA_NAME)
    origin_audit_sha = _verify_sidecar(DATA_DIR / ORIGIN_AUDIT_NAME, DATA_DIR / ORIGIN_AUDIT_SHA_NAME)
    devtest_split_sha = _verify_sidecar(DATA_DIR / DEVTEST_SPLIT_NAME, DATA_DIR / DEVTEST_SPLIT_SHA_NAME)

    eligible = _load(ELIGIBLE_NAME)
    origin_audit = _load(ORIGIN_AUDIT_NAME)
    devtest_split = _load(DEVTEST_SPLIT_NAME)

    org_by_id = {r["demand_id"]: r.get("requesting_organization") for r in origin_audit["records"]}
    eligible_ids = [d["demand_id"] for d in eligible["demands"]]

    missing = [did for did in eligible_ids if did not in org_by_id]
    if missing:
        raise SystemExit(f"origin_audit.json has no record for eligible demand_ids: {missing}")

    observations = [
        DemandOrganizationObservation(demand_id=did, requesting_organization=org_by_id[did])
        for did in eligible_ids
    ]
    entries = derive_independence_groups(observations, NON_IDENTIFYING_VALUES)

    independent_ids = [e.demand_id for e in entries if e.status == "INDEPENDENT"]
    pseudoreplicate_ids = [e.demand_id for e in entries if e.status == "PSEUDOREPLICATE"]

    # Organization group membership
    group_membership: dict[str, list[str]] = {}
    for e in entries:
        if e.independence_group_id is not None:
            group_membership.setdefault(e.independence_group_id, []).append(e.demand_id)

    # Dev/Test leakage audit
    dev_set = set(devtest_split["dev"])
    test_set = set(devtest_split["test"])
    split_demands = dev_set | test_set

    straddling_groups: dict[str, dict[str, list[str]]] = {}
    contaminated_split_demands: set[str] = set()

    for org, members in group_membership.items():
        if len(members) > 1:
            dev_members = [m for m in members if m in dev_set]
            test_members = [m for m in members if m in test_set]
            unsplit_members = [m for m in members if m not in split_demands]
            if dev_members and test_members:
                straddling_groups[org] = {
                    "dev_demands": sorted(dev_members),
                    "test_demands": sorted(test_members),
                    "unsplit_demands": sorted(unsplit_members),
                }
                contaminated_split_demands.update(dev_members)
                contaminated_split_demands.update(test_members)

    devtest_leakage_audit = {
        "source_devtest_split": f"experiments/wpi-demand-patent-matching/data/{DEVTEST_SPLIT_NAME}",
        "source_devtest_split_sha256": devtest_split_sha,
        "split_dataset_id": devtest_split.get("dataset_id"),
        "total_split_demands": len(split_demands),
        "leakage_status": "CONTAMINATED" if straddling_groups else "CLEAN",
        "scientific_finding": (
            "For the powered efficacy comparison, organization-level independent observations "
            "must not cross the Dev/Test boundary. The historical split is contaminated at the "
            "organization level because repeated organizations have observations in both Dev and Test."
            if straddling_groups
            else "No organization group crosses the Dev/Test boundary."
        ),
        "contaminated_split_demand_count": len(contaminated_split_demands),
        "contaminated_split_demand_fraction": (
            round(len(contaminated_split_demands) / len(split_demands), 4) if split_demands else 0.0
        ),
        "straddling_groups_count": len(straddling_groups),
        "straddling_organization_groups": straddling_groups,
    }

    artifact = {
        "audit_id": "phase2_demand_independence_audit_n24_v1",
        "protocol_reference": "docs/phase2-demand-independence-audit-protocol.md",
        "adr_reference": "docs/adr/0029-demand-independence-audit-contract.md",
        "derivation_rule": "Exact string match on requesting_organization, excluding documented placeholders",
        "organization_identity_source": "dataset_phase2_demand_corpus_n39.origin_audit.json (acquisition-time observation)",
        "source_eligible_corpus": f"experiments/wpi-demand-patent-matching/data/{ELIGIBLE_NAME}",
        "source_eligible_corpus_sha256": eligible_sha,
        "source_origin_audit": f"experiments/wpi-demand-patent-matching/data/{ORIGIN_AUDIT_NAME}",
        "source_origin_audit_sha256": origin_audit_sha,
        "non_identifying_values": sorted(NON_IDENTIFYING_VALUES),
        "counts": {
            "eligible_corpus_count": len(eligible_ids),
            "independent_count": len(independent_ids),
            "pseudoreplicate_count": len(pseudoreplicate_ids),
            "multi_member_group_count": sum(1 for members in group_membership.values() if len(members) > 1),
            "multi_member_organization_names": sorted(
                [org for org, members in group_membership.items() if len(members) > 1]
            ),
        },
        "retained_independent_demand_ids": independent_ids,
        "excluded_pseudoreplicate_demand_ids": pseudoreplicate_ids,
        "group_membership": group_membership,
        "historical_devtest_split_leakage_audit": devtest_leakage_audit,
        "entries": [e.model_dump(mode="json") for e in entries],
    }

    output_file = DATA_DIR / AUDIT_NAME
    serialized = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    output_file.write_text(serialized, encoding="utf-8")

    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    (DATA_DIR / AUDIT_SHA_NAME).write_text(f"{digest}  {output_file.name}\n", encoding="utf-8")

    manifest = {
        "audit_id": artifact["audit_id"],
        "total": len(entries),
        "independent_count": len(independent_ids),
        "pseudoreplicate_count": len(pseudoreplicate_ids),
        "content_sha256": digest,
        "devtest_split_leakage_status": devtest_leakage_audit["leakage_status"],
        "contaminated_split_demand_count": devtest_leakage_audit["contaminated_split_demand_count"],
        "straddling_groups_count": len(straddling_groups),
        "group_sizes": {org: len(members) for org, members in group_membership.items()},
    }
    (DATA_DIR / AUDIT_MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Emitted {output_file}: {digest}")
    print(f"INDEPENDENT={len(independent_ids)} PSEUDOREPLICATE={len(pseudoreplicate_ids)} (total={len(entries)})")
    print(f"Groups with >1 member: { {k: len(v) for k, v in group_membership.items() if len(v) > 1} }")
    print(f"Dev/Test leakage status: {devtest_leakage_audit['leakage_status']} ({len(straddling_groups)} straddling groups, {len(contaminated_split_demands)}/13 demands)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
