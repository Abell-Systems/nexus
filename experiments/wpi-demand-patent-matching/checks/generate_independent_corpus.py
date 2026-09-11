#!/usr/bin/env python3
"""Derives the WPI Phase 2 independent demand corpus (ADR 0029) as a
deterministic projection: read the independence audit -> select INDEPENDENT
demand_ids -> project the matching records out of the frozen N=24 eligible
corpus, in N=24 order.

Pure filter, no judgment: the audit's status is treated as already decided by
application.annotation.demand_independence.derive_independence_groups. This
script does not re-derive it.
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
INDEPENDENT_NAME = "dataset_phase2_independent_corpus_v1.json"
INDEPENDENT_SHA_NAME = "dataset_phase2_independent_corpus_v1.sha256"
INDEPENDENT_MANIFEST_NAME = "dataset_phase2_independent_corpus_v1.manifest.json"


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
    independent_demands = [d for d in eligible["demands"] if d["demand_id"] in independent_ids]

    independent_dataset = {
        "dataset_id": "nexus-phase2-independent-corpus-v1",
        "schema_version": eligible["schema_version"],
        "dataset_version": "1.0.0",
        "description": (
            "Nexus Phase 2 independent demand corpus: deterministic projection of "
            "dataset_phase2_eligible_corpus_n24_v1.json onto the status == INDEPENDENT "
            "entries of phase2_demand_independence_audit_n24_v1.json (ADR 0029). One "
            "demand per requesting-organization identity (exact string match); a demand "
            "whose organization is missing or a known non-identifying placeholder is "
            "always included. See docs/phase2-demand-independence-audit-protocol.md."
        ),
        "demands": independent_demands,
    }

    independent_path = DATA_DIR / INDEPENDENT_NAME
    independent_path.write_text(
        json.dumps(independent_dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    independent_sha = _sha256_file(independent_path)

    manifest = {
        "dataset_id": independent_dataset["dataset_id"],
        "schema_version": independent_dataset["schema_version"],
        "dataset_version": independent_dataset["dataset_version"],
        "source_authorities": eligible_manifest["source_authorities"],
        "demand_count": len(independent_demands),
        "patent_count": 0,
        "annotation_count": 0,
        "content_sha256": independent_sha,
        "derived_from": {
            "source_eligible_corpus_path": f"experiments/wpi-demand-patent-matching/data/{ELIGIBLE_NAME}",
            "source_eligible_corpus_sha256": eligible_sha,
            "independence_audit_path": f"experiments/wpi-demand-patent-matching/data/{AUDIT_NAME}",
            "independence_audit_sha256": audit_sha,
        },
    }

    (DATA_DIR / INDEPENDENT_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (DATA_DIR / INDEPENDENT_SHA_NAME).write_text(f"{independent_sha}  {INDEPENDENT_NAME}\n", encoding="utf-8")

    print(f"Wrote {len(independent_demands)} independent demands -> {independent_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
