import re
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator


class VerificationStatus(str, Enum):
    SOURCE_REPORTED = "source_reported"
    INDEPENDENTLY_VERIFIED = "independently_verified"
    DERIVED = "derived"
    UNAVAILABLE = "unavailable"


class FieldObservation(BaseModel):
    """Fine-grained provenance record tracking the origin and authority of a specific field observation."""

    entity_id: str
    field_name: str
    observed_value_json: str
    value_type: str
    source_authority: str
    source_uri: str
    retrieval_timestamp: datetime
    raw_payload_sha256: str
    extraction_version: str
    verification_status: VerificationStatus

    @field_validator("raw_payload_sha256")
    @classmethod
    def validate_sha256_format(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v
