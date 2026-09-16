#!/usr/bin/env python3
"""Derives the WPI Phase 2 eligible demand corpus (N=24) as a deterministic
projection: read the construct-eligibility audit -> select ELIGIBLE demand_ids ->
project the matching records out of the frozen N=39 corpus, in N=39 order.

Pure filter, no judgment: the audit's construct_status is treated as already
decided (by #85/#86, Auditor A + Auditor B). This script does not re-derive it.
"""

import hashlib
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CORPUS_NAME = "dataset_phase2_demand_corpus_n39.json"
CORPUS_SHA_NAME = "dataset_phase2_demand_corpus_n39.sha256"
AUDIT_NAME = "phase2_demand_construct_eligibility_n39_v1.json"
AUDIT_SHA_NAME = "phase2_demand_construct_eligibility_n39_v1.json.sha256"
ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
ELIGIBLE_MANIFEST_NAME = "dataset_phase2_eligible_corpus_n24_v1.manifest.json"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    """Precondition, not an observation: an input must match its own frozen sidecar
    before this script is allowed to read it as a derivation source."""
    computed = _sha256_file(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, (
        f"{artifact_path.name}: bytes do not match {sidecar_path.name} -- refusing to derive "
        "from a modified input. Investigate before regenerating."
    )
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    corpus_sha = _verify_sidecar(DATA_DIR / CORPUS_NAME, DATA_DIR / CORPUS_SHA_NAME)
    audit_sha = _verify_sidecar(DATA_DIR / AUDIT_NAME, DATA_DIR / AUDIT_SHA_NAME)

    corpus = _load(CORPUS_NAME)
    audit = _load(AUDIT_NAME)
    corpus_manifest = _load("dataset_phase2_demand_corpus_n39.manifest.json")

    eligible_ids = {e["demand_id"] for e in audit["entries"] if e["construct_status"] == "ELIGIBLE"}
    eligible_demands = [d for d in corpus["demands"] if d["demand_id"] in eligible_ids]

    eligible_dataset = {
        "dataset_id": "nexus-phase2-eligible-corpus-n24-v1",
        "schema_version": corpus["schema_version"],
        "dataset_version": "1.0.0",
        "description": (
            "Nexus Phase 2 eligible demand corpus (N=24): deterministic projection of "
            "dataset_phase2_demand_corpus_n39.json onto the construct_status == ELIGIBLE "
            "entries of phase2_demand_construct_eligibility_n39_v1.json (#84, closed via "
            "#85/#86). See docs/phase2-demand-construct-eligibility-audit-protocol.md "
            "(Closure) for the audit that determined this population."
        ),
        "demands": eligible_demands,
    }

    eligible_path = DATA_DIR / ELIGIBLE_NAME
    eligible_path.write_text(
        json.dumps(eligible_dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    eligible_sha = _sha256_file(eligible_path)

    prefix_counts: dict[str, int] = {}
    for d in eligible_demands:
        prefix = d["demand_id"].split("-")[0] + "-"
        prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1

    manifest = {
        "dataset_id": eligible_dataset["dataset_id"],
        "schema_version": eligible_dataset["schema_version"],
        "dataset_version": eligible_dataset["dataset_version"],
        "source_authorities": corpus_manifest["source_authorities"],
        "demand_count": len(eligible_demands),
        "patent_count": 0,
        "annotation_count": 0,
        "demand_id_prefix_counts": prefix_counts,
        "content_sha256": eligible_sha,
        "derived_from": {
            "source_corpus_path": f"experiments/wpi-demand-patent-matching/data/{CORPUS_NAME}",
            "source_corpus_sha256": corpus_sha,
            "construct_eligibility_audit_path": f"experiments/wpi-demand-patent-matching/data/{AUDIT_NAME}",
            "construct_eligibility_audit_sha256": audit_sha,
        },
    }

    (DATA_DIR / ELIGIBLE_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (DATA_DIR / ELIGIBLE_SHA_NAME).write_text(f"{eligible_sha}  {ELIGIBLE_NAME}\n", encoding="utf-8")

    print(f"Wrote {len(eligible_demands)} eligible demands -> {eligible_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
