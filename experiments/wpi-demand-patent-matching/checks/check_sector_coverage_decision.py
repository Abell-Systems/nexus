#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 sector coverage decision (#90).

Verifies phase2_sector_coverage_decision_v1.json against its own sha256 sidecar,
against docs/phase2-sector-coverage-decision.md's sha256 (so a later edit to the
decision doc can't silently revalidate an already-frozen declared ID set), and that
its declared no_sector_coverage_demand_ids are a subset of the frozen N=24 eligible
corpus. Does not validate any classification artifact -- that is
check_sector_assignments.py's job, which pins the exact same declared ID set.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

DECISION_CONFIG_NAME = "phase2_sector_coverage_decision_v1.json"
DECISION_CONFIG_SHA_NAME = "phase2_sector_coverage_decision_v1.sha256"
ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    config_path = CONFIG_DIR / DECISION_CONFIG_NAME
    sidecar_path = CONFIG_DIR / DECISION_CONFIG_SHA_NAME

    computed = _sha256(config_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{DECISION_CONFIG_NAME}: bytes do not match {DECISION_CONFIG_SHA_NAME}"
    assert declared_name == DECISION_CONFIG_NAME

    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["decision_id"] == "phase2_sector_coverage_decision_v1"
    assert config["option"] == "B"

    decision_doc_path = REPO_ROOT / config["decision_doc_path"]
    decision_doc_computed = _sha256(decision_doc_path)
    assert decision_doc_computed == config["decision_doc_sha256"], (
        f"docs/phase2-sector-coverage-decision.md changed since the decision was frozen: "
        f"recorded={config['decision_doc_sha256']} actual={decision_doc_computed}. "
        "A changed decision doc must not silently revalidate an already-frozen declared "
        "no_sector_coverage_demand_ids set -- recompute deliberately, or version the decision."
    )

    ids = config["no_sector_coverage_demand_ids"]
    assert len(ids) == len(set(ids)), "Duplicate demand_id in no_sector_coverage_demand_ids"
    assert ids, "no_sector_coverage_demand_ids must not be empty"

    eligible = json.loads((DATA_DIR / ELIGIBLE_NAME).read_text(encoding="utf-8"))
    eligible_ids = {d["demand_id"] for d in eligible["demands"]}
    assert set(ids) <= eligible_ids, (
        f"no_sector_coverage_demand_ids contains ids outside the N=24 eligible corpus: "
        f"{set(ids) - eligible_ids}"
    )

    print(f"OK: {len(ids)} demand_ids declared no_sector_coverage under decision option={config['option']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
