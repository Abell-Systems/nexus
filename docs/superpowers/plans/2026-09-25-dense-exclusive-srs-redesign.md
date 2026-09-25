# Dense-Exclusive SRS Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the buggy stratum-proportional + equal-per-demand allocation for the 553 dense-exclusive pairs with pure simple random sampling (SRS), giving every pair an equal, known inclusion probability, and delete the allocation mechanism the bug lived in.

**Architecture:** A pure sampling primitive (`simple_random_sample`) replaces the two-stage allocation logic in `experiments/phase2/dense_exclusive_sampling.py`. A new manifest-generation script (`experiments/phase2/sample_dense_exclusive_srs.py`) replaces `sample_dense_exclusive_stratified.py`, consuming the same frozen source data but with no allocation step — it builds the flat 553-pair population, verifies the population invariants, draws 66 uniformly, tags each drawn pair with its stratum for diagnostics only, and writes a manifest recording every pair's identity and inclusion probability (constant 66/553).

**Tech Stack:** Python 3.12, stdlib `random`/`hashlib`/`json` only (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md` (and `docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md` SS1-SS4/SS9-SS12, which the new spec explicitly carries forward unchanged).

## Global Constraints

- Population size N = 553 (11 Stratum A demands totaling 220 pairs, 19 Stratum B demands totaling 333 pairs) — unchanged from the 2026-09-23 design, verify against source data, do not hardcode without verification.
- Sample size n = 66. Inclusion probability π = 66/553 for every pair, exactly (a Python `Fraction(66, 553)` or the float `66/553` — pick one and use it consistently across the manifest; this plan uses the float `66/553` for JSON-serializability, computed once as a named constant).
- Sampling seed = 104 (`SAMPLING_SEED`, already defined in `dense_exclusive_sampling.py`, unchanged).
- `BLIND_EXPORT_SEED = 42` in `dense_exclusive_sampling.py` is used by a different, out-of-scope script (`generate_dense_exclusive_stratified_annotation_batch.py`) and must not be touched or removed.
- Decision rule constants unchanged: p0=14/108, p1=0.25, α=0.05 target (actual 0.0415), power target 0.80 (achieved 0.8013), n=66, critical c=14.
- Real source file: `data/experiments/phase2_v4/ted_at_scale_dense_retrieval_results.json`, expected sha256 `f9ddde0756830f07f88020efa562471ef3bedbe3b9785891e2bde0da1c469d60` (verified current as of 2026-09-25 — unchanged from the 2026-09-23 design's frozen value).
- **No task in this plan may invoke the new manifest generator against the real source file to produce a real manifest.** Every test in this plan uses a synthetic fixture population. The real draw is explicitly a separate, later, manual step gated on PR #112's TED construct-validity gate resolving (spec SS6/SS9) — not part of this plan's acceptance criteria.
- No annotation files (CSV export) are created or modified by this plan — that script (`generate_dense_exclusive_stratified_annotation_batch.py`) is unaffected and out of scope.
- Per ADR 0026, `backend/test/` must never reference the `experiments/` tree. Both new test files in this plan live under `experiments/phase2/`, not `backend/test/`.
- `experiments/phase2/sample_dense_exclusive_stratified.py` and `experiments/phase2/test_dense_exclusive_sampling.py`'s current content (testing `largest_remainder_allocation`/`select_stratified_sample`) are deleted, not deprecated — they test/exercise a mechanism this plan removes entirely. The already-committed output of the old script (`data/annotations/ted_dense_exclusive_stratified_sample_manifest.json` and its blind CSVs) is left on disk untouched by this plan (historical artifact, superseded the moment a real SRS draw happens later, not before).

## Review Focus

- **Population smaller than the sample size.** If a caller ever passes `n > len(population)`, `random.Random.sample` raises `ValueError` on its own — worth a test pinning that this surfaces clearly rather than silently truncating, since a silent truncation here would produce an under-powered sample without anyone noticing.
- **Non-hashable or duplicate-looking population entries.** The population is `list[tuple[str, str]]` (demand_id, publication_id) pairs; if the same `(demand_id, publication_id)` tuple appears twice in the input (a real data bug, not a hypothetical), `random.sample` could draw it twice into a 66-length result that then has only 65 distinct pairs. Worth a test asserting the manifest generator itself checks for duplicate identities in the *population* before sampling, not just checking the *output* for duplicates (which wouldn't catch this root cause).
- **Sort stability across dict-vs-list input shapes.** The old code pre-sorted per-demand lists before sampling for reproducibility regardless of input ordering; the new flat-population sort must do the same at the population level — a test should build the same logical population from two different insertion orders and assert identical output.
- **Stratum tag correctness on the sampled subset, not just the population.** It would be easy to write a bug where the *population* is correctly tagged A/B but the *manifest's per-pair records* lose or mis-copy that tag during the sample-then-annotate step — test the actual output records' stratum field against known ground truth, not just that the population dict was built correctly.
- **Empty or missing `unscored` provenance filtering.** The real source JSON's `per_demand[...]["candidates"]` includes both dense-exclusive-unscored and other-provenance candidates (see `sample_dense_exclusive_stratified.py`'s existing `provenance == "dense_exclusive_new_unscored"` filter) — a test must confirm the new script applies the same filter, not accidentally including already-scored or wrong-provenance candidates in the population.

---

### Task 1: Pure SRS sampling primitive

**Files:**
- Modify: `experiments/phase2/dense_exclusive_sampling.py` (remove `largest_remainder_allocation` and `select_stratified_sample`; add `simple_random_sample`)
- Test: `experiments/phase2/test_dense_exclusive_sampling.py` (replace entire contents — the old tests exercise functions this task deletes)

**Interfaces:**
- Produces: `simple_random_sample(population: list[tuple[str, str]], n: int, seed: int) -> list[tuple[str, str]]` — draws `n` items uniformly without replacement from `population`, pre-sorting `population` before any RNG call for reproducibility regardless of input order. Raises `ValueError` (via the underlying `random.Random.sample` call — do not catch/rewrap it, let the standard message surface) if `n > len(population)`.
- Consumes: nothing from other tasks (this is the first task).
- `SAMPLING_SEED = 104` and `BLIND_EXPORT_SEED = 42` module-level constants stay exactly as they are today — do not rename or move them.

- [ ] **Step 1: Write the failing tests**

Replace the entire contents of `experiments/phase2/test_dense_exclusive_sampling.py` with:

```python
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dense_exclusive_sampling import simple_random_sample


def _population(n: int) -> list[tuple[str, str]]:
    return [(f"D{i:03d}", f"P{i:03d}") for i in range(n)]


def test_simple_random_sample_returns_exactly_n_items():
    population = _population(553)
    sample = simple_random_sample(population, n=66, seed=104)
    assert len(sample) == 66


def test_simple_random_sample_has_no_duplicates():
    population = _population(553)
    sample = simple_random_sample(population, n=66, seed=104)
    assert len(sample) == len(set(sample))


def test_simple_random_sample_only_draws_from_population():
    population = _population(553)
    sample = simple_random_sample(population, n=66, seed=104)
    assert set(sample).issubset(set(population))


def test_simple_random_sample_is_deterministic_across_runs():
    population = _population(553)
    first = simple_random_sample(population, n=66, seed=104)
    second = simple_random_sample(population, n=66, seed=104)
    assert first == second


def test_simple_random_sample_is_order_independent():
    """Drawing from the same logical population in a different insertion
    order must produce the same sample -- the function must sort before
    sampling, not trust caller ordering."""
    population = _population(553)
    reversed_population = list(reversed(population))
    from_forward = simple_random_sample(population, n=66, seed=104)
    from_reversed = simple_random_sample(reversed_population, n=66, seed=104)
    assert from_forward == from_reversed


def test_simple_random_sample_raises_when_n_exceeds_population():
    population = _population(10)
    with pytest.raises(ValueError):
        simple_random_sample(population, n=66, seed=104)


def test_simple_random_sample_different_seeds_differ():
    population = _population(553)
    a = simple_random_sample(population, n=66, seed=104)
    b = simple_random_sample(population, n=66, seed=999)
    assert a != b
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd experiments/phase2 && python -m pytest test_dense_exclusive_sampling.py -v`
Expected: FAIL with `ImportError: cannot import name 'simple_random_sample'`

- [ ] **Step 3: Replace the implementation**

Replace the entire contents of `experiments/phase2/dense_exclusive_sampling.py` with:

```python
"""Pure sampling logic for the pre-registered dense-exclusive sample
(docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md).

No I/O here -- this module only implements the redesign's SS4 selection
procedure. The scripts that call it are responsible for reading the frozen
source data and writing output.

Supersedes the stratum-proportional + equal-per-demand allocation this
module used to hold (`largest_remainder_allocation`, the old
`select_stratified_sample`) -- deleted, not deprecated, per the redesign
spec SS2: pure SRS needs no allocation step at all.
"""

import random

SAMPLING_SEED = 104
BLIND_EXPORT_SEED = 42


def simple_random_sample(
    population: list[tuple[str, str]], n: int, seed: int
) -> list[tuple[str, str]]:
    """Uniform random draw of n items without replacement from population,
    deterministic given seed. Population is sorted before any RNG call, so
    the result is identical regardless of the caller's input ordering --
    required for bit-for-bit reproducibility. Raises ValueError (from the
    underlying random.Random.sample call) if n exceeds len(population).
    """
    rng = random.Random(seed)
    sorted_population = sorted(population)
    return rng.sample(sorted_population, n)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd experiments/phase2 && python -m pytest test_dense_exclusive_sampling.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Delete the now-orphaned old generator script**

`experiments/phase2/sample_dense_exclusive_stratified.py` imports
`largest_remainder_allocation` and the old `select_stratified_sample`,
both just deleted. It is fully superseded by Task 2's new script. Delete
it:

```bash
git rm experiments/phase2/sample_dense_exclusive_stratified.py
```

- [ ] **Step 6: Commit**

```bash
git add experiments/phase2/dense_exclusive_sampling.py experiments/phase2/test_dense_exclusive_sampling.py
git commit -m "feat(matching): pure SRS sampling primitive, delete stratified allocation

Replaces largest_remainder_allocation + the per-demand select_stratified_sample
with simple_random_sample: draw n uniformly from a flat population, no
allocation step, per docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md.
Deletes sample_dense_exclusive_stratified.py (the old real-data-wired
generator, now orphaned -- superseded by a new script in the next commit).

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: SRS manifest generator + tests

**Files:**
- Create: `experiments/phase2/sample_dense_exclusive_srs.py`
- Test: `experiments/phase2/test_sample_dense_exclusive_srs.py`

**Interfaces:**
- Consumes: `simple_random_sample(population, n, seed)` from Task 1 (`dense_exclusive_sampling.py`), and `SAMPLING_SEED` from the same module.
- Produces: `generate(dense_results_path: Path, out_path: Path) -> dict[str, Any]` — the manifest-generation function. `main()` wires it to the real source/output paths but **this plan's tests must never call `main()` or invoke `generate()` with the real repo paths** — every test constructs a synthetic `dense_results_path` fixture under `tmp_path`.

- [ ] **Step 1: Write the failing tests**

Create `experiments/phase2/test_sample_dense_exclusive_srs.py`:

```python
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sample_dense_exclusive_srs import EXPECTED_INCLUSION_PROBABILITY, generate


def _make_dense_results(tmp_path: Path) -> Path:
    """Builds a synthetic dense-retrieval-results fixture matching the real
    file's shape: 11 Stratum A demands (was_bm25_zero_pool=True, 20
    dense_exclusive_new_unscored candidates each = 220), 19 Stratum B
    demands (was_bm25_zero_pool=False, varying counts summing to 333).
    Total 553, matching the real frozen population's invariants."""
    per_demand = {}
    for i in range(11):
        demand_id = f"A{i:03d}-2024"
        candidates = [
            {"publication_id": f"{demand_id}-pub{j}", "provenance": "dense_exclusive_new_unscored"}
            for j in range(20)
        ]
        # One already-scored candidate per demand, must be filtered out by provenance.
        candidates.append({"publication_id": f"{demand_id}-scored", "provenance": "bm25_gold_scored"})
        per_demand[demand_id] = {"was_bm25_zero_pool": True, "candidates": candidates}

    # 19 Stratum B demands, sizes summing to 333 (17 x 17 = 289, + 2 x 22 = 44 -> 333).
    b_sizes = [17] * 17 + [22, 22]
    assert sum(b_sizes) == 333
    for i, size in enumerate(b_sizes):
        demand_id = f"B{i:03d}-2024"
        candidates = [
            {"publication_id": f"{demand_id}-pub{j}", "provenance": "dense_exclusive_new_unscored"}
            for j in range(size)
        ]
        per_demand[demand_id] = {"was_bm25_zero_pool": False, "candidates": candidates}

    dense_results_path = tmp_path / "dense_results.json"
    dense_results_path.write_text(json.dumps({"per_demand": per_demand}), encoding="utf-8")
    return dense_results_path


def test_generate_selects_exactly_66_pairs(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    assert len(out["selected"]) == 66
    assert out["sample_size"] == 66


def test_generate_selected_pairs_have_no_duplicates(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    ids = [(row["demand_id"], row["publication_id"]) for row in out["selected"]]
    assert len(ids) == len(set(ids))


def test_generate_every_selected_pair_exists_in_population(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    dense = json.loads(dense_results_path.read_text(encoding="utf-8"))
    population_ids = set()
    for demand_id, v in dense["per_demand"].items():
        for c in v["candidates"]:
            if c["provenance"] == "dense_exclusive_new_unscored":
                population_ids.add((demand_id, c["publication_id"]))

    out = generate(dense_results_path, tmp_path / "manifest.json")
    for row in out["selected"]:
        assert (row["demand_id"], row["publication_id"]) in population_ids


def test_generate_excludes_already_scored_candidates(tmp_path):
    """The one 'bm25_gold_scored' candidate injected per Stratum A demand in
    the fixture must never appear in the population or the sample -- proves
    the provenance filter is applied, not just population size checked."""
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    for row in out["selected"]:
        assert not row["publication_id"].endswith("-scored")


def test_generate_is_deterministic_with_same_seed_and_population(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    first = generate(dense_results_path, tmp_path / "manifest1.json")
    second = generate(dense_results_path, tmp_path / "manifest2.json")
    assert first["selected"] == second["selected"]


def test_generate_records_correct_inclusion_probability_per_pair(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    assert out["inclusion_probability"] == EXPECTED_INCLUSION_PROBABILITY
    for row in out["selected"]:
        assert row["inclusion_probability"] == EXPECTED_INCLUSION_PROBABILITY


def test_generate_tags_each_selected_pair_with_correct_stratum(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    for row in out["selected"]:
        if row["demand_id"].startswith("A"):
            assert row["stratum"] == "A"
        else:
            assert row["stratum"] == "B"


def test_generate_reports_population_stratum_totals(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    assert out["population_size"] == 553
    assert out["n_stratum_a_population"] == 220
    assert out["n_stratum_b_population"] == 333


def test_generate_raises_on_wrong_stratum_a_demand_count(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    dense = json.loads(dense_results_path.read_text(encoding="utf-8"))
    # Flip one Stratum A demand to Stratum B, breaking the 11/19 invariant.
    first_a_key = next(k for k in dense["per_demand"] if k.startswith("A"))
    dense["per_demand"][first_a_key]["was_bm25_zero_pool"] = False
    dense_results_path.write_text(json.dumps(dense), encoding="utf-8")

    with pytest.raises(ValueError, match="Stratum A"):
        generate(dense_results_path, tmp_path / "manifest.json")


def test_generate_raises_on_duplicate_population_identity(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    dense = json.loads(dense_results_path.read_text(encoding="utf-8"))
    first_a_key = next(k for k in dense["per_demand"] if k.startswith("A"))
    # Duplicate the first candidate's publication_id within the same demand.
    dupe = dict(dense["per_demand"][first_a_key]["candidates"][0])
    dense["per_demand"][first_a_key]["candidates"].append(dupe)
    dense_results_path.write_text(json.dumps(dense), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        generate(dense_results_path, tmp_path / "manifest.json")


def test_generate_writes_manifest_file_and_sha256_sidecar(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out_path = tmp_path / "manifest.json"
    generate(dense_results_path, out_path)
    assert out_path.is_file()
    assert out_path.with_suffix(".sha256").is_file()

    import hashlib
    written_bytes = out_path.read_bytes()
    sidecar = out_path.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(written_bytes).hexdigest() == sidecar


def test_generate_does_not_write_any_annotation_file(tmp_path):
    """This script's job stops at the manifest -- no CSV or blind-export
    artifact must be created as a side effect."""
    dense_results_path = _make_dense_results(tmp_path)
    generate(dense_results_path, tmp_path / "manifest.json")
    csv_files = list(tmp_path.glob("*.csv"))
    assert csv_files == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd experiments/phase2 && python -m pytest test_sample_dense_exclusive_srs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sample_dense_exclusive_srs'`

- [ ] **Step 3: Write the implementation**

Create `experiments/phase2/sample_dense_exclusive_srs.py`:

```python
# experiments/phase2/sample_dense_exclusive_srs.py
"""Dense-exclusive sample, SRS redesign: manifest generation.

Per docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md.
Reads the frozen dense-retrieval results verbatim (no re-retrieval),
verifies the population/strata counts the design was frozen against, draws
a pure simple random sample (no allocation step), and writes a manifest --
this script does not decide any sampling parameter, it only consumes what
the spec already committed.

Supersedes experiments/phase2/sample_dense_exclusive_stratified.py
(deleted -- its stratum-proportional + equal-per-demand allocation is the
mechanism this redesign replaces).
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dense_exclusive_sampling import SAMPLING_SEED, simple_random_sample  # noqa: E402

EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256 = (
    "f9ddde0756830f07f88020efa562471ef3bedbe3b9785891e2bde0da1c469d60"
)

SAMPLE_SIZE = 66
POPULATION_SIZE = 553
EXPECTED_INCLUSION_PROBABILITY = SAMPLE_SIZE / POPULATION_SIZE

DECISION_RULE = {
    "p0": 14 / 108,
    "p1": 0.25,
    "alpha_one_sided": 0.05,
    "target_power": 0.80,
    "n": 66,
    "critical_c": 14,
    "actual_alpha": 0.0415,
    "achieved_power": 0.8013,
    "caveat": (
        "actual_alpha/achieved_power are the pre-specified design-stage operating "
        "characteristics for the exact one-sided binomial test, not a claim that the "
        "66 SRS-without-replacement draws are literally independent Bernoulli trials "
        "-- see design spec SS8 for the finite-population dependence disclosure."
    ),
}


def generate(dense_results_path: Path, out_path: Path) -> dict[str, Any]:
    raw_bytes = dense_results_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    dense = json.loads(raw_bytes.decode("utf-8"))

    stratum_by_demand: dict[str, str] = {}
    population: list[tuple[str, str]] = []
    n_stratum_a_demands = 0
    n_stratum_b_demands = 0
    for demand_id, v in dense["per_demand"].items():
        unscored = [
            c["publication_id"]
            for c in v["candidates"]
            if c["provenance"] == "dense_exclusive_new_unscored"
        ]
        stratum = "A" if v["was_bm25_zero_pool"] else "B"
        stratum_by_demand[demand_id] = stratum
        if stratum == "A":
            n_stratum_a_demands += 1
        else:
            n_stratum_b_demands += 1
        for publication_id in unscored:
            population.append((demand_id, publication_id))

    if len(population) != len(set(population)):
        raise ValueError(
            "Population contains duplicate (demand_id, publication_id) identities -- "
            "refusing to sample from a population with duplicate entries, which could "
            "let random.sample draw the same logical pair twice."
        )

    n_stratum_a_population = sum(1 for d, _ in population if stratum_by_demand[d] == "A")
    n_stratum_b_population = sum(1 for d, _ in population if stratum_by_demand[d] == "B")

    if n_stratum_a_demands != 11:
        raise ValueError(f"Expected 11 Stratum A demands, found {n_stratum_a_demands}")
    if n_stratum_b_demands != 19:
        raise ValueError(f"Expected 19 Stratum B demands, found {n_stratum_b_demands}")
    if n_stratum_a_population != 220:
        raise ValueError(f"Expected Stratum A population 220, found {n_stratum_a_population}")
    if n_stratum_b_population != 333:
        raise ValueError(f"Expected Stratum B population 333, found {n_stratum_b_population}")
    if len(population) != POPULATION_SIZE:
        raise ValueError(f"Expected total population {POPULATION_SIZE}, found {len(population)}")

    sample = simple_random_sample(population, n=SAMPLE_SIZE, seed=SAMPLING_SEED)

    selected_rows = [
        {
            "demand_id": demand_id,
            "publication_id": publication_id,
            "stratum": stratum_by_demand[demand_id],
            "inclusion_probability": EXPECTED_INCLUSION_PROBABILITY,
        }
        for demand_id, publication_id in sorted(sample)
    ]

    out = {
        "dataset_id": "nexus-phase2-ted-dense-exclusive-srs-sample-v1",
        "purpose": (
            "DUAL_ANNOTATION_POOL -- #104/#113 dense-exclusive SRS sample, "
            "docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md"
        ),
        "source_dense_retrieval_results_path": str(dense_results_path.resolve().relative_to(REPO_ROOT))
        if dense_results_path.resolve().is_relative_to(REPO_ROOT)
        else str(dense_results_path),
        "source_dense_retrieval_results_sha256": actual_sha256,
        "sampling_seed": SAMPLING_SEED,
        "population_size": len(population),
        "sample_size": len(sample),
        "inclusion_probability": EXPECTED_INCLUSION_PROBABILITY,
        "n_stratum_a_population": n_stratum_a_population,
        "n_stratum_b_population": n_stratum_b_population,
        "n_stratum_a_sampled": sum(1 for r in selected_rows if r["stratum"] == "A"),
        "n_stratum_b_sampled": sum(1 for r in selected_rows if r["stratum"] == "B"),
        "decision_rule": DECISION_RULE,
        "selected": selected_rows,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(
        f"Wrote {len(sample)} SRS-selected pairs "
        f"({out['n_stratum_a_sampled']} A / {out['n_stratum_b_sampled']} B, diagnostic split) "
        f"to {out_path}"
    )
    return out


def main() -> int:
    dense_results_path = REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_retrieval_results.json"
    actual_sha256 = hashlib.sha256(dense_results_path.read_bytes()).hexdigest()
    if actual_sha256 != EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256:
        raise ValueError(
            f"Source file hash mismatch: expected {EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256}, "
            f"got {actual_sha256}. This script must BLOCK rather than sample against data "
            "the design spec was not frozen against."
        )
    generate(
        dense_results_path=dense_results_path,
        out_path=REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_srs_sample_manifest.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd experiments/phase2 && python -m pytest test_sample_dense_exclusive_srs.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Run the full experiments/phase2 test directory to confirm no cross-test breakage**

Run: `cd experiments/phase2 && python -m pytest . -v`
Expected: all tests pass, including Task 1's `test_dense_exclusive_sampling.py` and every other pre-existing test file in this directory (unrelated to this plan, must be unaffected).

- [ ] **Step 6: Do NOT run `main()` or `generate()` against the real repo paths**

This step is a checkpoint, not a code change: confirm you have not, at any point in this task, called `python sample_dense_exclusive_srs.py` directly or otherwise invoked `main()`/`generate()` with the real `data/experiments/phase2_v4/...` and `data/annotations/...` paths. Only `tmp_path`-based synthetic fixtures are permitted in this plan's tests. If you ran it for real by mistake, `git status` will show a new/modified file under `data/annotations/ted_dense_exclusive_srs_sample_manifest.json` (or `.sha256`) -- if so, revert it (`git checkout -- <path>` or delete if untracked) before committing.

- [ ] **Step 7: Commit**

```bash
git add experiments/phase2/sample_dense_exclusive_srs.py experiments/phase2/test_sample_dense_exclusive_srs.py
git commit -m "feat(matching): SRS manifest generator for dense-exclusive sample

Replaces sample_dense_exclusive_stratified.py (deleted in the prior
commit). Reads the frozen dense-retrieval results, verifies population
invariants (553 total, 220 Stratum A / 333 Stratum B), draws a pure SRS
sample of 66 via dense_exclusive_sampling.simple_random_sample, tags each
selected pair with its stratum for diagnostics only, and records every
pair's inclusion probability (66/553) explicitly per
docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md SS7.

Tested against synthetic fixtures only -- no real draw performed. The real
draw is a separate, later, manual step gated on PR #112's TED
construct-validity gate resolving (spec SS6/SS9).

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-review notes (from the plan author, not a task to execute)

- **Spec coverage:** SS2 (pure SRS, no allocation) -> Task 1. SS3 (inclusion probability) -> Task 2's `EXPECTED_INCLUSION_PROBABILITY` and per-row recording, tested. SS4 (selection procedure: flat population, deterministic sort, single seeded draw, no allocation) -> Task 1 + Task 2. SS5 (stratum as diagnostics only) -> Task 2's stratum tagging + tests, never used to constrain the draw. SS6 (n/c/alpha/power unchanged, gated on population stability) -> `DECISION_RULE` carried forward unchanged in Task 2, Global Constraints' explicit no-real-draw rule. SS7 (deterministic sampler: population hash, seed, exact IDs, manifest with inclusion probabilities, no annotation files) -> Task 2's manifest fields and the dedicated no-annotation-file test. SS8 (disclosed limitations, SRS-without-replacement not literal independence) -> `DECISION_RULE["caveat"]` wording in Task 2, phrased per the explicit correction during design review. SS10 (required test coverage: exactly 66, no duplicates, all IDs in population, reproducible, correct inclusion probability, refuses to run against unfrozen population) -> all present in Task 2's test file; the "refuses to run against unfrozen population" requirement is satisfied by `main()`'s pre-existing hash check (unchanged from the old script) plus the spec SS7 correction that this is a forward-looking requirement for downstream consumers, not this script re-checking itself.
- **Placeholder scan:** none found.
- **Type consistency:** `simple_random_sample(population: list[tuple[str, str]], n: int, seed: int) -> list[tuple[str, str]]` used identically in Task 1's tests and Task 2's implementation. `generate(dense_results_path: Path, out_path: Path) -> dict[str, Any]` matches the old script's signature shape (intentional continuity) and Task 2's tests.
- **Ambiguity check:** the manifest's `source_dense_retrieval_results_path` field's relative-path computation guards against `dense_results_path` not being under `REPO_ROOT` (true in every test, since tests use `tmp_path`) by falling back to the absolute path -- resolved explicitly rather than left to raise on `relative_to()`, so tests don't need to fake being under the repo root.
