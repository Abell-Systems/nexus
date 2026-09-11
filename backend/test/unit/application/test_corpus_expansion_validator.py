"""Unit tests for corpus expansion policy loader and candidate validator."""

from datetime import date
from pathlib import Path

import pytest

from application.corpus.expansion_policy_validator import (
    PolicyIntegrityError,
    load_corpus_expansion_policy,
    validate_demand_candidate,
)
from domain.models.corpus_expansion import (
    CandidateRejectionReason,
    DemandCandidateContractRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = REPO_ROOT / "config" / "policies" / "data" / "corpus_expansion_policy_v1.json"


def test_load_corpus_expansion_policy_success() -> None:
    policy = load_corpus_expansion_policy(POLICY_PATH)
    assert policy.policy_version == "corpus_expansion_policy_v1"
    assert policy.target_sample_size.target_independent_demands == 60
    assert len(policy.sources) == 2


def test_load_corpus_expansion_policy_missing_file_raises(tmp_path: Path) -> None:
    non_existent = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        load_corpus_expansion_policy(non_existent)


def test_load_corpus_expansion_policy_missing_hash_sidecar_raises(tmp_path: Path) -> None:
    fake_json = tmp_path / "policy.json"
    fake_json.write_text('{"policy_version": "test"}', encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="Policy hash sidecar file not found"):
        load_corpus_expansion_policy(fake_json)


def test_load_corpus_expansion_policy_hash_mismatch_raises(tmp_path: Path) -> None:
    fake_json = tmp_path / "policy.json"
    fake_hash = tmp_path / "policy.sha256"
    fake_json.write_text('{"policy_version": "test"}', encoding="utf-8")
    fake_hash.write_text("0000000000000000000000000000000000000000000000000000000000000000\n", encoding="utf-8")
    with pytest.raises(PolicyIntegrityError, match="SHA-256 hash mismatch"):
        load_corpus_expansion_policy(fake_json, fake_hash)


def test_load_corpus_expansion_policy_empty_hash_raises(tmp_path: Path) -> None:
    fake_json = tmp_path / "policy.json"
    fake_hash = tmp_path / "policy.sha256"
    fake_json.write_text('{"policy_version": "test"}', encoding="utf-8")
    fake_hash.write_text("   \n", encoding="utf-8")
    with pytest.raises(PolicyIntegrityError, match="Policy hash sidecar file is empty"):
        load_corpus_expansion_policy(fake_json, fake_hash)


def test_validate_demand_candidate_valid_passes() -> None:
    policy = load_corpus_expansion_policy(POLICY_PATH)
    candidate = DemandCandidateContractRecord(
        demand_id="INNOGET-3001",
        source_id="innoget",
        source_construct="Technology call",
        publication_date=date(2023, 5, 14),
        publication_date_evidence_field="posted_date",
        publication_date_evidence_text="14 May 2023",
        geographic_stratum="spain",
        title="Industrial bio-based adhesive demand",
        description_text=(
            "Seeking high strength bio adhesive for paper packaging with fast curing under thirty seconds "
            "in automated corrugated board production lines without emitting harmful volatile compounds."
        ),
        language_code="en",
        organization_raw="Packaging Corp",
        is_publicly_accessible=True,
        has_confidentiality_redaction=False,
    )
    res = validate_demand_candidate(candidate, policy)
    assert res.status == "ACCEPT"
    assert res.rejection_reasons == ()


def test_validate_demand_candidate_rejections_deterministic_exhaustive() -> None:
    policy = load_corpus_expansion_policy(POLICY_PATH)
    # Fails 3 criteria: unauthorized source, out of date window (2019), and short text (<25 words)
    candidate = DemandCandidateContractRecord(
        demand_id="UNKNOWN_PORTAL-01",
        source_id="unknown_portal",
        source_construct="Technology call",
        publication_date=date(2019, 12, 31),
        publication_date_evidence_field="date",
        publication_date_evidence_text="2019-12-31",
        geographic_stratum="spain",
        title="Short demand",
        description_text="Short description with few words only.",
        language_code="en",
        organization_raw=None,
        is_publicly_accessible=True,
        has_confidentiality_redaction=False,
    )
    res = validate_demand_candidate(candidate, policy)
    assert res.status == "REJECT"
    assert res.rejection_reasons == (
        CandidateRejectionReason.CONTENT_TOO_SHORT,
        CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW,
        CandidateRejectionReason.UNAUTHORIZED_SOURCE,
    )


def test_validate_demand_candidate_date_boundaries() -> None:
    policy = load_corpus_expansion_policy(POLICY_PATH)
    base_dict = {
        "demand_id": "INNOGET-DATE-TEST",
        "source_id": "innoget",
        "source_construct": "Technology call",
        "publication_date_evidence_field": "posted_date",
        "publication_date_evidence_text": "text",
        "geographic_stratum": "international_european",
        "title": "Date boundary test",
        "description_text": (
            "Seeking technical solution for high precision industrial manufacturing process with strict energy "
            "consumption standards and minimal thermal distortion during high speed continuous operation cycles for aerospace components."
        ),
        "language_code": "en",
        "is_publicly_accessible": True,
        "has_confidentiality_redaction": False,
    }
    # 2020-01-01 -> ACCEPT
    c1 = DemandCandidateContractRecord(publication_date=date(2020, 1, 1), **base_dict)
    assert validate_demand_candidate(c1, policy).status == "ACCEPT"

    # 2025-12-31 -> ACCEPT
    c2 = DemandCandidateContractRecord(publication_date=date(2025, 12, 31), **base_dict)
    assert validate_demand_candidate(c2, policy).status == "ACCEPT"

    # 2019-12-31 -> REJECT
    c3 = DemandCandidateContractRecord(publication_date=date(2019, 12, 31), **base_dict)
    assert validate_demand_candidate(c3, policy).status == "REJECT"

    # 2026-01-01 -> REJECT
    c4 = DemandCandidateContractRecord(publication_date=date(2026, 1, 1), **base_dict)
    assert validate_demand_candidate(c4, policy).status == "REJECT"


def test_validate_demand_candidate_word_count_boundaries() -> None:
    policy = load_corpus_expansion_policy(POLICY_PATH)
    base_dict = {
        "demand_id": "INNOGET-WORD-TEST",
        "source_id": "innoget",
        "source_construct": "Technology call",
        "publication_date": date(2023, 6, 1),
        "publication_date_evidence_field": "posted_date",
        "publication_date_evidence_text": "text",
        "geographic_stratum": "spain",
        "title": "Word count boundary test",
        "language_code": "en",
        "is_publicly_accessible": True,
        "has_confidentiality_redaction": False,
    }
    # 24 words -> REJECT
    words_24 = " ".join([f"word{i}" for i in range(24)])
    c_24 = DemandCandidateContractRecord(description_text=words_24, **base_dict)
    res_24 = validate_demand_candidate(c_24, policy)
    assert res_24.status == "REJECT"
    assert res_24.rejection_reasons == (CandidateRejectionReason.CONTENT_TOO_SHORT,)

    # 25 words -> ACCEPT
    words_25 = " ".join([f"word{i}" for i in range(25)])
    c_25 = DemandCandidateContractRecord(description_text=words_25, **base_dict)
    res_25 = validate_demand_candidate(c_25, policy)
    assert res_25.status == "ACCEPT"
    assert res_25.rejection_reasons == ()


def test_validate_demand_candidate_confidentiality_and_access() -> None:
    policy = load_corpus_expansion_policy(POLICY_PATH)
    base_dict = {
        "demand_id": "INNOGET-CONF-TEST",
        "source_id": "innoget",
        "source_construct": "Technology call",
        "publication_date": date(2022, 6, 1),
        "publication_date_evidence_field": "posted_date",
        "publication_date_evidence_text": "text",
        "geographic_stratum": "spain",
        "title": "Access test",
        "description_text": (
            "Seeking innovative solution for recycling polymer components from electronic equipment safely and "
            "cleanly without releasing toxic chemical substances into groundwater or municipal infrastructure networks in European facilities."
        ),
        "language_code": "es",
    }
    # Confidentiality redacted -> REJECT
    c1 = DemandCandidateContractRecord(
        is_publicly_accessible=True,
        has_confidentiality_redaction=True,
        **base_dict,
    )
    res1 = validate_demand_candidate(c1, policy)
    assert CandidateRejectionReason.CONFIDENTIALITY_REDACTED in res1.rejection_reasons

    # Non-public access -> REJECT
    c2 = DemandCandidateContractRecord(
        is_publicly_accessible=False,
        has_confidentiality_redaction=False,
        **base_dict,
    )
    res2 = validate_demand_candidate(c2, policy)
    assert CandidateRejectionReason.ACCESS_NOT_PUBLIC in res2.rejection_reasons


def test_validate_demand_candidate_incompatible_construct_and_geographic_stratum() -> None:
    policy = load_corpus_expansion_policy(POLICY_PATH)
    base_dict = {
        "demand_id": "EEN-CONSTRUCT-TEST",
        "source_id": "een_pod",
        "source_construct": "Technology offer",  # Permitted is "Technology request"
        "publication_date": date(2022, 6, 1),
        "publication_date_evidence_field": "posted_date",
        "publication_date_evidence_text": "text",
        "geographic_stratum": "unauthorized_asia",  # Not in allowed strata
        "title": "Incompatible construct and stratum test",
        "description_text": (
            "Seeking innovative solution for recycling polymer components from electronic equipment safely and "
            "cleanly without releasing toxic chemical substances into groundwater or municipal infrastructure networks in European facilities."
        ),
        "language_code": "en",
        "is_publicly_accessible": True,
        "has_confidentiality_redaction": False,
    }
    candidate = DemandCandidateContractRecord(**base_dict)
    res = validate_demand_candidate(candidate, policy)
    assert res.status == "REJECT"
    assert res.rejection_reasons == (
        CandidateRejectionReason.INCOMPATIBLE_CONSTRUCT,
        CandidateRejectionReason.UNAUTHORIZED_GEOGRAPHIC_STRATUM,
    )
