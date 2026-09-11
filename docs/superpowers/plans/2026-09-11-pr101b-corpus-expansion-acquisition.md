# PR #101b Implementation Plan: Phase-2 Corpus Expansion Acquisition, Structured Temporal Evidence, and Offline Validation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Phase-2 demand corpus acquisition, structured temporal evidence provenance, immutable raw staging, candidate mappers, deterministic offline policy validation, and audit verification tools (Milestone #101b) without modifying the matching engine or evaluators.

**Architecture:** A decoupled four-tier pipeline: (1) Harvesters write uninterpreted raw payloads and `.meta.json` sidecars to `data/raw/phase2_candidates/` under strict immutability; (2) Mappers translate raw records into `DemandCandidateContractRecord` instances with structured `PublicationDateEvidence` without performing eligibility filtering; (3) The offline policy validator evaluates candidates against `corpus_expansion_policy_v1.json`, partitioning them into `candidates_accepted.json` and `candidates_rejected.json`; (4) The audit tool verifies cryptographic hashes and the partition invariant $\text{mapped} = \text{accepted} \cup \text{rejected}$ with disjointness.

**Tech Stack:** Python 3.12, Pydantic v2, BeautifulSoup4, pytest, ruff, mypy, import-linter.

## Global Constraints
- Every change must strictly comply with ADR 0008, ADR 0009, ADR 0025, ADR 0026, ADR 0029, ADR 0030, ADR 0031, and ADR 0032.
- Zero modifications to the matching engine, dense embeddings, BM25 ranker, fusion algorithms, relevance judgments, or benchmark evaluators.
- Publication date $t_{\mathrm{demand}}$ must represent the original verifiable publication/creation date. Deadlines or crawl timestamps must never substitute for $t_{\mathrm{demand}}$.
- Missing/unverifiable dates evaluate strictly to `UNVERIFIABLE_PUBLICATION_DATE`, never to `OUT_OF_TEMPORAL_WINDOW`.
- Operational parsing/network errors are logged to `acquisition_errors.json` and `mapping_errors.json`, preserving `CandidateRejectionReason` purely for scientific policy exclusions.
- All datasets in `data/experiments/phase2/` must be sealed with SHA-256 sidecars.

---

### Task 1: Domain Model Refinement for Structured Temporal Evidence

**Files:**
- Modify: `backend/src/main/domain/models/corpus_expansion.py`
- Modify: `backend/test/unit/domain/test_corpus_expansion_models.py`

**Interfaces:**
- Produces:
  - `PublicationDateEvidenceType` (`StrEnum`: `POD_REFERENCE`, `EXPLICIT_METADATA`, `HISTORICAL_FEED`, `UNVERIFIABLE`)
  - `PublicationDateEvidence` (`publication_date: date | None`, `evidence_type: PublicationDateEvidenceType`, `evidence_field: str`, `evidence_value: str`)
  - Updated `DemandCandidateContractRecord` (`publication_date_evidence: PublicationDateEvidence`, `@property def publication_date(self) -> date | None`)
  - `CandidateRejectionReason.UNVERIFIABLE_PUBLICATION_DATE`

- [ ] **Step 1: Write the failing tests for domain models**
In `backend/test/unit/domain/test_corpus_expansion_models.py`, add tests for `PublicationDateEvidenceType`, `PublicationDateEvidence` validation rules, `DemandCandidateContractRecord` with evidence, and `CandidateRejectionReason.UNVERIFIABLE_PUBLICATION_DATE`:

```python
from datetime import date
import pytest
from pydantic import ValidationError
from domain.models.corpus_expansion import (
    PublicationDateEvidenceType,
    PublicationDateEvidence,
    DemandCandidateContractRecord,
    CandidateRejectionReason,
)

def test_publication_date_evidence_type_members():
    expected = {"pod_reference", "explicit_metadata", "historical_feed", "unverifiable"}
    assert {e.value for e in PublicationDateEvidenceType} == expected

def test_publication_date_evidence_valid_date():
    ev = PublicationDateEvidence(
        publication_date=date(2025, 8, 6),
        evidence_type=PublicationDateEvidenceType.POD_REFERENCE,
        evidence_field="pod_reference",
        evidence_value="TRES20250806011",
    )
    assert ev.publication_date == date(2025, 8, 6)
    assert ev.evidence_type == PublicationDateEvidenceType.POD_REFERENCE

def test_publication_date_evidence_unverifiable_requires_none():
    ev = PublicationDateEvidence(
        publication_date=None,
        evidence_type=PublicationDateEvidenceType.UNVERIFIABLE,
        evidence_field="deadline_date_raw",
        evidence_value="31/12/2026",
    )
    assert ev.publication_date is None

    with pytest.raises(ValidationError):
        PublicationDateEvidence(
            publication_date=date(2025, 1, 1),
            evidence_type=PublicationDateEvidenceType.UNVERIFIABLE,
            evidence_field="deadline_date_raw",
            evidence_value="31/12/2026",
        )

def test_publication_date_evidence_verified_requires_date():
    with pytest.raises(ValidationError):
        PublicationDateEvidence(
            publication_date=None,
            evidence_type=PublicationDateEvidenceType.POD_REFERENCE,
            evidence_field="pod_reference",
            evidence_value="TRES20250806011",
        )

def test_candidate_record_derived_publication_date():
    record = DemandCandidateContractRecord(
        demand_id="EEN-1",
        source_id="een_pod",
        source_construct="Technology request",
        publication_date_evidence=PublicationDateEvidence(
            publication_date=date(2024, 5, 1),
            evidence_type=PublicationDateEvidenceType.POD_REFERENCE,
            evidence_field="pod_reference",
            evidence_value="TRES20240501001",
        ),
        geographic_stratum="spain",
        title="Valid Title",
        description_text="This is a valid technical problem description with sufficient length.",
        language_code="en",
        organization_raw="Org",
        is_publicly_accessible=True,
        has_confidentiality_redaction=False,
        has_articulated_technical_problem=True,
        technical_problem_evidence_text="Valid problem text.",
    )
    assert record.publication_date == date(2024, 5, 1)

def test_unverifiable_publication_date_in_rejection_reasons():
    assert "UNVERIFIABLE_PUBLICATION_DATE" in CandidateRejectionReason.__members__
```

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/test/unit/domain/test_corpus_expansion_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'PublicationDateEvidenceType'`

- [ ] **Step 3: Implement domain model updates**
In `backend/src/main/domain/models/corpus_expansion.py`:
- Add `PublicationDateEvidenceType(StrEnum)`.
- Add `PublicationDateEvidence(BaseModel)` with model validator enforcing date coherence.
- Update `DemandCandidateContractRecord` to replace raw `publication_date: date` and evidence strings with `publication_date_evidence: PublicationDateEvidence`, and add `@property def publication_date(self) -> date | None: return self.publication_date_evidence.publication_date`.
- Add `UNVERIFIABLE_PUBLICATION_DATE = "UNVERIFIABLE_PUBLICATION_DATE"` to `CandidateRejectionReason`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/test/unit/domain/test_corpus_expansion_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/src/main/domain/models/corpus_expansion.py backend/test/unit/domain/test_corpus_expansion_models.py
git commit -m "feat(domain): add PublicationDateEvidence and UNVERIFIABLE_PUBLICATION_DATE reason (ADR 0032)"
```

---

### Task 2: Application Policy Validator Update for Unverifiable vs Out-of-Window Dates

**Files:**
- Modify: `backend/src/main/application/corpus/expansion_policy_validator.py`
- Modify: `backend/test/unit/application/test_corpus_expansion_validator.py`

**Interfaces:**
- Consumes: `DemandCandidateContractRecord`, `PublicationDateEvidence`, `PublicationDateEvidenceType`, `CandidateRejectionReason`
- Produces: Updated `validate_demand_candidate(candidate, policy)` emitting `UNVERIFIABLE_PUBLICATION_DATE` when `candidate.publication_date is None`, or `OUT_OF_TEMPORAL_WINDOW` when outside `[min_date, max_date]`.

