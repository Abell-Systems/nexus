# Minesoft Extraction Contract v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formalize the Minesoft Origin extraction acquisition contract as executable, tested Python
under `experiments/article/`, plus a retroactive read-only conformance audit of the already-frozen
v0.1 dataset.

**Architecture:** A pure, stdlib-only validation library (`validate_extraction_contract.py`) implements
every invariant as a small function returning `Finding` tuples. Two thin CLI scripts consume it: one
gates future extraction runs (hard-fail on any `FAIL`), one retroactively audits the frozen v0.1 CSVs
(read-only, writes a committed report, never fails on the expected `LEGACY_UNVERIFIABLE` findings).

**Tech Stack:** Python 3.12 stdlib only (`csv`, `hashlib`, `json`, `math`, `collections.namedtuple`,
`pathlib`, `sys`) — no pydantic, no pytest, no new dependency. Matches the existing convention in
`scripts/check_docs_correctness.py` and `experiments/wpi-demand-patent-matching/checks/*.py`.

**Spec:** `docs/superpowers/specs/2026-09-16-minesoft-extraction-contract-design.md`

## Global Constraints

- No new third-party dependency. Stdlib only.
- No modification to `experiments/article/minesoft_origin_2000_2025/` (frozen v0.1) anywhere in this
  plan — the audit script is strictly read-only against those files.
- Four-state verdict vocabulary is exactly `PASS` / `FAIL` / `NOT_APPLICABLE` / `LEGACY_UNVERIFIABLE` —
  no other verdict strings anywhere.
- `validate_extraction_contract.py` performs **no file I/O** — every function takes already-loaded
  Python data structures and returns `Finding` tuples. File reading/hashing lives in the two CLI
  scripts.
- No pytest. Tests are plain `assert` statements in `test_extraction_contract.py`, run via
  `python3 experiments/article/test_extraction_contract.py`.
- Every commit message credits Lydia Bares as co-author (per project CLAUDE.md) plus the session's
  Claude attribution lines (per system reminder).

---

### Task 1: Contract config JSON + sha256 sidecar

**Files:**
- Create: `experiments/article/config/extraction_contract_v1.json`
- Create: `experiments/article/config/extraction_contract_v1.sha256`

**Interfaces:**
- Produces: `CONTRACT_VERSION = "extraction_contract_v1"` — the string every later task checks the
  JSON's `contract_version` field against.

- [ ] **Step 1: Create the config directory and write the contract JSON**

```bash
mkdir -p /home/valentin/code/active/nexus/experiments/article/config
```

Write `experiments/article/config/extraction_contract_v1.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "contract_version": "extraction_contract_v1",
  "description": "Binding acquisition contract for Minesoft Origin extractions supporting the CEIMAR marine-policy article dataset. Governs future extraction runs; does not retroactively modify minesoft_origin_2000_2025 v0.1.",
  "layers": {
    "source": {
      "description": "Immutable, byte-for-byte Minesoft API responses, one artifact per page/call.",
      "required_fields": [
        "raw_response_path",
        "content_sha256",
        "endpoint",
        "query",
        "fl",
        "rows",
        "start",
        "compound_id",
        "extraction_run_id",
        "timestamp"
      ]
    },
    "extraction": {
      "description": "Deterministic, unfiltered (compound, publication_id) records derived from the source layer.",
      "dataset_unit": "compound_publication_id_pair",
      "uniqueness_scope": "per_compound",
      "required_fields": [
        "publication_id",
        "score",
        "compound",
        "capped",
        "total_hits_reported",
        "extraction_cap",
        "extraction_run_id",
        "page_number",
        "row_index"
      ]
    }
  },
  "pagination": {
    "required_mode": "sequential_single_run",
    "provider_index_stability": "unverified"
  }
}
```

- [ ] **Step 2: Compute and write the sha256 sidecar**

```bash
cd /home/valentin/code/active/nexus
python3 -c "
import hashlib
from pathlib import Path
p = Path('experiments/article/config/extraction_contract_v1.json')
Path('experiments/article/config/extraction_contract_v1.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest() + '\n')
"
cat experiments/article/config/extraction_contract_v1.sha256
```

Expected: a 64-character lowercase hex string.

- [ ] **Step 3: Verify the JSON parses and the hash matches**

```bash
cd /home/valentin/code/active/nexus
python3 -c "
import hashlib, json
from pathlib import Path
content = Path('experiments/article/config/extraction_contract_v1.json').read_bytes()
expected = Path('experiments/article/config/extraction_contract_v1.sha256').read_text().strip()
assert hashlib.sha256(content).hexdigest() == expected, 'hash mismatch'
data = json.loads(content)
assert data['contract_version'] == 'extraction_contract_v1'
print('OK')
"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /home/valentin/code/active/nexus
git add experiments/article/config/extraction_contract_v1.json experiments/article/config/extraction_contract_v1.sha256
git commit -m "$(cat <<'EOF'
feat(article): Minesoft extraction contract v1 config

Declares the required source-layer and extraction-layer fields, the
dataset unit (compound, publication_id pair, per-compound uniqueness),
and the required sequential-single-run pagination mode with a
disclosed provider-index-stability caveat. No behavior yet -- this is
the schema the validator in the next tasks checks against.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CNy86bSaG5PASgxekgkaHy
EOF
)"
```

---

### Task 2: Validator core — `Finding`, verdict constants, `evaluate_count_reconciliation`

**Files:**
- Create: `experiments/article/checks/validate_extraction_contract.py`
- Create: `experiments/article/test_extraction_contract.py`

**Interfaces:**
- Consumes: nothing (first code task).
- Produces:
  - `Finding = namedtuple("Finding", ["invariant", "verdict", "detail"])`
  - `PASS: str`, `FAIL: str`, `NOT_APPLICABLE: str`, `LEGACY_UNVERIFIABLE: str`
  - `evaluate_count_reconciliation(rows_extracted: int, unique_ids: int, total_hits_reported: int, capped: bool, extraction_cap: int | None) -> Finding`

- [ ] **Step 1: Write the failing test**

Create `experiments/article/test_extraction_contract.py`:

