# PR #101a: Phase-2 Demand Corpus Expansion Contract ($N \ge 60$) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the formal, pre-specified corpus expansion contract (ADR 0031), declarative versioned acquisition policy (`corpus_expansion_policy_v1.json` + `.sha256`), canonical candidate contract model, and typed application validator to expand the demand corpus towards $N \ge 60$ independent observations without convenience or outcome-dependent sampling bias.

**Architecture:** Domain models in `backend/src/main/domain/models/corpus_expansion.py` define frozen schemas for declarative policies and canonical candidate records. An application validator in `backend/src/main/application/corpus/expansion_policy_validator.py` provides fail-fast cryptographic policy loading and deterministic multi-criteria candidate evaluation. A binding ADR 0031 and operational protocol document complete the contract. Zero data acquisition, scrapers, or split alterations are performed in this PR.

**Tech Stack:** Python 3.11+, Pydantic v2 (`BaseModel`, `ConfigDict(frozen=True, extra="forbid")`), `hashlib`, `pathlib`, `pytest`, `ruff`, `mypy`.

## Global Constraints

- **AGENTS.md Directive:** Zero hardcoded business lists or policy values in code; all thresholds externalized to versioned JSON in `config/policies/data/`.
- **Fail-Fast Invariant:** Missing, corrupted, or altered policy/hash configuration raises an immediate `FileNotFoundError` or `PolicyIntegrityError`; no in-memory fallbacks.
- **Provider-Agnostic Core (ADR 0009):** `domain` and `application` contain zero scraper SDKs, HTTP clients, or network dependencies.
- **Strict Separation:** PR #101a defines the contract and validator; it acquires zero candidates, produces zero data artifacts, and leaves historical splits (`devtest_split_n18_v2.json`) untouched.
- **Candidate Evaluation vs. Corpus Audit:** The validator evaluates individual candidates deterministically (`ACCEPT` / `REJECT` with exhaustive reasons); multi-candidate independence grouping (ADR 0029), sector concentration, and corpus sufficiency ($N \ge 60$) are enforced downstream in #102.

---

### Task 1: Domain Models for Corpus Expansion Policy and Candidate Contract

**Files:**
- Create: `backend/src/main/domain/models/corpus_expansion.py`
- Test: `backend/test/unit/domain/test_corpus_expansion_models.py`

**Interfaces:**
- Produces:
  - `PermittedSourceConfig(source_id: str, display_name: str, permitted_constructs: tuple[str, ...], public_access_mode: str)`
  - `TemporalWindowConfig(min_publication_date: date, max_publication_date: date, date_interpretation: str)`
  - `GeographicStratumConfig(stratum_id: str, description: str)`
  - `ContentRequirementsConfig(min_word_count: int, require_technical_problem: bool, allow_explicit_confidentiality_redaction: bool)`
  - `ConcentrationMonitoringConfig(sector_warning_threshold: float, max_independent_per_organization: int)`
  - `UnknownHandlingConfig(unknown_organization_split_policy: str, counts_towards_independent_target: bool)`
  - `TargetSampleSizeConfig(target_independent_demands: int, power_analysis_reference: str)`
  - `CorpusExpansionPolicy(...)`
  - `DemandCandidateContractRecord(demand_id: str, source_id: str, source_construct: str, publication_date: date, publication_date_evidence_field: str, publication_date_evidence_text: str, geographic_stratum: str, title: str, description_text: str, language_code: str, organization_raw: str | None, is_publicly_accessible: bool, has_confidentiality_redaction: bool)`
  - `CandidateRejectionReason(str, Enum)`
  - `CandidateValidationResult(status: str, rejection_reasons: tuple[CandidateRejectionReason, ...])`

- [ ] **Step 1: Write the failing unit tests for domain models**

