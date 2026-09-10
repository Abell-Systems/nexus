#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 sector assignment artifact (#80).

Verifies sector_assignments_n24_v1.json against dataset_phase2_eligible_corpus_n24_v1.json
(#88), phase2_sector_taxonomy_v1.json (#83), and phase2_sector_coverage_decision_v1.json
(#90), per docs/phase2-sector-assignment-protocol.md's contract. The artifact splits the
N=24 corpus between `assignments` (demands with a defensible sector) and
`no_sector_coverage` (demands D4 cannot place in any of the six categories). Which
demand_ids land in `no_sector_coverage` is NOT decided by this artifact: it is pinned
to exactly the set #90's decision already declared (phase2_sector_coverage_decision_v1.json,
verified by check_sector_coverage_decision.py) -- so this artifact cannot silently
partition N=24 however it likes and still pass. A demand is in exactly one of the two.

Intentionally RED right now: sector_assignments_n24_v1.json does not exist yet (no
classification has been done -- see that protocol doc, "What this protocol does not
do"). This check exists so the contract is executable and fixed before the follow-up
PR performs the actual classification.
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
COVERAGE_DECISION_NAME = "phase2_sector_coverage_decision_v1.json"
COVERAGE_DECISION_SHA_NAME = "phase2_sector_coverage_decision_v1.sha256"
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

# Exact key sets per docs/phase2-sector-assignment-protocol.md's artifact shape.
# No extra/unknown fields permitted anywhere in the artifact -- an entry with a
# surprise key (e.g. a post-hoc "scientifically_convenient" flag) must fail loudly,
# not be silently ignored by dict.get().
TOP_LEVEL_KEYS = {"dataset_id", "assignments", "no_sector_coverage"}
ENTRY_KEYS = {"demand_id", "sector_code", "decision_trace", "rationale", "evidence", "assignment", "audit"}
NO_COVERAGE_KEYS = {"demand_id", "rationale", "evidence", "reviewer"}
DECISION_TRACE_KEYS = {
    "resolved_at_step",
    "primary_technical_object",
    "primary_technical_problem",
    "application_domain",
    "candidates_after_step_3",
    "joint_reread_result",
    "title_first_object",
}
ASSIGNMENT_KEYS = {"reviewer"}
AUDIT_KEYS = {
    "needs_auditor_b",
    "auditor_b_reviewer",
    "auditor_b_status",
    "agreement",
    "adjudication_required",
    "adjudication",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_exact_keys(obj: dict, expected: set, label: str) -> None:
    actual = set(obj.keys())
    assert actual == expected, (
        f"{label}: keys do not match the frozen contract -- "
        f"missing={expected - actual or None}, unexpected={actual - expected or None}"
    )


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    eligible_sha = _verify_sidecar(DATA_DIR / ELIGIBLE_NAME, DATA_DIR / ELIGIBLE_SHA_NAME)
    taxonomy_sha = _verify_sidecar(CONFIG_DIR / TAXONOMY_NAME, CONFIG_DIR / TAXONOMY_SHA_NAME)
    coverage_decision_sha = _verify_sidecar(CONFIG_DIR / COVERAGE_DECISION_NAME, CONFIG_DIR / COVERAGE_DECISION_SHA_NAME)
    assignments_sha = _verify_sidecar(DATA_DIR / ASSIGNMENTS_NAME, DATA_DIR / ASSIGNMENTS_SHA_NAME)

    eligible = json.loads((DATA_DIR / ELIGIBLE_NAME).read_text(encoding="utf-8"))
    taxonomy = json.loads((CONFIG_DIR / TAXONOMY_NAME).read_text(encoding="utf-8"))
    coverage_decision = json.loads((CONFIG_DIR / COVERAGE_DECISION_NAME).read_text(encoding="utf-8"))
    assignments = json.loads((DATA_DIR / ASSIGNMENTS_NAME).read_text(encoding="utf-8"))
    manifest = json.loads((DATA_DIR / ASSIGNMENTS_MANIFEST_NAME).read_text(encoding="utf-8"))

    assert manifest["content_sha256"] == assignments_sha
    assert manifest["derived_from"]["eligible_corpus_sha256"] == eligible_sha
    assert manifest["derived_from"]["taxonomy_config_sha256"] == taxonomy_sha
    assert manifest["derived_from"]["coverage_decision_sha256"] == coverage_decision_sha, (
        "phase2_sector_coverage_decision_v1.json changed since the assignment artifact "
        "was frozen -- this artifact's no_sector_coverage mechanism is invalid until "
        "regenerated deliberately against the current decision."
    )
    declared_no_coverage_ids = set(coverage_decision["no_sector_coverage_demand_ids"])

    _assert_exact_keys(assignments, TOP_LEVEL_KEYS, "top-level assignments object")
    assert isinstance(assignments["dataset_id"], str) and assignments["dataset_id"].strip()

    eligible_ids = {d["demand_id"] for d in eligible["demands"]}
    valid_codes = {s["code"] for s in taxonomy["sectors"]}

    entries = assignments["assignments"]
    entry_ids = [e["demand_id"] for e in entries]
    no_coverage_entries = assignments["no_sector_coverage"]
    no_coverage_ids = [e["demand_id"] for e in no_coverage_entries]

    assert len(entry_ids) == len(set(entry_ids)), "Duplicate demand_id in sector assignments"
    assert len(no_coverage_ids) == len(set(no_coverage_ids)), "Duplicate demand_id in no_sector_coverage"
    assert not (set(entry_ids) & set(no_coverage_ids)), (
        "A demand_id appears in both assignments and no_sector_coverage: "
        f"{set(entry_ids) & set(no_coverage_ids)}"
    )
    covered_ids = set(entry_ids) | set(no_coverage_ids)
    assert covered_ids == eligible_ids, (
        "assignments + no_sector_coverage do not cover exactly the N=24 eligible corpus "
        f"(missing={eligible_ids - covered_ids}, extra={covered_ids - eligible_ids})"
    )
    assert set(no_coverage_ids) == declared_no_coverage_ids, (
        "no_sector_coverage does not match exactly the demand_ids #90's decision "
        "(phase2_sector_coverage_decision_v1.json) already declared -- this artifact "
        "cannot choose its own partition of N=24: "
        f"missing={declared_no_coverage_ids - set(no_coverage_ids)}, "
        f"unexpected={set(no_coverage_ids) - declared_no_coverage_ids}"
    )

    for entry in no_coverage_entries:
        _assert_exact_keys(entry, NO_COVERAGE_KEYS, f"{entry.get('demand_id', '?')}: no_sector_coverage entry")
        assert isinstance(entry["demand_id"], str) and entry["demand_id"].strip()
        assert isinstance(entry["rationale"], str) and entry["rationale"].strip(), (
            f"{entry['demand_id']}: empty rationale in no_sector_coverage"
        )
        assert (
            isinstance(entry["evidence"], list)
            and entry["evidence"]
            and all(isinstance(e, str) and e.strip() for e in entry["evidence"])
        ), f"{entry['demand_id']}: empty or missing evidence in no_sector_coverage"
        assert isinstance(entry["reviewer"], str) and entry["reviewer"].strip(), (
            f"{entry['demand_id']}: empty reviewer in no_sector_coverage"
        )

    per_sector_counts: dict[str, int] = {}
    for entry in entries:
        _assert_exact_keys(entry, ENTRY_KEYS, f"{entry.get('demand_id', '?')}: entry")
        _assert_exact_keys(entry["decision_trace"], DECISION_TRACE_KEYS, f"{entry['demand_id']}: decision_trace")
        _assert_exact_keys(entry["assignment"], ASSIGNMENT_KEYS, f"{entry['demand_id']}: assignment")
        _assert_exact_keys(entry["audit"], AUDIT_KEYS, f"{entry['demand_id']}: audit")

        assert isinstance(entry["demand_id"], str) and entry["demand_id"].strip()
        assert isinstance(entry["sector_code"], str)
        assert entry["sector_code"] in valid_codes, (
            f"{entry['demand_id']}: sector_code '{entry['sector_code']}' is not in the closed "
            f"taxonomy {sorted(valid_codes)}"
        )
        per_sector_counts[entry["sector_code"]] = per_sector_counts.get(entry["sector_code"], 0) + 1

        assert isinstance(entry["rationale"], str) and entry["rationale"].strip(), (
            f"{entry['demand_id']}: empty rationale"
        )
        assert (
            isinstance(entry["evidence"], list)
            and entry["evidence"]
            and all(isinstance(e, str) and e.strip() for e in entry["evidence"])
        ), f"{entry['demand_id']}: empty or missing evidence"
        assert isinstance(entry["assignment"]["reviewer"], str) and entry["assignment"]["reviewer"].strip(), (
            f"{entry['demand_id']}: empty reviewer"
        )

        trace = entry["decision_trace"]
        assert isinstance(trace["primary_technical_object"], str) and trace["primary_technical_object"].strip(), (
            f"{entry['demand_id']}: empty primary_technical_object"
        )
        step = trace["resolved_at_step"]
        assert isinstance(step, int) and not isinstance(step, bool) and step in STEP_REQUIRED_FIELDS, (
            f"{entry['demand_id']}: invalid resolved_at_step={step!r}"
        )
        for field in ("primary_technical_problem", "application_domain", "joint_reread_result", "title_first_object"):
            assert trace[field] is None or (isinstance(trace[field], str) and trace[field].strip()), (
                f"{entry['demand_id']}: decision_trace.{field} must be null or a non-empty string"
            )
        assert trace["candidates_after_step_3"] is None or (
            isinstance(trace["candidates_after_step_3"], list)
            and all(isinstance(c, str) for c in trace["candidates_after_step_3"])
        ), f"{entry['demand_id']}: decision_trace.candidates_after_step_3 must be null or a list of strings"

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
        assert isinstance(audit["needs_auditor_b"], bool)
        assert isinstance(audit["adjudication_required"], bool)
        assert audit["agreement"] is None or isinstance(audit["agreement"], bool)
        if step >= 4:
            # This protocol's own QA policy (not D6 itself -- D6 mandates auditability
            # only for step-5 tie-break cases; this PR additionally requires Auditor B
            # review for every step-4/5 case as a stricter, deliberate choice).
            assert audit["needs_auditor_b"] is True, (
                f"{entry['demand_id']}: resolved_at_step={step} requires needs_auditor_b=true "
                "(this protocol's step-4/5 Auditor B policy)"
            )
        if audit["needs_auditor_b"]:
            assert isinstance(audit["auditor_b_reviewer"], str) and audit["auditor_b_reviewer"].strip(), (
                f"{entry['demand_id']}: missing auditor_b_reviewer"
            )
            assert audit["auditor_b_status"] in valid_codes, f"{entry['demand_id']}: invalid auditor_b_status"
            expected_agreement = audit["auditor_b_status"] == entry["sector_code"]
            assert audit["agreement"] == expected_agreement, f"{entry['demand_id']}: agreement flag inconsistent"
            if not expected_agreement:
                assert audit["adjudication_required"] is True
                assert isinstance(audit["adjudication"], str) and audit["adjudication"].strip(), (
                    f"{entry['demand_id']}: disagreement with no adjudication recorded"
                )
            else:
                assert audit["adjudication_required"] is False
                assert audit["adjudication"] is None
        else:
            assert audit["auditor_b_reviewer"] is None
            assert audit["auditor_b_status"] is None
            assert audit["agreement"] is None
            assert audit["adjudication_required"] is False
            assert audit["adjudication"] is None

    assert manifest["demand_count"] == len(entries), manifest["demand_count"]
    assert manifest["no_sector_coverage_count"] == len(no_coverage_entries), manifest["no_sector_coverage_count"]
    assert set(manifest["no_sector_coverage_demand_ids"]) == set(no_coverage_ids)
    assert len(manifest["no_sector_coverage_demand_ids"]) == len(no_coverage_ids)
    assert len(entries) + len(no_coverage_entries) == len(eligible_ids), (
        len(entries), len(no_coverage_entries), len(eligible_ids)
    )
    for code, expected_count in manifest["per_sector_counts"].items():
        assert per_sector_counts.get(code, 0) == expected_count, (code, per_sector_counts.get(code, 0), expected_count)
    assert sum(manifest["per_sector_counts"].values()) == len(entries)

    print(
        f"OK: {len(entries)} sector assignments, {len(no_coverage_entries)} no_sector_coverage, "
        f"per_sector_counts={per_sector_counts}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
