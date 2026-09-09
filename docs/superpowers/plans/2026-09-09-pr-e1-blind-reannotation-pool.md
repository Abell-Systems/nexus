# PR-E.1: Blind Re-Annotation Candidate Pool under Strict Temporal Eligibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the canonical, blinded annotation candidate pool for the 3 pilot demands (`INNOGET-2415`, `INNOGET-2292`, `INNOGET-2501`) under `strict` temporal eligibility (ADR 0018), enforcing fail-fast policy binding, canonical pre-sorting, deterministic seeded shuffle (`seed=42`), structural blindness, and exact candidate set identity (38 pairs) without touching the sealed benchmark.

**Architecture:** Extend `infrastructure/annotation/blind_export.py` with `BlindedAnnotationSet` and stable pre-sorting by `publication_id` before seeded shuffle. Implement a generator service that validates benchmark SHA-256 and temporal policy binding (`temporal_pool_mode="strict"`), filters candidates strictly (`t_pub < t_demand`), and serializes `data/annotations/pilot_strict_annotation_batch.json` alongside its `.sha256` sidecar. Automated pytest suites enforce structural blindness, exact set identity, and bit-for-bit reproducibility.

**Tech Stack:** Python 3.12, Pydantic v2, hashlib, json, pytest.

## Global Constraints

- **Sealed Benchmark Untouched:** `data/evaluation/dataset_pilot_benchmark.json` and historical experiment files (`data/experiments/`) must never be modified.
- **Fail-Fast Invariant:** Missing benchmark file, SHA-256 digest mismatch, or `temporal_pool_mode != "strict"` must immediately raise `FileNotFoundError` or `ValueError`. Never synthesize fallback policy.
- **Structural Blindness Contract:** Raw serialized JSON payload must not expose `retrieval_scores`, `rank`, `retriever_id`, `publication_date`, or `method` to annotators.
- **Deterministic Bit-for-Bit Reproducibility:** No non-deterministic timestamps (e.g. `created_at`) inside the canonical payload. Candidate lists must be pre-sorted alphabetically by `publication_id` before calling `random.Random(seed=42).shuffle(order)`.
- **Zero Policy/Data Hardcoding:** Candidate sets are derived dynamically by evaluating `DefaultPatentEligibilityPolicy` against the benchmark. Tests verify exact set identity (12 for `INNOGET-2415`, 13 for `INNOGET-2292`, 13 for `INNOGET-2501`; total 38 pairs).

---

### Task 1: Canonical Pre-Sorting in `build_annotation_batch` and `BlindedAnnotationSet` Model

**Files:**
- Modify: `backend/src/main/infrastructure/annotation/blind_export.py`
- Test: `backend/test/unit/infrastructure/annotation/test_blind_export.py`

**Interfaces:**
- Consumes: `domain.models.matching.CandidatePool`, `domain.models.demand.DemandRecord | DemandSignal`, `domain.models.patent.PatentDocument`
- Produces: `BlindedAnnotationSet` model, pre-sorted `build_annotation_batch()` behavior invariant to input candidate list order.

- [ ] **Step 1: Write failing tests for canonical pre-sorting invariance and `BlindedAnnotationSet` model**

Add to `backend/test/unit/infrastructure/annotation/test_blind_export.py`:

```python
from infrastructure.annotation.blind_export import BlindedAnnotationSet


class BlindExportOrderingTest:
    def test_should_produce_identical_batch_regardless_of_candidate_input_order(self):
        pool_forward = CandidatePool(
            demand_id="D1",
            candidates=[
                Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.LEXICAL: 0.5}),
                Candidate(publication_id="ES-1", retrieval_scores={RetrievalMethod.LEXICAL: 0.9}),
                Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.LEXICAL: 0.7}),
            ],
        )
        pool_reverse = CandidatePool(
            demand_id="D1",
            candidates=[
                Candidate(publication_id="ES-1", retrieval_scores={RetrievalMethod.LEXICAL: 0.9}),
                Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.LEXICAL: 0.7}),
                Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.LEXICAL: 0.5}),
            ],
        )
        batch_a = build_annotation_batch(pool_forward, _demand(), _patents(), seed=42)
        batch_b = build_annotation_batch(pool_reverse, _demand(), _patents(), seed=42)
        assert [e.publication_id for e in batch_a.entries] == [e.publication_id for e in batch_b.entries]
        assert batch_a.model_dump_json() == batch_b.model_dump_json()


class BlindedAnnotationSetModelTest:
    def test_should_require_explicit_schema_version_and_mandatory_provenance(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        annotation_set = BlindedAnnotationSet(
            schema_version="1.0.0",
            dataset_id="nexus-pilot-16-evaluation-corpus-v1",
            dataset_sha256="bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453",
            temporal_pool_mode="strict",
            seed=42,
            demands=[batch],
        )
        assert annotation_set.schema_version == "1.0.0"
        assert annotation_set.temporal_pool_mode == "strict"
        assert len(annotation_set.demands) == 1
        assert not hasattr(annotation_set, "created_at")

    def test_should_reject_empty_schema_version_or_mismatched_sha_length(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        with pytest.raises(ValueError):
            BlindedAnnotationSet(
                schema_version="",
                dataset_id="nexus-pilot-16-evaluation-corpus-v1",
                dataset_sha256="bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453",
                temporal_pool_mode="strict",
                seed=42,
                demands=[batch],
            )
        with pytest.raises(ValueError):
            BlindedAnnotationSet(
                schema_version="1.0.0",
                dataset_id="nexus-pilot-16-evaluation-corpus-v1",
                dataset_sha256="short_hash",
                temporal_pool_mode="strict",
                seed=42,
                demands=[batch],
            )
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest backend/test/unit/infrastructure/annotation/test_blind_export.py -k "BlindExportOrderingTest or BlindedAnnotationSetModelTest" -v`
Expected: FAIL — `ImportError: cannot import name 'BlindedAnnotationSet'` and ordering mismatch.