Create `backend/test/unit/domain/test_corpus_expansion_models.py`:
```python
"""Unit tests for corpus expansion domain models and candidate contracts."""

from datetime import date
import pytest
from pydantic import ValidationError

from domain.models.corpus_expansion import (
    CandidateRejectionReason,
    CandidateValidationResult,
    ConcentrationMonitoringConfig,
    ContentRequirementsConfig,
    CorpusExpansionPolicy,
    DemandCandidateContractRecord,
    GeographicStratumConfig,
    PermittedSourceConfig,
    TargetSampleSizeConfig,
    TemporalWindowConfig,
    UnknownHandlingConfig,
)


def test_permitted_source_config_valid() -> None:
    src = PermittedSourceConfig(
        source_id="innoget",
        display_name="InnoGet",
        permitted_constructs=("Technology call",),
        public_access_mode="unauthenticated_public_http",
    )
    assert src.source_id == "innoget"
    assert "Technology call" in src.permitted_constructs


def test_temporal_window_invalid_order_raises() -> None:
    with pytest.raises(ValidationError, match="min_publication_date must be <= max_publication_date"):
        TemporalWindowConfig(
            min_publication_date=date(2026, 1, 1),
            max_publication_date=date(2020, 1, 1),
            date_interpretation="public_publication_date",
        )


def test_content_requirements_min_word_count_non_negative() -> None:
    with pytest.raises(ValidationError, match="min_word_count must be >= 0"):
        ContentRequirementsConfig(
            min_word_count=-1,
            require_technical_problem=True,
            allow_explicit_confidentiality_redaction=False,
        )


def test_concentration_monitoring_threshold_bounds() -> None:
    with pytest.raises(ValidationError, match="sector_warning_threshold must be in"):
        ConcentrationMonitoringConfig(
            sector_warning_threshold=1.5,
            max_independent_per_organization=1,
        )


def test_corpus_expansion_policy_frozen() -> None:
    policy = CorpusExpansionPolicy(
        policy_version="corpus_expansion_policy_v1",
        description="Phase 2 expansion policy",
        target_sample_size=TargetSampleSizeConfig(
            target_independent_demands=60,
            power_analysis_reference="data/experiments/power_analysis_wilcoxon.json",
        ),
        sources=(
            PermittedSourceConfig(
                source_id="innoget",
                display_name="InnoGet",
                permitted_constructs=("Technology call",),
                public_access_mode="unauthenticated_public_http",
            ),
        ),
        temporal_window=TemporalWindowConfig(
            min_publication_date=date(2020, 1, 1),
            max_publication_date=date(2025, 12, 31),
            date_interpretation="public_publication_date",
        ),
        geographic_strata=(
            GeographicStratumConfig(stratum_id="spain", description="Spain"),
            GeographicStratumConfig(stratum_id="international_european", description="Europe"),
        ),
        content_requirements=ContentRequirementsConfig(
            min_word_count=25,
            require_technical_problem=True,
            allow_explicit_confidentiality_redaction=False,
        ),
        concentration_monitoring=ConcentrationMonitoringConfig(
            sector_warning_threshold=0.35,
            max_independent_per_organization=1,
        ),
        unknown_handling=UnknownHandlingConfig(
            unknown_organization_split_policy="dev_only",
            counts_towards_independent_target=False,
        ),
    )
    with pytest.raises(ValidationError):
        policy.policy_version = "corpus_expansion_policy_v2"  # type: ignore[misc]


def test_demand_candidate_contract_record_frozen_extra_forbid() -> None:
    candidate = DemandCandidateContractRecord(
        demand_id="INNOGET-3001",
        source_id="innoget",
        source_construct="Technology call",
        publication_date=date(2023, 5, 14),
        publication_date_evidence_field="posted_date",
        publication_date_evidence_text="14 May 2023",
        geographic_stratum="spain",
        title="Biodegradable surfactant demand",
        description_text="Seeking surfactant with high biodegradability under 20 degrees Celsius.",
        language_code="en",
        organization_raw="EcoClean S.L.",
        is_publicly_accessible=True,
        has_confidentiality_redaction=False,
    )
    assert candidate.demand_id == "INNOGET-3001"
    with pytest.raises(ValidationError):
        candidate.title = "New title"  # type: ignore[misc]


def test_candidate_validation_result_deterministic_sorting() -> None:
    res = CandidateValidationResult.reject([
        CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW,
        CandidateRejectionReason.CONTENT_TOO_SHORT,
    ])
    assert res.status == "REJECT"
    assert res.rejection_reasons == (
        CandidateRejectionReason.CONTENT_TOO_SHORT,
        CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/domain/test_corpus_expansion_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain.models.corpus_expansion'`

- [ ] **Step 3: Implement domain models in `backend/src/main/domain/models/corpus_expansion.py`**

