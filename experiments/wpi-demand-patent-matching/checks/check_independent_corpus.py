#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 independent demand corpus
(ADR 0029). Verifies dataset_phase2_independent_corpus_v1.json is exactly the
deterministic projection of dataset_phase2_eligible_corpus_n24_v1.json onto the
status == INDEPENDENT entries of phase2_demand_independence_audit_n24_v1.json:
  - both inputs are treated as frozen (sha256-checked; independence status
    itself is not re-derived here, that is check_independence_audit.py's job);
  - the independent sequence is exactly the N=24 subsequence induced by
    INDEPENDENT, in N=24 order (no reordering, no PSEUDOREPLICATE leakage);
  - each selected demand object is field-for-field identical, as parsed JSON,
    to its N=24 counterpart -- no field transformation.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from domain.models.evaluation import DemandCorpus  # noqa: E402

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
    audit_sha = _verify_sidecar(DATA_DIR / AUDIT_NAME, DATA_DIR / AUDIT_SHA_NAME)
    independent_sha = _verify_sidecar(DATA_DIR / INDEPENDENT_NAME, DATA_DIR / INDEPENDENT_SHA_NAME)

    eligible = _load(ELIGIBLE_NAME)
    audit = _load(AUDIT_NAME)
    independent = _load(INDEPENDENT_NAME)
    manifest = _load(INDEPENDENT_MANIFEST_NAME)

    assert manifest["content_sha256"] == independent_sha
    assert manifest["derived_from"]["source_eligible_corpus_sha256"] == eligible_sha
    assert manifest["derived_from"]["independence_audit_sha256"] == audit_sha

    eligible_by_id = {d["demand_id"]: d for d in eligible["demands"]}
    eligible_order = [d["demand_id"] for d in eligible["demands"]]

    independent_ids_from_audit = {e["demand_id"] for e in audit["entries"] if e["status"] == "INDEPENDENT"}
    pseudoreplicate_ids = {e["demand_id"] for e in audit["entries"] if e["status"] != "INDEPENDENT"}

    independent_demands = independent["demands"]
    independent_ids = [d["demand_id"] for d in independent_demands]

    assert len(independent_ids) == len(set(independent_ids)), "Duplicate demand_id in independent corpus"
    assert set(independent_ids) == independent_ids_from_audit, (
        "Independent corpus does not match exactly the audit's INDEPENDENT demand_ids "
        f"(missing={independent_ids_from_audit - set(independent_ids)}, "
        f"extra={set(independent_ids) - independent_ids_from_audit})"
    )
    assert not (set(independent_ids) & pseudoreplicate_ids), "Independent corpus leaks a PSEUDOREPLICATE demand_id"

    expected_order = [did for did in eligible_order if did in independent_ids_from_audit]
    assert independent_ids == expected_order, (
        "Independent corpus order must be the N=24 subsequence induced by INDEPENDENT, "
        f"got {independent_ids} expected {expected_order}"
    )

    for demand in independent_demands:
        assert demand == eligible_by_id[demand["demand_id"]], (
            f"{demand['demand_id']}: independent-corpus object differs from its N=24 counterpart"
        )

    assert manifest["demand_count"] == len(independent_demands)

    # Schema-contract validity (generic DemandCorpus, not an experiment-specific rule).
    DemandCorpus.model_validate_json((DATA_DIR / INDEPENDENT_NAME).read_bytes())

    print(f"OK: {len(independent_demands)} independent demands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
