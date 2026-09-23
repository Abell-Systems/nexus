# Dense-Exclusive Stratified Sample Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic sampling script and annotation-batch pipeline that draws the pre-registered 66-pair stratified sample from the 553 dense-exclusive unscored pairs, per the frozen design spec.

**Architecture:** A pure, unit-tested allocation/selection module (`experiments/phase2/dense_exclusive_sampling.py`) holds all sampling logic and is fully covered by tests before any I/O touches it. Three thin, assertion-heavy scripts around it (matching this repo's existing `experiments/phase2/generate_dense_blindspot_annotation_batch.py` / `scripts/export_dense_blindspot_annotation_csv.py` pattern) do the actual population read, manifest write, blind annotation-batch export, and CSV export — each one BLOCKs (raises) rather than silently proceeding if a pre-registered count or hash doesn't match.

**Tech Stack:** Python 3.12, `pydantic` (existing `AnnotationBatch`/`CandidatePool`/`DemandSignal` models), `duckdb` (patent corpus lookup), `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md`

## Global Constraints

Copied verbatim from the spec — every task's code must match these exactly, not recompute or approximate them:

- Population: N=553 dense-exclusive unscored pairs, 30 demands.
- Stratum A (BM25-zero-pool): 11 demands, N_A=220 (each demand: 20 candidates).
- Stratum B (BM25-nonempty-pool): 19 demands, N_B=333.
- Source file: `data/experiments/phase2_v4/ted_at_scale_dense_retrieval_results.json`, expected sha256 `f9ddde0756830f07f88020efa562471ef3bedbe3b9785891e2bde0da1c469d60` (computed via `git show 2abefb3:data/experiments/phase2_v4/ted_at_scale_dense_retrieval_results.json | sha256sum`, verified against the real file, not guessed).
- n=66 total, n_A=26, n_B=40 (proportional to stratum size).
- Sampling seed: `SAMPLING_SEED = 104` (draws which pairs are selected — this is the statistically load-bearing seed).
- Blind-export shuffle seed: `BLIND_EXPORT_SEED = 42` (matches existing project convention in `generate_dense_blindspot_annotation_batch.py` — governs only annotator-facing ordering, not selection).
- Decision-rule parameters (echoed into output for provenance, not recomputed): p0=14/108≈0.1296, p1=0.25, alpha=0.05 (one-sided), target power=0.80, n=66, critical_c=14, actual_alpha=0.0415, achieved_power=0.8013.
- Per-demand allocation tables (Stratum A and Stratum B) are exactly the tables in spec §6 — reproduced below, hardcoded as the expected result in tests and as a cross-check in the manifest script.
- `180c5f7`'s parked 220-pair batch is never read or referenced by any script in this plan.
- This sample must be a **separate, disjoint artifact** from the 108-pair gold set and the parked 220-pair batch — different filenames, no merging.

**Stratum A allocation (n_A=26):**

```
122428-2024: 3   146289-2024: 3   158024-2024: 3   221305-2025: 3
273005-2025: 2   410719-2024: 2   588217-2024: 2   642378-2025: 2
654218-2024: 2   794374-2025: 2   820594-2025: 2
```

**Stratum B allocation (n_B=40):**

```
104441-2025: 3   137639-2024: 3   140590-2024: 2   200095-2024: 2
22543-2024: 2    264820-2024: 2   268550-2024: 2   277089-2025: 2
315512-2025: 2   368294-2025: 2   380300-2024: 2   42938-2024: 2
454027-2024: 2   498443-2025: 2   566290-2025: 2   584867-2024: 2
696940-2025: 2   814207-2025: 2   89204-2025: 2
```

---

## Prerequisites (do before Task 1)

The data files this plan reads only exist on branch `feat/pr101b-corpus-expansion-acquisition` (74 commits ahead of `main`, not part of this plan's scope to review or merge). Work happens on a new branch based on it, in an isolated worktree:

```bash
git worktree add .claude/worktrees/dense-exclusive-stratified-sample -b feat/104-dense-exclusive-stratified-sample feat/pr101b-corpus-expansion-acquisition
cd .claude/worktrees/dense-exclusive-stratified-sample
```

All file paths below are relative to this worktree's repo root. Verify the prerequisite files exist before Task 1:

```bash
test -f data/experiments/phase2_v4/ted_at_scale_dense_retrieval_results.json && echo OK
test -f data/experiments/phase2_v4/ted_independent_corpus_v1.json && echo OK
test -f data/annotations/ted_at_scale_gold_set_v1.json && echo OK
```

---

### Task 1: Pure sampling module + tests

**Files:**
- Create: `experiments/phase2/dense_exclusive_sampling.py`
- Test: `experiments/phase2/test_dense_exclusive_sampling.py`

**Interfaces:**
- Produces: `largest_remainder_allocation(total_n: int, sizes: dict[str, int]) -> dict[str, int]`, `select_stratified_sample(candidates_by_demand: dict[str, list[str]], allocation: dict[str, int], seed: int) -> dict[str, list[str]]`, module-level constants `SAMPLING_SEED = 104`, `BLIND_EXPORT_SEED = 42`.

- [ ] **Step 1: Write the failing tests**

```python
# experiments/phase2/test_dense_exclusive_sampling.py
import pytest

from dense_exclusive_sampling import largest_remainder_allocation, select_stratified_sample

STRATUM_A_SIZES = {d: 20 for d in [
    "122428-2024", "146289-2024", "158024-2024", "221305-2025", "273005-2025",
    "410719-2024", "588217-2024", "642378-2025", "654218-2024", "794374-2025",
    "820594-2025",
]}

STRATUM_A_EXPECTED = {
    "122428-2024": 3, "146289-2024": 3, "158024-2024": 3, "221305-2025": 3,
    "273005-2025": 2, "410719-2024": 2, "588217-2024": 2, "642378-2025": 2,
    "654218-2024": 2, "794374-2025": 2, "820594-2025": 2,
}

STRATUM_B_SIZES = {
    "104441-2025": 19, "137639-2024": 20, "140590-2024": 16, "200095-2024": 20,
    "22543-2024": 19, "264820-2024": 19, "268550-2024": 18, "277089-2025": 17,
    "315512-2025": 19, "368294-2025": 19, "380300-2024": 20, "42938-2024": 20,
    "454027-2024": 10, "498443-2025": 20, "566290-2025": 16, "584867-2024": 20,
    "696940-2025": 19, "814207-2025": 13, "89204-2025": 9,
}

STRATUM_B_EXPECTED = {
    "104441-2025": 3, "137639-2024": 3, "140590-2024": 2, "200095-2024": 2,
    "22543-2024": 2, "264820-2024": 2, "268550-2024": 2, "277089-2025": 2,
    "315512-2025": 2, "368294-2025": 2, "380300-2024": 2, "42938-2024": 2,
    "454027-2024": 2, "498443-2025": 2, "566290-2025": 2, "584867-2024": 2,
    "696940-2025": 2, "814207-2025": 2, "89204-2025": 2,
}


def test_largest_remainder_allocation_matches_stratum_a_table():
    assert largest_remainder_allocation(26, STRATUM_A_SIZES) == STRATUM_A_EXPECTED


def test_largest_remainder_allocation_matches_stratum_b_table():
    assert largest_remainder_allocation(40, STRATUM_B_SIZES) == STRATUM_B_EXPECTED


def test_largest_remainder_allocation_sums_to_total_n():
    alloc = largest_remainder_allocation(26, STRATUM_A_SIZES)
    assert sum(alloc.values()) == 26


def test_largest_remainder_allocation_raises_when_total_exceeds_capacity():
    with pytest.raises(ValueError):
        largest_remainder_allocation(1000, STRATUM_A_SIZES)


def test_largest_remainder_allocation_raises_when_allocation_exceeds_one_demand_size():
    tiny = {"a": 1, "b": 100}
    with pytest.raises(ValueError):
        largest_remainder_allocation(3, tiny)


def test_select_stratified_sample_respects_allocation_counts():
    candidates = {d: [f"{d}-p{i}" for i in range(20)] for d in STRATUM_A_SIZES}
    selected = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    for demand_id, k in STRATUM_A_EXPECTED.items():
        assert len(selected[demand_id]) == k


def test_select_stratified_sample_never_selects_duplicate_within_demand():
    candidates = {d: [f"{d}-p{i}" for i in range(20)] for d in STRATUM_A_SIZES}
    selected = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    for demand_id, picks in selected.items():
        assert len(picks) == len(set(picks))


def test_select_stratified_sample_is_deterministic_across_runs():
    candidates = {d: [f"{d}-p{i}" for i in range(20)] for d in STRATUM_A_SIZES}
    first = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    second = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    assert first == second


def test_select_stratified_sample_only_picks_from_given_pool():
    candidates = {d: [f"{d}-p{i}" for i in range(20)] for d in STRATUM_A_SIZES}
    selected = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    for demand_id, picks in selected.items():
        assert set(picks).issubset(set(candidates[demand_id]))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd experiments/phase2 && python -m pytest test_dense_exclusive_sampling.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dense_exclusive_sampling'`

- [ ] **Step 3: Write minimal implementation**

```python
# experiments/phase2/dense_exclusive_sampling.py
"""Pure sampling logic for the pre-registered dense-exclusive stratified
sample (docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md).

No I/O here -- this module only implements SS6 (demand allocation) and SS8
(within-demand selection) of the spec. The scripts that call it are
responsible for reading the frozen source data and writing output.
"""

import random

SAMPLING_SEED = 104
BLIND_EXPORT_SEED = 42


def largest_remainder_allocation(total_n: int, sizes: dict[str, int]) -> dict[str, int]:
    """Spreads total_n as evenly as possible across sizes.keys(), largest-remainder
    rounding, remainder assigned in ascending lexicographic demand_id order (the
    spec's SS6 deterministic tie-break). Raises ValueError if total_n exceeds the
    combined capacity, or if any single demand's allocation would exceed its size.
    """
    if total_n > sum(sizes.values()):
        raise ValueError(
            f"total_n={total_n} exceeds combined capacity={sum(sizes.values())}"
        )
    ids = sorted(sizes)
    m = len(ids)
    base = total_n // m
    remainder = total_n - base * m
    allocation = {demand_id: base for demand_id in ids}
    for demand_id in ids[:remainder]:
        allocation[demand_id] += 1
    for demand_id in ids:
        if allocation[demand_id] > sizes[demand_id]:
            raise ValueError(
                f"{demand_id}: allocation {allocation[demand_id]} exceeds pool size {sizes[demand_id]}"
            )
    return allocation


def select_stratified_sample(
    candidates_by_demand: dict[str, list[str]],
    allocation: dict[str, int],
    seed: int,
) -> dict[str, list[str]]:
    """Uniform random draw without replacement per demand (spec SS8). One
    random.Random instance is seeded once and reused across all demands, visited
    in ascending lexicographic demand_id order, each demand's candidate list
    pre-sorted before sampling -- both required for bit-for-bit reproducibility
    regardless of input dict ordering.
    """
    rng = random.Random(seed)
    selected: dict[str, list[str]] = {}
    for demand_id in sorted(allocation):
        pool = sorted(candidates_by_demand[demand_id])
        k = allocation[demand_id]
        selected[demand_id] = rng.sample(pool, k)
    return selected
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd experiments/phase2 && python -m pytest test_dense_exclusive_sampling.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add experiments/phase2/dense_exclusive_sampling.py experiments/phase2/test_dense_exclusive_sampling.py
git commit -m "feat(matching): pure allocation/selection module for #104 dense-exclusive stratified sample

Implements the design spec's SS6 (largest-remainder demand allocation,
deterministic lexicographic tie-break) and SS8 (seeded uniform-random
within-demand selection) as pure, fully unit-tested functions -- no I/O,
no dependency on the frozen source data yet.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 2: Sampling manifest generation script

**Files:**
- Create: `experiments/phase2/sample_dense_exclusive_stratified.py`

**Interfaces:**
- Consumes: `dense_exclusive_sampling.largest_remainder_allocation`, `dense_exclusive_sampling.select_stratified_sample`, `dense_exclusive_sampling.SAMPLING_SEED` (Task 1).
- Produces: `generate(dense_results_path: Path, out_path: Path) -> dict` and a written manifest JSON (+ `.sha256` sidecar) at `data/annotations/ted_dense_exclusive_stratified_sample_manifest.json`, consumed by Task 3 as `{"selected": [{"demand_id": str, "publication_id": str, "stratum": "A"|"B"}, ...]}`.

- [ ] **Step 1: Write the script**

```python
# experiments/phase2/sample_dense_exclusive_stratified.py
"""#104 dense-exclusive stratified sample, step 1: manifest generation.

Per docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md.
Reads the frozen dense-retrieval results verbatim (no re-retrieval), verifies
the population/strata counts and source hash the design was frozen against,
computes the pre-registered demand allocation, draws the seeded sample, and
writes a manifest -- this script does not decide any sampling parameter, it
only consumes what the spec already committed.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dense_exclusive_sampling import (  # noqa: E402
    SAMPLING_SEED,
    largest_remainder_allocation,
    select_stratified_sample,
)

EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256 = (
    "f9ddde0756830f07f88020efa562471ef3bedbe3b9785891e2bde0da1c469d60"
)

EXPECTED_STRATUM_A_ALLOCATION = {
    "122428-2024": 3, "146289-2024": 3, "158024-2024": 3, "221305-2025": 3,
    "273005-2025": 2, "410719-2024": 2, "588217-2024": 2, "642378-2025": 2,
    "654218-2024": 2, "794374-2025": 2, "820594-2025": 2,
}

EXPECTED_STRATUM_B_ALLOCATION = {
    "104441-2025": 3, "137639-2024": 3, "140590-2024": 2, "200095-2024": 2,
    "22543-2024": 2, "264820-2024": 2, "268550-2024": 2, "277089-2025": 2,
    "315512-2025": 2, "368294-2025": 2, "380300-2024": 2, "42938-2024": 2,
    "454027-2024": 2, "498443-2025": 2, "566290-2025": 2, "584867-2024": 2,
    "696940-2025": 2, "814207-2025": 2, "89204-2025": 2,
}

DECISION_RULE = {
    "p0": 14 / 108,
    "p1": 0.25,
    "alpha_one_sided": 0.05,
    "target_power": 0.80,
    "n": 66,
    "critical_c": 14,
    "actual_alpha": 0.0415,
    "achieved_power": 0.8013,
}


def generate(dense_results_path: Path, out_path: Path) -> dict[str, Any]:
    raw_bytes = dense_results_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256 != EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256:
        raise ValueError(
            f"Source file hash mismatch: expected {EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256}, "
            f"got {actual_sha256}. This script must BLOCK rather than sample against data "
            "the design spec was not frozen against."
        )
    dense = json.loads(raw_bytes.decode("utf-8"))

    sizes_a: dict[str, int] = {}
    sizes_b: dict[str, int] = {}
    pool_a: dict[str, list[str]] = {}
    pool_b: dict[str, list[str]] = {}
    for demand_id, v in dense["per_demand"].items():
        unscored = [
            c["publication_id"]
            for c in v["candidates"]
            if c["provenance"] == "dense_exclusive_new_unscored"
        ]
        if v["was_bm25_zero_pool"]:
            sizes_a[demand_id] = len(unscored)
            pool_a[demand_id] = unscored
        else:
            sizes_b[demand_id] = len(unscored)
            pool_b[demand_id] = unscored

    if len(sizes_a) != 11:
        raise ValueError(f"Expected 11 Stratum A demands, found {len(sizes_a)}")
    if len(sizes_b) != 19:
        raise ValueError(f"Expected 19 Stratum B demands, found {len(sizes_b)}")
    if sum(sizes_a.values()) != 220:
        raise ValueError(f"Expected Stratum A total 220, found {sum(sizes_a.values())}")
    if sum(sizes_b.values()) != 333:
        raise ValueError(f"Expected Stratum B total 333, found {sum(sizes_b.values())}")

    allocation_a = largest_remainder_allocation(26, sizes_a)
    allocation_b = largest_remainder_allocation(40, sizes_b)
    if allocation_a != EXPECTED_STRATUM_A_ALLOCATION:
        raise ValueError(
            f"Stratum A allocation drift from pre-registered table: {allocation_a} != "
            f"{EXPECTED_STRATUM_A_ALLOCATION}"
        )
    if allocation_b != EXPECTED_STRATUM_B_ALLOCATION:
        raise ValueError(
            f"Stratum B allocation drift from pre-registered table: {allocation_b} != "
            f"{EXPECTED_STRATUM_B_ALLOCATION}"
        )

    combined_allocation = {**allocation_a, **allocation_b}
    combined_pool = {**pool_a, **pool_b}
    selected = select_stratified_sample(combined_pool, combined_allocation, seed=SAMPLING_SEED)

    total_selected = sum(len(v) for v in selected.values())
    if total_selected != 66:
        raise ValueError(f"Expected 66 total selected pairs, got {total_selected}")

    stratum_by_demand = {**{d: "A" for d in sizes_a}, **{d: "B" for d in sizes_b}}
    selected_rows = [
        {"demand_id": demand_id, "publication_id": publication_id, "stratum": stratum_by_demand[demand_id]}
        for demand_id in sorted(selected)
        for publication_id in selected[demand_id]
    ]

    out = {
        "dataset_id": "nexus-phase2-ted-dense-exclusive-stratified-sample-v1",
        "purpose": "DUAL_ANNOTATION_POOL -- #104 dense-exclusive stratified sample, "
                   "docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md",
        "source_dense_retrieval_results_path": str(dense_results_path.relative_to(REPO_ROOT)),
        "source_dense_retrieval_results_sha256": actual_sha256,
        "sampling_seed": SAMPLING_SEED,
        "n_total": total_selected,
        "n_stratum_a": sum(allocation_a.values()),
        "n_stratum_b": sum(allocation_b.values()),
        "stratum_a_allocation": allocation_a,
        "stratum_b_allocation": allocation_b,
        "decision_rule": DECISION_RULE,
        "selected": selected_rows,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote {total_selected} selected pairs ({out['n_stratum_a']} A / {out['n_stratum_b']} B) to {out_path}")
    return out


def main() -> int:
    generate(
        dense_results_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_retrieval_results.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_stratified_sample_manifest.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `python experiments/phase2/sample_dense_exclusive_stratified.py`
Expected: prints `Wrote 66 selected pairs (26 A / 40 B) to .../ted_dense_exclusive_stratified_sample_manifest.json`, exit 0.

- [ ] **Step 3: Verify the manifest by hand**

```bash
python3 -c "
import json
m = json.load(open('data/annotations/ted_dense_exclusive_stratified_sample_manifest.json'))
assert m['n_total'] == 66
assert m['n_stratum_a'] == 26
assert m['n_stratum_b'] == 40
assert len(m['selected']) == 66
assert len({(r['demand_id'], r['publication_id']) for r in m['selected']}) == 66
print('manifest verified: 66 unique pairs, 26 A / 40 B')
"
```

Expected: `manifest verified: 66 unique pairs, 26 A / 40 B`, no assertion errors.

- [ ] **Step 4: Re-run and confirm determinism**

```bash
cp data/annotations/ted_dense_exclusive_stratified_sample_manifest.json /tmp/manifest_run1.json
python experiments/phase2/sample_dense_exclusive_stratified.py
diff /tmp/manifest_run1.json data/annotations/ted_dense_exclusive_stratified_sample_manifest.json
```

Expected: no diff output (identical byte-for-byte across runs).

- [ ] **Step 5: Commit**

```bash
git add experiments/phase2/sample_dense_exclusive_stratified.py data/annotations/ted_dense_exclusive_stratified_sample_manifest.json data/annotations/ted_dense_exclusive_stratified_sample_manifest.sha256
git commit -m "feat(matching): generate #104 dense-exclusive stratified sample manifest

Reads the frozen dense-retrieval results (hash-verified against the value
the design spec was frozen against), recomputes the demand allocation and
cross-checks it against the spec's pre-registered tables (BLOCKs on any
drift), then draws the seed=104 sample: 66 pairs, 26 Stratum A / 40
Stratum B. Re-run confirmed byte-for-byte deterministic.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 3: Blind annotation batch generation

**Files:**
- Create: `experiments/phase2/generate_dense_exclusive_stratified_annotation_batch.py`

**Interfaces:**
- Consumes: manifest JSON from Task 2 (`{"selected": [{"demand_id", "publication_id", "stratum"}], "n_total": 66}`), `infrastructure.annotation.blind_export.build_annotation_batch(pool: CandidatePool, demand: DemandRecord | DemandSignal, patents_by_id: dict[str, PatentDocument], seed: int) -> AnnotationBatch` (existing, `backend/src/main/infrastructure/annotation/blind_export.py`), `domain.models.demand.DemandSignal`, `domain.models.matching.Candidate`, `domain.models.matching.CandidatePool`, `domain.models.patent.PatentDocument` (existing).
- Produces: `data/annotations/ted_dense_exclusive_stratified_annotation_batch.json` (+ `.sha256`), same top-level shape as `180c5f7`'s `ted_dense_blindspot_annotation_batch.json` (`{"demands": [AnnotationBatch, ...], "total_annotation_pairs": int, ...}`), consumed by Task 4 via `data["demands"][i]["entries"][j]["evidence"]`.

- [ ] **Step 1: Write the script**

```python
# experiments/phase2/generate_dense_exclusive_stratified_annotation_batch.py
"""#104 dense-exclusive stratified sample, step 2: blind batch generation.

Per docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md
SS10. Takes the exact (demand, patent) pairs already selected by
sample_dense_exclusive_stratified.py (no re-sampling, no re-selection here)
and blind-exports them via the existing
infrastructure.annotation.blind_export.build_annotation_batch -- same
deterministic seeded shuffle, same evidence fields, same provenance
stripping used for the original 108-pair gold set and the parked
220-pair batch.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import duckdb  # noqa: E402

from dense_exclusive_sampling import BLIND_EXPORT_SEED  # noqa: E402
from domain.models.demand import DemandSignal  # noqa: E402
from domain.models.matching import Candidate, CandidatePool  # noqa: E402
from domain.models.patent import PatentDocument  # noqa: E402
from infrastructure.annotation.blind_export import AnnotationBatch, build_annotation_batch  # noqa: E402


def generate(
    manifest_path: Path,
    demand_corpus_path: Path,
    corpus_parquet_glob: str,
    out_path: Path,
    seed: int = BLIND_EXPORT_SEED,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    demand_corpus = json.loads(demand_corpus_path.read_text(encoding="utf-8"))
    corpus_by_id = {d["demand_id"]: d for d in demand_corpus["demands"]}

    pairs_by_demand: dict[str, list[str]] = {}
    for row in manifest["selected"]:
        pairs_by_demand.setdefault(row["demand_id"], []).append(row["publication_id"])

    con = duckdb.connect()
    con.execute(f"""
        CREATE TABLE patents AS
        SELECT DISTINCT ON (publication_id)
            publication_id, country_code, doc_number, kind_code, title, abstract,
            publication_date, classifications_cpc AS cpc_codes
        FROM read_parquet('{corpus_parquet_glob}')
        ORDER BY publication_id
    """)
    rows = con.execute(
        "SELECT publication_id, country_code, doc_number, kind_code, title, abstract, "
        "publication_date, cpc_codes FROM patents"
    ).fetchall()
    con.close()

    patents_by_id: dict[str, PatentDocument] = {
        row[0]: PatentDocument(
            publication_id=row[0], country_code=row[1] or "", doc_number=row[2] or "",
            kind_code=row[3] or "", title=row[4] or "", abstract=row[5] or "",
            publication_date=row[6], classifications_cpc=list(row[7]) if row[7] is not None else [],
        )
        for row in rows
    }

    batches: list[AnnotationBatch] = []
    total_pairs = 0
    for demand_id in sorted(pairs_by_demand):
        d = corpus_by_id[demand_id]
        demand = DemandSignal(
            demand_id=demand_id, source_network="ted", title=d["title"],
            description=d["description_text"],
            posted_date=d["publication_date_evidence"]["publication_date"],
        )
        publication_ids = pairs_by_demand[demand_id]
        pool = CandidatePool(
            demand_id=demand_id,
            candidates=[Candidate(publication_id=pid, retrieval_scores={}) for pid in publication_ids],
        )
        batch = build_annotation_batch(pool, demand, patents_by_id, seed=seed)
        batches.append(batch)
        total_pairs += len(batch.entries)

    if total_pairs != manifest["n_total"]:
        raise ValueError(f"Expected {manifest['n_total']} total pairs, got {total_pairs}")

    out = {
        "dataset_id": "nexus-phase2-ted-dense-exclusive-stratified-annotation-v1",
        "purpose": "DUAL_ANNOTATION_POOL -- #104 dense-exclusive stratified sample, "
                   "docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md",
        "source_manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
        "source_manifest_sha256": manifest_sha256,
        "seed": seed,
        "demand_count": len(batches),
        "total_annotation_pairs": total_pairs,
        "demand_ids": sorted(pairs_by_demand),
        "demands": [json.loads(b.model_dump_json()) for b in batches],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote {total_pairs} pairs across {len(batches)} demands to {out_path}")
    return out


def main() -> int:
    generate(
        manifest_path=REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_stratified_sample_manifest.json",
        demand_corpus_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_independent_corpus_v1.json",
        corpus_parquet_glob=str(REPO_ROOT / "data" / "snapshots" / "oepm_invenes_corpus_v1" / "OEPM-INVENES-CORPUS-2026-V1" / "patents" / "*.parquet"),
        out_path=REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_stratified_annotation_batch.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `python experiments/phase2/generate_dense_exclusive_stratified_annotation_batch.py`
Expected: prints `Wrote 66 pairs across <=30 demands to .../ted_dense_exclusive_stratified_annotation_batch.json`, exit 0.

- [ ] **Step 3: Verify by hand**

```bash
python3 -c "
import json
b = json.load(open('data/annotations/ted_dense_exclusive_stratified_annotation_batch.json'))
assert b['total_annotation_pairs'] == 66
n = sum(len(d['entries']) for d in b['demands'])
assert n == 66
print('annotation batch verified: 66 entries across', len(b['demands']), 'demands')
"
```

Expected: `annotation batch verified: 66 entries across <=30 demands`.

- [ ] **Step 4: Commit**

```bash
git add experiments/phase2/generate_dense_exclusive_stratified_annotation_batch.py data/annotations/ted_dense_exclusive_stratified_annotation_batch.json data/annotations/ted_dense_exclusive_stratified_annotation_batch.sha256
git commit -m "feat(matching): generate #104 dense-exclusive stratified sample blind annotation batch

Blind-exports the 66 (demand, patent) pairs selected by the manifest via
the existing build_annotation_batch -- same deterministic seeded shuffle
and evidence-field discipline as the 108-pair gold set. Sealed as its own
artifact, disjoint from the gold set and the parked 220-pair batch.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 4: Blank CSV export for annotation

**Files:**
- Create: `scripts/export_dense_exclusive_stratified_annotation_csv.py`

**Interfaces:**
- Consumes: `data/annotations/ted_dense_exclusive_stratified_annotation_batch.json` from Task 3 (`data["demands"][i]["entries"][j]["evidence"]` with fields `publication_id`, `title`, `abstract`, `classifications_cpc`).
- Produces: three files `data/annotations/ted_dense_exclusive_stratified_annotation_{template,valentin,lydia}.csv`.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Exports the #104 dense-exclusive stratified sample annotation batch (JSON)
to flat CSV templates for human annotation -- same columns as the original
at-scale template and the parked dense blind-spot template
(demand_id,publication_id,title,abstract,classifications_cpc,judgment), so
the same annotation guide/scale applies unchanged. Writes three identical
blank copies: template, valentin, lydia."""

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIELDNAMES = ["demand_id", "publication_id", "title", "abstract", "classifications_cpc", "judgment"]


def main() -> int:
    in_path = REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_stratified_annotation_batch.json"
    data = json.loads(in_path.read_text(encoding="utf-8"))

    rows = []
    for demand in data["demands"]:
        for entry in demand["entries"]:
            ev = entry["evidence"]
            rows.append({
                "demand_id": demand["demand_id"],
                "publication_id": ev["publication_id"],
                "title": ev["title"],
                "abstract": ev["abstract"],
                "classifications_cpc": "; ".join(ev["classifications_cpc"]),
                "judgment": "",
            })

    for suffix in ("template", "valentin", "lydia"):
        out_path = REPO_ROOT / "data" / "annotations" / f"ted_dense_exclusive_stratified_annotation_{suffix}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `python scripts/export_dense_exclusive_stratified_annotation_csv.py`
Expected: prints three `Wrote 66 rows to ...` lines, exit 0.

- [ ] **Step 3: Verify row counts**

```bash
for f in template valentin lydia; do
  n=$(($(wc -l < "data/annotations/ted_dense_exclusive_stratified_annotation_${f}.csv") - 1))
  echo "$f: $n data rows"
  test "$n" -eq 66 || { echo "FAIL: expected 66"; exit 1; }
done
```

Expected: `template: 66 data rows`, `valentin: 66 data rows`, `lydia: 66 data rows`, no FAIL.

- [ ] **Step 4: Commit**

```bash
git add scripts/export_dense_exclusive_stratified_annotation_csv.py data/annotations/ted_dense_exclusive_stratified_annotation_template.csv data/annotations/ted_dense_exclusive_stratified_annotation_valentin.csv data/annotations/ted_dense_exclusive_stratified_annotation_lydia.csv
git commit -m "feat(matching): export blank CSVs for #104 dense-exclusive stratified sample annotation

Same columns/convention as the existing at-scale and parked dense
blind-spot templates. Three identical blank copies for independent
dual annotation.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 5: End-to-end verification and results doc

**Files:**
- Create: `docs/phase2-ted-dense-exclusive-stratified-sample-results.md`

**Interfaces:**
- Consumes: outputs of Tasks 1-4 (manifest, annotation batch, CSVs) — read-only, no new production code.

- [ ] **Step 1: Run the full pytest suite for this module**

Run: `cd experiments/phase2 && python -m pytest test_dense_exclusive_sampling.py -v`
Expected: PASS (9 passed).

- [ ] **Step 2: Confirm end-to-end determinism (fresh re-run from the manifest step onward)**

```bash
cp data/annotations/ted_dense_exclusive_stratified_sample_manifest.json /tmp/manifest_check.json
cp data/annotations/ted_dense_exclusive_stratified_annotation_batch.json /tmp/batch_check.json
python experiments/phase2/sample_dense_exclusive_stratified.py
python experiments/phase2/generate_dense_exclusive_stratified_annotation_batch.py
diff /tmp/manifest_check.json data/annotations/ted_dense_exclusive_stratified_sample_manifest.json
diff /tmp/batch_check.json data/annotations/ted_dense_exclusive_stratified_annotation_batch.json
```

Expected: no diff output from either `diff`.

- [ ] **Step 3: Write the results doc**

```markdown
# #104 dense-exclusive stratified sample -- generation results

Spec: docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md

## What ran

1. `experiments/phase2/sample_dense_exclusive_stratified.py` -- read the frozen
   dense-retrieval results (sha256 `f9ddde0756830f07f88020efa562471ef3bedbe3b9785891e2bde0da1c469d60`,
   matches the value the design spec was frozen against), verified the 553/220/333
   population counts, recomputed the demand allocation and confirmed it matches
   the spec's pre-registered tables exactly (no drift), drew the seed=104 sample.
2. `experiments/phase2/generate_dense_exclusive_stratified_annotation_batch.py` --
   blind-exported the 66 selected pairs via the existing `build_annotation_batch`.
3. `scripts/export_dense_exclusive_stratified_annotation_csv.py` -- wrote three
   blank CSVs (template/valentin/lydia), 66 rows each.

## Result

- 66 pairs selected: 26 from Stratum A (BM25-zero-pool), 40 from Stratum B.
- Re-run from the manifest step onward is byte-for-byte identical (verified).
- No annotation has occurred yet -- `judgment` columns are blank in all three CSVs.
- This artifact is disjoint from the 108-pair gold set and from `180c5f7`'s
  parked 220-pair batch (which itself has no filled-in labels).

## Next step (not done here)

Independent dual annotation (Valentín + Lydia) on the blank CSVs, under the
same 0-3 contract as the gold set, followed by adjudication of any
disagreements and application of the pre-registered decision rule
(spec SS9): count relevant (score >=1) among the 66; >=14 rejects H0.
```

- [ ] **Step 4: Commit**

```bash
git add docs/phase2-ted-dense-exclusive-stratified-sample-results.md
git commit -m "docs(matching): record #104 dense-exclusive stratified sample generation results

66 pairs generated (26 Stratum A / 40 Stratum B), end-to-end determinism
verified by re-run, no annotation performed yet. Next step is independent
dual annotation per the pre-registered decision rule.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```
