#!/usr/bin/env python3
"""Manifest-conformance check for the WPI demand construct-eligibility audit.

Verifies the frozen phase2_demand_construct_eligibility_n39_v1.json artifact
against its own recorded manifest and sha256 sidecar, and against the generic
Nexus decision rule (application.annotation.construct_eligibility). Expected
counts are read from the manifest, never hardcoded here — this validates one
scientific run's evidence, not a Nexus domain invariant.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.annotation.construct_eligibility import derive_construct_status  # noqa: E402
from domain.models.annotation import ConstructEligibilityRubric, RubricValue  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TAXONOMY_CATEGORIES = (
    "consumer_chemistry",
    "sanitary_materials",
    "industrial_machinery_iot",
    "energy_storage",
    "metallurgy",
    "biotechnology",
)


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    audit = _load("phase2_demand_construct_eligibility_n39_v1.json")
    manifest = _load("phase2_demand_construct_eligibility_n39_v1.manifest.json")
    corpus = _load("dataset_phase2_demand_corpus_n39.json")

    protocol_ref_path = Path(__file__).resolve().parent.parent / "protocol" / "protocol-reference.json"
    protocol_ref = json.loads(protocol_ref_path.read_text(encoding="utf-8"))
    protocol_path = REPO_ROOT / protocol_ref["protocol_path"]
    protocol_computed = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    assert protocol_computed == protocol_ref["protocol_sha256"], (
        f"protocol-reference.json's protocol_sha256 is stale: recorded="
        f"{protocol_ref['protocol_sha256']} actual={protocol_computed}. "
        "Recompute it after editing docs/empirical-study-protocol.md."
    )

    artifact_path = DATA_DIR / "phase2_demand_construct_eligibility_n39_v1.json"
    sidecar_path = DATA_DIR / "phase2_demand_construct_eligibility_n39_v1.json.sha256"
    computed = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    expected = sidecar_path.read_text(encoding="utf-8").split()[0]
    assert computed == expected, f"Artifact sha256 mismatch: {computed} != {expected}"

    audit_ids = [e["demand_id"] for e in audit["entries"]]
    corpus_ids = {d["demand_id"] for d in corpus["demands"]}
    assert len(audit_ids) == len(set(audit_ids)), "Duplicate demand_id in audit entries"
    assert set(audit_ids) == corpus_ids, "Audit does not cover exactly the frozen corpus"

    eligible = ineligible = uncertain = needs_b = 0
    for entry in audit["entries"]:
        rubric = ConstructEligibilityRubric(
            technical_problem_present=RubricValue(entry["technical_problem_present"]),
            technology_solution_requested=RubricValue(entry["technology_solution_requested"]),
            technical_specification_present=RubricValue(entry["technical_specification_present"]),
            exclusion_criterion_1=RubricValue(entry["exclusion_criterion_1"]),
        )
        derived = derive_construct_status(rubric)
        assert derived.value == entry["construct_status"], (
            f"{entry['demand_id']}: decision rule implies {derived.value}, got {entry['construct_status']}"
        )
        assert entry["rationale"].strip(), f"{entry['demand_id']}: empty rationale"
        assert entry["evidence"].strip(), f"{entry['demand_id']}: empty evidence"

        if entry["construct_status"] == "ELIGIBLE":
            eligible += 1
        elif entry["construct_status"] == "INELIGIBLE":
            ineligible += 1
        else:
            uncertain += 1

        if entry["construct_status"] in ("INELIGIBLE", "UNCERTAIN"):
            assert entry["needs_auditor_b"] is True, entry["demand_id"]
        if entry["needs_auditor_b"]:
            needs_b += 1
            assert entry["agreement"] is True, entry["demand_id"]
            assert entry["auditor_b_status"] == entry["construct_status"], entry["demand_id"]
            assert entry["adjudication"] is None, entry["demand_id"]
        else:
            assert entry["agreement"] is None, entry["demand_id"]
            assert entry["auditor_b_status"] is None, entry["demand_id"]

    assert eligible == manifest["eligible_count"], (eligible, manifest["eligible_count"])
    assert ineligible == manifest["ineligible_count"], (ineligible, manifest["ineligible_count"])
    assert uncertain == manifest["uncertain_count"], (uncertain, manifest["uncertain_count"])
    assert needs_b == manifest["needs_auditor_b_count"], (needs_b, manifest["needs_auditor_b_count"])
    assert len(audit_ids) == manifest["total"], (len(audit_ids), manifest["total"])

    assert audit["status"] == "auditor_a_and_b_complete_no_disagreement"
    assert audit["auditor_b_disagreements"] == 0
    assert audit["adjudication_required"] is False

    serialized = json.dumps(audit).lower()
    for forbidden in TAXONOMY_CATEGORIES:
        assert forbidden not in serialized, f"Audit references taxonomy category: {forbidden}"

    corpus_sha_path = DATA_DIR / "dataset_phase2_demand_corpus_n39.sha256"
    corpus_path = DATA_DIR / "dataset_phase2_demand_corpus_n39.json"
    corpus_computed = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    corpus_expected = corpus_sha_path.read_text(encoding="utf-8").split()[0]
    assert corpus_computed == corpus_expected, "dataset_phase2_demand_corpus_n39.json was modified"

    print(f"OK: {len(audit_ids)} entries, ELIGIBLE={eligible} INELIGIBLE={ineligible} UNCERTAIN={uncertain}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