- [ ] **Step 1: Write the failing tests in application test suite**
Update `backend/test/unit/application/test_corpus_expansion_validator.py` to use `publication_date_evidence`, and add tests:
- `test_should_reject_unverifiable_publication_date`: Candidate with `publication_date=None` and `evidence_type=UNVERIFIABLE` produces rejection reason `UNVERIFIABLE_PUBLICATION_DATE` (and NOT `OUT_OF_TEMPORAL_WINDOW`).
- `test_should_reject_out_of_temporal_window_only_when_date_verified`: Candidate with `publication_date=date(2019, 12, 31)` produces `OUT_OF_TEMPORAL_WINDOW` (and NOT `UNVERIFIABLE_PUBLICATION_DATE`).
- `test_should_combine_multiple_rejection_reasons_in_deterministic_order`: Candidate with short text and unverifiable date produces both reasons sorted.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/test/unit/application/test_corpus_expansion_validator.py -v`
Expected: FAIL due to validator still expecting old fields or not recognizing `UNVERIFIABLE_PUBLICATION_DATE`.

- [ ] **Step 3: Implement validator updates**
In `backend/src/main/application/corpus/expansion_policy_validator.py`:
Update `validate_demand_candidate`:
```python
    # 3. Temporal window boundary
    if candidate.publication_date is None:
        reasons.append(CandidateRejectionReason.UNVERIFIABLE_PUBLICATION_DATE)
    elif (
        candidate.publication_date < policy.temporal_window.min_publication_date
        or candidate.publication_date > policy.temporal_window.max_publication_date
    ):
        reasons.append(CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW)
```

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/test/unit/application/test_corpus_expansion_validator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/src/main/application/corpus/expansion_policy_validator.py backend/test/unit/application/test_corpus_expansion_validator.py
git commit -m "feat(application): handle UNVERIFIABLE_PUBLICATION_DATE in expansion validator (ADR 0032)"
```

---

### Task 3: Candidate Mappers for EEN/POD and InnoGet

**Files:**
- Create: `backend/src/main/application/corpus/mappers/een_pod_mapper.py`
- Create: `backend/src/main/application/corpus/mappers/innoget_mapper.py`
- Create: `backend/src/main/application/corpus/mappers/errors.py`
- Create: `backend/test/unit/application/corpus/test_candidate_mappers.py`

**Interfaces:**
- Produces:
  - `EenPodCandidateMapper.map_payload(raw_bytes: bytes, metadata: dict) -> DemandCandidateContractRecord`
  - `InnogetCandidateMapper.map_payload(raw_bytes: bytes, metadata: dict) -> DemandCandidateContractRecord`
  - `MappingError` exception class

- [ ] **Step 1: Write failing unit tests for candidate mappers**
In `backend/test/unit/application/corpus/test_candidate_mappers.py`:
- Test `EenPodCandidateMapper` with a fixture containing POD Reference `TRES20250806011` -> `publication_date=date(2025, 8, 6)`, `evidence_type=POD_REFERENCE`, `geographic_stratum="spain"`.
- Test `EenPodCandidateMapper` with international POD Reference `TRIT20240315002` -> `publication_date=date(2024, 3, 15)`, `evidence_type=POD_REFERENCE`, `geographic_stratum="international_european"`.
- Test `InnogetCandidateMapper` with page containing explicit publication date in meta tag -> `evidence_type=EXPLICIT_METADATA`.
- Test `InnogetCandidateMapper` with page containing only `Deadline at 31/12/2026` -> `publication_date=None`, `evidence_type=UNVERIFIABLE`, `evidence_value="31/12/2026"`.
- Test `InnogetCandidateMapper` extracting technical problem evidence from `Details of the Innovation Need`.
- Test malformed payload raising `MappingError`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/test/unit/application/corpus/test_candidate_mappers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'application.corpus.mappers'`

- [ ] **Step 3: Implement candidate mappers and error types**
Create:
- `backend/src/main/application/corpus/mappers/errors.py`: defines `MappingError`.
- `backend/src/main/application/corpus/mappers/een_pod_mapper.py`: implements regex on POD reference (`TR([A-Z]{2})(\d{4})(\d{2})(\d{2})\d+`), HTML parsing with BeautifulSoup, extracts title, abstract description, technical problem evidence text.
- `backend/src/main/application/corpus/mappers/innoget_mapper.py`: uses BeautifulSoup, checks for meta `datePublished` / `article:published_time` / explicit metadata tag, falls back to `UNVERIFIABLE` with deadline/no-date observed text, extracts title, description, technical problem evidence text, organization.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/test/unit/application/corpus/test_candidate_mappers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add backend/src/main/application/corpus/mappers/ backend/test/unit/application/corpus/test_candidate_mappers.py
git commit -m "feat(application): add EEN/POD and InnoGet candidate mappers with date evidence (ADR 0032)"
```

---

### Task 4: Harvesters and Operational Raw Storage

**Files:**
- Create: `experiments/phase2/harvesters/base.py`
- Create: `experiments/phase2/harvesters/innoget_harvester.py`
- Create: `experiments/phase2/harvesters/een_pod_harvester.py`
- Create: `experiments/phase2/acquire.py`
- Create: `backend/test/unit/application/corpus/test_harvesters.py`

