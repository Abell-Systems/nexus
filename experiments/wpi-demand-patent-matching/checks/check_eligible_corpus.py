#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 eligible demand corpus (N=24).

Verifies dataset_phase2_eligible_corpus_n24_v1.json is exactly the deterministic
projection of dataset_phase2_demand_corpus_n39.json onto the construct_status ==
ELIGIBLE entries of phase2_demand_construct_eligibility_n39_v1.json:
  - both inputs are treated as frozen (sha256-checked, never recomputed from them
    beyond membership/order -- construct_status itself is not re-derived here, that
    is check_construct_eligibility.py's job);
  - the N=24 sequence is exactly the N=39 subsequence induced by ELIGIBLE, in N=39
    order (no reordering, no INELIGIBLE/UNCERTAIN leakage);
  - each selected demand object is byte-identical (as parsed JSON) to its N=39
    counterpart -- no field transformation.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from domain.models.evaluation import DemandCorpus  # noqa: E402

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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    corpus_sha = _verify_sidecar(DATA_DIR / CORPUS_NAME, DATA_DIR / CORPUS_SHA_NAME)
    audit_sha = _verify_sidecar(DATA_DIR / AUDIT_NAME, DATA_DIR / AUDIT_SHA_NAME)
    eligible_sha = _verify_sidecar(DATA_DIR / ELIGIBLE_NAME, DATA_DIR / ELIGIBLE_SHA_NAME)

    corpus = _load(CORPUS_NAME)
    audit = _load(AUDIT_NAME)
    eligible = _load(ELIGIBLE_NAME)
    manifest = _load(ELIGIBLE_MANIFEST_NAME)

    assert manifest["content_sha256"] == eligible_sha
    assert manifest["derived_from"]["source_corpus_sha256"] == corpus_sha
    assert manifest["derived_from"]["construct_eligibility_audit_sha256"] == audit_sha

    corpus_by_id = {d["demand_id"]: d for d in corpus["demands"]}
    corpus_order = [d["demand_id"] for d in corpus["demands"]]

    eligible_ids_from_audit = {
        e["demand_id"] for e in audit["entries"] if e["construct_status"] == "ELIGIBLE"
    }
    ineligible_or_uncertain_ids = {
        e["demand_id"] for e in audit["entries"] if e["construct_status"] != "ELIGIBLE"
    }

    eligible_demands = eligible["demands"]
    eligible_ids = [d["demand_id"] for d in eligible_demands]

    assert len(eligible_ids) == len(set(eligible_ids)), "Duplicate demand_id in eligible corpus"
    assert set(eligible_ids) == eligible_ids_from_audit, (
        "Eligible corpus does not match exactly the audit's ELIGIBLE demand_ids "
        f"(missing={eligible_ids_from_audit - set(eligible_ids)}, "
        f"extra={set(eligible_ids) - eligible_ids_from_audit})"
    )
    assert not (set(eligible_ids) & ineligible_or_uncertain_ids), (
        "Eligible corpus leaks an INELIGIBLE/UNCERTAIN demand_id"
    )

    expected_order = [did for did in corpus_order if did in eligible_ids_from_audit]
    assert eligible_ids == expected_order, (
        "Eligible corpus order must be the N=39 subsequence induced by ELIGIBLE, "
        f"got {eligible_ids} expected {expected_order}"
    )

    for demand in eligible_demands:
        assert demand == corpus_by_id[demand["demand_id"]], (
            f"{demand['demand_id']}: N=24 object differs from its N=39 counterpart"
        )

    assert manifest["demand_count"] == len(eligible_demands) == 24, manifest["demand_count"]

    prefix_counts = manifest["demand_id_prefix_counts"]
    for prefix, expected_count in prefix_counts.items():
        actual = [did for did in eligible_ids if did.startswith(prefix)]
        assert len(actual) == expected_count, (prefix, len(actual), expected_count)
    assert sum(prefix_counts.values()) == len(eligible_ids)

    # Schema-contract validity (generic DemandCorpus, not an experiment-specific rule).
    DemandCorpus.model_validate_json((DATA_DIR / ELIGIBLE_NAME).read_bytes())

    print(f"OK: {len(eligible_demands)} eligible demands, prefix counts={prefix_counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