Create `backend/src/main/domain/models/corpus_expansion.py`:
```python
"""Domain models and contracts for Phase-2 demand corpus expansion."""

from datetime import date
from enum import Enum
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PermittedSourceConfig(BaseModel):
    """Configuration for an authorized acquisition source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    permitted_constructs: tuple[str, ...] = Field(..., min_length=1)
    public_access_mode: str = Field(..., min_length=1)


class TemporalWindowConfig(BaseModel):
    """Temporal boundaries for demand publication."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_publication_date: date
    max_publication_date: date
    date_interpretation: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_date_order(self) -> "TemporalWindowConfig":
        if self.min_publication_date > self.max_publication_date:
            raise ValueError("min_publication_date must be <= max_publication_date")
        return self


class GeographicStratumConfig(BaseModel):
    """Specification of an authorized geographic sampling stratum."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stratum_id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)


class ContentRequirementsConfig(BaseModel):
    """Pre-specified content completeness and integrity criteria."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_word_count: int = Field(..., ge=0)
    require_technical_problem: bool
    allow_explicit_confidentiality_redaction: bool

    @field_validator("min_word_count")
    @classmethod
    def validate_min_word_count(cls, v: int) -> int:
        if v < 0:
            raise ValueError("min_word_count must be >= 0")
        return v


class ConcentrationMonitoringConfig(BaseModel):
    """Thresholds for monitoring corpus-level concentration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sector_warning_threshold: float = Field(..., gt=0.0, le=1.0)
    max_independent_per_organization: int = Field(..., ge=1)

    @field_validator("sector_warning_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError("sector_warning_threshold must be in (0.0, 1.0]")
        return v


class UnknownHandlingConfig(BaseModel):
    """Handling rules for indeterminate organization independence."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    unknown_organization_split_policy: str = Field(..., min_length=1)
    counts_towards_independent_target: bool


class TargetSampleSizeConfig(BaseModel):
    """Target statistical power requirements for the independent corpus."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target_independent_demands: int = Field(..., ge=1)
    power_analysis_reference: str = Field(..., min_length=1)


class CorpusExpansionPolicy(BaseModel):
    """Declarative versioned policy governing Phase-2 corpus expansion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_version: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    target_sample_size: TargetSampleSizeConfig
    sources: tuple[PermittedSourceConfig, ...] = Field(..., min_length=1)
    temporal_window: TemporalWindowConfig
    geographic_strata: tuple[GeographicStratumConfig, ...] = Field(..., min_length=1)
    content_requirements: ContentRequirementsConfig
    concentration_monitoring: ConcentrationMonitoringConfig
    unknown_handling: UnknownHandlingConfig

    @field_validator("policy_version")
    @classmethod
    def validate_policy_version_prefix(cls, v: str) -> str:
        if not v.startswith("corpus_expansion_policy_"):
            raise ValueError("policy_version must start with 'corpus_expansion_policy_'")
        return v


class DemandCandidateContractRecord(BaseModel):
    """Canonical representation of an acquired candidate prior to policy validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    demand_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    source_construct: str = Field(..., min_length=1)
    publication_date: date
    publication_date_evidence_field: str = Field(..., min_length=1)
    publication_date_evidence_text: str = Field(..., min_length=1)
    geographic_stratum: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description_text: str = Field(..., min_length=1)
    language_code: str = Field(..., min_length=2, max_length=5)
    organization_raw: str | None = None
    is_publicly_accessible: bool
    has_confidentiality_redaction: bool


class CandidateRejectionReason(str, Enum):
    """Pre-specified candidate exclusion reasons."""

    UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"
    INCOMPATIBLE_CONSTRUCT = "INCOMPATIBLE_CONSTRUCT"
    OUT_OF_TEMPORAL_WINDOW = "OUT_OF_TEMPORAL_WINDOW"
    UNAUTHORIZED_GEOGRAPHIC_STRATUM = "UNAUTHORIZED_GEOGRAPHIC_STRATUM"
    CONTENT_TOO_SHORT = "CONTENT_TOO_SHORT"
    CONFIDENTIALITY_REDACTED = "CONFIDENTIALITY_REDACTED"
    ACCESS_NOT_PUBLIC = "ACCESS_NOT_PUBLIC"


class CandidateValidationResult(BaseModel):
    """Result of validating a candidate against corpus expansion policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str
    rejection_reasons: tuple[CandidateRejectionReason, ...]

    @classmethod
    def accept(cls) -> "CandidateValidationResult":
        return cls(status="ACCEPT", rejection_reasons=())

    @classmethod
    def reject(
        cls, reasons: Sequence[CandidateRejectionReason]
    ) -> "CandidateValidationResult":
        # Deduplicate and sort deterministically by enum name
        sorted_reasons = tuple(sorted(set(reasons), key=lambda r: r.value))
        return cls(status="REJECT", rejection_reasons=sorted_reasons)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest backend/test/unit/domain/test_corpus_expansion_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit domain models**

```bash
git add backend/src/main/domain/models/corpus_expansion.py backend/test/unit/domain/test_corpus_expansion_models.py
git commit -m "feat(domain): add corpus expansion policy and candidate contract models"
```

---

### Task 2: Declarative Policy Configuration, Hash Sidecar, and Application Validator

**Files:**
- Create: `config/policies/data/corpus_expansion_policy_v1.json`
- Create: `config/policies/data/corpus_expansion_policy_v1.sha256`
- Create: `backend/src/main/application/corpus/expansion_policy_validator.py`
- Test: `backend/test/unit/application/test_corpus_expansion_validator.py`

**Interfaces:**
- Consumes: Models from `backend/src/main/domain/models/corpus_expansion.py`
- Produces:
  - `load_corpus_expansion_policy(policy_path: Path, hash_path: Path | None = None) -> CorpusExpansionPolicy`
  - `validate_demand_candidate(candidate: DemandCandidateContractRecord, policy: CorpusExpansionPolicy) -> CandidateValidationResult`
  - `PolicyIntegrityError(Exception)`

- [ ] **Step 1: Write declarative policy JSON and generate its SHA-256 sidecar**

Write `config/policies/data/corpus_expansion_policy_v1.json`:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "policy_version": "corpus_expansion_policy_v1",
  "description": "Binding acquisition and sampling frame policy for Phase-2 demand corpus expansion towards N>=60 independent observations.",
  "target_sample_size": {
    "target_independent_demands": 60,
    "power_analysis_reference": "data/experiments/power_analysis_wilcoxon.json"
  },
  "sources": [
    {
      "source_id": "innoget",
      "display_name": "InnoGet Open Innovation Network",
      "permitted_constructs": [
        "Technology call"
      ],
      "public_access_mode": "unauthenticated_public_http"
    },
    {
      "source_id": "een_pod",
      "display_name": "Enterprise Europe Network Partnering Opportunities Database",
      "permitted_constructs": [
        "Technology request"
      ],
      "public_access_mode": "unauthenticated_public_http"
    }
  ],
  "temporal_window": {
    "min_publication_date": "2020-01-01",
    "max_publication_date": "2025-12-31",
    "date_interpretation": "public_publication_date"
  },
  "geographic_strata": [
    {
      "stratum_id": "spain",
      "description": "Domestic Spanish demand stratum (continuity with Phase 1)"
    },
    {
      "stratum_id": "international_european",
      "description": "Complementary European/International demand stratum"
    }
  ],
  "content_requirements": {
    "min_word_count": 25,
    "require_technical_problem": true,
    "allow_explicit_confidentiality_redaction": false
  },
  "concentration_monitoring": {
    "sector_warning_threshold": 0.35,
    "max_independent_per_organization": 1
  },
  "unknown_handling": {
    "unknown_organization_split_policy": "dev_only",
    "counts_towards_independent_target": false
  }
}
```

