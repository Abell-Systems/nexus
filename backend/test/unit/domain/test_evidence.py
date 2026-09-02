from datetime import datetime

import pytest

from domain.models.evidence import FieldObservation, VerificationStatus


def test_field_observation_strict_64_hex_sha():
    # Valid 64-char hex SHA passes
    obs = FieldObservation(
        entity_id="ES-2849102-B2",
        field_name="publication_date",
        observed_value_json='"2021-11-25"',
        value_type="str",
        source_authority="OEPM BOPI",
        source_uri="https://consultas2.oepm.es/InvenesWeb/detalle?tipo=PAT&ref=P202030431",
        retrieval_timestamp=datetime(2026, 8, 25, 11, 8, 53),
        raw_payload_sha256="2832dc5936b881b4045b26b415f5c5ed2c0bfdc71f6902b838d85000e6799d7b",
        extraction_version="1.0.0",
        verification_status=VerificationStatus.SOURCE_REPORTED,
    )
    assert obs.verification_status == VerificationStatus.SOURCE_REPORTED
    assert obs.raw_payload_sha256 == "2832dc5936b881b4045b26b415f5c5ed2c0bfdc71f6902b838d85000e6799d7b"


def test_field_observation_invalid_sha_raises():
    base_kwargs = {
        "entity_id": "ES-2849102-B2",
        "field_name": "publication_date",
        "observed_value_json": '"2021-11-25"',
        "value_type": "str",
        "source_authority": "OEPM BOPI",
        "source_uri": "https://consultas2.oepm.es/InvenesWeb/",
        "retrieval_timestamp": datetime(2026, 8, 25, 11, 8, 53),
        "extraction_version": "1.0.0",
        "verification_status": VerificationStatus.SOURCE_REPORTED,
    }

    # Short SHA fails
    with pytest.raises(ValueError, match="Invalid SHA-256 digest format"):
        FieldObservation(raw_payload_sha256="abc123short", **base_kwargs)

    # Non-hex characters fail
    bad_z_sha = "z" * 64
    with pytest.raises(ValueError, match="Invalid SHA-256 digest format"):
        FieldObservation(raw_payload_sha256=bad_z_sha, **base_kwargs)

    # Uppercase hex characters fail (strict lowercase hex)
    bad_a_sha = "A" * 64
    with pytest.raises(ValueError, match="Invalid SHA-256 digest format"):
        FieldObservation(raw_payload_sha256=bad_a_sha, **base_kwargs)


def test_verification_status_values():
    assert VerificationStatus.SOURCE_REPORTED == "source_reported"
    assert VerificationStatus.INDEPENDENTLY_VERIFIED == "independently_verified"
    assert VerificationStatus.DERIVED == "derived"
    assert VerificationStatus.UNAVAILABLE == "unavailable"
