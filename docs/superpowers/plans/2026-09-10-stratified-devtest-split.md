# Stratified Dev/Test Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a generic, seeded, stratified Dev/Test split mechanism in `backend/src`, then freeze the WPI Phase 2 Dev/Test partition of the 13 sector-covered demands (#92) as a content-addressed experiment artifact.

**Architecture:** `application.evaluation.stratified_split.stratified_split()` implements a domain-agnostic allocation-policy-with-feasibility-floor algorithm over generic `Sequence[T]`, returning a `StratifiedSplitResult` (`domain.models.evaluation`) that wraps two deliberately distinct frozen types, `DevPartition` and `TestPartition`. `experiments/wpi-demand-patent-matching/` supplies the WPI-specific parameters (input artifact, `dev_fraction=0.40`, `seed=42`, `stratum_key=sector_code`) and freezes the result as `data/devtest_split_n13_v1.json`.

**Tech Stack:** Python, pydantic (existing `BaseModel`/`ConfigDict(frozen=True)` convention), stdlib `random.Random` for seeded shuffling — no new dependency.

**Spec:** `docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md`

## Global Constraints

- `backend/src/main` must never contain a WPI sector name, the literal `13`/`N=13`, or a hardcoded `dev_fraction`/`seed` default value — `dev_fraction` and `seed` are always caller-supplied, with no default in `stratified_split()`'s signature (spec, "Architecture"; review requirement on the `0.40` example).
- Round-half-up is defined exactly as $d_s = \lfloor \text{dev\_fraction} \cdot n_s + 0.5 \rfloor$ — never Python's `round()` (banker's rounding).
- Feasibility floor: $n_s = 1$ → all of it to Test (dev count 0); $n_s \ge 2$ → apply the formula above, then if the result is `0` set it to `1`, if the result equals `n_s` set it to `n_s - 1`.
- Within a stratum, items are sorted by `item_id` before the seeded shuffle, so the result is independent of the input list's iteration order.
- `DevPartition` and `TestPartition` are separate pydantic types (not two fields users could swap) — this is the no-leakage-as-interface-property requirement from #79's review.
- `stratum_key(item)` returning `None`/`""` for any item, or a duplicate `item_id` across `items`, raises `ValueError` at the boundary before any allocation runs.
- Every new/modified file ends with the tests for it passing (`pytest <path> -v`) before moving to the next task.

---

## Task 1: Domain models — `DevPartition`, `TestPartition`, `StratifiedSplitResult`

**Files:**
- Modify: `backend/src/main/domain/models/evaluation.py` (append new classes at end of file)
- Test: `backend/test/unit/domain/test_devtest_partition.py`

**Interfaces:**
- Produces: `DevPartition(demand_ids: tuple[str, ...])`, `TestPartition(demand_ids: tuple[str, ...])`, `StratifiedSplitResult(dev: DevPartition, test: TestPartition, per_stratum_counts: dict[str, dict[str, int]])` — all pydantic `BaseModel`, `ConfigDict(frozen=True)`, importable as `from domain.models.evaluation import DevPartition, TestPartition, StratifiedSplitResult`.

- [ ] **Step 1: Write the failing tests**

Create `backend/test/unit/domain/test_devtest_partition.py`:

```python
"""Tests for DevPartition/TestPartition/StratifiedSplitResult (#79).

DevPartition and TestPartition are deliberately distinct types -- not two fields
on one class -- so a future consumer's constructor can type-hint one and be
statically/structurally unable to accept the other. See
docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md.
"""

import pytest
from pydantic import ValidationError

from domain.models.evaluation import DevPartition, StratifiedSplitResult, TestPartition


def test_dev_partition_holds_demand_ids():
    p = DevPartition(demand_ids=("A", "B"))
    assert p.demand_ids == ("A", "B")


def test_test_partition_holds_demand_ids():
    p = TestPartition(demand_ids=("C", "D"))
    assert p.demand_ids == ("C", "D")


def test_dev_partition_is_frozen():
    p = DevPartition(demand_ids=("A",))
    with pytest.raises(ValidationError):
        p.demand_ids = ("B",)


def test_dev_partition_rejects_empty():
    with pytest.raises(ValidationError):
        DevPartition(demand_ids=())


def test_dev_partition_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        DevPartition(demand_ids=("A", "A"))


def test_test_partition_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        TestPartition(demand_ids=("A", "A"))


def test_dev_partition_and_test_partition_are_distinct_types():
    dev = DevPartition(demand_ids=("A",))
    test = TestPartition(demand_ids=("A",))
    assert type(dev) is not type(test)
    assert not isinstance(dev, TestPartition)
    assert not isinstance(test, DevPartition)


def test_stratified_split_result_wraps_both_partitions_and_counts():
    result = StratifiedSplitResult(
        dev=DevPartition(demand_ids=("A",)),
        test=TestPartition(demand_ids=("B", "C")),
        per_stratum_counts={"SECTOR_X": {"dev": 1, "test": 2}},
    )
    assert result.dev.demand_ids == ("A",)
    assert result.test.demand_ids == ("B", "C")
    assert result.per_stratum_counts == {"SECTOR_X": {"dev": 1, "test": 2}}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest backend/test/unit/domain/test_devtest_partition.py -v`
