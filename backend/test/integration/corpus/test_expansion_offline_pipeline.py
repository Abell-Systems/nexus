"""Integration tests for deterministic Phase-2 offline validation pipeline (ADR 0032)."""

import hashlib
import importlib
import json
import socket
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

from application.corpus.expansion_policy_validator import PolicyIntegrityError

REPO_ROOT = Path(__file__).resolve().parents[4]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

_validate_mod = importlib.import_module("experiments.phase2.validate")
main = _validate_mod.main
run_offline_validation = _validate_mod.run_offline_validation

POLICY_PATH = REPO_ROOT / "config" / "policies" / "data" / "corpus_expansion_policy_v1.json"


@pytest.fixture
def block_network() -> Generator[None, None, None]:
    """Strictly prevent all network socket connections during offline pipeline test."""
    original_socket = socket.socket

    def guard_socket(*args, **kwargs):
        raise RuntimeError("Network socket connection attempted during 100% offline validation pipeline!")

    socket.socket = guard_socket  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket = original_socket  # type: ignore[assignment]


def _write_fixture(
    source_dir: Path,
    demand_id: str,
    source_id: str,
    source_uri: str,
    payload_content: bytes,
    extension: str = ".html",
    extra_meta: dict | None = None,
) -> tuple[Path, Path]:
    source_dir.mkdir(parents=True, exist_ok=True)
    payload_path = source_dir / f"{demand_id}{extension}"
    payload_path.write_bytes(payload_content)

    sha256_hex = hashlib.sha256(payload_content).hexdigest()
    meta = {
        "demand_id": demand_id,
        "source_id": source_id,
        "source_uri": source_uri,
        "acquisition_timestamp": "2026-09-11T12:00:00.000000Z",
        "raw_payload_sha256": sha256_hex,
        "harvester_version": "phase2_harvester_v1",
        "http_status": 200,
    }
    if extra_meta:
        meta.update(extra_meta)

    meta_path = source_dir / f"{demand_id}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload_path, meta_path