- [ ] **Step 3: Implement `BlindedAnnotationSet` and alphabetical pre-sorting in `blind_export.py`**

In `backend/src/main/infrastructure/annotation/blind_export.py`:

```python
class BlindedAnnotationSet(BaseModel):
    """Canonical multi-demand blinded annotation set. Built once per (benchmark, policy, seed)
    and completely deterministic without timestamps or scores."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    dataset_sha256: str = Field(min_length=64, max_length=64)
    temporal_pool_mode: str = Field(min_length=1)
    seed: int
    demands: list[AnnotationBatch] = Field(default_factory=list)
```

In `build_annotation_batch` of `backend/src/main/infrastructure/annotation/blind_export.py`:

```python
def build_annotation_batch(
    pool: CandidatePool,
    demand: DemandRecord | DemandSignal,
    patents_by_id: dict[str, PatentDocument],
    seed: int,
) -> AnnotationBatch:
    """Strips retrieval provenance and applies a deterministic seeded shuffle.

    Pre-sorts publication IDs alphabetically before shuffling to guarantee bit-for-bit
    reproducibility regardless of the order candidates were inserted into the pool.
    """
    order = sorted([c.publication_id for c in pool.candidates])
    random.Random(seed).shuffle(order)
    ...
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest backend/test/unit/infrastructure/annotation/test_blind_export.py -v`
Expected: PASS (all tests in file pass).

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/annotation/blind_export.py backend/test/unit/infrastructure/annotation/test_blind_export.py
git commit -m "feat(lab): add BlindedAnnotationSet model and canonical pre-sorting before seeded shuffle"
```

---

### Task 2: Fail-Fast Benchmark Loading and Temporal Pool Generation Engine

**Files:**
- Modify: `backend/src/main/infrastructure/annotation/blind_export.py`
- Test: `backend/test/unit/infrastructure/annotation/test_blind_export.py`

**Interfaces:**
- Consumes: `backend/src/main/infrastructure/matching/eligibility.py:DefaultPatentEligibilityPolicy`
- Produces: `generate_blinded_annotation_set(benchmark_path: Path, temporal_pool_mode: str, seed: int) -> BlindedAnnotationSet`

- [ ] **Step 1: Write failing tests for generator and fail-fast validation**

Add to `backend/test/unit/infrastructure/annotation/test_blind_export.py`:

```python
from pathlib import Path
from infrastructure.annotation.blind_export import generate_blinded_annotation_set