```python
"""Assert-based self-check for the Minesoft extraction contract validator.

No pytest -- run directly: python3 experiments/article/test_extraction_contract.py
Matches this repo's experiments/ convention (standalone check scripts, no test framework).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "checks"))

from validate_extraction_contract import (  # noqa: E402
    FAIL,
    PASS,
    evaluate_count_reconciliation,
)


def test_count_reconciliation_uncapped_pass():
    finding = evaluate_count_reconciliation(
        rows_extracted=2613, unique_ids=2613, total_hits_reported=2613,
        capped=False, extraction_cap=None,
    )
    assert finding.invariant == "count_reconciliation"
    assert finding.verdict == PASS


def test_count_reconciliation_uncapped_fail_brentuximab_shaped():
    # Shape of the historical Brentuximab bug: 2,612 rows saved against a declared 2,613 total.
    finding = evaluate_count_reconciliation(
        rows_extracted=2612, unique_ids=2612, total_hits_reported=2613,
        capped=False, extraction_cap=None,
    )
    assert finding.verdict == FAIL
    assert "2612" in finding.detail and "2613" in finding.detail


def test_count_reconciliation_capped_binding():
    # total_hits_reported (19075) >= extraction_cap (1000) -> cap_binding True, expects exactly 1000.
    finding = evaluate_count_reconciliation(
        rows_extracted=1000, unique_ids=1000, total_hits_reported=19075,
        capped=True, extraction_cap=1000,
    )
    assert finding.verdict == PASS
    assert "cap_binding=True" in finding.detail


def test_count_reconciliation_capped_not_binding():
    # total_hits_reported (731) < extraction_cap (1000) -> cap never binds, full population expected.
    finding = evaluate_count_reconciliation(
        rows_extracted=731, unique_ids=731, total_hits_reported=731,
        capped=True, extraction_cap=1000,
    )
    assert finding.verdict == PASS
    assert "cap_binding=False" in finding.detail


def test_count_reconciliation_capped_binding_rejects_partial_rows():
    # This is exactly the case the design review flagged: 731 rows against a 1000 cap with
    # total_hits_reported >= cap must FAIL, not be accepted as "<= cap".
    finding = evaluate_count_reconciliation(
        rows_extracted=731, unique_ids=731, total_hits_reported=19075,
        capped=True, extraction_cap=1000,
    )
    assert finding.verdict == FAIL


def test_count_reconciliation_capped_requires_declared_cap():
    finding = evaluate_count_reconciliation(
        rows_extracted=1000, unique_ids=1000, total_hits_reported=19075,
        capped=True, extraction_cap=None,
    )
    assert finding.verdict == FAIL
    assert "not declared" in finding.detail


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"\n{len(tests)} test(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: `ModuleNotFoundError: No module named 'validate_extraction_contract'` (the `checks/` package
doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

```bash
mkdir -p /home/valentin/code/active/nexus/experiments/article/checks
```

Create `experiments/article/checks/validate_extraction_contract.py`:

```python
"""Pure validation library for the Minesoft extraction contract (v1).

Every function here is pure: it takes already-loaded Python data and returns Finding tuples.
No file I/O, no network calls -- that lives in the CLI scripts (check_extraction_run.py,
audit_minesoft_origin_v0_1.py) that call into this module.
"""

import math
from collections import namedtuple

CONTRACT_VERSION = "extraction_contract_v1"

PASS = "PASS"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"
LEGACY_UNVERIFIABLE = "LEGACY_UNVERIFIABLE"

Finding = namedtuple("Finding", ["invariant", "verdict", "detail"])