**Interfaces:**
- Produces:
  - `BaseHarvester.save_raw_payload(demand_id: str, source_id: str, source_uri: str, payload_bytes: bytes, out_dir: Path) -> Path` (enforcing SHA-256 calculation and collision prevention raising `PayloadCollisionError` if content differs).
  - `InnogetHarvester.harvest(out_dir: Path, max_pages: int | None = None)`
  - `EenPodHarvester.harvest(out_dir: Path)`
  - `acquire.py` CLI module (`python -m experiments.phase2.acquire --out-dir data/raw/phase2_candidates`)

- [ ] **Step 1: Write failing unit tests for harvesters and raw storage**
In `backend/test/unit/application/corpus/test_harvesters.py`:
- Test `save_raw_payload` writes `<demand_id>.<ext>` and `<demand_id>.meta.json` with matching SHA-256.
- Test `save_raw_payload` skips if identical file already exists.
- Test `save_raw_payload` raises `PayloadCollisionError` if file exists with different content.
- Test mock harvesting loop recording network errors into `acquisition_errors.json`.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/test/unit/application/corpus/test_harvesters.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement harvesters and acquire CLI**
Create:
- `experiments/phase2/harvesters/base.py`: base harvester class with `save_raw_payload`, polite delay `time.sleep(polite_delay_seconds)`, user-agent header, SHA-256 sidecar writer.
- `experiments/phase2/harvesters/innoget_harvester.py`: discovers `/technology-calls?page={N}` links, harvests detail pages.
- `experiments/phase2/harvesters/een_pod_harvester.py`: discovers and harvests listings from certified mirrors (Lombardia `/en/collaborations/collaboration-proposals`) and public EEN POD mirrors.
- `experiments/phase2/acquire.py`: orchestration CLI script with argument parsing (`--out-dir`, `--sources`, `--limit`).

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/test/unit/application/corpus/test_harvesters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add experiments/phase2/harvesters/ experiments/phase2/acquire.py backend/test/unit/application/corpus/test_harvesters.py
git commit -m "feat(experiments): add polite harvesters and immutable raw staging (ADR 0032)"
```

---

### Task 5: Deterministic Offline Validation Pipeline & Dataset Sealer

**Files:**
- Create: `experiments/phase2/validate.py`
- Create: `backend/test/integration/corpus/test_expansion_offline_pipeline.py`

**Interfaces:**
- Produces:
  - `validate.py` CLI: `python -m experiments.phase2.validate --raw-dir data/raw/phase2_candidates --out-dir data/experiments/phase2`
  - Emits:
    - `candidates_raw.manifest.json` + `.sha256`
    - `candidates_mapped.json` + `.sha256`
    - `candidates_accepted.json` + `.sha256`
    - `candidates_rejected.json` + `.sha256`
    - `mapping_errors.json`
    - `acquisition_run.manifest.json`

- [ ] **Step 1: Write integration test for offline validation pipeline**
In `backend/test/integration/corpus/test_expansion_offline_pipeline.py`:
- Sets up a temporary `raw_dir` with a mix of fixtures:
  - 1 valid EEN candidate (accepted)
  - 1 InnoGet candidate with deadline only (rejected with `UNVERIFIABLE_PUBLICATION_DATE`)
  - 1 candidate with date in 2018 (rejected with `OUT_OF_TEMPORAL_WINDOW`)
  - 1 candidate with short text (<25 words) (rejected with `CONTENT_TOO_SHORT`)
  - 1 malformed payload (emits to `mapping_errors.json`)
- Runs `run_offline_validation(raw_dir, out_dir, policy_path)`.
- Asserts all files are created.
- Asserts every file has a valid matching `.sha256` sidecar.
- Asserts $\text{mapped} = \text{accepted} \cup \text{rejected}$ and $\text{accepted} \cap \text{rejected} = \emptyset$.
- Asserts rejected items contain rejection reasons and evidence text.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/test/integration/corpus/test_expansion_offline_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement offline validation runner**
In `experiments/phase2/validate.py`:
- Scans `raw-dir` across source subdirectories.
- Reads raw files and `.meta.json` sidecars.
- Passes through appropriate mapper based on `source_id`.
- Captures `MappingError` into `mapping_errors.json`.
- Writes `candidates_mapped.json`.
- Validates each candidate using `validate_demand_candidate(candidate, policy)` against loaded `corpus_expansion_policy_v1.json`.
- Segregates into accepted and rejected arrays.
- Emits all JSON datasets and generates `.sha256` sidecars.
- Emits `candidates_raw.manifest.json` and `acquisition_run.manifest.json`.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/test/integration/corpus/test_expansion_offline_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add experiments/phase2/validate.py backend/test/integration/corpus/test_expansion_offline_pipeline.py
git commit -m "feat(experiments): add deterministic offline validation pipeline and dataset sealer (ADR 0032)"
```

