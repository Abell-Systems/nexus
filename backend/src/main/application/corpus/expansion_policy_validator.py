"""Application service for loading, verifying, and validating demand candidates against expansion policy."""

import hashlib
import json
from pathlib import Path

from domain.models.corpus_expansion import (
    CandidateRejectionReason,
    CandidateValidationResult,
    CorpusExpansionPolicy,
    DemandCandidateContractRecord,
)


class PolicyIntegrityError(Exception):
    """Raised when policy configuration file is corrupted or hash does not match."""


def load_corpus_expansion_policy(policy_path: Path, hash_path: Path | None = None) -> CorpusExpansionPolicy:
    """Load, verify cryptographic integrity, and parse a CorpusExpansionPolicy."""
    p_path = Path(policy_path)
    if not p_path.is_file():
        raise FileNotFoundError(f"Policy configuration file not found: {p_path}")

    h_path = Path(hash_path) if hash_path is not None else p_path.with_suffix(".sha256")
    if not h_path.is_file():
        raise FileNotFoundError(f"Policy hash sidecar file not found: {h_path}")

    content_bytes = p_path.read_bytes()
    raw_hash = h_path.read_text(encoding="utf-8").strip()
    parts = raw_hash.split()
    if not parts:
        raise PolicyIntegrityError(f"Policy hash sidecar file is empty: {h_path}")
    expected_hash = parts[0]
    actual_hash = hashlib.sha256(content_bytes).hexdigest()

    if actual_hash.lower() != expected_hash.lower():
        raise PolicyIntegrityError(
            f"Policy configuration SHA-256 hash mismatch: expected {expected_hash}, got {actual_hash}"
        )

    data = json.loads(content_bytes.decode("utf-8"))
    if isinstance(data, dict):
        data = {k: v for k, v in data.items() if k != "$schema"}
    return CorpusExpansionPolicy.model_validate(data)


def validate_demand_candidate(
    candidate: DemandCandidateContractRecord, policy: CorpusExpansionPolicy
) -> CandidateValidationResult:
    """Deterministically validate an acquired candidate against individual candidate policy criteria."""
    reasons: list[CandidateRejectionReason] = []

    # 1. Source authorization
    source_cfg = next((s for s in policy.sources if s.source_id == candidate.source_id), None)
    if source_cfg is None:
        reasons.append(CandidateRejectionReason.UNAUTHORIZED_SOURCE)
    else:
        # 2. Document construct compatibility
        if candidate.source_construct not in source_cfg.permitted_constructs:
            reasons.append(CandidateRejectionReason.INCOMPATIBLE_CONSTRUCT)

    # 3. Temporal window boundary
    if (
        candidate.publication_date < policy.temporal_window.min_publication_date
        or candidate.publication_date > policy.temporal_window.max_publication_date
    ):
        reasons.append(CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW)

    # 4. Geographic stratum authorization
    allowed_strata = {s.stratum_id for s in policy.geographic_strata}
    if candidate.geographic_stratum not in allowed_strata:
        reasons.append(CandidateRejectionReason.UNAUTHORIZED_GEOGRAPHIC_STRATUM)

    # 5. Content requirements: word count
    word_count = len(candidate.description_text.split())
    if word_count < policy.content_requirements.min_word_count:
        reasons.append(CandidateRejectionReason.CONTENT_TOO_SHORT)

    # 6. Confidentiality redaction
    if (
        not policy.content_requirements.allow_explicit_confidentiality_redaction
        and candidate.has_confidentiality_redaction
    ):
        reasons.append(CandidateRejectionReason.CONFIDENTIALITY_REDACTED)

    # 7. Public access verification
    if not candidate.is_publicly_accessible:
        reasons.append(CandidateRejectionReason.ACCESS_NOT_PUBLIC)

    if not reasons:
        return CandidateValidationResult.accept()
    return CandidateValidationResult.reject(reasons)