Compute sha256:
```bash
sha256sum config/policies/data/corpus_expansion_policy_v1.json | awk '{print $1}' > config/policies/data/corpus_expansion_policy_v1.sha256
```

- [ ] **Step 2: Write failing unit tests for policy loading, hash integrity, and candidate validation**

Create `backend/test/unit/application/test_corpus_expansion_validator.py`:
```python
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

REPO_ROOT = Path(__file__).resolve().parents[5]
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


def test_load_corpus_expansion_policy_hash_mismatch_raises(tmp_path: Path) -> None:
    fake_json = tmp_path / "policy.json"
    fake_hash = tmp_path / "policy.sha256"
    fake_json.write_text('{"policy_version": "test"}', encoding="utf-8")
    fake_hash.write_text("0000000000000000000000000000000000000000000000000000000000000000\n", encoding="utf-8")
    with pytest.raises(PolicyIntegrityError, match="SHA-256 hash mismatch"):
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
        description_text="Seeking high strength bio adhesive for paper packaging with fast curing under thirty seconds.",
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
        "description_text": "Seeking technical solution for high precision industrial manufacturing process with strict energy consumption standards.",
        "language_code="en",
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
        "description_text": "Seeking innovative solution for recycling polymer components from electronic equipment safely and cleanly.",
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest backend/test/unit/application/test_corpus_expansion_validator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'application.corpus'`

