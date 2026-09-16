#!/usr/bin/env python3
"""Derives the WPI Phase 2 organization-audited demand corpus (ADR 0029) as a
deterministic projection: read the independence audit -> select demands whose
status is INDEPENDENT or UNKNOWN (excluding PSEUDOREPLICATE) -> project the
matching records out of the frozen N=24 eligible corpus, in N=24 order.

Produces an operational corpus of N=18 demands (12 verified independent + 6
unknown organization independence) while excluding the 6 observed pseudoreplicates.
"""

import hashlib
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
AUDIT_NAME = "phase2_demand_independence_audit_n24_v1.json"
AUDIT_SHA_NAME = "phase2_demand_independence_audit_n24_v1.json.sha256"
AUDITED_CORPUS_NAME = "dataset_phase2_organization_audited_corpus_v1.json"
AUDITED_CORPUS_SHA_NAME = "dataset_phase2_organization_audited_corpus_v1.sha256"
AUDITED_CORPUS_MANIFEST_NAME = "dataset_phase2_organization_audited_corpus_v1.manifest.json"


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
    audit_sha = _verify_sidecar(DATA_DIR / AUDIT_NAME, DATA_DIR / AUDIT_SHA_NAME)

    eligible = _load(ELIGIBLE_NAME)
    audit = _load(AUDIT_NAME)
    eligible_manifest = _load("dataset_phase2_eligible_corpus_n24_v1.manifest.json")

    independent_ids = {e["demand_id"] for e in audit["entries"] if e["status"] == "INDEPENDENT"}
    unknown_ids = {e["demand_id"] for e in audit["entries"] if e["status"] == "UNKNOWN"}
    retained_ids = independent_ids | unknown_ids

    retained_demands = [d for d in eligible["demands"] if d["demand_id"] in retained_ids]

    audited_dataset = {
        "dataset_id": "nexus-phase2-organization-audited-corpus-v1",
        "schema_version": eligible["schema_version"],
        "dataset_version": "1.0.0",
        "description": (
            "Nexus Phase 2 organization-audited demand corpus: deterministic projection of "
            "dataset_phase2_eligible_corpus_n24_v1.json onto the status in {INDEPENDENT, UNKNOWN} "
            "entries of phase2_demand_independence_audit_n24_v1.json (ADR 0029). Excludes the 6 "
            "detected organizational pseudoreplicates while retaining 12 verified independent "
            "demands and 6 demands with unverified/unknown organization identity (None or "
            "Anonymous Organization placeholder). See docs/phase2-demand-independence-audit-protocol.md."
        ),
        "demands": retained_demands,
    }

    corpus_path = DATA_DIR / AUDITED_CORPUS_NAME
    corpus_path.write_text(
        json.dumps(audited_dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    corpus_sha = _sha256_file(corpus_path)

    manifest = {
        "dataset_id": audited_dataset["dataset_id"],
        "schema_version": audited_dataset["schema_version"],
        "dataset_version": audited_dataset["dataset_version"],
        "source_authorities": eligible_manifest["source_authorities"],
        "demand_count": len(retained_demands),
        "verified_independent_demand_count": len(independent_ids),
        "unknown_independence_demand_count": len(unknown_ids),
        "patent_count": 0,
        "annotation_count": 0,
        "content_sha256": corpus_sha,
        "derived_from": {
            "source_eligible_corpus_path": f"experiments/wpi-demand-patent-matching/data/{ELIGIBLE_NAME}",
            "source_eligible_corpus_sha256": eligible_sha,
            "independence_audit_path": f"experiments/wpi-demand-patent-matching/data/{AUDIT_NAME}",
            "independence_audit_sha256": audit_sha,
        },
    }

    (DATA_DIR / AUDITED_CORPUS_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (DATA_DIR / AUDITED_CORPUS_SHA_NAME).write_text(f"{corpus_sha}  {AUDITED_CORPUS_NAME}\n", encoding="utf-8")

    print(
        f"Wrote {len(retained_demands)} organization-audited demands "
        f"({len(independent_ids)} INDEPENDENT, {len(unknown_ids)} UNKNOWN) -> {corpus_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
