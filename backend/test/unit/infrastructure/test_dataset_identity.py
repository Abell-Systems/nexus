"""Invariant tests for canonical dataset identity & temporal audit (PR #43).

Deliberately stdlib-only (plus pytest): these tests audit the sealed inputs and the
audit script itself, so they must run even where backend dependencies are absent.
They assert facts about files on disk — never efficacy, never ranking quality.

The frozen expectations below (SHA, counts, the exact 3 temporal violations) are the
traceable registry: any silent change to the sealed data fails loudly here. Remedy is
a new, separately sealed dataset version — never an edit of these expectations.
"""

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_AUDIT_SCRIPT = _REPO_ROOT / "scripts" / "audit_dataset_identity.py"

_KNOWN_DATASET_SHA = "bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453"
_KNOWN_TEMPORAL_VIOLATIONS = [
    {
        "demand_id": "INNOGET-2292",
        "publication_id": "ES-2856789-A1",
        "grade": 0,
        "publication_date": "2023-03-25",
        "demand_posted_date": "2023-02-15",
        "status": "TEMPORAL_VIOLATION",
    },
    {
        "demand_id": "INNOGET-2415",
        "publication_id": "ES-2901234-A1",
        "grade": 2,
        "publication_date": "2023-04-20",
        "demand_posted_date": "2023-01-10",
        "status": "TEMPORAL_VIOLATION",
    },
    {
        "demand_id": "INNOGET-2501",
        "publication_id": "ES-2901234-A1",
        "grade": 0,
        "publication_date": "2023-04-20",
        "demand_posted_date": "2023-03-20",
        "status": "TEMPORAL_VIOLATION",
    },
]


def _run_audit(output: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(_AUDIT_SCRIPT), "--output", str(output)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"audit script must report, not gate:\n{proc.stderr}"
    return json.loads(output.read_text(encoding="utf-8"))


class DatasetIdentityAuditTest:
    def test_should_report_known_canonical_identity(self, tmp_path: Path) -> None:
        report = _run_audit(tmp_path / "audit.json")
        assert report["dataset_id"] == "nexus-pilot-16-evaluation-corpus-v1"
        assert report["dataset_sha256"] == _KNOWN_DATASET_SHA
        assert report["counts"] == {"demands": 3, "patents": 15, "annotations": 23}
        assert report["demand_ids"] == ["INNOGET-2292", "INNOGET-2415", "INNOGET-2501"]
        assert report["embedding_artifact_id"] == (
            "m1_embeddings_nexus-pilot-16-evaluation-corpus-v1_1.0.0"
        )
        assert report["snapshots_total_records"] == 16
        assert report["snapshots_only_ids"] == ["ES-2918450-A1"]
        non_temporal = [c for c in report["checks"] if c["check"] != "temporal_eligibility"]
        assert non_temporal
        assert all(c["status"] == "PASS" for c in non_temporal)

    def test_should_freeze_known_temporal_violations(self, tmp_path: Path) -> None:
        report = _run_audit(tmp_path / "audit.json")
        assert report["temporal_violation_count"] == 3
        assert report["temporal_violations"] == _KNOWN_TEMPORAL_VIOLATIONS
        temp_check = next(c for c in report["checks"] if c["check"] == "temporal_eligibility")
        assert temp_check["status"] == "SKIPPED"
        assert temp_check["reason"] == "accepted_temporal_exception"
        assert temp_check["policy_ref"] == "ADR-0018/ADR-0019"
        assert report["verdict"] == "PASS"
        assert report["failed_checks"] == []

    def test_should_report_fail_under_strict_mode_without_policy(self, tmp_path: Path) -> None:
        proc = subprocess.run(
            [sys.executable, str(_AUDIT_SCRIPT), "--output", str(tmp_path / "strict.json"), "--strict"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0
        report = json.loads((tmp_path / "strict.json").read_text(encoding="utf-8"))
        assert report["verdict"] == "FAIL"
        assert report["failed_checks"] == ["temporal_eligibility"]
        temp_check = next(c for c in report["checks"] if c["check"] == "temporal_eligibility")
        assert temp_check["status"] == "FAIL"

    def test_should_fail_when_temporal_policy_target_dataset_id_mismatches(self, tmp_path: Path) -> None:
        policy_path = _REPO_ROOT / "config" / "policies" / "data" / "temporal_integrity_policy.json"
        policy_data = json.loads(policy_path.read_text(encoding="utf-8"))
        policy_data["target_dataset_id"] = "wrong-corpus-id-v2"
        tampered_policy = tmp_path / "tampered_policy.json"
        tampered_policy.write_text(json.dumps(policy_data), encoding="utf-8")

        proc = subprocess.run(
            [
                sys.executable,
                str(_AUDIT_SCRIPT),
                "--policy",
                str(tampered_policy),
                "--output",
                str(tmp_path / "mismatch.json"),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0
        report = json.loads((tmp_path / "mismatch.json").read_text(encoding="utf-8"))
        assert report["verdict"] == "FAIL"
        assert "temporal_policy_binding" in report["failed_checks"]
        assert "temporal_eligibility" in report["failed_checks"]

    def test_should_fail_when_temporal_policy_target_dataset_sha_mismatches(self, tmp_path: Path) -> None:
        policy_path = _REPO_ROOT / "config" / "policies" / "data" / "temporal_integrity_policy.json"
        policy_data = json.loads(policy_path.read_text(encoding="utf-8"))
        policy_data["target_dataset_sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
        tampered_policy = tmp_path / "tampered_policy.json"
        tampered_policy.write_text(json.dumps(policy_data), encoding="utf-8")

        proc = subprocess.run(
            [
                sys.executable,
                str(_AUDIT_SCRIPT),
                "--policy",
                str(tampered_policy),
                "--output",
                str(tmp_path / "mismatch.json"),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0
        report = json.loads((tmp_path / "mismatch.json").read_text(encoding="utf-8"))
        assert report["verdict"] == "FAIL"
        assert "temporal_policy_binding" in report["failed_checks"]
        assert "temporal_eligibility" in report["failed_checks"]

    def test_should_be_reproducible_across_runs(self, tmp_path: Path) -> None:
        first = _run_audit(tmp_path / "audit1.json")
        second = _run_audit(tmp_path / "audit2.json")
        assert first["canonical_fingerprint"] == second["canonical_fingerprint"]