def evaluate_count_reconciliation(
    rows_extracted: int,
    unique_ids: int,
    total_hits_reported: int,
    capped: bool,
    extraction_cap: int | None,
) -> Finding:
    """Dataset unit is (compound, publication_id); uniqueness is scoped per compound.

    Uncapped: rows_extracted and unique_ids must both equal total_hits_reported exactly.
    Capped: extraction_cap must be declared; the expected count is min(total_hits_reported,
    extraction_cap), and cap_binding records which bound actually applied.
    """
    if not capped:
        if rows_extracted == total_hits_reported and unique_ids == rows_extracted:
            return Finding(
                "count_reconciliation", PASS,
                f"rows_extracted={rows_extracted}, total_hits_reported={total_hits_reported}, "
                f"unique={unique_ids}",
            )
        return Finding(
            "count_reconciliation", FAIL,
            f"rows_extracted={rows_extracted}, unique={unique_ids} do not both equal "
            f"total_hits_reported={total_hits_reported} for an uncapped run",
        )

    if extraction_cap is None:
        return Finding("count_reconciliation", FAIL, "capped=True but extraction_cap was not declared")

    cap_binding = total_hits_reported >= extraction_cap
    expected = extraction_cap if cap_binding else total_hits_reported
    if rows_extracted == expected and unique_ids == rows_extracted:
        return Finding(
            "count_reconciliation", PASS,
            f"rows_extracted={rows_extracted}, expected={expected}, cap_binding={cap_binding}",
        )
    return Finding(
        "count_reconciliation", FAIL,
        f"rows_extracted={rows_extracted}, unique={unique_ids} do not both equal expected={expected} "
        f"(cap_binding={cap_binding})",
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: 6 `PASS:` lines, then `6 test(s) passed.`

- [ ] **Step 5: Commit**

```bash
cd /home/valentin/code/active/nexus
git add experiments/article/checks/validate_extraction_contract.py experiments/article/test_extraction_contract.py
git commit -m "$(cat <<'EOF'
feat(article): count-reconciliation invariant for Minesoft extraction contract

evaluate_count_reconciliation enforces exact rows==total_hits_reported
for uncapped runs and exact rows==min(total_hits_reported,cap) with a
recorded cap_binding for capped runs -- rejects a partial capped count
(e.g. 731/1000) that a looser "<=cap" check would have let through.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CNy86bSaG5PASgxekgkaHy
EOF
)"
```

---

### Task 3: Pagination invariants — `evaluate_pagination_completeness`, `evaluate_pagination_mode`

**Files:**
- Modify: `experiments/article/checks/validate_extraction_contract.py`
- Modify: `experiments/article/test_extraction_contract.py`

**Interfaces:**
- Consumes: `Finding`, `PASS`, `FAIL`, `NOT_APPLICABLE` from Task 2.
- Produces:
  - `evaluate_pagination_completeness(pages_extracted: int, total_hits_reported: int, page_size: int, capped: bool) -> Finding`
  - `evaluate_pagination_mode(pagination_mode: str) -> Finding`

- [ ] **Step 1: Write the failing tests**

Append to `experiments/article/test_extraction_contract.py` (add the import and the two test
functions; keep everything already there):

```python
from validate_extraction_contract import (  # noqa: E402
    FAIL,
    NOT_APPLICABLE,
    PASS,
    evaluate_count_reconciliation,
    evaluate_pagination_completeness,
    evaluate_pagination_mode,
)


def test_pagination_completeness_uncapped_pass():
    # 2613 hits at page_size=50 -> ceil(2613/50) = 53 pages.
    finding = evaluate_pagination_completeness(
        pages_extracted=53, total_hits_reported=2613, page_size=50, capped=False,
    )
    assert finding.verdict == PASS


def test_pagination_completeness_uncapped_fail():
    finding = evaluate_pagination_completeness(
        pages_extracted=52, total_hits_reported=2613, page_size=50, capped=False,
    )
    assert finding.verdict == FAIL


def test_pagination_completeness_capped_not_applicable():
    finding = evaluate_pagination_completeness(
        pages_extracted=20, total_hits_reported=19075, page_size=50, capped=True,
    )
    assert finding.verdict == NOT_APPLICABLE


def test_pagination_mode_pass():
    finding = evaluate_pagination_mode("sequential_single_run")
    assert finding.verdict == PASS


def test_pagination_mode_fail():
    finding = evaluate_pagination_mode("multi_session_resumable")
    assert finding.verdict == FAIL
```

(Replace the single-line `from validate_extraction_contract import (FAIL, PASS, evaluate_count_reconciliation)`
import block from Task 2 with the expanded one above — same module, more names.)

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: `ImportError: cannot import name 'evaluate_pagination_completeness'`

- [ ] **Step 3: Write minimal implementation**

Append to `experiments/article/checks/validate_extraction_contract.py`:

```python
def evaluate_pagination_completeness(
    pages_extracted: int,
    total_hits_reported: int,
    page_size: int,
    capped: bool,
) -> Finding:
    """Capped runs are not required to exhaust every page -- they stop at the cap by design."""
    if capped:
        return Finding(
            "pagination_completeness", NOT_APPLICABLE,
            "capped runs are not required to exhaust all pages",
        )
    expected_pages = math.ceil(total_hits_reported / page_size) if total_hits_reported else 0
    if pages_extracted == expected_pages:
        return Finding(
            "pagination_completeness", PASS,
            f"pages_extracted={pages_extracted}, expected={expected_pages}",
        )
    return Finding(
        "pagination_completeness", FAIL,
        f"pages_extracted={pages_extracted} != expected={expected_pages}",
    )


def evaluate_pagination_mode(pagination_mode: str) -> Finding:
    """The contract requires one continuous session per compound -- no pause/resume/restart."""
    if pagination_mode == "sequential_single_run":
        return Finding("pagination_mode", PASS, "pagination_mode == 'sequential_single_run'")
    return Finding(
        "pagination_mode", FAIL,
        f"pagination_mode={pagination_mode!r} != required 'sequential_single_run'",
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: 11 `PASS:` lines, then `11 test(s) passed.`

- [ ] **Step 5: Commit**

```bash
cd /home/valentin/code/active/nexus
git add experiments/article/checks/validate_extraction_contract.py experiments/article/test_extraction_contract.py
git commit -m "$(cat <<'EOF'
feat(article): pagination invariants for Minesoft extraction contract

evaluate_pagination_completeness checks pages_extracted against
ceil(total_hits/page_size) for uncapped runs (NOT_APPLICABLE for
capped, which stop early by design); evaluate_pagination_mode requires
sequential_single_run -- the contract's mitigation for provider-side
live-index drift, disclosed as a residual risk rather than eliminated.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CNy86bSaG5PASgxekgkaHy
EOF
)"
```

---

### Task 4: Source-layer invariants — `evaluate_raw_source_archive`, `evaluate_row_provenance`, `evaluate_future_run`

**Files:**
- Modify: `experiments/article/checks/validate_extraction_contract.py`
- Modify: `experiments/article/test_extraction_contract.py`

**Interfaces:**
- Consumes: `Finding`, `PASS`, `FAIL`, all `evaluate_*` functions from Tasks 2–3.
- Produces:
  - `evaluate_raw_source_archive(pages: list[dict], computed_hashes: dict[int, str] | None = None) -> Finding`
  - `evaluate_row_provenance(rows: list[dict], pages: list[dict], extraction_run_id: str) -> Finding`
  - `evaluate_future_run(run: dict, computed_hashes: dict[int, str] | None = None) -> list[Finding]` —
    the aggregate entry point `check_extraction_run.py` (Task 6) calls. `run` keys: `extraction_run_id`
    (str), `compound` (str), `capped` (bool), `extraction_cap` (int|None), `total_hits_reported` (int),
    `page_size` (int), `pagination_mode` (str), `pages` (list of page dicts, each with `page_number`,
    `raw_response_path`, `content_sha256`), `rows` (list of row dicts, each with `publication_id`,
    `extraction_run_id`, `page_number`, `row_index`).

- [ ] **Step 1: Write the failing tests**

Append to `experiments/article/test_extraction_contract.py`'s import block (extend it again) and add
new test functions:

```python
from validate_extraction_contract import (  # noqa: E402
    FAIL,
    NOT_APPLICABLE,
    PASS,
    evaluate_count_reconciliation,
    evaluate_future_run,
    evaluate_pagination_completeness,
    evaluate_pagination_mode,
    evaluate_raw_source_archive,
    evaluate_row_provenance,
)


def _sample_pages():
    return [
        {"page_number": 0, "raw_response_path": "raw/page_0.json", "content_sha256": "abc123"},
        {"page_number": 1, "raw_response_path": "raw/page_1.json", "content_sha256": "def456"},
    ]


def _sample_rows(run_id="run-1"):
    return [
        {"publication_id": "US-1-A1", "extraction_run_id": run_id, "page_number": 0, "row_index": 0},
        {"publication_id": "US-2-A1", "extraction_run_id": run_id, "page_number": 1, "row_index": 1},
    ]


def test_raw_source_archive_pass_structural():
    finding = evaluate_raw_source_archive(_sample_pages())
    assert finding.verdict == PASS


def test_raw_source_archive_fail_missing_field():
    pages = [{"page_number": 0, "raw_response_path": None, "content_sha256": None}]
    finding = evaluate_raw_source_archive(pages)
    assert finding.verdict == FAIL