Expected: FAIL/ERROR — `ImportError: cannot import name 'DevPartition' from 'domain.models.evaluation'`

- [ ] **Step 3: Implement the models**

Append to `backend/src/main/domain/models/evaluation.py` (the file already imports `BaseModel, ConfigDict, Field, field_validator` at the top — reuse those, do not re-import):

```python
class DevPartition(BaseModel):
    """Frozen membership set for a Development split (protocol §3 D_dev). A future
    tuning component (ADR 0016 alpha/beta/gamma grid search) must be constructible
    only from this type -- never from TestPartition or an undivided corpus -- so
    that no-leakage is an interface property, not only a test (see
    docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md).
    """

    model_config = ConfigDict(frozen=True)

    demand_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("demand_ids")
    @classmethod
    def validate_unique(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if len(v) != len(set(v)):
            raise ValueError("DevPartition.demand_ids must not contain duplicates")
        return v


class TestPartition(BaseModel):
    """Mirror of DevPartition for the Test split (protocol §3 D_test)."""

    model_config = ConfigDict(frozen=True)

    demand_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("demand_ids")
    @classmethod
    def validate_unique(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if len(v) != len(set(v)):
            raise ValueError("TestPartition.demand_ids must not contain duplicates")
        return v


class StratifiedSplitResult(BaseModel):
    """Return type of application.evaluation.stratified_split.stratified_split().
    Exists only to carry the algorithm's output and to be frozen to a content-
    addressed artifact -- a future consumer must be constructed from .dev / .test
    individually, never from this whole object.
    """

    model_config = ConfigDict(frozen=True)

    dev: DevPartition
    test: TestPartition
    per_stratum_counts: dict[str, dict[str, int]]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest backend/test/unit/domain/test_devtest_partition.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/domain/models/evaluation.py backend/test/unit/domain/test_devtest_partition.py
git commit -m "feat(domain): add DevPartition/TestPartition/StratifiedSplitResult (#79)"
```

---

## Task 2: `stratified_split()` — input contract and validation

**Files:**
- Create: `backend/src/main/application/evaluation/stratified_split.py`
- Test: `backend/test/unit/application/evaluation/test_stratified_split.py`

**Interfaces:**
- Consumes: `DevPartition`, `TestPartition`, `StratifiedSplitResult` from Task 1 (`domain.models.evaluation`).
- Produces: `stratified_split(items: Sequence[T], stratum_key: Callable[[T], str | None], item_id: Callable[[T], str], dev_fraction: float, seed: int) -> StratifiedSplitResult`, importable as `from application.evaluation.stratified_split import stratified_split`. Task 3 adds the allocation logic to the same function; this task establishes its signature and boundary validation.

- [ ] **Step 1: Write the failing contract tests**

Create `backend/test/unit/application/evaluation/test_stratified_split.py`:

```python
"""Tests for the generic stratified Dev/Test split (#79).

Synthetic strata only -- this function is domain-agnostic (ADR 0026): no WPI
sector name, no real demand_id, no experiment-specific fraction/seed appears
here. See docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md.
"""

import inspect

import pytest

from application.evaluation.stratified_split import stratified_split


class _Item:
    def __init__(self, item_id: str, stratum: str | None):
        self.item_id = item_id
        self.stratum = stratum


def _sk(item: _Item) -> str | None:
    return item.stratum


def _iid(item: _Item) -> str:
    return item.item_id


def test_rejects_empty_items():
    with pytest.raises(ValueError, match="items must not be empty"):
        stratified_split([], stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


@pytest.mark.parametrize("bad_fraction", [0.0, 1.0, -0.1, 1.1])
def test_rejects_dev_fraction_out_of_range(bad_fraction):
    items = [_Item("A", "S1"), _Item("B", "S1")]
    with pytest.raises(ValueError, match="dev_fraction"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=bad_fraction, seed=1)


def test_rejects_non_int_seed():
    items = [_Item("A", "S1"), _Item("B", "S1")]
    with pytest.raises(ValueError, match="seed"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1.5)


def test_rejects_duplicate_item_id():
    items = [_Item("A", "S1"), _Item("A", "S2")]
    with pytest.raises(ValueError, match="item_id values must be unique"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


def test_rejects_none_stratum_key():
    items = [_Item("A", "S1"), _Item("B", None)]
    with pytest.raises(ValueError, match="stratum_key returned"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


def test_rejects_empty_string_stratum_key():
    items = [_Item("A", "S1"), _Item("B", "")]
    with pytest.raises(ValueError, match="stratum_key returned"):
        stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)


def test_dev_fraction_and_seed_have_no_default_value():
    """Structural guard (not a source-text regex): dev_fraction/seed must always
    come from the caller, never a backend-side default -- the #79 review's
    'verifiable prohibition' on hardcoding 0.40 in the mechanism."""
    sig = inspect.signature(stratified_split)
    assert sig.parameters["dev_fraction"].default is inspect.Parameter.empty
    assert sig.parameters["seed"].default is inspect.Parameter.empty
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest backend/test/unit/application/evaluation/test_stratified_split.py -v`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'application.evaluation.stratified_split'`

- [ ] **Step 3: Implement the validation boundary**

Create `backend/src/main/application/evaluation/stratified_split.py`:

```python
"""Generic stratified Dev/Test split with a feasibility-floor allocation policy.

Implements the algorithm fixed by docs/superpowers/specs/
2026-09-10-stratified-devtest-split-design.md. Domain-agnostic (ADR 0026): callers
supply the stratum key, the item id, the target Dev fraction, and the seed --
nothing here assumes a WPI sector name, a specific N, or a specific fraction/seed
value. dev_fraction and seed have no default value by design (see that spec's
"Architecture" section) so a caller cannot silently inherit a backend-side default.
"""

import random
from collections.abc import Callable, Sequence
from typing import TypeVar

from domain.models.evaluation import DevPartition, StratifiedSplitResult, TestPartition

T = TypeVar("T")


