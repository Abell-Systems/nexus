# PR #101b: Phase-2 Demand Corpus Expansion Acquisition & Evidence Design Specification

**Status:** Proposed  
**Date:** 2026-09-11  
**Target Milestone:** Milestone #101b  
**Binding Architecture:** ADR 0008, ADR 0009, ADR 0025, ADR 0026, ADR 0029, ADR 0030, ADR 0031, ADR 0032  

---

## 1. Executive Summary & Purpose

Milestone #101a established the binding acquisition contract, candidate schema (`DemandCandidateContractRecord`), declarative policy (`corpus_expansion_policy_v1.json`), and individual policy validator (`validate_demand_candidate`). Per the golden rule of Milestone #101a, zero data records were harvested or selected.

**Milestone #101b executes the data acquisition and audit pipeline strictly against the frozen contract**:
> **#101a defines what can enter. #101b demonstrates what entered and why.**

Milestone #101b acquires raw candidate demands from authorized European sources (InnoGet and EEN/POD), structures observed facts and temporal provenance, executes deterministic offline policy validation, and partitions candidates into verified accepted and rejected sets with cryptographically sealed audit manifests.

### Golden Invariants for PR #101b
1. **Absolute Decoupling from Evaluation:** PR #101b introduces zero modifications to the matching engine, dense embedding models, candidate generators, rankers, relevance judgments, or benchmark evaluators.
2. **Zero Outcome-Dependent Selection:** Harvesters and mappers do not filter or score candidates based on technological familiarity, expected difficulty, or patent retrieval outcomes.
3. **Primary Evidence for Publication Date ($t_{\mathrm{demand}}$):** Publication date must represent the authentic public creation/publication timestamp. Acquisition/crawl dates, access dates, cache timestamps, or application deadlines (`deadline_raw`) strictly cannot substitute for $t_{\mathrm{demand}}$.
4. **Separation of Uncertainty from Negation:** Absence of a verifiable publication date evaluates strictly to `UNVERIFIABLE_PUBLICATION_DATE` (insufficient evidence for eligibility), never to `OUT_OF_TEMPORAL_WINDOW` (which is reserved exclusively for verifiable dates falling outside `[2020-01-01, 2025-12-31]`).
5. **Separation of Operational Failures from Scientific Exclusions:** Network, extraction, or DOM parsing errors are captured in operational error logs (`acquisition_errors.json`, `mapping_errors.json`), leaving `CandidateRejectionReason` reserved purely for substantive scientific policy exclusions.

---

## 2. Architecture & Data Flow Pipeline

The acquisition and validation pipeline is partitioned into four strictly decoupled tiers:

```text
                    INTERNET (Public HTTP)
                              │
                    ┌─────────▼─────────┐
                    │    HARVESTERS     │  Polite crawling (1.0-1.5s delay)
                    │ InnoGet / EEN-POD │  Zero scientific selection / filtering
                    └─────────┬─────────┘
                              │
                              ▼
                     RAW IMMUTABLE INPUT
                     data/raw/phase2_candidates/{source_id}/{record_id}.{html|json}
                     + {record_id}.meta.json (URL, acquisition_ts, sha256)
                              │
                              ▼
                    ┌───────────────────┐
                    │      MAPPERS      │  Parses observed facts into schema
                    │  raw → Candidate  │  Builds PublicationDateEvidence
                    └─────────┬─────────┘  (Zero eligibility decisions)
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
DemandCandidateContractRecord              MAPPING_ERRORS
(candidates_mapped.json)               (mapping_errors.json)
            │
            ▼
 ┌─────────────────────┐
 │  POLICY VALIDATOR   │  100% Offline & Deterministic
 │  validate_demand()  │  Evaluates against corpus_expansion_policy_v1
 └──────────┬──────────┘
            │
     ┌──────┴────────┐
     ▼               ▼
  ACCEPTED        REJECTED
  candidates_     candidates_
  accepted.json   rejected.json (with typed reasons & evidence)
     │               │
     └───────┬───────┘
             ▼
      AUDIT & MANIFESTS
      candidates_raw.manifest.json + sha256
      candidates_mapped.sha256
      candidates_accepted.sha256
      candidates_rejected.sha256
      acquisition_run.manifest.json
```

---

## 3. Domain Model Refinements

### 3.1 Closed Publication Date Evidence Type
In `backend/src/main/domain/models/corpus_expansion.py`:

```python
class PublicationDateEvidenceType(StrEnum):
    """Closed taxonomy of acceptable publication date evidence sources."""

    POD_REFERENCE = "pod_reference"
    EXPLICIT_METADATA = "explicit_metadata"
    HISTORICAL_FEED = "historical_feed"
    UNVERIFIABLE = "unverifiable"
```

