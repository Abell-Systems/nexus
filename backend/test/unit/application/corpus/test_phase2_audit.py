"""Unit tests for Phase-2 corpus expansion audit verification script (ADR 0032).

Verifies that the audit script detects:
1. Valid datasets meeting all invariants (cryptographic, partition, and candidate fields).
2. Partition violations (accepted/rejected overlap, missing records).
3. Corrupt SHA-256 sidecars.
4. Accepted records with publication_date=None or canonical_word_count < 25.
5. Accepted records missing technical problem evidence.
6. Rejected records with invalid reasons, UNVERIFIABLE_PUBLICATION_DATE coherence,
   or OUT_OF_TEMPORAL_WINDOW coherence.
7. CLI entry point exit codes (0 for valid, 1 for failure).
"""

import hashlib
import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Use dynamic import to respect ADR 0026 architecture invariant in test tree
_audit_mod = importlib.import_module("experiments.phase2.audit")
run_phase2_audit = _audit_mod.run_phase2_audit
main = _audit_mod.main
AuditResult = _audit_mod.AuditResult

POLICY_PATH = REPO_ROOT / "config" / "policies" / "data" / "corpus_expansion_policy_v1.json"


def _write_sealed_file(path: Path, data: object) -> str:
    """Write JSON file and corresponding .sha256 sidecar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content_bytes = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(content_bytes)
    sha256_hex = hashlib.sha256(content_bytes).hexdigest()
    sidecar_path = path.with_suffix(".sha256")
    sidecar_path.write_text(f"{sha256_hex}  {path.name}\n", encoding="utf-8")
    return sha256_hex


def _sample_candidate(
    demand_id: str,
    source_id: str = "een_pod",
    source_construct: str = "Technology request",
    publication_date: str = "2024-05-10",
    geographic_stratum: str = "spain",
    word_count: int = 30,
    has_technical_problem: bool = True,
    technical_problem_evidence: str = "Specific technical limitation in thermal dissipation efficiency.",
) -> dict:
    words = " ".join([f"word{i}" for i in range(word_count)])
    return {
        "demand_id": demand_id,
        "source_id": source_id,
        "source_construct": source_construct,
        "publication_date_evidence": {
            "evidence_field": "pod_reference",
            "evidence_type": "pod_reference",
            "evidence_value": f"TR{demand_id}",
            "publication_date": publication_date,
        },
        "geographic_stratum": geographic_stratum,
        "title": f"Sample Demand {demand_id}",
        "description_text": f"This is an industrial demand describing {words}",
        "language_code": "en",
        "organization_raw": "Research Org",
        "is_publicly_accessible": True,
        "has_confidentiality_redaction": False,
        "has_articulated_technical_problem": has_technical_problem,
        "technical_problem_evidence_text": technical_problem_evidence,
    }


def _create_valid_audit_environment(base_dir: Path) -> tuple[Path, Path]:
    experiments_dir = base_dir / "experiments"
    raw_dir = base_dir / "raw"
    experiments_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    cand_acc_1 = _sample_candidate("D001", source_id="een_pod", geographic_stratum="spain")
    cand_acc_2 = _sample_candidate(
        "D002", source_id="innoget", source_construct="Technology call", geographic_stratum="international_european"
    )

    cand_rej_1 = _sample_candidate("D003", source_id="een_pod", word_count=10)
    cand_rej_1["publication_date_evidence"]["publication_date"] = None
    cand_rej_1["publication_date_evidence"]["evidence_type"] = "unverifiable"

    rejected_entry_1 = {
        **cand_rej_1,
        "candidate": cand_rej_1,
        "rejection_reasons": ["UNVERIFIABLE_PUBLICATION_DATE", "CONTENT_TOO_SHORT"],
        "trigger_evidence": {
            "UNVERIFIABLE_PUBLICATION_DATE": {},
            "CONTENT_TOO_SHORT": {"observed_word_count": 10},
        },
    }

    raw_manifest = [
        {
            "acquisition_timestamp": "2026-09-11T12:00:00Z",
            "demand_id": "D001",
            "file_name": "D001.html",
            "file_path": "een_pod/D001.html",
            "raw_payload_sha256": "aaaa1111",
            "source_id": "een_pod",
            "source_uri": "https://een.ec.europa.eu/D001",
        },
        {
            "acquisition_timestamp": "2026-09-11T12:00:00Z",
            "demand_id": "D002",
            "file_name": "D002.json",
            "file_path": "innoget/D002.json",
            "raw_payload_sha256": "bbbb2222",
            "source_id": "innoget",
            "source_uri": "https://innoget.com/D002",
        },
        {
            "acquisition_timestamp": "2026-09-11T12:00:00Z",
            "demand_id": "D003",
            "file_name": "D003.html",
            "file_path": "een_pod/D003.html",
            "raw_payload_sha256": "cccc3333",
            "source_id": "een_pod",
            "source_uri": "https://een.ec.europa.eu/D003",
        },
    ]

    mapped = [cand_acc_1, cand_acc_2, cand_rej_1]
    accepted = [cand_acc_1, cand_acc_2]
    rejected = [rejected_entry_1]
    mapping_errors = []

    _write_sealed_file(experiments_dir / "candidates_raw.manifest.json", raw_manifest)
    _write_sealed_file(experiments_dir / "candidates_mapped.json", mapped)
    _write_sealed_file(experiments_dir / "candidates_accepted.json", accepted)
    _write_sealed_file(experiments_dir / "candidates_rejected.json", rejected)
    (experiments_dir / "mapping_errors.json").write_text(json.dumps(mapping_errors, indent=2), encoding="utf-8")

    return experiments_dir, raw_dir


def test_audit_passes_on_valid_dataset(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.summary_metrics["total_raw"] == 3
    assert result.summary_metrics["total_mapped"] == 3
    assert result.summary_metrics["total_accepted"] == 2
    assert result.summary_metrics["total_rejected"] == 1
    assert result.summary_metrics["total_mapping_errors"] == 0
    assert result.stratum_distribution.get("spain") == 1
    assert result.stratum_distribution.get("international_european") == 1
    assert result.rejection_breakdown.get("UNVERIFIABLE_PUBLICATION_DATE") == 1
    assert result.rejection_breakdown.get("CONTENT_TOO_SHORT") == 1


def test_audit_fails_on_corrupt_sha256_sidecar(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    # Corrupt the sidecar for candidates_accepted.json
    sidecar_file = experiments_dir / "candidates_accepted.sha256"
    sidecar_file.write_text("badhashbadhashbadhash  candidates_accepted.json\n", encoding="utf-8")

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("Cryptographic hash mismatch" in err and "candidates_accepted.json" in err for err in result.errors)


def test_audit_fails_on_partition_overlap(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    # Corrupt partition: add accepted record D001 into rejected as well
    accepted_path = experiments_dir / "candidates_accepted.json"
    rejected_path = experiments_dir / "candidates_rejected.json"

    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))

    # Put D001 into rejected
    duplicate = dict(accepted[0])
    duplicate["rejection_reasons"] = ["OUT_OF_TEMPORAL_WINDOW"]
    duplicate["publication_date_evidence"]["publication_date"] = "2018-01-01"
    rejected.append(duplicate)

    _write_sealed_file(rejected_path, rejected)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("Partition violation: overlap" in err for err in result.errors)


def test_audit_fails_on_partition_missing_mapped(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    # Remove D002 from accepted so mapped has D002 but accepted+rejected doesn't
    accepted_path = experiments_dir / "candidates_accepted.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted = [c for c in accepted if c["demand_id"] != "D002"]
    _write_sealed_file(accepted_path, accepted)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("Partition violation: mapped candidates missing" in err for err in result.errors)


def test_audit_fails_on_accepted_with_null_publication_date(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    accepted_path = experiments_dir / "candidates_accepted.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted[0]["publication_date_evidence"]["publication_date"] = None
    _write_sealed_file(accepted_path, accepted)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("null publication_date" in err for err in result.errors)


def test_audit_fails_on_accepted_with_out_of_window_publication_date(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    accepted_path = experiments_dir / "candidates_accepted.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted[0]["publication_date_evidence"]["publication_date"] = "2019-12-31"
    _write_sealed_file(accepted_path, accepted)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("outside temporal window" in err for err in result.errors)


def test_audit_fails_on_accepted_with_short_text(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    accepted_path = experiments_dir / "candidates_accepted.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted[0]["description_text"] = "Short description only five words."
    _write_sealed_file(accepted_path, accepted)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("canonical word count" in err for err in result.errors)


def test_audit_fails_on_accepted_without_technical_problem(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    accepted_path = experiments_dir / "candidates_accepted.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted[0]["has_articulated_technical_problem"] = False
    _write_sealed_file(accepted_path, accepted)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("has_articulated_technical_problem=False" in err for err in result.errors)


def test_audit_fails_on_accepted_with_rejection_reasons(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    accepted_path = experiments_dir / "candidates_accepted.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted[0]["rejection_reasons"] = ["CONTENT_TOO_SHORT"]
    _write_sealed_file(accepted_path, accepted)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("non-empty rejection_reasons" in err for err in result.errors)


def test_audit_fails_on_rejected_with_invalid_reason(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    rejected_path = experiments_dir / "candidates_rejected.json"
    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))
    rejected[0]["rejection_reasons"] = ["NOT_A_VALID_REASON"]
    _write_sealed_file(rejected_path, rejected)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("invalid rejection reason" in err for err in result.errors)


def test_audit_fails_on_rejected_unverifiable_with_non_null_date(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    rejected_path = experiments_dir / "candidates_rejected.json"
    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))
    rejected[0]["rejection_reasons"] = ["UNVERIFIABLE_PUBLICATION_DATE"]
    rejected[0]["publication_date_evidence"]["publication_date"] = "2024-01-01"
    _write_sealed_file(rejected_path, rejected)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any("UNVERIFIABLE_PUBLICATION_DATE but publication_date is not None" in err for err in result.errors)


def test_audit_fails_on_rejected_out_of_window_with_valid_date(tmp_path: Path):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    rejected_path = experiments_dir / "candidates_rejected.json"
    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))
    rejected[0]["rejection_reasons"] = ["OUT_OF_TEMPORAL_WINDOW"]
    rejected[0]["publication_date_evidence"]["publication_date"] = "2023-06-01"
    _write_sealed_file(rejected_path, rejected)

    result = run_phase2_audit(
        experiments_dir=experiments_dir,
        raw_dir=raw_dir,
        policy_path=POLICY_PATH,
    )

    assert result.is_valid is False
    assert any(
        "OUT_OF_TEMPORAL_WINDOW but publication_date" in err and "is inside temporal window" in err
        for err in result.errors
    )


def test_cli_main_exit_code_zero_on_valid(tmp_path: Path, monkeypatch, capsys):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    argv = [
        "--experiments-dir",
        str(experiments_dir),
        "--raw-dir",
        str(raw_dir),
        "--policy-path",
        str(POLICY_PATH),
    ]
    exit_code = main(argv)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "PASSED" in captured.out


def test_cli_main_exit_code_one_on_failure(tmp_path: Path, monkeypatch, capsys):
    experiments_dir, raw_dir = _create_valid_audit_environment(tmp_path)

    # Break hash sidecar
    sidecar_file = experiments_dir / "candidates_accepted.sha256"
    sidecar_file.write_text("corrupted_hash  candidates_accepted.json\n", encoding="utf-8")

    argv = [
        "--experiments-dir",
        str(experiments_dir),
        "--raw-dir",
        str(raw_dir),
        "--policy-path",
        str(POLICY_PATH),
    ]
    exit_code = main(argv)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "FAILED" in captured.out