@pytest.fixture
def staged_raw_dir(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "raw" / "phase2_candidates"
    een_dir = raw_dir / "een_pod"
    innoget_dir = raw_dir / "innoget"

    # 1. Valid EEN candidate (accepted)
    een_valid_html = (
        b"<!DOCTYPE html>\n<html lang=\"en\">\n<head><title>TRFR20220315001 - Seeking advanced polymer recycling</title></head>\n"
        b"<body>\n"
        b"  <h1>Seeking advanced polymer recycling technologies for circular packaging</h1>\n"
        b"  <div class=\"reference-info\">POD Reference: TRFR20220315001</div>\n"
        b"  <div class=\"summary\">\n"
        b"    A French industrial packaging manufacturer is actively seeking innovative chemical recycling solutions\n"
        b"    capable of processing contaminated multi-layer post-consumer polymers into virgin-grade resins for food contact.\n"
        b"    The company aims to transition 100 percent of its flexible packaging product line towards circular materials\n"
        b"    to comply with strict European sustainability directives and reduce fossil hydrocarbon consumption.\n"
        b"  </div>\n"
        b"  <div class=\"technical-problem\">\n"
        b"    <h3>Technical problem</h3>\n"
        b"    Current mechanical recycling processes degrade the mechanical integrity of multi-layer polymer films\n"
        b"    and fail to eliminate volatile organic contaminants and legacy ink pigments.\n"
        b"    The company requires thermal or catalytic depolymerization technologies that operate efficiently at industrial scale.\n"
        b"  </div>\n"
        b"</body></html>\n"
    )
    _write_fixture(
        een_dir,
        demand_id="TRFR20220315001",
        source_id="een_pod",
        source_uri="https://een.ec.europa.eu/partnering-opportunities/TRFR20220315001",
        payload_content=een_valid_html,
    )

    # 2. InnoGet candidate with deadline only (rejected with UNVERIFIABLE_PUBLICATION_DATE)
    innoget_deadline_html = (
        b"<!DOCTYPE html>\n<html lang=\"en\">\n<head><title>Rapid Biosensor Detection for Water Systems</title></head>\n"
        b"<body>\n"
        b"  <h1>Rapid Biosensor Detection for Municipal Water Systems</h1>\n"
        b"  <div class=\"tech-owner\"><p class=\"blue\">WaterTech Solutions</p><p>from Germany</p></div>\n"
        b"  <ul class=\"details\">\n"
        b"    <li>WaterTech Solutions</li>\n"
        b"    <li>Deadline at 31/12/2026</li>\n"
        b"  </ul>\n"
        b"  <div class=\"body post\">\n"
        b"    We are seeking novel microfluidic biosensors capable of detecting low concentrations\n"
        b"    of bacterial pathogens in real-time within drinking water distribution networks.\n"
        b"    The intended deployment is municipal monitoring stations requiring autonomous operation.\n"
        b"  </div>\n"
        b"  <div class=\"post-section-container\">\n"
        b"    <h3>Details of the Innovation Need</h3>\n"
        b"    Existing laboratory culture tests require up to forty-eight hours to deliver conclusive results.\n"
        b"    We require an inline biosensor cartridge with automated fluidic handling and sub-picomolar sensitivity.\n"
        b"  </div>\n"
        b"</body></html>\n"
    )
    _write_fixture(
        innoget_dir,
        demand_id="INNOGET-9001",
        source_id="innoget",
        source_uri="https://www.innoget.com/technology-calls/9001/water-biosensors",
        payload_content=innoget_deadline_html,
        extra_meta={"deadline_date_raw": "31/12/2026"},
    )

    # 3. Candidate with date in 2018 (rejected with OUT_OF_TEMPORAL_WINDOW)
    een_2018_html = (
        b"<!DOCTYPE html>\n<html lang=\"en\">\n<head><title>TRES20180612001 - Legacy Optical Sorting Systems</title></head>\n"
        b"<body>\n"
        b"  <h1>Legacy Optical Sorting Systems for High-Speed Agricultural Packaging</h1>\n"
        b"  <div class=\"reference-info\">POD Reference: TRES20180612001</div>\n"
        b"  <div class=\"summary\">\n"
        b"    A Spanish cooperative located in Valencia is seeking machine vision sorting systems\n"
        b"    specifically tailored to inspect citrus fruits on conveyor belts at rates exceeding\n"
        b"    ten tonnes per hour with high spectral accuracy and minimal bruising.\n"
        b"  </div>\n"
        b"  <div class=\"technical-problem\">\n"
        b"    <h3>Technical problem</h3>\n"
        b"    Current RGB cameras fail to distinguish surface fungal infections during early incubation stages.\n"
        b"    Hyperspectral imaging solutions are required to detect subsurface rot before packaging.\n"
        b"  </div>\n"
        b"</body></html>\n"
    )
    _write_fixture(
        een_dir,
        demand_id="TRES20180612001",
        source_id="een_pod",
        source_uri="https://een.ec.europa.eu/partnering-opportunities/TRES20180612001",
        payload_content=een_2018_html,
    )

    # 4. Candidate with short text (<25 words) (rejected with CONTENT_TOO_SHORT)
    een_short_html = (
        b"<!DOCTYPE html>\n<html lang=\"en\">\n<head><title>TRES20230510001 - Short Demand</title></head>\n"
        b"<body>\n"
        b"  <h1>Seeking Software Partner</h1>\n"
        b"  <div class=\"reference-info\">POD Reference: TRES20230510001</div>\n"
        b"  <div class=\"summary\">\n"
        b"    We need a partner for python web development.\n"
        b"  </div>\n"
        b"  <div class=\"technical-problem\">\n"
        b"    <h3>Technical problem</h3>\n"
        b"    We require a developer to build backend REST APIs.\n"
        b"  </div>\n"
        b"</body></html>\n"
    )
    _write_fixture(
        een_dir,
        demand_id="TRES20230510001",
        source_id="een_pod",
        source_uri="https://een.ec.europa.eu/partnering-opportunities/TRES20230510001",
        payload_content=een_short_html,
    )

    # 5. Completely malformed payload (emits to mapping_errors.json)
    malformed_html = b"   \n  \t  \n"
    _write_fixture(
        een_dir,
        demand_id="CORRUPT_PAYLOAD",
        source_id="een_pod",
        source_uri="https://een.ec.europa.eu/partnering-opportunities/CORRUPT_PAYLOAD",
        payload_content=malformed_html,
    )

    return raw_dir


def test_offline_validation_pipeline_execution(
    staged_raw_dir: Path,
    tmp_path: Path,
    block_network: None,
):
    """Verify entire offline pipeline: discovery, mapping, validation, partitioning, and sealing."""
    out_dir = tmp_path / "phase2_validation_out"

    summary = run_offline_validation(
        raw_dir=staged_raw_dir,
        out_dir=out_dir,
        policy_path=POLICY_PATH,
    )

    # Check returned summary
    assert summary["counts"]["total_raw"] == 5
    assert summary["counts"]["total_mapped"] == 4
    assert summary["counts"]["total_accepted"] == 1
    assert summary["counts"]["total_rejected"] == 3
    assert summary["counts"]["total_mapping_errors"] == 1

    # Verify all output files exist
    expected_files = [
        "candidates_raw.manifest.json",
        "candidates_raw.manifest.sha256",
        "candidates_mapped.json",
        "candidates_mapped.sha256",
        "candidates_accepted.json",
        "candidates_accepted.sha256",
        "candidates_rejected.json",
        "candidates_rejected.sha256",
        "mapping_errors.json",
        "acquisition_run.manifest.json",
    ]
    for fname in expected_files:
        p = out_dir / fname
        assert p.is_file(), f"Expected artifact not created: {p}"

    # Verify all cryptographic sidecars match actual file SHA-256
    for sidecar_name in [
        "candidates_raw.manifest.sha256",
        "candidates_mapped.sha256",
        "candidates_accepted.sha256",
        "candidates_rejected.sha256",
    ]:
        sidecar_path = out_dir / sidecar_name
        sidecar_content = sidecar_path.read_text(encoding="utf-8")
        assert sidecar_content.endswith("\n")
        parts = sidecar_content.strip().split()
        expected_hash = parts[0]
        basename = parts[1]

        target_file = out_dir / basename
        assert target_file.is_file()
        actual_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {basename}: {actual_hash} != {expected_hash}"

    # Verify candidates_raw.manifest.json
    raw_manifest = json.loads((out_dir / "candidates_raw.manifest.json").read_text(encoding="utf-8"))
    assert len(raw_manifest) == 5
    raw_ids = {r["demand_id"] for r in raw_manifest}
    assert raw_ids == {
        "TRFR20220315001",
        "INNOGET-9001",
        "TRES20180612001",
        "TRES20230510001",
        "CORRUPT_PAYLOAD",
    }
    for item in raw_manifest:
        assert "raw_payload_sha256" in item
        assert "source_uri" in item
        assert "acquisition_timestamp" in item

    # Verify mapping errors
    mapping_errors = json.loads((out_dir / "mapping_errors.json").read_text(encoding="utf-8"))
    assert len(mapping_errors) == 1
    assert mapping_errors[0]["demand_id"] == "CORRUPT_PAYLOAD"
    assert mapping_errors[0]["error_type"] == "MappingError"

    # Verify mapped dataset
    mapped = json.loads((out_dir / "candidates_mapped.json").read_text(encoding="utf-8"))
    assert len(mapped) == 4
    mapped_ids = {c["demand_id"] for c in mapped}
    assert mapped_ids == {
        "TRFR20220315001",
        "INNOGET-9001",
        "TRES20180612001",
        "TRES20230510001",
    }

    # Verify accepted dataset
    accepted = json.loads((out_dir / "candidates_accepted.json").read_text(encoding="utf-8"))
    assert len(accepted) == 1
    assert accepted[0]["demand_id"] == "TRFR20220315001"
    assert accepted[0]["publication_date_evidence"]["publication_date"] == "2022-03-15"

    # Verify rejected dataset
    rejected = json.loads((out_dir / "candidates_rejected.json").read_text(encoding="utf-8"))
    assert len(rejected) == 3
    rejected_by_id = {r["demand_id"]: r for r in rejected}

    # 1. InnoGet candidate with deadline only
    r_innoget = rejected_by_id["INNOGET-9001"]
    assert "UNVERIFIABLE_PUBLICATION_DATE" in r_innoget["rejection_reasons"]
    assert r_innoget["publication_date_evidence"]["publication_date"] is None
    assert r_innoget["publication_date_evidence"]["evidence_type"] == "unverifiable"
    assert "trigger_evidence" in r_innoget
    assert "UNVERIFIABLE_PUBLICATION_DATE" in r_innoget["trigger_evidence"]

    # 2. Date in 2018
    r_2018 = rejected_by_id["TRES20180612001"]
    assert "OUT_OF_TEMPORAL_WINDOW" in r_2018["rejection_reasons"]
    assert r_2018["publication_date_evidence"]["publication_date"] == "2018-06-12"
    assert "OUT_OF_TEMPORAL_WINDOW" in r_2018["trigger_evidence"]

    # 3. Short content
    r_short = rejected_by_id["TRES20230510001"]
    assert "CONTENT_TOO_SHORT" in r_short["rejection_reasons"]
    assert "CONTENT_TOO_SHORT" in r_short["trigger_evidence"]

    # Verify formal partition invariants (ADR 0032 Section 2.5)
    accepted_ids = {c["demand_id"] for c in accepted}
    rejected_ids = {c["demand_id"] for c in rejected}
    assert mapped_ids == accepted_ids | rejected_ids
    assert accepted_ids & rejected_ids == set()
    assert len(mapped) == len(accepted) + len(rejected)

    # Verify acquisition run manifest
    run_manifest = json.loads((out_dir / "acquisition_run.manifest.json").read_text(encoding="utf-8"))
    assert run_manifest["policy_version"] == "corpus_expansion_policy_v1"
    assert "policy_sha256" in run_manifest
    assert run_manifest["counts"]["total_raw"] == 5
    assert run_manifest["counts"]["total_mapped"] == 4
    assert run_manifest["counts"]["total_accepted"] == 1
    assert run_manifest["counts"]["total_rejected"] == 3
    assert run_manifest["counts"]["total_mapping_errors"] == 1


def test_offline_validation_cli(staged_raw_dir: Path, tmp_path: Path, block_network: None):
    """Verify main() CLI execution and exit code."""
    out_dir = tmp_path / "phase2_cli_out"
    exit_code = main(
        [
            "--raw-dir",
            str(staged_raw_dir),
            "--out-dir",
            str(out_dir),
            "--policy-path",
            str(POLICY_PATH),
        ]
    )
    assert exit_code == 0
    assert (out_dir / "candidates_accepted.json").is_file()
    assert (out_dir / "candidates_rejected.json").is_file()


def test_offline_validation_empty_raw_dir(tmp_path: Path, block_network: None):
    """Verify offline validation gracefully handles an empty raw directory."""
    empty_raw = tmp_path / "empty_raw"
    empty_raw.mkdir()
    out_dir = tmp_path / "empty_out"

    summary = run_offline_validation(
        raw_dir=empty_raw,
        out_dir=out_dir,
        policy_path=POLICY_PATH,
    )

    assert summary["counts"]["total_raw"] == 0
    assert summary["counts"]["total_mapped"] == 0
    assert summary["counts"]["total_accepted"] == 0
    assert summary["counts"]["total_rejected"] == 0
    assert summary["counts"]["total_mapping_errors"] == 0

    assert (out_dir / "candidates_accepted.json").is_file()
    assert (out_dir / "candidates_accepted.sha256").is_file()


def test_offline_validation_missing_policy_fails_fast(tmp_path: Path):
    """Verify that missing policy file raises FileNotFoundError immediately."""
    empty_raw = tmp_path / "empty_raw"
    empty_raw.mkdir()
    out_dir = tmp_path / "empty_out"

    with pytest.raises(FileNotFoundError, match="Corpus expansion policy file not found"):
        run_offline_validation(
            raw_dir=empty_raw,
            out_dir=out_dir,
            policy_path=tmp_path / "nonexistent_policy.json",
        )


def test_offline_validation_corrupt_policy_sidecar_fails_fast(tmp_path: Path):
    """Verify that corrupted policy sidecar raises PolicyIntegrityError immediately."""
    empty_raw = tmp_path / "empty_raw"
    empty_raw.mkdir()
    out_dir = tmp_path / "empty_out"

    fake_policy = tmp_path / "fake_policy.json"
    fake_policy.write_text(POLICY_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    fake_sidecar = tmp_path / "fake_policy.sha256"
    fake_sidecar.write_text("0" * 64 + "  fake_policy.json\n", encoding="utf-8")

    with pytest.raises(PolicyIntegrityError, match="hash mismatch"):
        run_offline_validation(
            raw_dir=empty_raw,
            out_dir=out_dir,
            policy_path=fake_policy,
        )