def test_raw_source_archive_fail_no_pages():
    finding = evaluate_raw_source_archive([])
    assert finding.verdict == FAIL


def test_raw_source_archive_fail_hash_mismatch():
    finding = evaluate_raw_source_archive(_sample_pages(), computed_hashes={0: "abc123", 1: "WRONG"})
    assert finding.verdict == FAIL
    assert "page(s): [1]" in finding.detail


def test_raw_source_archive_pass_hash_match():
    finding = evaluate_raw_source_archive(_sample_pages(), computed_hashes={0: "abc123", 1: "def456"})
    assert finding.verdict == PASS


def test_row_provenance_pass():
    finding = evaluate_row_provenance(_sample_rows(), _sample_pages(), extraction_run_id="run-1")
    assert finding.verdict == PASS


def test_row_provenance_fail_wrong_run_id():
    finding = evaluate_row_provenance(_sample_rows(run_id="other-run"), _sample_pages(), extraction_run_id="run-1")
    assert finding.verdict == FAIL


def test_row_provenance_fail_dangling_page_pointer():
    rows = [{"publication_id": "US-1-A1", "extraction_run_id": "run-1", "page_number": 99, "row_index": 0}]
    finding = evaluate_row_provenance(rows, _sample_pages(), extraction_run_id="run-1")
    assert finding.verdict == FAIL


def test_evaluate_future_run_all_pass():
    run = {
        "extraction_run_id": "run-1",
        "compound": "Test_compound",
        "capped": False,
        "extraction_cap": None,
        "total_hits_reported": 2,
        "page_size": 1,
        "pagination_mode": "sequential_single_run",
        "pages": _sample_pages(),
        "rows": _sample_rows(),
    }
    findings = evaluate_future_run(run, computed_hashes={0: "abc123", 1: "def456"})
    invariants = {f.invariant: f.verdict for f in findings}
    assert invariants == {
        "raw_source_archive": PASS,
        "count_reconciliation": PASS,
        "pagination_completeness": PASS,
        "pagination_mode": PASS,
        "row_provenance": PASS,
    }
```

(Extend the existing import blocks from Tasks 2–3 into this single expanded one; don't duplicate
imports.)

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: `ImportError: cannot import name 'evaluate_raw_source_archive'`

- [ ] **Step 3: Write minimal implementation**

Append to `experiments/article/checks/validate_extraction_contract.py`:

```python
def evaluate_raw_source_archive(
    pages: list[dict],
    computed_hashes: dict[int, str] | None = None,
) -> Finding:
    """Structural check: every page declares raw_response_path + content_sha256.

    If computed_hashes is given (page_number -> actual sha256 of the file on disk, computed by the
    caller), also verifies each page's declared content_sha256 matches -- this function stays pure
    by taking the already-computed hashes rather than reading files itself.
    """
    if not pages:
        return Finding("raw_source_archive", FAIL, "no pages recorded")
    missing = [
        p["page_number"] for p in pages
        if not p.get("raw_response_path") or not p.get("content_sha256")
    ]
    if missing:
        return Finding(
            "raw_source_archive", FAIL,
            f"pages missing raw_response_path/content_sha256: {missing}",
        )
    if computed_hashes is not None:
        mismatched = [
            p["page_number"] for p in pages
            if computed_hashes.get(p["page_number"]) != p["content_sha256"]
        ]
        if mismatched:
            return Finding(
                "raw_source_archive", FAIL,
                f"content_sha256 mismatch for page(s): {mismatched}",
            )
    return Finding("raw_source_archive", PASS, f"{len(pages)} page(s) with verified raw archive")


def evaluate_row_provenance(
    rows: list[dict],
    pages: list[dict],
    extraction_run_id: str,
) -> Finding:
    """Every extraction-layer row must trace back to a recorded page in this same run."""
    page_numbers = {p["page_number"] for p in pages}
    bad = [
        r["row_index"] for r in rows
        if r.get("extraction_run_id") != extraction_run_id or r.get("page_number") not in page_numbers
    ]
    if bad:
        return Finding(
            "row_provenance", FAIL,
            f"row(s) with a bad run_id or dangling page_number back-pointer: {bad}",
        )
    return Finding(
        "row_provenance", PASS,
        f"{len(rows)} row(s) traceable to a recorded page and run_id={extraction_run_id!r}",
    )