### 3.2 Structured Publication Date Evidence
```python
class PublicationDateEvidence(BaseModel):
    """Auditable evidence establishing t_demand publication date provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    publication_date: date | None = None
    evidence_type: PublicationDateEvidenceType
    evidence_field: str = Field(..., min_length=1)
    evidence_value: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_date_coherence(self) -> "PublicationDateEvidence":
        if self.evidence_type == PublicationDateEvidenceType.UNVERIFIABLE:
            if self.publication_date is not None:
                raise ValueError("publication_date must be None when evidence_type is UNVERIFIABLE")
        else:
            if self.publication_date is None:
                raise ValueError(f"publication_date is required when evidence_type is '{self.evidence_type}'")
        return self
```

### 3.3 Refined `DemandCandidateContractRecord`
```python
class DemandCandidateContractRecord(BaseModel):
    """Canonical representation of an acquired candidate prior to policy validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    demand_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    source_construct: str = Field(..., min_length=1)
    publication_date_evidence: PublicationDateEvidence
    geographic_stratum: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description_text: str = Field(..., min_length=1)
    language_code: str = Field(..., min_length=2, max_length=5)
    organization_raw: str | None = None
    is_publicly_accessible: bool
    has_confidentiality_redaction: bool
    has_articulated_technical_problem: bool
    technical_problem_evidence_text: str | None = None

    @property
    def publication_date(self) -> date | None:
        """Derived view for backward compatibility with downstream consumers."""
        return self.publication_date_evidence.publication_date
```

### 3.4 Candidate Rejection Reason Taxonomy
```python
class CandidateRejectionReason(StrEnum):
    """Pre-specified candidate exclusion reasons."""

    UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"
    INCOMPATIBLE_CONSTRUCT = "INCOMPATIBLE_CONSTRUCT"
    OUT_OF_TEMPORAL_WINDOW = "OUT_OF_TEMPORAL_WINDOW"
    UNVERIFIABLE_PUBLICATION_DATE = "UNVERIFIABLE_PUBLICATION_DATE"
    UNAUTHORIZED_GEOGRAPHIC_STRATUM = "UNAUTHORIZED_GEOGRAPHIC_STRATUM"
    CONTENT_TOO_SHORT = "CONTENT_TOO_SHORT"
    CONFIDENTIALITY_REDACTED = "CONFIDENTIALITY_REDACTED"
    ACCESS_NOT_PUBLIC = "ACCESS_NOT_PUBLIC"
    NO_TECHNICAL_PROBLEM = "NO_TECHNICAL_PROBLEM"
```

### 3.5 Temporal Validation Rules in `validate_demand_candidate`
The validator applies deterministic date verification in mutually exclusive branches:
1. **Unverifiable Date:**
   If `candidate.publication_date is None`:
   $\longrightarrow$ append `CandidateRejectionReason.UNVERIFIABLE_PUBLICATION_DATE`.
2. **Verifiable Date Outside Temporal Bounds:**
   If `candidate.publication_date is not None`:
   $\longrightarrow$ if `candidate.publication_date < policy.temporal_window.min_publication_date` or `candidate.publication_date > policy.temporal_window.max_publication_date`, append `CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW`.
3. **Verifiable Date Inside Bounds:**
   Temporal criterion passes cleanly.

---

## 4. Components & Implementation Details

### 4.1 Raw Immutable Storage & Harvesters
Location: `data/raw/phase2_candidates/{source_id}/`
- `een_pod/`: raw HTML or JSON payloads from EEN / Open Innovation Lombardia.
- `innoget/`: raw HTML challenge pages from InnoGet.

#### Operational Immutability Guarantee
- If a target file `<demand_id>.<ext>` already exists on disk:
  - If its computed SHA-256 matches `<demand_id>.meta.json["raw_payload_sha256"]`, re-download is skipped.
  - If its contents differ, the harvester aborts with an explicit error (`PayloadCollisionError`). Silent overwrites and mutations are prohibited.
- Accompanying `<demand_id>.meta.json` format:
  ```json
  {
    "demand_id": "INNOGET-2446",
    "source_id": "innoget",
    "source_uri": "https://www.innoget.com/technology-calls/2446/...",
    "acquisition_timestamp": "2026-09-11T12:00:00.000000Z",
    "raw_payload_sha256": "2f791a8ef01970d5ad850fccf3df1705c7b8c3345a0a990d949deebd194b510d",
    "harvester_version": "phase2_harvester_v1",
    "http_status": 200
  }
  ```