---

### Task 6: Audit Verification Script

**Files:**
- Create: `experiments/phase2/audit.py`
- Create: `backend/test/unit/application/corpus/test_phase2_audit.py`

**Interfaces:**
- Produces:
  - `python -m experiments.phase2.audit --experiments-dir data/experiments/phase2 --raw-dir data/raw/phase2_candidates`
  - Emits summary report and exits with 0 if all invariants pass, 1 if any invariant fails.

- [ ] **Step 1: Write unit tests for audit script**
In `backend/test/unit/application/corpus/test_phase2_audit.py`:
- Test audit passes when datasets satisfy all partition, hash, and field invariants.
- Test audit fails when an accepted record has `publication_date=None`.
- Test audit fails when $\text{accepted} \cap \text{rejected} \neq \emptyset$.
- Test audit fails when a SHA-256 sidecar does not match file contents.

- [ ] **Step 2: Run test to verify it fails**
Run: `pytest backend/test/unit/application/corpus/test_phase2_audit.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement audit verification script**
In `experiments/phase2/audit.py`:
- Verify all `.sha256` sidecars match file content hashes.
- Verify `mapped == accepted + rejected` and disjointness.
- Verify accepted items pass all policy requirements.
- Print tabular summary: total raw, total mapped, total mapping errors, total accepted, total rejected, breakdown of rejection reasons, yield by source and stratum.

- [ ] **Step 4: Run test to verify it passes**
Run: `pytest backend/test/unit/application/corpus/test_phase2_audit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add experiments/phase2/audit.py backend/test/unit/application/corpus/test_phase2_audit.py
git commit -m "feat(experiments): add Phase-2 corpus expansion audit script (ADR 0032)"
```

---

### Task 7: Data Harvesting Execution, Sealing, and Quality Gate Verification

**Files:**
- Output directory: `data/raw/phase2_candidates/`
- Output directory: `data/experiments/phase2/`

- [x] **Step 1: Run candidate harvesting**
Run: `python -m experiments.phase2.acquire --out-dir data/raw/phase2_candidates`
Verify raw files and `.meta.json` files are created in `data/raw/phase2_candidates/`.
Result: 824 raw payloads (innoget: 424, een_pod: 400), 0 acquisition errors.

- [x] **Step 2: Run offline validation pipeline**
Run: `python -m experiments.phase2.validate --raw-dir data/raw/phase2_candidates --out-dir data/experiments/phase2`
Verify all sealed datasets, manifests, and `.sha256` sidecars are generated.
Result: mapped=824, accepted=10, rejected=814, mapping_errors=0.

- [x] **Step 3: Run audit verification script**
Run: `python -m experiments.phase2.audit --experiments-dir data/experiments/phase2 --raw-dir data/raw/phase2_candidates`
Verify audit completes 100% green with exit code 0.
Result: PASSED. Candidate volume does **not** provide a plausible margin for Milestone #102 (10 eligible, need ~60) — see spec Section 8 for root cause (source-frame failure, not implementation defect) and closure decision.

- [x] **Step 4: Run full test suite and quality gates**
Run:
```bash
pytest backend/test/unit -v --cov=backend/src/main --cov-report=xml:coverage.xml
ruff check .
mypy backend/src/main
python scripts/check_architecture.py
PYTHONPATH=backend/src/main lint-imports
```
Result: 805 passed, ruff/mypy/architecture/import-linter all green.

- [x] **Step 5: Commit generated datasets, manifests, and code**
```bash
git add data/raw/phase2_candidates/ data/experiments/phase2/
git commit -m "data(phase2): seal diagnostic acquisition run (10/824 eligible, ADR 0032)"
```

**Milestone #101b closed as a diagnostic outcome (2026-09-11).** See design spec Section 8 for full analysis. Follow-up (historical-source acquisition feasibility) continues as a separate milestone, #101c — not a retroactive extension of this plan.
