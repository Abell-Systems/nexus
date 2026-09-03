"""Domain models for versioned, cryptographically-hashed jurisdiction origin policies."""

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JurisdictionEntry(BaseModel):
    """Canonical jurisdiction definition with associated aliases."""

    canonical_name: str
    aliases: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class OriginPolicyConfig(BaseModel):
    """Immutable, versioned policy mapping observed country tokens to canonical jurisdictions."""

    policy_id: str
    policy_version: str
    target_jurisdiction: str
    recognized_jurisdictions: dict[str, JurisdictionEntry] = Field(default_factory=dict)
    policy_sha256: str = ""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_policy_invariants(self) -> "OriginPolicyConfig":
        if not self.policy_id.strip():
            raise ValueError("policy_id cannot be empty")
        if not self.policy_version.strip():
            raise ValueError("policy_version cannot be empty")
        if not self.target_jurisdiction.strip():
            raise ValueError("target_jurisdiction cannot be empty")
        if self.target_jurisdiction not in self.recognized_jurisdictions:
            raise ValueError(
                f"target_jurisdiction '{self.target_jurisdiction}' must be defined in recognized_jurisdictions"
            )
        return self

    @classmethod
    def load_from_json(cls, policy_path: Path | str) -> "OriginPolicyConfig":
        """Load policy JSON and compute its deterministic SHA-256 digest."""
        path = Path(policy_path)
        if not path.exists():
            raise FileNotFoundError(f"Origin policy configuration file does not exist: {path}")
        content_bytes = path.read_bytes()
        try:
            data = json.loads(content_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Corrupted or invalid origin policy JSON in {path}: {e}") from e

        data_no_sha = {k: v for k, v in data.items() if k != "policy_sha256"}
        canonical_json = json.dumps(data_no_sha, sort_keys=True)
        computed_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        return cls(**data, policy_sha256=computed_sha256)

    def resolve_jurisdiction(self, raw_token: str | None) -> str | None:
        """Resolve a raw string token to an ISO 2-letter country code if recognized."""
        if not raw_token or not raw_token.strip():
            return None
        token = raw_token.strip().lower()

        for code, entry in self.recognized_jurisdictions.items():
            if token == code.lower() or token == entry.canonical_name.lower():
                return code
            if any(token == alias.lower() for alias in entry.aliases):
                return code

        return None
