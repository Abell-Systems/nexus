# ADR 0006: Scientific Validation Dataset, Schema, and Evaluation Provenance

**Status:** Accepted  
**Date:** 2026-09-03  
**Scope:** `domain/models/evaluation`, `domain/protocols/evaluation`, `infrastructure/evaluation`, `data/evaluation`  

---

## Context

Under ADR 0001 (Testing Strategy), ADR 0002 (Minimal Clean Code & SOLID), ADR 0003 (Externalized Origin Policy & Evidence-Based Resolution), ADR 0004 (Matching Engine Contract & Evidence Assessment), and ADR 0005 (Explicit Policy Injection & No Implicit Configuration), Nexus enforces strict separation between observed facts, policy, and decision logic.

However, an algorithm cannot scientifically validate itself. Merely demonstrating that tests pass against unit test fixtures (`backend/test/fixtures/`) proves syntactic execution and structural compliance, but does not prove technological accuracy, ranking quality, or operational competence on real industrial demands.

Furthermore, empirical benchmarks present severe epistemological hazards if not governed by rigorous engineering contracts:
1. **Conflating Annotations with Absolute Truth:** An expert or annotator assigning a label provides an observation of human judgment (`EXPERT_LABELLED`), not an immutable laws-of-nature fact (`GROUND_TRUTH`).
2. **Fixture Pollution:** Using unit test fixtures or mock samples as empirical benchmark data creates circular reasoning and self-fulfilling evaluations.
3. **Data Tampering & Silent Drift:** Storing evaluation datasets without external, byte-level cryptographic integrity checks allows data to drift or be altered to make algorithms appear superior.
4. **Synthetic Pollution:** Injecting synthetic demands or mock patents into an empirical corpus without explicit demarcation distorts scientific measurement.
5. **CWD Coupling:** Benchmark loaders attempting to locate datasets via relative working directory paths (`data/evaluation/...`) violate the dependency boundary established in ADR 0005.

We require a binding architectural and scientific contract governing how empirical evaluation datasets are structured, verified, loaded, and audited.

---

## Decision

### 1. Fundamental Principle of Evaluation Independence

> **The benchmark is not created to satisfy the engine; the engine is evaluated against a benchmark defined independently of its implementation.**

Evaluation datasets MUST NOT be curated, tweaked, or selected opportunistically to make a specific matching algorithm, weight set, or retriever score artificially high. Any benchmark dataset must be created, sealed, and versioned before evaluating the engine.

---

### 2. Epistemological Classification of Evaluation Data

All evaluation entities MUST explicitly declare their epistemic modality (`DataModality`):

* **`OBSERVED`**: Authentic data collected directly from primary sources (e.g., raw publication records from OEPM, unedited challenge calls from InnoGet). Contains factual text, dates, and classifications.
* **`EXPERT_LABELLED`**: Human expert evaluations or annotations (e.g., technical relevance grades $0, 1, 2, 3$). These represent recorded expert opinions, subject to inter-annotator variance. They MUST NOT be termed "absolute ground truth".
* **`SYNTHETIC_CONTROL`**: Programmatically generated or modified records used strictly as negative controls, edge-case probes, or stress tests. Any synthetic entity NOT explicitly tagged as `SYNTHETIC_CONTROL` is invalid and MUST be rejected by schema validation.

---

### 3. Separation of Domain Content, Manifest, and Validation State

To prevent circular dependencies and serialization ambiguity, the evaluation architecture cleanly separates three distinct concepts:

```text
┌───────────────────────────┐         ┌───────────────────────────────┐
│     EvaluationDataset     │         │   EvaluationDatasetManifest   │
│ ───────────────────────── │         │ ───────────────────────────── │
│ - dataset_id: str         │         │ - dataset_id: str             │
│ - schema_version: str     │         │ - dataset_version: str        │
│ - dataset_version: str    │         │ - schema_version: str         │
│ - demands: list[...]      │         │ - source_authorities: list    │
│ - patents: list[...]      │         │ - record_counts: dict         │
│ - annotations: list[...]  │         │ - content_sha256: str (64 hex)│
└─────────────┬─────────────┘         └───────────────┬───────────────┘
              │                                       │
              └───────────────────┬───────────────────┘
                                  ▼
                    ┌───────────────────────────┐
                    │     ValidatedDataset      │
                    │ ───────────────────────── │
                    │ - dataset: Evaluation...  │
                    │ - manifest: Evaluation... │
                    │ - verified_at: datetime   │
                    └───────────────────────────┘
```

1. **`EvaluationDataset` (Domain Layer):** Encapsulates the scientific domain content: demands, candidate patents, and expert annotations. It contains **no** self-referential cryptographic hash of itself.
2. **`EvaluationDatasetManifest` (Metadata & Identity):** Describes the dataset externally: record counts per modality, source authorities, schema version, and declared byte-exact SHA-256 digest.
3. **`ValidatedDataset` (Execution Boundary):** The immutable tuple returned by the infrastructure loader **only** after byte-exact hash verification, manifest consistency, and schema validation have completely succeeded. Downstream evaluation engines receive `ValidatedDataset`; they MUST NOT load or validate datasets internally.