def evaluate_future_run(
    run: dict,
    computed_hashes: dict[int, str] | None = None,
) -> list[Finding]:
    """Aggregate entry point for a FUTURE extraction run's full provenance bundle.

    `run` keys: extraction_run_id, compound, capped, extraction_cap, total_hits_reported, page_size,
    pagination_mode, pages (list of page dicts), rows (list of row dicts). See module docstring
    examples in test_extraction_contract.py for the exact shape.
    """
    rows = run["rows"]
    pages = run["pages"]
    rows_extracted = len(rows)
    unique_ids = len({r["publication_id"] for r in rows})
    return [
        evaluate_raw_source_archive(pages, computed_hashes=computed_hashes),
        evaluate_count_reconciliation(
            rows_extracted, unique_ids, run["total_hits_reported"], run["capped"], run.get("extraction_cap"),
        ),
        evaluate_pagination_completeness(len(pages), run["total_hits_reported"], run["page_size"], run["capped"]),
        evaluate_pagination_mode(run["pagination_mode"]),
        evaluate_row_provenance(rows, pages, run["extraction_run_id"]),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: 20 `PASS:` lines, then `20 test(s) passed.`

- [ ] **Step 5: Commit**

```bash
cd /home/valentin/code/active/nexus
git add experiments/article/checks/validate_extraction_contract.py experiments/article/test_extraction_contract.py
git commit -m "$(cat <<'EOF'
feat(article): raw-archive and provenance invariants + future-run aggregator

evaluate_raw_source_archive checks structural presence and (given
caller-computed hashes) integrity of every page's declared
content_sha256; evaluate_row_provenance requires every extraction row
to trace back to a recorded page in the same run.
evaluate_future_run(run, computed_hashes) is the single entry point
check_extraction_run.py will call for a future extraction's full
provenance bundle.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CNy86bSaG5PASgxekgkaHy
EOF
)"
```

---

### Task 5: Legacy audit invariants — `evaluate_query_documented_legacy`, `evaluate_legacy_compound`

**Files:**
- Modify: `experiments/article/checks/validate_extraction_contract.py`
- Modify: `experiments/article/test_extraction_contract.py`

**Interfaces:**
- Consumes: `Finding`, `PASS`, `FAIL`, `LEGACY_UNVERIFIABLE`, `evaluate_count_reconciliation` from
  earlier tasks.
- Produces:
  - `evaluate_query_documented_legacy(compound_display_name: str, readme_text: str) -> Finding`
  - `evaluate_legacy_compound(compound_display_name: str, rows: list[dict], capped: bool, total_hits_reported: int, readme_text: str) -> list[Finding]` —
    the entry point `audit_minesoft_origin_v0_1.py` (Task 7) calls once per compound CSV.
    `compound_display_name` is the space-separated form (e.g. `"Brentuximab vedotin"`), since that's
    how compound names appear in the README prose, not the underscored CSV `compound` column value.

- [ ] **Step 1: Write the failing tests**

Extend the import block once more and add:

```python
from validate_extraction_contract import (  # noqa: E402
    FAIL,
    LEGACY_UNVERIFIABLE,
    NOT_APPLICABLE,
    PASS,
    evaluate_count_reconciliation,
    evaluate_future_run,
    evaluate_legacy_compound,
    evaluate_pagination_completeness,
    evaluate_pagination_mode,
    evaluate_query_documented_legacy,
    evaluate_raw_source_archive,
    evaluate_row_provenance,
)


def test_query_documented_legacy_pass():
    readme = "## Per-compound counts\n\n| 01 | Brentuximab vedotin | 2,613 |"
    finding = evaluate_query_documented_legacy("Brentuximab vedotin", readme)
    assert finding.verdict == PASS


def test_query_documented_legacy_fail():
    readme = "## Per-compound counts\n\n| 01 | Trabectedin | 1,890 |"
    finding = evaluate_query_documented_legacy("Brentuximab vedotin", readme)
    assert finding.verdict == FAIL


def test_evaluate_legacy_compound_brentuximab_shaped():
    rows = [{"publication_id": f"US-{i}-A1"} for i in range(2613)]
    readme = "Brentuximab vedotin appears here"
    findings = evaluate_legacy_compound(
        "Brentuximab vedotin", rows, capped=False, total_hits_reported=2613, readme_text=readme,
    )
    by_invariant = {f.invariant: f.verdict for f in findings}
    assert by_invariant["count_reconciliation"] == PASS
    assert by_invariant["raw_source_archive"] == LEGACY_UNVERIFIABLE
    assert by_invariant["pagination_completeness"] == LEGACY_UNVERIFIABLE
    assert by_invariant["pagination_mode"] == LEGACY_UNVERIFIABLE
    assert by_invariant["query_documented_human_readable"] == PASS
    assert by_invariant["query_documented_machine_readable"] == LEGACY_UNVERIFIABLE


def test_evaluate_legacy_compound_capped_cytarabine_shaped():
    rows = [{"publication_id": f"US-{i}-A1"} for i in range(1000)]
    readme = "Cytarabine cap: only the first 1,000 results"
    findings = evaluate_legacy_compound(
        "Cytarabine", rows, capped=True, total_hits_reported=19075, readme_text=readme,
    )
    by_invariant = {f.invariant: f.verdict for f in findings}
    assert by_invariant["count_reconciliation"] == PASS
    count_finding = next(f for f in findings if f.invariant == "count_reconciliation")
    assert "inferred" in count_finding.detail
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: `ImportError: cannot import name 'evaluate_query_documented_legacy'`

- [ ] **Step 3: Write minimal implementation**

Append to `experiments/article/checks/validate_extraction_contract.py`:

```python
def evaluate_query_documented_legacy(compound_display_name: str, readme_text: str) -> Finding:
    """Real (not rubber-stamped) check: the compound's display name must actually appear in the
    README prose for this to count as documented -- not assumed true for every compound."""
    if compound_display_name in readme_text:
        return Finding(
            "query_documented_human_readable", PASS,
            f"README mentions compound {compound_display_name!r}",
        )
    return Finding(
        "query_documented_human_readable", FAIL,
        f"README does not mention compound {compound_display_name!r}",
    )


def evaluate_legacy_compound(
    compound_display_name: str,
    rows: list[dict],
    capped: bool,
    total_hits_reported: int,
    readme_text: str,
) -> list[Finding]:
    """Retroactive, read-only audit of one v0.1 compound CSV against the v1 contract.

    v0.1 never recorded a raw archive, page-level trace, session log, or a separately declared
    extraction_cap -- those invariants report LEGACY_UNVERIFIABLE, not FAIL, and are never
    backfilled. count_reconciliation IS checkable from the CSV's own columns (publication_id,
    capped, total_hits_reported) and is the one invariant that would have caught the historical
    Brentuximab under-count immediately.
    """
    rows_extracted = len(rows)
    unique_ids = len({r["publication_id"] for r in rows})
    extraction_cap = rows_extracted if capped else None

    count_finding = evaluate_count_reconciliation(
        rows_extracted, unique_ids, total_hits_reported, capped, extraction_cap,
    )
    if capped and count_finding.verdict == PASS:
        count_finding = Finding(
            "count_reconciliation", PASS,
            count_finding.detail + " (extraction_cap inferred as rows saved -- v0.1 does not "
            "record a separately declared cap)",
        )

    return [
        Finding("raw_source_archive", LEGACY_UNVERIFIABLE, "no raw API archive captured for this pass"),
        count_finding,
        Finding("pagination_completeness", LEGACY_UNVERIFIABLE, "no page-level trace recorded for this pass"),
        Finding("pagination_mode", LEGACY_UNVERIFIABLE, "no session log recorded for this pass"),
        evaluate_query_documented_legacy(compound_display_name, readme_text),
        Finding(
            "query_documented_machine_readable", LEGACY_UNVERIFIABLE,
            "no machine-readable request metadata (endpoint/params) captured for this pass",
        ),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: 24 `PASS:` lines, then `24 test(s) passed.`

- [ ] **Step 5: Commit**

```bash
cd /home/valentin/code/active/nexus
git add experiments/article/checks/validate_extraction_contract.py experiments/article/test_extraction_contract.py
git commit -m "$(cat <<'EOF'
feat(article): legacy-audit invariants for retroactive v0.1 conformance check

evaluate_legacy_compound audits one v0.1 CSV against the v1 contract
using only what the CSV itself contains (publication_id, capped,
total_hits_reported): count_reconciliation is checkable and PASSes for
the historical data, while raw-archive, page-trace, and session-log
invariants correctly report LEGACY_UNVERIFIABLE rather than an
invented PASS or an unfair FAIL against a pre-contract artifact.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CNy86bSaG5PASgxekgkaHy
EOF
)"
```

---

### Task 6: `checks/check_extraction_run.py` — CLI gate for future runs

**Files:**
- Create: `experiments/article/checks/check_extraction_run.py`
- Create (temp, deleted at end of step 2 below): a synthetic fixture bundle under
  `/tmp/claude-1000/.../scratchpad/` (your scratchpad directory) for the manual smoke test.

**Interfaces:**
- Consumes: `evaluate_future_run`, `Finding`, `PASS`, `FAIL`, `CONTRACT_VERSION` from
  `validate_extraction_contract.py`.
- Produces: a CLI, invoked as `python3 experiments/article/checks/check_extraction_run.py <bundle.json>`,
  exit code `0` if every finding is `PASS`/`NOT_APPLICABLE`, exit code `1` if any finding is `FAIL`.

This task has no pytest-style failing-test step (it's a CLI script, not a library function) — its
test is the manual smoke test in Step 2.

- [ ] **Step 1: Write the CLI script**

Create `experiments/article/checks/check_extraction_run.py`:

```python
#!/usr/bin/env python3
"""CLI gate for a FUTURE Minesoft extraction run against extraction_contract_v1.

Usage: python3 check_extraction_run.py <run_bundle.json>

<run_bundle.json> is a single JSON file describing one compound's extraction run:
{
  "extraction_run_id": "...", "compound": "...", "capped": false, "extraction_cap": null,
  "total_hits_reported": 1234, "page_size": 50, "pagination_mode": "sequential_single_run",
  "pages": [{"page_number": 0, "raw_response_path": "raw/page_0.json", "content_sha256": "<hex>", ...}],
  "rows": [{"publication_id": "...", "extraction_run_id": "...", "page_number": 0, "row_index": 0}]
}

raw_response_path in each page is resolved relative to the bundle file's own directory; this script
reads each referenced raw file and verifies its actual sha256 against the page's declared
content_sha256 (evaluate_future_run stays pure by taking these pre-computed hashes as input).

Hard-fails (non-zero exit) on any FAIL finding. Never patches, fills in, or silently accepts
missing/partial data.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_extraction_contract import CONTRACT_VERSION, FAIL, evaluate_future_run  # noqa: E402


def _compute_page_hashes(bundle_dir: Path, pages: list[dict]) -> dict[int, str]:
    hashes: dict[int, str] = {}
    for page in pages:
        raw_path = page.get("raw_response_path")
        if not raw_path:
            continue
        full_path = bundle_dir / raw_path
        if not full_path.is_file():
            continue
        hashes[page["page_number"]] = hashlib.sha256(full_path.read_bytes()).hexdigest()
    return hashes


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: check_extraction_run.py <run_bundle.json>", file=sys.stderr)
        return 2

    bundle_path = Path(argv[1]).resolve()
    if not bundle_path.is_file():
        print(f"Run bundle not found: {bundle_path}", file=sys.stderr)
        return 2

    run = json.loads(bundle_path.read_text(encoding="utf-8"))

    bundle_contract_version = run.get("contract_version", CONTRACT_VERSION)
    if bundle_contract_version != CONTRACT_VERSION:
        print(
            f"contract_version mismatch: bundle declares {bundle_contract_version!r}, "
            f"validator implements {CONTRACT_VERSION!r}",
            file=sys.stderr,
        )
        return 2

    computed_hashes = _compute_page_hashes(bundle_path.parent, run.get("pages", []))
    findings = evaluate_future_run(run, computed_hashes=computed_hashes)

    for finding in findings:
        print(f"{finding.invariant}: {finding.verdict} -- {finding.detail}")

    failures = [f for f in findings if f.verdict == FAIL]
    if failures:
        print(f"\n{len(failures)} invariant(s) FAILED. Run does not conform to {CONTRACT_VERSION}.", file=sys.stderr)
        return 1

    print(f"\nAll invariants satisfied for {CONTRACT_VERSION}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 2: Manual smoke test with a synthetic passing bundle**

Use your scratchpad directory for this throwaway fixture (do not commit it):

```bash
mkdir -p /tmp/claude-1000/-home-valentin-code-active-nexus/*/scratchpad/smoke_bundle/raw 2>/dev/null || true
SCRATCH=$(ls -d /tmp/claude-1000/-home-valentin-code-active-nexus/*/scratchpad 2>/dev/null | head -1)
mkdir -p "$SCRATCH/smoke_bundle/raw"
cd /home/valentin/code/active/nexus

python3 -c "
import hashlib, json
from pathlib import Path
bundle_dir = Path('$SCRATCH/smoke_bundle')
raw0 = bundle_dir / 'raw' / 'page_0.json'
raw0.write_text('{\"fake\": \"minesoft response\"}')
h0 = hashlib.sha256(raw0.read_bytes()).hexdigest()
bundle = {
    'contract_version': 'extraction_contract_v1',
    'extraction_run_id': 'smoke-test-run-1',
    'compound': 'Smoke_test_compound',
    'capped': False,
    'extraction_cap': None,
    'total_hits_reported': 1,
    'page_size': 50,
    'pagination_mode': 'sequential_single_run',
    'pages': [{'page_number': 0, 'raw_response_path': 'raw/page_0.json', 'content_sha256': h0}],
    'rows': [{'publication_id': 'US-1-A1', 'extraction_run_id': 'smoke-test-run-1', 'page_number': 0, 'row_index': 0}],
}
(bundle_dir / 'bundle.json').write_text(json.dumps(bundle))
"

python3 experiments/article/checks/check_extraction_run.py "$SCRATCH/smoke_bundle/bundle.json"
echo "exit code: $?"
```

Expected: 5 findings printed, all `PASS`, then `All invariants satisfied...`, `exit code: 0`.

Now verify the hard-fail path by corrupting the raw file's declared hash:

```bash
python3 -c "
import json
from pathlib import Path
bundle_path = Path('$SCRATCH/smoke_bundle/bundle.json')
bundle = json.loads(bundle_path.read_text())
bundle['pages'][0]['content_sha256'] = 'deadbeef'
bundle_path.write_text(json.dumps(bundle))
"
python3 experiments/article/checks/check_extraction_run.py "$SCRATCH/smoke_bundle/bundle.json"
echo "exit code: $?"
```

Expected: `raw_source_archive: FAIL -- content_sha256 mismatch for page(s): [0]`, exit code `1`.

Clean up the throwaway fixture:

```bash
rm -rf "$SCRATCH/smoke_bundle"
```

- [ ] **Step 3: Commit**

```bash
cd /home/valentin/code/active/nexus
git add experiments/article/checks/check_extraction_run.py
git commit -m "$(cat <<'EOF'
feat(article): CLI gate for future Minesoft extraction runs

check_extraction_run.py loads a run's provenance bundle, computes each
page's actual raw-file sha256, calls evaluate_future_run, prints every
finding, and hard-fails (non-zero exit) on any FAIL -- never patches
or silently accepts missing/partial data. Smoke-tested against a
synthetic passing bundle and a corrupted-hash failing bundle.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CNy86bSaG5PASgxekgkaHy
EOF
)"
```

---

### Task 7: `checks/audit_minesoft_origin_v0_1.py` — retroactive read-only audit

**Files:**
- Create: `experiments/article/checks/audit_minesoft_origin_v0_1.py`
- Create (generated by this script, committed): `experiments/article/audit/v0.1_conformance_report.json`

**Interfaces:**
- Consumes: `evaluate_legacy_compound`, `CONTRACT_VERSION` from `validate_extraction_contract.py`.
- Produces: `experiments/article/audit/v0.1_conformance_report.json`, read-only against
  `experiments/article/minesoft_origin_2000_2025/*.csv` and `.../README.md`.

- [ ] **Step 1: Write the CLI script**

Create `experiments/article/checks/audit_minesoft_origin_v0_1.py`:

```python
#!/usr/bin/env python3
"""Retroactive, read-only conformance audit of the frozen v0.1 Minesoft Origin extraction
(experiments/article/minesoft_origin_2000_2025/, commit c7bf50e) against extraction_contract_v1.

Never modifies the audited CSVs. Never regenerates or backfills missing evidence -- a
LEGACY_UNVERIFIABLE finding stays LEGACY_UNVERIFIABLE. Writes a baseline report, not a
certification: its purpose is to make legacy gaps explicit, not to declare v0.1 fully conformant
to a contract it predates.

Usage: python3 audit_minesoft_origin_v0_1.py
Writes: experiments/article/audit/v0.1_conformance_report.json
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_extraction_contract import CONTRACT_VERSION, evaluate_legacy_compound  # noqa: E402

ARTICLE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ARTICLE_DIR / "minesoft_origin_2000_2025"
AUDIT_DIR = ARTICLE_DIR / "audit"


def _compound_display_name(csv_filename: str) -> str:
    # e.g. "01_Brentuximab_vedotin_ids.csv" -> "Brentuximab vedotin"
    stem = csv_filename.removesuffix("_ids.csv")
    _, _, name_part = stem.partition("_")
    return name_part.replace("_", " ")


def _audit_one_csv(csv_path: Path, readme_text: str) -> dict:
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    capped = rows[0]["capped"] == "True"
    total_hits_reported = int(rows[0]["total_hits_reported"])
    compound_display_name = _compound_display_name(csv_path.name)

    findings = evaluate_legacy_compound(
        compound_display_name, rows, capped, total_hits_reported, readme_text,
    )
    return {
        "csv_file": csv_path.name,
        "compound": compound_display_name,
        "findings": [
            {"invariant": f.invariant, "verdict": f.verdict, "detail": f.detail} for f in findings
        ],
    }


def main() -> int:
    readme_text = (DATASET_DIR / "README.md").read_text(encoding="utf-8")
    csv_paths = sorted(DATASET_DIR.glob("*_ids.csv"))
    if not csv_paths:
        print(f"No CSV files found under {DATASET_DIR}", file=sys.stderr)
        return 1

    compounds = {}
    summary = {"PASS": 0, "FAIL": 0, "NOT_APPLICABLE": 0, "LEGACY_UNVERIFIABLE": 0}
    for csv_path in csv_paths:
        result = _audit_one_csv(csv_path, readme_text)
        compounds[result["compound"]] = result
        for finding in result["findings"]:
            summary[finding["verdict"]] += 1

    report = {
        "contract_version": CONTRACT_VERSION,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "minesoft_origin_2000_2025 v0.1 (frozen c7bf50e)",
        "note": (
            "Read-only retroactive baseline. LEGACY_UNVERIFIABLE findings are never backfilled -- "
            "this report documents what the v0.1 artifact can and cannot demonstrate against a "
            "contract it predates, not a certification of full conformance."
        ),
        "compounds": compounds,
        "summary": summary,
    }

    AUDIT_DIR.mkdir(exist_ok=True)
    report_path = AUDIT_DIR / "v0.1_conformance_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"Wrote {report_path}")
    print(f"Summary: {summary}")

    unexpected_fails = [
        (c, f) for c, result in compounds.items() for f in result["findings"]
        if f["verdict"] == "FAIL"
    ]
    if unexpected_fails:
        print(f"\n{len(unexpected_fails)} unexpected FAIL finding(s):", file=sys.stderr)
        for compound, finding in unexpected_fails:
            print(f"  {compound}: {finding['invariant']} -- {finding['detail']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the audit against the real frozen v0.1 dataset**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/checks/audit_minesoft_origin_v0_1.py
echo "exit code: $?"
```

Expected: `exit code: 0`, and a summary line whose `PASS` count is `24` (12 compounds ×
`count_reconciliation` PASS + `query_documented_human_readable` PASS), `LEGACY_UNVERIFIABLE` count is
`48` (12 compounds × 4: `raw_source_archive`, `pagination_completeness`, `pagination_mode`,
`query_documented_machine_readable`), `FAIL` count is `0`.

- [ ] **Step 3: Verify the report's per-compound content matches the spec's §6 table**

```bash
cd /home/valentin/code/active/nexus
python3 -c "
import json
report = json.loads(open('experiments/article/audit/v0.1_conformance_report.json').read())
brentuximab = report['compounds']['Brentuximab vedotin']
count = next(f for f in brentuximab['findings'] if f['invariant'] == 'count_reconciliation')
assert count['verdict'] == 'PASS', count
assert '2613' in count['detail'], count
cytarabine = report['compounds']['Cytarabine']
count = next(f for f in cytarabine['findings'] if f['invariant'] == 'count_reconciliation')
assert count['verdict'] == 'PASS', count
assert 'cap_binding=True' in count['detail'], count
assert 'inferred' in count['detail'], count
print('OK -- Brentuximab and Cytarabine match the spec table.')
"
```

Expected: `OK -- Brentuximab and Cytarabine match the spec table.`

- [ ] **Step 4: Commit**

```bash
cd /home/valentin/code/active/nexus
git add experiments/article/checks/audit_minesoft_origin_v0_1.py experiments/article/audit/v0.1_conformance_report.json
git commit -m "$(cat <<'EOF'
feat(article): retroactive read-only audit of frozen Minesoft v0.1

audit_minesoft_origin_v0_1.py evaluates all 12 minesoft_origin_2000_2025
CSVs against extraction_contract_v1 using only evidence the CSVs
themselves contain. count_reconciliation PASSes for all 12 (confirming
Brentuximab's post-repair 2,613/2,613 and Cytarabine's declared
1,000/19,075 cap); raw-archive, page-trace, and session-log invariants
correctly report LEGACY_UNVERIFIABLE rather than an invented PASS.
Committed report is a baseline, not a certification -- v0.1 itself is
untouched.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CNy86bSaG5PASgxekgkaHy
EOF
)"
```

---

### Task 8: Final verification pass

**Files:** none created/modified — this task only runs and checks existing artifacts.

- [ ] **Step 1: Run the full self-check suite**

```bash
cd /home/valentin/code/active/nexus
python3 experiments/article/test_extraction_contract.py
```

Expected: `24 test(s) passed.`

- [ ] **Step 2: Confirm `minesoft_origin_2000_2025/` was never modified**

```bash
cd /home/valentin/code/active/nexus
git log --oneline -- experiments/article/minesoft_origin_2000_2025/ | head -5
git diff c7bf50e -- experiments/article/minesoft_origin_2000_2025/
```

Expected: the `git log` output shows no new commits touching that directory since `c7bf50e`; the
`git diff` is empty.

- [ ] **Step 3: Re-run the audit script idempotency check**

```bash
cd /home/valentin/code/active/nexus
cp experiments/article/audit/v0.1_conformance_report.json /tmp/report_before.json
python3 experiments/article/checks/audit_minesoft_origin_v0_1.py
python3 -c "
import json
before = json.load(open('/tmp/report_before.json'))
after = json.load(open('experiments/article/audit/v0.1_conformance_report.json'))
before.pop('audited_at'); after.pop('audited_at')
assert before == after, 'audit report is not deterministic (ignoring the timestamp)'
print('OK -- audit is deterministic.')
"
rm /tmp/report_before.json
```

Expected: `OK -- audit is deterministic.`

- [ ] **Step 4: Verify the sha256 sidecar still matches after all commits**

```bash
cd /home/valentin/code/active/nexus
python3 -c "
import hashlib
from pathlib import Path
content = Path('experiments/article/config/extraction_contract_v1.json').read_bytes()
expected = Path('experiments/article/config/extraction_contract_v1.sha256').read_text().strip()
assert hashlib.sha256(content).hexdigest() == expected
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Final commit (if step 3's re-run produced a diff only in `audited_at`, no commit
      needed; if the working tree is otherwise clean, this step is a no-op — confirm with `git status`)**

```bash
cd /home/valentin/code/active/nexus
git status --short
```

Expected: clean (the re-run in Step 3 wrote back an identical file except for `audited_at`, and Step 3
didn't `git add`/commit that diff — leave the committed report from Task 7 as the canonical one; do
not commit the Step 3 re-run's output).

---

## Plan Self-Review

**Spec coverage:**
- §2 layout → Task 1 (config), Task 2/4/6 (checks/), Task 7 (audit/), Task 2 (test file). ✅
- §3 three-layer model + raw≠unfiltered → Task 1 (JSON schema fields), Task 4 (`evaluate_raw_source_archive`
  vs `evaluate_count_reconciliation`/extraction-layer checks keep the two properties separate). ✅
- §4 run identity/immutability → `extraction_run_id` threaded through `evaluate_row_provenance` and
  the run bundle schema in Task 6. ✅ (No code enforces "never overwrite a prior run" as a mechanical
  check — that's a process/convention discipline, not a checkable invariant against a single bundle;
  noted here rather than silently dropped.)
- §5.1/5.2 count reconciliation + cap semantics → Task 2, including the exact "731/1000 against a
  binding cap must FAIL" case the design review flagged. ✅
- §5.3 pagination consistency → Task 3 (`evaluate_pagination_completeness`, `evaluate_pagination_mode`). ✅
- §5.4 declared residual risk → JSON's `provider_index_stability: "unverified"` field (Task 1); the
  validator does not claim to eliminate drift, only checks the mitigating `pagination_mode`. ✅
- §6 retroactive audit + 4-state vocabulary → Task 5 (`evaluate_legacy_compound`), Task 7 (CLI +
  committed report), with the exact expected-verdict table from spec §6 verified in Task 7 Step 3. ✅
- §7 tooling/error handling (pure validator, hard-fail CLI, no CI) → Task 2's module docstring, Task 6's
  hard-fail exit code, no workflow file created anywhere in this plan. ✅
- §8 testing scenarios (5 fixtures) → covered across Tasks 2–5's test functions (uncapped pass/fail,
  capped binding/non-binding/partial-rejection, raw-archive-missing legacy vs future). ✅
- §9 out of scope → correctly nothing in this plan touches enrichment, family-dedup, or CI wiring. ✅

**Placeholder scan:** No "TBD"/"TODO"/"implement later" found. Every step has runnable code or an
exact shell command with expected output.

**Type consistency:** `Finding` (namedtuple with `.invariant`/`.verdict`/`.detail`) is used identically
across Tasks 2–7. `evaluate_future_run(run, computed_hashes=None)` and `evaluate_legacy_compound(...)`
signatures match their call sites in Tasks 6 and 7 respectively. `CONTRACT_VERSION` is defined once
(Task 2) and consumed by both CLI scripts (Tasks 6, 7) and the JSON config (Task 1) without drift.

---

Plan complete and saved to `docs/superpowers/plans/2026-09-16-minesoft-extraction-contract.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