class GenerateBlindedAnnotationSetTest:
    def test_should_fail_fast_if_benchmark_does_not_exist(self, tmp_path: Path):
        non_existent = tmp_path / "missing.json"
        with pytest.raises(FileNotFoundError, match="Benchmark dataset file not found"):
            generate_blinded_annotation_set(non_existent, temporal_pool_mode="strict", seed=42)

    def test_should_fail_fast_if_temporal_pool_mode_not_strict(self, tmp_path: Path):
        benchmark_file = tmp_path / "dummy.json"
        benchmark_file.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match="temporal_pool_mode must be 'strict'"):
            generate_blinded_annotation_set(benchmark_file, temporal_pool_mode="unconstrained", seed=42)

    def test_should_fail_fast_if_benchmark_sha256_mismatch(self, tmp_path: Path):
        benchmark_file = tmp_path / "corrupted.json"
        benchmark_file.write_text('{"dataset_id": "nexus-pilot-16"}', encoding="utf-8")
        with pytest.raises(ValueError, match="SHA-256 digest mismatch"):
            generate_blinded_annotation_set(
                benchmark_file,
                temporal_pool_mode="strict",
                seed=42,
                expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            )

    def test_should_derive_exact_eligible_sets_from_real_pilot_benchmark(self):
        real_benchmark = Path("data/evaluation/dataset_pilot_benchmark.json")
        if not real_benchmark.exists():
            pytest.skip("Benchmark file not present")

        result = generate_blinded_annotation_set(real_benchmark, temporal_pool_mode="strict", seed=42)

        assert result.schema_version == "1.0.0"
        assert result.dataset_id == "nexus-pilot-16-evaluation-corpus-v1"
        assert result.temporal_pool_mode == "strict"
        assert result.seed == 42
        assert len(result.demands) == 3

        demands_by_id = {d.demand_id: d for d in result.demands}
        assert set(demands_by_id.keys()) == {"INNOGET-2415", "INNOGET-2292", "INNOGET-2501"}

        # Exact candidate counts per demand
        assert len(demands_by_id["INNOGET-2415"].entries) == 12
        assert len(demands_by_id["INNOGET-2292"].entries) == 13
        assert len(demands_by_id["INNOGET-2501"].entries) == 13

        # Total candidate pairs = 38
        total_candidates = sum(len(d.entries) for d in result.demands)
        assert total_candidates == 38

        # Invariant: excluded publications must never appear
        pub_2415 = {e.publication_id for e in demands_by_id["INNOGET-2415"].entries}
        assert "ES-2856789-A1" not in pub_2415
        assert "ES-2895412-B1" not in pub_2415
        assert "ES-2901234-A1" not in pub_2415

        pub_2292 = {e.publication_id for e in demands_by_id["INNOGET-2292"].entries}
        assert "ES-2856789-A1" not in pub_2292
        assert "ES-2901234-A1" not in pub_2292
        assert "ES-2895412-B1" in pub_2292  # Eligible for 2292 (pub 2023-01-15 < demand 2023-02-15)

        pub_2501 = {e.publication_id for e in demands_by_id["INNOGET-2501"].entries}
        assert "ES-2856789-A1" not in pub_2501
        assert "ES-2901234-A1" not in pub_2501
        assert "ES-2895412-B1" in pub_2501
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest backend/test/unit/infrastructure/annotation/test_blind_export.py -k "GenerateBlindedAnnotationSetTest" -v`
Expected: FAIL — `ImportError: cannot import name 'generate_blinded_annotation_set'`

- [ ] **Step 3: Implement `generate_blinded_annotation_set` in `blind_export.py`**

In `backend/src/main/infrastructure/annotation/blind_export.py`:

```python
import hashlib
from pathlib import Path
from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, CandidatePool, EligibilityReason
from domain.models.patent import PatentDocument
from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy

EXPECTED_PILOT_BENCHMARK_SHA256 = "bf7c501f817f9d6e3f87574f61c003670b008910d76b1d17632ff21451195453"


