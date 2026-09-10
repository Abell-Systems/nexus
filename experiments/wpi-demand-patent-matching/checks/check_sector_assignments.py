#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 sector assignment artifact (#80).

Verifies sector_assignments_n24_v1.json against dataset_phase2_eligible_corpus_n24_v1.json
(#88) and phase2_sector_taxonomy_v1.json (#83), per
docs/phase2-sector-assignment-protocol.md's contract.

Intentionally RED right now: sector_assignments_n24_v1.json does not exist yet (no
classification has been done -- see that protocol doc, "What this protocol does not
do"). This check exists so the contract is executable and fixed before the follow-up
PR performs the actual 24 classifications.
"""

import hashlib
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
TAXONOMY_NAME = "phase2_sector_taxonomy_v1.json"
TAXONOMY_SHA_NAME = "phase2_sector_taxonomy_v1.sha256"
ASSIGNMENTS_NAME = "sector_assignments_n24_v1.json"
ASSIGNMENTS_SHA_NAME = "sector_assignments_n24_v1.sha256"
ASSIGNMENTS_MANIFEST_NAME = "sector_assignments_n24_v1.manifest.json"

# resolved_at_step -> which decision_trace fields must be set (not null) vs null.
# Per docs/phase2-sector-assignment-protocol.md's invariant table.
STEP_REQUIRED_FIELDS = {
    1: set(),
    2: {"primary_technical_problem"},
    3: {"primary_technical_problem", "application_domain"},
    4: {"primary_technical_problem", "application_domain", "candidates_after_step_3", "joint_reread_result"},
    5: {
        "primary_technical_problem",
        "application_domain",
        "candidates_after_step_3",
        "joint_reread_result",
        "title_first_object",
    },
}
ALL_CONDITIONAL_FIELDS = {
    "primary_technical_problem",
    "application_domain",
    "candidates_after_step_3",
    "joint_reread_result",
    "title_first_object",
}


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
    taxonomy_sha = _verify_sidecar(CONFIG_DIR / TAXONOMY_NAME, CONFIG_DIR / TAXONOMY_SHA_NAME)
    assignments_sha = _verify_sidecar(DATA_DIR / ASSIGNMENTS_NAME, DATA_DIR / ASSIGNMENTS_SHA_NAME)

    eligible = json.loads((DATA_DIR / ELIGIBLE_NAME).read_text(encoding="utf-8"))
    taxonomy = json.loads((CONFIG_DIR / TAXONOMY_NAME).read_text(encoding="utf-8"))
    assignments = json.loads((DATA_DIR / ASSIGNMENTS_NAME).read_text(encoding="utf-8"))
    manifest = json.loads((DATA_DIR / ASSIGNMENTS_MANIFEST_NAME).read_text(encoding="utf-8"))

    assert manifest["content_sha256"] == assignments_sha
    assert manifest["derived_from"]["eligible_corpus_sha256"] == eligible_sha
    assert manifest["derived_from"]["taxonomy_config_sha256"] == taxonomy_sha

    eligible_ids = {d["demand_id"] for d in eligible["demands"]}
    valid_codes = {s["code"] for s in taxonomy["sectors"]}

    entries = assignments["assignments"]
    entry_ids = [e["demand_id"] for e in entries]

    assert len(entry_ids) == len(set(entry_ids)), "Duplicate demand_id in sector assignments"
    assert set(entry_ids) == eligible_ids, (
        "Sector assignments do not cover exactly the N=24 eligible corpus "
        f"(missing={eligible_ids - set(entry_ids)}, extra={set(entry_ids) - eligible_ids})"
    )

    per_sector_counts: dict[str, int] = {}
    for entry in entries:
        assert entry["sector_code"] in valid_codes, (
            f"{entry['demand_id']}: sector_code '{entry['sector_code']}' is not in the closed "
            f"taxonomy {sorted(valid_codes)}"
        )
        per_sector_counts[entry["sector_code"]] = per_sector_counts.get(entry["sector_code"], 0) + 1

        assert entry["rationale"].strip(), f"{entry['demand_id']}: empty rationale"
        assert entry["evidence"] and all(e.strip() for e in entry["evidence"]), (
            f"{entry['demand_id']}: empty or missing evidence"
        )
        assert entry["assignment"]["reviewer"].strip(), f"{entry['demand_id']}: empty reviewer"

        trace = entry["decision_trace"]
        assert trace["primary_technical_object"].strip(), f"{entry['demand_id']}: empty primary_technical_object"
        step = trace["resolved_at_step"]
        assert step in STEP_REQUIRED_FIELDS, f"{entry['demand_id']}: invalid resolved_at_step={step}"

        required = STEP_REQUIRED_FIELDS[step]
        for field in ALL_CONDITIONAL_FIELDS:
            present = trace.get(field) is not None
            should_be_present = field in required
            assert present == should_be_present, (
                f"{entry['demand_id']}: resolved_at_step={step} but decision_trace.{field} is "
                f"{'set' if present else 'null'} (expected {'set' if should_be_present else 'null'})"
            )
        if step >= 4:
            assert len(trace["candidates_after_step_3"]) >= 2, (
                f"{entry['demand_id']}: resolved_at_step={step} implies a tie after step 3, "
                "candidates_after_step_3 must name at least 2 sectors"
            )

        audit = entry["audit"]
        if step >= 4:
            assert audit["needs_auditor_b"] is True, (
                f"{entry['demand_id']}: resolved_at_step={step} requires needs_auditor_b=true (D6)"
            )
        if audit["needs_auditor_b"]:
            assert audit["auditor_b_reviewer"], f"{entry['demand_id']}: missing auditor_b_reviewer"
            assert audit["auditor_b_status"] in valid_codes, f"{entry['demand_id']}: invalid auditor_b_status"
            expected_agreement = audit["auditor_b_status"] == entry["sector_code"]
            assert audit["agreement"] == expected_agreement, f"{entry['demand_id']}: agreement flag inconsistent"
            if not expected_agreement:
                assert audit["adjudication_required"] is True
                assert audit["adjudication"], f"{entry['demand_id']}: disagreement with no adjudication recorded"
        else:
            assert audit["auditor_b_reviewer"] is None
            assert audit["auditor_b_status"] is None
            assert audit["agreement"] is None

    assert manifest["demand_count"] == len(entries) == 24, manifest["demand_count"]
    for code, expected_count in manifest["per_sector_counts"].items():
        assert per_sector_counts.get(code, 0) == expected_count, (code, per_sector_counts.get(code, 0), expected_count)
    assert sum(manifest["per_sector_counts"].values()) == len(entries)

    print(f"OK: {len(entries)} sector assignments, per_sector_counts={per_sector_counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