#### Harvester Implementations (`experiments/phase2/harvesters/`)
- `InnogetHarvester`:
  - Scrapes directory `/technology-calls?page={N}` obeying `robots.txt`.
  - Polite pacing: 1.0 – 1.5 seconds delay between requests.
  - Saves all discovered challenge detail pages.
  - Captures network/HTTP errors in `data/experiments/phase2/acquisition_errors.json`.
- `EenPodHarvester`:
  - Crawls public technology request listings from certified mirror (Open Innovation Lombardia) and public EEN POD mirrors.
  - Saves raw HTML/JSON with `.meta.json`.

### 4.2 Candidate Mappers (`experiments/phase2/mappers/`)
Mappers transform raw payloads into `DemandCandidateContractRecord` without applying eligibility gates:
1. **`EenPodCandidateMapper`:**
   - Decodes POD reference `TR([A-Z]{2})(\d{4})(\d{2})(\d{2})\d+` to obtain country code and date `YYYY-MM-DD`.
   - Populates `PublicationDateEvidence(publication_date=date(...), evidence_type=POD_REFERENCE, evidence_field="pod_reference", evidence_value=...)`.
   - Extracts abstract, title, technical problem evidence text.
   - Assigns geographic stratum (`spain` if country is `ES`, else `international_european`).
2. **`InnogetCandidateMapper`:**
   - Extracts title, description, requesting organization, origin country.
   - Extracts publication date following strict hierarchy:
     1. Explicit publication metadata tag in DOM (`PublicationDateEvidenceType.EXPLICIT_METADATA`).
     2. Historical feed / registry timestamp if present (`PublicationDateEvidenceType.HISTORICAL_FEED`).
     3. If only deadline is available or no publication date exists:
        `publication_date=None`, `evidence_type=PublicationDateEvidenceType.UNVERIFIABLE`, `evidence_field="deadline_date_raw"`, `evidence_value="31/12/2026"` (or `"no_date_field_observed"`).
   - Extracts technical problem evidence from problem description / details section.
   - Assigns geographic stratum (`spain` if country is `Spain`, else `international_european`).
3. **Operational Error Handling:**
   If a raw file is completely corrupt or cannot be mapped, it produces a typed `MappingError` record written to `data/experiments/phase2/mapping_errors.json`.

### 4.3 Deterministic Offline Validation Runner (`experiments/phase2/validate.py`)
CLI interface:
```bash
python -m experiments.phase2.validate --raw-dir data/raw/phase2_candidates
```
- Operates 100% offline with zero network calls.
- Loads `corpus_expansion_policy_v1.json` and verifies its SHA-256 sidecar.
- Reads all valid raw items and runs mappers to emit `candidates_mapped.json`.
- Validates each candidate with `validate_demand_candidate(candidate, policy)`.
- Bifurcates candidates deterministically:
  - `candidates_accepted.json` (0 rejection reasons).
  - `candidates_rejected.json` (contains candidate record, tuple of rejection reasons, and evidence excerpts).
- Computes and signs all `.sha256` sidecars.

### 4.4 Formal Partition Invariant & Audit Verification (`experiments/phase2/audit.py`)
The audit script mathematically verifies:
1. **Partition Equality and Disjointness:**
   $$\text{candidates\_mapped} = \text{candidates\_accepted} \cup \text{candidates\_rejected}$$
   $$\text{candidates\_accepted} \cap \text{candidates\_rejected} = \emptyset$$
2. **Integrity of Accepted Candidates:**
   - 100% of accepted records have `publication_date is not None`.
   - 100% of accepted records have `min_publication_date <= publication_date <= max_publication_date`.
   - 100% of accepted records have `canonical_word_count >= 25`.
   - 100% of accepted records have `has_articulated_technical_problem is True` and non-empty `technical_problem_evidence_text`.
   - 0% of accepted records have `UNVERIFIABLE_PUBLICATION_DATE` or `OUT_OF_TEMPORAL_WINDOW`.
3. **Cryptographic Integrity:**
   - 100% of raw files match their hash in `.meta.json`.
   - 100% of output JSON datasets match their `.sha256` sidecars.
4. **Descriptive Stratification Metrics:**
   - Candidate yield per source (`innoget`, `een_pod`).
   - Candidate yield per stratum (`spain`, `international_european`).
   - Frequency breakdown of rejection reasons.

---

## 5. Artifact Manifest Specification

All experimental artifacts reside under `data/experiments/phase2/`:

| Artifact | Format | Description |
| :--- | :--- | :--- |
| `candidates_raw.manifest.json` | JSON | Registry of all successfully acquired raw files, source URLs, timestamps, and hashes. |
| `candidates_raw.manifest.sha256` | SHA-256 | Cryptographic sidecar for raw manifest. |
| `candidates_mapped.json` | JSON | Normalized array of `DemandCandidateContractRecord` items before validation. |
| `candidates_mapped.sha256` | SHA-256 | Cryptographic sidecar for mapped candidates. |
| `candidates_accepted.json` | JSON | Array of policy-compliant candidates passing all criteria (input pool for Milestone #102). |
| `candidates_accepted.sha256` | SHA-256 | Cryptographic sidecar for accepted candidates. |
| `candidates_rejected.json` | JSON | Array of rejected candidates with typed reasons and trigger evidence. |
| `candidates_rejected.sha256` | SHA-256 | Cryptographic sidecar for rejected candidates. |
| `acquisition_errors.json` | JSON | Operational network/HTTP errors encountered during harvesting. |
| `mapping_errors.json` | JSON | Operational parsing/structural errors encountered during mapping. |
| `acquisition_run.manifest.json` | JSON | High-level summary of acquisition run (dates, counts, policy hash, pipeline versions). |

---

## 6. Testing & Quality Gate Strategy

Testing follows strict Test-Driven Development (TDD) across 4 progressive tiers:

### Tier 1: Domain Unit Tests
- `backend/test/unit/domain/test_corpus_expansion_models.py`:
  - `PublicationDateEvidenceType` closed enum membership.
  - `PublicationDateEvidence` validation rules (UNVERIFIABLE requires `publication_date=None`, valid types require date).
  - `DemandCandidateContractRecord` initialization and derived `publication_date` property.
  - `CandidateRejectionReason.UNVERIFIABLE_PUBLICATION_DATE` presence.

### Tier 2: Application Validator Unit Tests
- `backend/test/unit/application/test_corpus_expansion_validator.py`:
  - Missing publication date (`publication_date is None`) $\to$ deterministic `UNVERIFIABLE_PUBLICATION_DATE`.
  - Publication date $< 2020-01-01$ or $> 2025-12-31$ $\to$ deterministic `OUT_OF_TEMPORAL_WINDOW`.
  - Publication date inside window $\to$ temporal check passes.
  - Multi-trigger scenario: candidate with short text and missing date receives both `CONTENT_TOO_SHORT` and `UNVERIFIABLE_PUBLICATION_DATE` in stable sorted order.

### Tier 3: Mapper Unit Tests
- `backend/test/unit/application/corpus/test_candidate_mappers.py`:
  - EEN POD mapper extracts correct date, country code, and text from fixtures.
  - InnoGet mapper extracts title, description, organization, and structures `PublicationDateEvidence` without substituting deadline for publication date.
  - Corrupt payload handling emits `MappingError`.

### Tier 4: Pipeline Integration Tests
- `backend/test/integration/corpus/test_expansion_offline_pipeline.py`:
  - Executes offline validation against a temporary fixture tree of raw payloads.
  - Verifies output file generation, cryptographic sidecars, and the partition invariant $\text{accepted} \cap \text{rejected} = \emptyset$.

---

## 7. Definition of Done (DoD) for PR #101b

A pull request for Milestone #101b is merge-ready if and only if:

1. **ADR Compliance:** ADR 0032 is documented, committed, and compliant with ADR 0001 through ADR 0031.
2. **Domain & Application Contracts:** `PublicationDateEvidence` and `UNVERIFIABLE_PUBLICATION_DATE` are implemented and verified via unit tests.
3. **Mapper & Harvester Isolation:** Harvesters and mappers operate with zero evaluation/ranking imports and zero scientific selection bias.
4. **Offline Reproducibility:** The validator runs completely offline against raw files stored in `data/raw/phase2_candidates/`.
5. **Partition Invariant:** The audit script passes cleanly with $\text{mapped} = \text{accepted} \cup \text{rejected}$ and $\text{accepted} \cap \text{rejected} = \emptyset$.
6. **Sufficiency Criterion:** The harvesting run provides a sufficient margin of eligible candidates such that, following the multidimensional independence audit in Milestone #102, it is plausible to achieve $N_{\mathrm{power}} = N_{\mathrm{eligible, independent}} \ge 60$. (If Milestone #102 subsequently finds $N_{\mathrm{power}} < 60$, expansion will continue before benchmark freeze).
7. **Verification Gates:**
   - 100% green tests: `pytest backend/test/unit -v --cov=backend/src/main --cov-report=xml:coverage.xml`.
   - 100% green linting & types: `ruff check .` and `mypy backend/src/main`.
   - 100% green architectural gates: `python scripts/check_architecture.py` and `PYTHONPATH=backend/src/main lint-imports`.
8. **Evaluation Immutability:** Zero modifications have been made to matching engine, rankers, or evaluation runner.