def generate_blinded_annotation_set(
    benchmark_path: Path,
    temporal_pool_mode: str = "strict",
    seed: int = 42,
    expected_sha256: str | None = EXPECTED_PILOT_BENCHMARK_SHA256,
) -> BlindedAnnotationSet:
    """Loads the benchmark dataset, enforces fail-fast validations on SHA-256 and temporal policy,
    evaluates candidates under strict eligibility (ADR 0018), and produces the canonical BlindedAnnotationSet."""
    if temporal_pool_mode != "strict":
        raise ValueError(
            f"PR-E.1 contract requires temporal_pool_mode must be 'strict', got '{temporal_pool_mode}'"
        )

    path = Path(benchmark_path)
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark dataset file not found: {path}")

    content_bytes = path.read_bytes()
    computed_sha256 = hashlib.sha256(content_bytes).hexdigest()
    if expected_sha256 and computed_sha256 != expected_sha256:
        raise ValueError(
            f"Benchmark SHA-256 digest mismatch. Expected {expected_sha256}, got {computed_sha256}"
        )

    data = json.loads(content_bytes.decode("utf-8"))
    dataset_id = data.get("dataset_id")
    if not dataset_id:
        raise ValueError("Benchmark JSON is missing 'dataset_id'")

    # Instantiate DefaultPatentEligibilityPolicy
    policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")

    # Ingest patents
    patents_by_id: dict[str, PatentDocument] = {}
    for p_raw in data.get("patents", []):
        doc = PatentDocument(
            publication_id=p_raw["publication_id"],
            country_code=p_raw.get("country_code", p_raw["publication_id"].split("-")[0]),
            doc_number=p_raw.get("doc_number", p_raw["publication_id"].split("-")[1]),
            kind_code=p_raw.get("kind_code", p_raw["publication_id"].split("-")[2]),
            title=p_raw.get("title", ""),
            abstract=p_raw.get("abstract", ""),
            publication_date=p_raw.get("publication_date"),
            classifications_cpc=p_raw.get("classifications_cpc", []),
        )
        patents_by_id[doc.publication_id] = doc

    demands_batches: list[AnnotationBatch] = []
    for d_raw in data.get("demands", []):
        demand = DemandSignal(
            demand_id=d_raw["demand_id"],
            title=d_raw["title"],
            description=d_raw["description"],
            posted_date=d_raw.get("posted_date"),
        )

        eligible_candidates: list[Candidate] = []
        for pub_id, patent in patents_by_id.items():
            eligibility = policy.evaluate(patent, demand)
            if eligibility.is_eligible and eligibility.reason == EligibilityReason.ELIGIBLE:
                eligible_candidates.append(
                    Candidate(publication_id=pub_id, retrieval_scores={})
                )

        pool = CandidatePool(demand_id=demand.demand_id, candidates=eligible_candidates)
        batch = build_annotation_batch(pool, demand, patents_by_id, seed=seed)
        demands_batches.append(batch)

    return BlindedAnnotationSet(
        schema_version="1.0.0",
        dataset_id=dataset_id,
        dataset_sha256=computed_sha256,
        temporal_pool_mode=temporal_pool_mode,
        seed=seed,
        demands=demands_batches,
    )
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest backend/test/unit/infrastructure/annotation/test_blind_export.py -k "GenerateBlindedAnnotationSetTest" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/annotation/blind_export.py backend/test/unit/infrastructure/annotation/test_blind_export.py
git commit -m "feat(lab): implement generate_blinded_annotation_set with fail-fast temporal policy binding"
```

---

### Task 3: Comprehensive Structural Blindness and Set Identity Quality Gate Tests

**Files:**
- Modify: `backend/test/unit/infrastructure/annotation/test_blind_export.py`

**Interfaces:**
- Consumes: `BlindedAnnotationSet`, `generate_blinded_annotation_set`
- Produces: Automated invariant assertions in CI ensuring zero leakage of score, retriever, rank, date, or method.

- [ ] **Step 1: Write structural blindness and forbidden-field invariant tests**

Add to `backend/test/unit/infrastructure/annotation/test_blind_export.py`:

```python
import json
import re


class StructuralBlindnessInvariantTest:
    def test_serialized_json_payload_must_not_contain_forbidden_keys(self):
        real_benchmark = Path("data/evaluation/dataset_pilot_benchmark.json")
        annotation_set = generate_blinded_annotation_set(real_benchmark, temporal_pool_mode="strict", seed=42)
        serialized = annotation_set.model_dump_json(indent=2)
        parsed = json.loads(serialized)

        forbidden_patterns = [
            r'"score"',
            r'"retrieval_scores"',
            r'"rank"',
            r'"position"',
            r'"retriever_id"',
            r'"retrieval_method"',
            r'"method"',
            r'"publication_date":\s*"[^"]+"',  # Non-null publication date string
        ]

        for pattern in forbidden_patterns:
            assert not re.search(pattern, serialized, re.IGNORECASE), f"Forbidden pattern {pattern} found in serialized JSON"

        # Verify entry structure
        for demand_batch in parsed["demands"]:
            assert "demand_id" in demand_batch
            assert "demand_title" in demand_batch
            assert "demand_description" in demand_batch
            for entry in demand_batch["entries"]:
                assert set(entry.keys()) == {"publication_id", "evidence"}
                evidence = entry["evidence"]
                assert "title" in evidence
                assert "abstract" in evidence
                assert "classifications_cpc" in evidence
                assert evidence.get("publication_date") is None
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest backend/test/unit/infrastructure/annotation/test_blind_export.py::StructuralBlindnessInvariantTest -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/test/unit/infrastructure/annotation/test_blind_export.py
git commit -m "test(lab): enforce structural blindness and forbidden-field invariants on BlindedAnnotationSet"
```

---

### Task 4: CLI Script and Canonical Artifact Emission with Sidecar Hash

**Files:**
- Create: `scripts/generate_blind_annotation_batch.py`
- Create: `data/annotations/pilot_strict_annotation_batch.json`
- Create: `data/annotations/pilot_strict_annotation_batch.json.sha256`
- Test: `backend/test/unit/infrastructure/annotation/test_blind_export.py`

**Interfaces:**
- Consumes: `generate_blinded_annotation_set`
- Produces: Committed canonical JSON artifact and its `.sha256` integrity sidecar.

- [ ] **Step 1: Write CLI generation script `scripts/generate_blind_annotation_batch.py`**

```python
#!/usr/bin/env python3
"""Generates the canonical blinded annotation candidate pool under strict temporal eligibility (PR-E.1)."""