def stratified_split(
    items: Sequence[T],
    stratum_key: Callable[[T], str | None],
    item_id: Callable[[T], str],
    dev_fraction: float,
    seed: int,
) -> StratifiedSplitResult:
    if not items:
        raise ValueError("stratified_split: items must not be empty")
    if not (0.0 < dev_fraction < 1.0):
        raise ValueError(f"stratified_split: dev_fraction must be in (0, 1), got {dev_fraction!r}")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"stratified_split: seed must be an int, got {seed!r}")

    ids = [item_id(item) for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("stratified_split: item_id values must be unique across items")

    strata: dict[str, list[T]] = {}
    for item in items:
        key = stratum_key(item)
        if not key:
            raise ValueError(
                f"stratified_split: stratum_key returned {key!r} for "
                f"item_id={item_id(item)!r} -- a missing/empty stratum key is not permitted"
            )
        strata.setdefault(key, []).append(item)

    raise NotImplementedError("allocation policy implemented in Task 3")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest backend/test/unit/application/evaluation/test_stratified_split.py -v`
Expected: 9 passed (empty items; 4x bad `dev_fraction` by parametrization; non-int seed; duplicate `item_id`; `None` stratum key; empty-string stratum key; no-default signature)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/application/evaluation/stratified_split.py backend/test/unit/application/evaluation/test_stratified_split.py
git commit -m "feat(application): stratified_split input contract + validation (#79)"
```

---

## Task 3: `stratified_split()` — allocation policy and full behavior

**Files:**
- Modify: `backend/src/main/application/evaluation/stratified_split.py` (replace the `raise NotImplementedError` line with the allocation loop)
- Modify: `backend/test/unit/application/evaluation/test_stratified_split.py` (append allocation tests)

**Interfaces:**
- Produces: `stratified_split()` now fully functional, returning a real `StratifiedSplitResult`.

- [ ] **Step 1: Write the failing allocation tests**

Append to `backend/test/unit/application/evaluation/test_stratified_split.py`:

```python
def _make_stratum(prefix: str, n: int) -> list[_Item]:
    return [_Item(f"{prefix}{i}", prefix) for i in range(n)]


@pytest.mark.parametrize(
    "n,expected_dev,expected_test",
    [(1, 0, 1), (2, 1, 1), (3, 1, 2), (4, 2, 2), (5, 2, 3), (10, 4, 6)],
)
def test_floor_policy_table_at_dev_fraction_040(n, expected_dev, expected_test):
    items = _make_stratum("S", n)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)
    assert result.per_stratum_counts["S"] == {"dev": expected_dev, "test": expected_test}
    assert len(result.dev.demand_ids) == expected_dev
    assert len(result.test.demand_ids) == expected_test


def test_floor_bumps_zero_dev_up_to_one():
    """dev_fraction=0.1, n=2: formula alone gives floor(0.2+0.5)=0. Floor must bump to 1."""
    items = _make_stratum("S", 2)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.1, seed=1)
    assert result.per_stratum_counts["S"] == {"dev": 1, "test": 1}


def test_floor_reduces_full_dev_down_to_n_minus_one():
    """dev_fraction=0.9, n=2: formula alone gives floor(1.8+0.5)=2=n. Floor must reduce to 1."""
    items = _make_stratum("S", 2)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.9, seed=1)
    assert result.per_stratum_counts["S"] == {"dev": 1, "test": 1}


def test_no_overlap_and_exact_union_across_multiple_strata():
    items = _make_stratum("A", 3) + _make_stratum("B", 4) + _make_stratum("C", 1)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=7)
    dev = set(result.dev.demand_ids)
    test = set(result.test.demand_ids)
    all_ids = {i.item_id for i in items}
    assert dev & test == set()
    assert dev | test == all_ids
    assert len(dev) + len(test) == len(items)


def test_deterministic_for_same_seed():
    items = _make_stratum("A", 5) + _make_stratum("B", 4)
    r1 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=99)
    r2 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=99)
    assert r1.dev.demand_ids == r2.dev.demand_ids
    assert r1.test.demand_ids == r2.test.demand_ids


def test_different_seed_changes_membership():
    items = _make_stratum("A", 4)
    r1 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)
    r2 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=2)
    assert r1.dev.demand_ids != r2.dev.demand_ids


def test_result_independent_of_input_order():
    items = _make_stratum("A", 5) + _make_stratum("B", 4)
    reversed_items = list(reversed(items))
    r1 = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=13)
    r2 = stratified_split(reversed_items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=13)
    assert r1.dev.demand_ids == r2.dev.demand_ids
    assert r1.test.demand_ids == r2.test.demand_ids


def test_dev_and_test_are_distinct_partition_types_on_real_result():
    from domain.models.evaluation import DevPartition, TestPartition

    items = _make_stratum("A", 3)
    result = stratified_split(items, stratum_key=_sk, item_id=_iid, dev_fraction=0.4, seed=1)
    assert isinstance(result.dev, DevPartition)
    assert isinstance(result.test, TestPartition)
    assert not isinstance(result.dev, TestPartition)
```

- [ ] **Step 2: Run the tests to verify the new ones fail**

Run: `pytest backend/test/unit/application/evaluation/test_stratified_split.py -v`
Expected: the Task 2 tests still pass; every new allocation test FAILs with `NotImplementedError: allocation policy implemented in Task 3`

- [ ] **Step 3: Implement the allocation policy**

In `backend/src/main/application/evaluation/stratified_split.py`, replace the final line
`raise NotImplementedError("allocation policy implemented in Task 3")` with:

```python
    dev_ids: list[str] = []
    test_ids: list[str] = []
    per_stratum_counts: dict[str, dict[str, int]] = {}

    for stratum, members in strata.items():
        n_s = len(members)
        ordered = sorted(members, key=item_id)

        if n_s == 1:
            dev_count = 0
        else:
            dev_count = int(dev_fraction * n_s + 0.5)  # round-half-up: floor(x + 0.5)
            if dev_count == 0:
                dev_count = 1
            elif dev_count == n_s:
                dev_count = n_s - 1

        rng = random.Random(seed)
        shuffled = ordered[:]
        rng.shuffle(shuffled)

        stratum_dev = shuffled[:dev_count]
        stratum_test = shuffled[dev_count:]

        dev_ids.extend(item_id(i) for i in stratum_dev)
        test_ids.extend(item_id(i) for i in stratum_test)
        per_stratum_counts[stratum] = {"dev": len(stratum_dev), "test": len(stratum_test)}

    return StratifiedSplitResult(
        dev=DevPartition(demand_ids=tuple(sorted(dev_ids))),
        test=TestPartition(demand_ids=tuple(sorted(test_ids))),
        per_stratum_counts=per_stratum_counts,
    )
```

- [ ] **Step 4: Run the full test file to verify everything passes**

Run: `pytest backend/test/unit/application/evaluation/test_stratified_split.py -v`
Expected: all tests pass (validation tests from Task 2 + all allocation tests from this task)

- [ ] **Step 5: Run the full backend suite to check for regressions**

Run: `pytest backend/test -q`
Expected: no new failures (pre-existing suite size grows by the tests added in Tasks 1-3 only)

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/application/evaluation/stratified_split.py backend/test/unit/application/evaluation/test_stratified_split.py
git commit -m "feat(application): stratified_split allocation policy with feasibility floor (#79)"
```

---

## Task 4: Experiment config + RED check (`check_devtest_split.py`)

**Files:**
- Create: `experiments/wpi-demand-patent-matching/config/devtest_split_v1.json`
- Create: `experiments/wpi-demand-patent-matching/config/devtest_split_v1.sha256`
- Create: `experiments/wpi-demand-patent-matching/checks/check_devtest_split.py`

**Interfaces:**
- Consumes: `experiments/wpi-demand-patent-matching/data/sector_assignments_n24_v1.json` (its `assignments` list only — the 13 sector-covered demands, #92), the config file this task creates.
- Produces: the check script other tasks (and CI, eventually) run to validate `data/devtest_split_n13_v1.json`, which Task 5 creates. Intentionally RED at the end of this task — that file does not exist yet.

- [ ] **Step 1: Compute the assignments artifact's sha256 and write the config**

Run: `sha256sum experiments/wpi-demand-patent-matching/data/sector_assignments_n24_v1.json`
Expected output: `634ada0a3be36bc46c4b603c18efc21625cfb1609feee10f4df3d00ecef22916  ...` (this is the already-frozen #92 artifact — confirm the hash matches before using it; if it doesn't, the corpus changed and this plan's later steps must be re-derived from the actual current hash, not this one).

Create `experiments/wpi-demand-patent-matching/config/devtest_split_v1.json`:

```json
{
  "config_id": "phase2_devtest_split_v1",
  "dev_fraction": 0.4,
  "seed": 42,
  "stratum_key": "sector_code",
  "assignments_path": "experiments/wpi-demand-patent-matching/data/sector_assignments_n24_v1.json",
  "assignments_sha256": "634ada0a3be36bc46c4b603c18efc21625cfb1609feee10f4df3d00ecef22916"
}
```

- [ ] **Step 2: Write its sha256 sidecar**

Run:
```bash
cd experiments/wpi-demand-patent-matching/config
sha256sum devtest_split_v1.json | awk '{print $1"  devtest_split_v1.json"}' > devtest_split_v1.sha256
cd -
```

- [ ] **Step 3: Write the check script (will fail — no artifact yet)**

Create `experiments/wpi-demand-patent-matching/checks/check_devtest_split.py`:

```python
#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 Dev/Test split artifact (#79).

Verifies devtest_split_n13_v1.json against sector_assignments_n24_v1.json (#92) and
devtest_split_v1.json (this experiment's config), per docs/superpowers/specs/
2026-09-10-stratified-devtest-split-design.md. The population is exactly the 13
`assignments` entries -- the 11 `no_sector_coverage` entries (#90/#91) must never
appear in dev or test.

Intentionally RED right now: devtest_split_n13_v1.json does not exist yet.
"""

import hashlib
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

ASSIGNMENTS_NAME = "sector_assignments_n24_v1.json"
ASSIGNMENTS_SHA_NAME = "sector_assignments_n24_v1.sha256"
CONFIG_NAME = "devtest_split_v1.json"
CONFIG_SHA_NAME = "devtest_split_v1.sha256"
SPLIT_NAME = "devtest_split_n13_v1.json"
SPLIT_SHA_NAME = "devtest_split_n13_v1.sha256"
SPLIT_MANIFEST_NAME = "devtest_split_n13_v1.manifest.json"

# Expected floor-policy outcome for this run's real per-stratum sizes
# ({1: ENERGY_STORAGE, 2: SANITARY_MATERIALS, 3: METALLURGY, 3: INDUSTRIAL_MACHINERY_IOT,
# 4: BIOTECHNOLOGY}) at dev_fraction=0.40 -- see the plan/spec's floor-policy table.
EXPECTED_STRATUM_SIZE_TO_DEV_TEST = {1: (0, 1), 2: (1, 1), 3: (1, 2), 4: (2, 2)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    assignments_sha = _verify_sidecar(DATA_DIR / ASSIGNMENTS_NAME, DATA_DIR / ASSIGNMENTS_SHA_NAME)
    config_sha = _verify_sidecar(CONFIG_DIR / CONFIG_NAME, CONFIG_DIR / CONFIG_SHA_NAME)
    split_sha = _verify_sidecar(DATA_DIR / SPLIT_NAME, DATA_DIR / SPLIT_SHA_NAME)

    config = json.loads((CONFIG_DIR / CONFIG_NAME).read_text(encoding="utf-8"))
    assert config["assignments_sha256"] == assignments_sha, (
        "devtest_split_v1.json's pinned assignments_sha256 no longer matches "
        "sector_assignments_n24_v1.json -- that input changed underneath this config."
    )

    assignments = json.loads((DATA_DIR / ASSIGNMENTS_NAME).read_text(encoding="utf-8"))
    covered = {a["demand_id"]: a["sector_code"] for a in assignments["assignments"]}
    no_coverage_ids = {e["demand_id"] for e in assignments["no_sector_coverage"]}

    split = json.loads((DATA_DIR / SPLIT_NAME).read_text(encoding="utf-8"))
    manifest = json.loads((DATA_DIR / SPLIT_MANIFEST_NAME).read_text(encoding="utf-8"))

    assert manifest["content_sha256"] == split_sha
    assert manifest["derived_from"]["assignments_sha256"] == assignments_sha
    assert manifest["derived_from"]["config_sha256"] == config_sha

    dev_ids = split["dev"]
    test_ids = split["test"]

    assert len(dev_ids) == len(set(dev_ids)), "Duplicate demand_id in dev"
    assert len(test_ids) == len(set(test_ids)), "Duplicate demand_id in test"
    assert not (set(dev_ids) & set(test_ids)), "A demand_id appears in both dev and test"
    assert set(dev_ids) | set(test_ids) == set(covered), (
        f"dev + test do not cover exactly the 13 sector-covered demand_ids "
        f"(missing={set(covered) - (set(dev_ids) | set(test_ids))}, "
        f"extra={(set(dev_ids) | set(test_ids)) - set(covered)})"
    )
    assert not (set(dev_ids) & no_coverage_ids), "A no_sector_coverage demand_id leaked into dev"
    assert not (set(test_ids) & no_coverage_ids), "A no_sector_coverage demand_id leaked into test"

    per_stratum: dict[str, dict[str, int]] = {}
    for demand_id, sector in covered.items():
        side = "dev" if demand_id in dev_ids else "test"
        per_stratum.setdefault(sector, {"dev": 0, "test": 0})[side] += 1

    stratum_sizes: dict[str, int] = {}
    for sector in covered.values():
        stratum_sizes[sector] = stratum_sizes.get(sector, 0) + 1

    for sector, size in stratum_sizes.items():
        expected_dev, expected_test = EXPECTED_STRATUM_SIZE_TO_DEV_TEST[size]
        actual = per_stratum[sector]
        assert (actual["dev"], actual["test"]) == (expected_dev, expected_test), (
            f"{sector} (n={size}): expected dev/test={expected_dev}/{expected_test}, "
            f"got {actual['dev']}/{actual['test']}"
        )

    assert manifest["per_stratum_counts"] == per_stratum

    print(f"OK: dev={len(dev_ids)} test={len(test_ids)} per_stratum={per_stratum}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the check to confirm it is RED**

Run: `python experiments/wpi-demand-patent-matching/checks/check_devtest_split.py`
Expected: exit code 1, `FileNotFoundError` for `devtest_split_n13_v1.json`

- [ ] **Step 5: Commit**

```bash
git add experiments/wpi-demand-patent-matching/config/devtest_split_v1.json \
        experiments/wpi-demand-patent-matching/config/devtest_split_v1.sha256 \
        experiments/wpi-demand-patent-matching/checks/check_devtest_split.py
git commit -m "test(lab): devtest split config + RED check (#79)"
```

---

## Task 5: `generate_devtest_split.py` — freeze the artifact

**Files:**
- Create: `experiments/wpi-demand-patent-matching/checks/generate_devtest_split.py`
- Produces (generated, not hand-written): `experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.json`, `.sha256`, `.manifest.json`

**Interfaces:**
- Consumes: `stratified_split()` from Task 3 (`application.evaluation.stratified_split`), the config from Task 4.
- Produces: the frozen split artifact `check_devtest_split.py` (Task 4) validates.

- [ ] **Step 1: Write the generator**

Create `experiments/wpi-demand-patent-matching/checks/generate_devtest_split.py`:

```python
#!/usr/bin/env python3
"""Instantiates the generic stratified_split() mechanism (backend/src/main/
application/evaluation/stratified_split.py) against the WPI Phase 2 sector
assignments (#92), per experiments/wpi-demand-patent-matching/config/devtest_split_v1.json
and docs/superpowers/specs/2026-09-10-stratified-devtest-split-design.md.

Reads only sector_assignments_n24_v1.json's `assignments` list (the 13
sector-covered demands) -- `no_sector_coverage` is never read for membership.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.evaluation.stratified_split import stratified_split  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

ASSIGNMENTS_NAME = "sector_assignments_n24_v1.json"
ASSIGNMENTS_SHA_NAME = "sector_assignments_n24_v1.sha256"
CONFIG_NAME = "devtest_split_v1.json"
CONFIG_SHA_NAME = "devtest_split_v1.sha256"
SPLIT_NAME = "devtest_split_n13_v1.json"
SPLIT_SHA_NAME = "devtest_split_n13_v1.sha256"
SPLIT_MANIFEST_NAME = "devtest_split_n13_v1.manifest.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sidecar(artifact_path: Path, sidecar_path: Path) -> str:
    computed = _sha256_file(artifact_path)
    declared_sha, declared_name = sidecar_path.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == computed, f"{artifact_path.name}: bytes do not match {sidecar_path.name}"
    assert declared_name == artifact_path.name
    return computed


def main() -> int:
    assignments_sha = _verify_sidecar(DATA_DIR / ASSIGNMENTS_NAME, DATA_DIR / ASSIGNMENTS_SHA_NAME)
    config_sha = _verify_sidecar(CONFIG_DIR / CONFIG_NAME, CONFIG_DIR / CONFIG_SHA_NAME)

    config = json.loads((CONFIG_DIR / CONFIG_NAME).read_text(encoding="utf-8"))
    assert config["assignments_sha256"] == assignments_sha, "config's pinned input hash is stale"

    assignments = json.loads((DATA_DIR / ASSIGNMENTS_NAME).read_text(encoding="utf-8"))
    covered = assignments["assignments"]  # the 13 -- no_sector_coverage deliberately unused

    result = stratified_split(
        covered,
        stratum_key=lambda a: a["sector_code"],
        item_id=lambda a: a["demand_id"],
        dev_fraction=config["dev_fraction"],
        seed=config["seed"],
    )

    split_dataset = {
        "dataset_id": "nexus-phase2-devtest-split-n13-v1",
        "dev": list(result.dev.demand_ids),
        "test": list(result.test.demand_ids),
    }

    split_path = DATA_DIR / SPLIT_NAME
    split_path.write_text(json.dumps(split_dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    split_sha = _sha256_file(split_path)

    manifest = {
        "dev_count": len(result.dev.demand_ids),
        "test_count": len(result.test.demand_ids),
        "per_stratum_counts": result.per_stratum_counts,
        "content_sha256": split_sha,
        "derived_from": {
            "assignments_sha256": assignments_sha,
            "config_sha256": config_sha,
        },
    }
    (DATA_DIR / SPLIT_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (DATA_DIR / SPLIT_SHA_NAME).write_text(f"{split_sha}  {SPLIT_NAME}\n", encoding="utf-8")

    print(
        f"Wrote dev={len(result.dev.demand_ids)} test={len(result.test.demand_ids)} "
        f"-> {split_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the generator**

Run: `python experiments/wpi-demand-patent-matching/checks/generate_devtest_split.py`

Expected per-stratum breakdown, from the real #92 sizes (METALLURGY n=3, BIOTECHNOLOGY
n=4, INDUSTRIAL_MACHINERY_IOT n=3, ENERGY_STORAGE n=1, SANITARY_MATERIALS n=2) against
the floor-policy table: `1/2, 2/2, 1/2, 0/1, 1/1` (dev/test) respectively — dev total
`1+2+1+0+1=5`, test total `2+2+2+1+1=8`.

Expected output: `Wrote dev=5 test=8 -> .../devtest_split_n13_v1.json`

If the printed counts differ from `dev=5 test=8`, treat that as a signal that the real
`sector_assignments_n24_v1.json` no longer has the per-stratum sizes assumed here —
recheck it (`python3 -c "import json; d=json.load(open('experiments/wpi-demand-patent-matching/data/sector_assignments_n24_v1.json')); from collections import Counter; print(Counter(a['sector_code'] for a in d['assignments']))"`)
before proceeding, rather than editing `check_devtest_split.py`'s
`EXPECTED_STRATUM_SIZE_TO_DEV_TEST` table to match whatever came out.

- [ ] **Step 3: Run the check to confirm it is now GREEN**

Run: `python experiments/wpi-demand-patent-matching/checks/check_devtest_split.py`
Expected: exit code 0, `OK: dev=5 test=8 per_stratum=...`

- [ ] **Step 4: Verify determinism — regenerate and diff**

Run:
```bash
cp experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.json /tmp/run1_split.json
cp experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.manifest.json /tmp/run1_manifest.json
python experiments/wpi-demand-patent-matching/checks/generate_devtest_split.py
diff /tmp/run1_split.json experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.json
diff /tmp/run1_manifest.json experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.manifest.json
```
Expected: both `diff`s produce no output (byte-identical)

- [ ] **Step 5: Verify no `no_sector_coverage` id leaked in, by hand**

Run:
```bash
python3 -c "
import json
split = json.load(open('experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.json'))
assignments = json.load(open('experiments/wpi-demand-patent-matching/data/sector_assignments_n24_v1.json'))
no_cov = {e['demand_id'] for e in assignments['no_sector_coverage']}
leaked = (set(split['dev']) | set(split['test'])) & no_cov
assert not leaked, leaked
print('OK: no no_sector_coverage id in dev or test')
"
```
Expected: `OK: no no_sector_coverage id in dev or test`

- [ ] **Step 6: Run the full backend suite and ruff, to check for regressions**

Run: `pytest backend/test -q && ruff check experiments/wpi-demand-patent-matching/checks/generate_devtest_split.py experiments/wpi-demand-patent-matching/checks/check_devtest_split.py`
Expected: all backend tests pass; ruff reports no issues

- [ ] **Step 7: Commit**

```bash
git add experiments/wpi-demand-patent-matching/checks/generate_devtest_split.py \
        experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.json \
        experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.sha256 \
        experiments/wpi-demand-patent-matching/data/devtest_split_n13_v1.manifest.json
git commit -m "data(lab): freeze Phase 2 Dev/Test split (#79)"
```

---

## After all tasks: open the PR

Follow the same pattern as #88/#89/#91/#92: push the branch, open a PR summarizing the generic mechanism (backend) and the frozen instantiation (experiment) separately in the PR body, note the exact dev/test counts and per-stratum table, and flag explicitly that #79 unblocks ADR 0016 next (not implemented here) and that `DevPartition`/`TestPartition` are the only types a future tuning/confirmatory-evaluation component may accept.