- [ ] **Step 4: Implement validator in `backend/src/main/application/corpus/expansion_policy_validator.py`**

Create `backend/src/main/application/corpus/expansion_policy_validator.py`:
```python
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


def load_corpus_expansion_policy(
    policy_path: Path, hash_path: Path | None = None
) -> CorpusExpansionPolicy:
    """Load, verify cryptographic integrity, and parse a CorpusExpansionPolicy."""
    p_path = Path(policy_path)
    if not p_path.is_file():
        raise FileNotFoundError(f"Policy configuration file not found: {p_path}")

    h_path = hash_path or p_path.with_suffix(".sha256")
    if not h_path.is_file():
        raise FileNotFoundError(f"Policy hash sidecar file not found: {h_path}")

    content_bytes = p_path.read_bytes()
    expected_hash = h_path.read_text(encoding="utf-8").strip().split()[0]
    actual_hash = hashlib.sha256(content_bytes).hexdigest()

    if actual_hash.lower() != expected_hash.lower():
        raise PolicyIntegrityError(
            f"Policy configuration SHA-256 hash mismatch: expected {expected_hash}, got {actual_hash}"
        )

    data = json.loads(content_bytes.decode("utf-8"))
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest backend/test/unit/application/test_corpus_expansion_validator.py -v`
Expected: PASS

- [ ] **Step 6: Commit policy configuration, hash, and validator**

```bash
git add config/policies/data/corpus_expansion_policy_v1.json \
        config/policies/data/corpus_expansion_policy_v1.sha256 \
        backend/src/main/application/corpus/expansion_policy_validator.py \
        backend/test/unit/application/test_corpus_expansion_validator.py
git commit -m "feat(application): add corpus expansion policy loader, SHA-256 sidecar, and candidate validator"
```

---

### Task 3: ADR 0031, Operational Protocol Document, and Documentation Synchronization

**Files:**
- Create: `docs/adr/0031-corpus-expansion-contract.md`
- Create: `docs/phase2-corpus-expansion-protocol.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/empirical-study-protocol.md`

**Interfaces:**
- Normative ADR and scientific protocol defining contract invariants, sampling methodology, and sequencing.

- [ ] **Step 1: Write `docs/adr/0031-corpus-expansion-contract.md`**

Create ADR 0031 with full context, decision, consequences, and enforcement invariants matching the approved design specification.

- [ ] **Step 2: Write `docs/phase2-corpus-expansion-protocol.md`**

Create operational protocol detailing sampling universe, explicit geographic stratification (`spain`, `international_european`), source qualification rules, hierarchical $t_{\mathrm{demand}}$ evidence determination, anti-concentration guidelines, and pre-specified exclusion reasons.

- [ ] **Step 3: Update `docs/roadmap.md`**

Update `docs/roadmap.md` to record Milestone #101a as complete (contract frozen) and mark Milestone #101b (data acquisition against frozen contract) as the active next step.

- [ ] **Step 4: Update `docs/empirical-study-protocol.md`**

Update `docs/empirical-study-protocol.md` §3.2 and §4.1 with explicit cross-reference to ADR 0031 and the frozen `corpus_expansion_policy_v1.json` specification.

- [ ] **Step 5: Commit documentation and ADR**

```bash
git add docs/adr/0031-corpus-expansion-contract.md \
        docs/phase2-corpus-expansion-protocol.md \
        docs/roadmap.md \
        docs/empirical-study-protocol.md
git commit -m "docs(adr): add ADR 0031 corpus expansion contract and operational protocol"
```

---

### Task 4: Architectural Quality Gates & Invariant Verification

**Files:**
- All touched files

- [ ] **Step 1: Run full unit test suite with coverage**

Run: `pytest backend/test/unit -v --cov=backend/src/main --cov-report=xml:coverage.xml`
Expected: 100% tests pass.

- [ ] **Step 2: Run Ruff linter and formatter check**

Run: `ruff check .` and `ruff format --check .`
Expected: 0 errors.

- [ ] **Step 3: Run strict Mypy type checker**

Run: `mypy backend/src/main`
Expected: 0 errors.

- [ ] **Step 4: Run architectural quality gate and import linter**

Run: `python scripts/check_architecture.py` and `PYTHONPATH=backend/src/main lint-imports`
Expected: 0 violations, all layers strictly compliant with ADR 0008 and ADR 0009.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-11-pr101a-corpus-expansion-contract.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