import hashlib
from pathlib import Path
import sys

# Ensure backend/src/main is on sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "backend" / "src" / "main"))

from infrastructure.annotation.blind_export import generate_blinded_annotation_set


def main() -> int:
    benchmark_path = repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.json"
    output_dir = repo_root / "data" / "annotations"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "pilot_strict_annotation_batch.json"
    sidecar_file = output_dir / "pilot_strict_annotation_batch.json.sha256"

    print(f"Loading benchmark from {benchmark_path}...")
    annotation_set = generate_blinded_annotation_set(
        benchmark_path,
        temporal_pool_mode="strict",
        seed=42,
    )

    serialized_json = annotation_set.model_dump_json(indent=2) + "\n"
    output_file.write_text(serialized_json, encoding="utf-8")
    print(f"Emitted canonical batch to {output_file}")

    digest = hashlib.sha256(serialized_json.encode("utf-8")).hexdigest()
    sidecar_content = f"{digest}  {output_file.name}\n"
    sidecar_file.write_text(sidecar_content, encoding="utf-8")
    print(f"Emitted sidecar to {sidecar_file}: {digest}")

    total_candidates = sum(len(d.entries) for d in annotation_set.demands)
    print(f"Validation successful: {len(annotation_set.demands)} demands, {total_candidates} candidate pairs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add test verifying sidecar integrity and artifact reproducibility**

Add to `backend/test/unit/infrastructure/annotation/test_blind_export.py`:

```python
class SidecarAndArtifactIntegrityTest:
    def test_emitted_artifact_matches_sidecar_digest(self):
        batch_file = Path("data/annotations/pilot_strict_annotation_batch.json")
        sidecar_file = Path("data/annotations/pilot_strict_annotation_batch.json.sha256")
        if not batch_file.exists() or not sidecar_file.exists():
            pytest.skip("Artifact not generated yet")

        content_bytes = batch_file.read_bytes()
        computed_sha = hashlib.sha256(content_bytes).hexdigest()

        sidecar_line = sidecar_file.read_text(encoding="utf-8").strip()
        expected_sha = sidecar_line.split()[0]

        assert computed_sha == expected_sha
```

- [ ] **Step 3: Run generator script to emit canonical artifact and sidecar**

Run: `python scripts/generate_blind_annotation_batch.py`
Expected: Outputs 3 demands and 38 candidate pairs, creates `pilot_strict_annotation_batch.json` and `.sha256`.

- [ ] **Step 4: Run tests to verify artifact integrity**

Run: `pytest backend/test/unit/infrastructure/annotation/test_blind_export.py -v`
Expected: PASS (all tests pass, including `SidecarAndArtifactIntegrityTest`).

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_blind_annotation_batch.py data/annotations/pilot_strict_annotation_batch.json data/annotations/pilot_strict_annotation_batch.json.sha256 backend/test/unit/infrastructure/annotation/test_blind_export.py
git commit -m "feat(lab): emit canonical blinded annotation batch artifact and sha256 sidecar (PR-E.1)"
```

---

### Task 5: Quality Gate Verification and PR Readiness

**Files:**
- Verify: All touched files

- [ ] **Step 1: Run static analysis (ruff and mypy)**

Run: `ruff check backend/src/main/infrastructure/annotation scripts/generate_blind_annotation_batch.py backend/test/unit/infrastructure/annotation`
Expected: PASS (no lint or format issues).

Run: `mypy backend/src/main/infrastructure/annotation/blind_export.py`
Expected: PASS (0 errors).

- [ ] **Step 2: Run import linter and architecture checks**

Run: `python scripts/check_architecture.py`
Expected: PASS (all architectural checks pass).

Run: `PYTHONPATH=backend/src/main lint-imports`
Expected: PASS (all 7 contracts kept).

- [ ] **Step 3: Run documentation correctness gate**

Run: `python scripts/check_docs_correctness.py`
Expected: PASS (all markdown files and ADRs verified).

- [ ] **Step 4: Run full backend unit test suite**

Run: `pytest backend/test/unit -v --cov=backend/src/main --cov-report=xml:coverage.xml`
Expected: PASS (all tests pass, 0 regressions).