---

### 4. Byte-Exact Cryptographic Integrity (`.sha256`)

1. Integrity is determined strictly by computing the SHA-256 digest of the **exact raw bytes** of the JSON dataset file on disk (`hashlib.sha256(raw_bytes).hexdigest()`).
2. Hash calculation MUST NOT parse, deserialize, format, or re-serialize the JSON. Byte-for-byte fidelity is mandatory.
3. The digest is stored in a companion file with extension `.sha256`, formatted strictly as:
   ```text
   <64-character-hex-digest>  <filename>\n
   ```
4. If computed `SHA256(raw_bytes) != declared_digest`, loading MUST immediately abort with `ValueError`.

---

### 5. Rigorous Provenance Contract

Every demand and patent document in the evaluation corpus MUST include canonical provenance metadata:
* `source_authority`: Explicit primary authority (e.g., `"innoget"`, `"oepm"`, `"epo"`).
* `source_uri`: Canonical URI or document identifier from which the observation originates.
* `extraction_timestamp`: ISO 8601 UTC timestamp of acquisition.
* `raw_payload_sha256`: Hexadecimal SHA-256 digest of the raw source payload.

> **Epistemological Constraint on Hashes:**  
> A provenance hash (`raw_payload_sha256`) is **evidence of payload identity and integrity**, not proof of primary authority provenance by itself. The presence of a valid SHA-256 does not certify authenticity if the underlying observation pipeline was unverified.

---

### 6. Architectural Boundary and Explicit Path Injection

Under ADR 0005:
1. `EvaluationDatasetLoader` MUST require explicit `Path` arguments (`dataset_path`, `checksum_path`, `manifest_path`).
2. Internal domain and application components MUST NOT resolve datasets via hardcoded relative paths (e.g., `Path("data/evaluation/...")`) or rely on the process current working directory (`CWD`).
3. Unit test fixtures under `backend/test/fixtures/` MUST NOT be imported or substituted as evaluation datasets.

---

### 7. Fail-Fast Invariant

The dataset loader and domain models MUST fail fast with explicit exceptions (`FileNotFoundError`, `ValueError`, `TypeError`):
* Missing dataset file $\to$ `FileNotFoundError`.
* Missing `.sha256` checksum file $\to$ `FileNotFoundError`.
* Byte hash mismatch $\to$ `ValueError` (integrity failure).
* Malformed checksum file format $\to$ `ValueError`.
* Manifest record counts mismatching actual dataset contents $\to$ `ValueError`.
* Schema validation failure (malformed dates, missing fields) $\to$ `ValueError`.
* Unlabelled synthetic data $\to$ `ValueError`.

Silent fallbacks, automatic repairing of corrupt JSON, or synthesizing missing records in memory are strictly forbidden.

---

## Consequences

### Positive
* **Scientific Reproducibility:** Every evaluation run binds directly to a byte-exact, versioned dataset whose integrity is provable and immutable.
* **Epistemological Clarity:** Explicit distinction between observed facts, expert annotations, and synthetic controls prevents methodological fallacies.
* **Decoupled Architecture:** The evaluation engine receives pre-validated data and does not touch the filesystem or manage checksums.
* **Working Directory Independence:** Loaders and evaluation scripts execute identically from any environment or test harness.

### Negative
* Manual curation overhead: every benchmark dataset must be explicitly created, manifested, and sealed with a `.sha256` companion file.
* Strictness: minor whitespace edits in dataset files invalidate the checksum and require an intentional update of `.sha256`.

---

## Enforcement

A Pull Request is **non-compliant** and MUST NOT be merged if:

1. A dataset loader resolves paths implicitly using `CWD` or embedded relative strings without explicit path injection.
2. `EvaluationDataset` contains an in-memory fallback policy or synthetic sample generator.
3. Checksum verification parses and re-serializes JSON before hashing rather than inspecting raw bytes.
4. An evaluation claims "ground truth" for subjective expert annotations.
5. Unit test fixtures (`backend/test/fixtures/`) are coupled to or imported by evaluation pipelines.
6. A test or script introduces synthetic data without `DataModality.SYNTHETIC_CONTROL`.
7. Architectural tests fail to verify that byte-level tampering of dataset files triggers immediate rejection.

### Automated Test Requirements
The test suite MUST verify:
1. **Tamper Rejection Test:** Modifying 1 byte in a dataset file causes the loader to reject it with `ValueError`.
2. **Missing Checksum Test:** Deleting the `.sha256` file raises `FileNotFoundError`.
3. **CWD Independence Test:** Executing the loader from an arbitrary temporary directory (`monkeypatch.chdir`) behaves identically.
4. **Modality Boundary Test:** Rejection of untagged synthetic records during schema validation.
