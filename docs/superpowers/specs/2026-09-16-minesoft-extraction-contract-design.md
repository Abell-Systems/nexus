# Design Specification — Minesoft Extraction Contract v1

**Document ID:** `SPEC-2026-09-16-MINESOFT-EXTRACTION-CONTRACT`
**Status:** Approved by User (Brainstorming Phase Complete)
**Date:** 2026-09-16
**Authors:** Valentín Liñeiro; Claude Sonnet 5
**Binding Directives:** ADR 0026 (experiment/domain boundary)
**Scope:** `experiments/article/` (CEIMAR marine-policy article support data), not `backend/` — this is an
acquisition contract for article-support datasets, not a Nexus product or scientific-track contract.

---

## 1. Executive Summary & Problem Statement

`experiments/article/minesoft_origin_2000_2025/` (frozen v0.1, commit `c7bf50e`) is a 12-compound,
IDs-only Minesoft Origin extraction produced by informal practice: manual pagination, manual
transcription into CSV, no raw-response archive, no machine-readable provenance. That informal
practice already produced two real findings that a formal contract should have caught mechanically
rather than by manual diff:

1. **Brentuximab vedotin** lost 1 of 2,613 publication IDs to a manual-transcription error, only
   caught by an independent re-pull + `comm -23` diff against the stored CSV.
2. **Cytarabine** required an ad hoc, undocumented-until-now decision (cap at 1,000 of 19,075 hits,
   sorted by relevance) with no structural place in the dataset to record cap semantics.

Two further extraction runs are coming (Minesoft enrichment via `bulk_publications`, pending Lydia's
geographic-scope and Cytarabine decisions — tracked separately, out of scope here). Before those run,
this spec formalizes the acquisition contract those runs must satisfy, and retroactively audits v0.1
against it as a read-only baseline.

### Golden Rule
> **This contract governs how future Minesoft extractions are acquired and verified. It does not
> modify, regenerate, or retrofit `minesoft_origin_2000_2025/` v0.1, which remains frozen exactly as
> committed in `c7bf50e`.**

---

## 2. Layout

Extends the existing `experiments/article/` directory (the frozen v0.1 data stays where it is — no
migration to a fresh `experiments/<paper-slug>/` directory, since that would churn git history for no
contract-relevant reason):

```text
experiments/article/
├── config/
│   ├── extraction_contract_v1.json
│   └── extraction_contract_v1.sha256
├── checks/
│   ├── validate_extraction_contract.py   # importable validation library, pure functions, no I/O
│   ├── check_extraction_run.py           # CLI gate for a FUTURE extraction run's provenance bundle
│   └── audit_minesoft_origin_v0_1.py     # CLI, retroactive read-only audit of frozen v0.1
├── audit/
│   └── v0.1_conformance_report.json      # committed output of the audit script
├── test_extraction_contract.py           # assert-based self-check against synthetic fixtures
└── minesoft_origin_2000_2025/            # untouched, unmodified
```

No `tests/` subpackage, no pytest — matches this repo's existing convention for `experiments/`
check scripts (see `experiments/wpi-demand-patent-matching/checks/*.py`, `scripts/check_docs_correctness.py`):
standalone scripts with assertions and process exit codes.

---

## 3. Three-Layer Data Model

```text
contract v1
│
├── source layer      — immutable Minesoft responses + request metadata + hashes
│
├── extraction layer  — deterministic, unfiltered (compound, publication_id) records
│
└── derived layer      — explicitly OUTSIDE this contract (enrichment, dedup, filtering)
```

**Raw ≠ unfiltered.** These are two independent properties:
- *Raw* = source-faithful and untransformed (a provenance/reproducibility property of the **source
  layer**).
- *Unfiltered* = no relevance-based selection applied (a property of the **extraction layer**).
  Conflating them was the mistake v0.1 made informally: its CSVs are unfiltered, but they are not raw.

### 3.1 Source layer
One immutable artifact per API call/page:
- `raw_response`: the exact Minesoft API response body, byte-for-byte, never mutated after capture.
- `request_metadata` (sidecar, not merged into the response body): `endpoint`, `query`, `fl`, `rows`,
  `start`, `compound_id`, `extraction_run_id`, `timestamp`.
- `content_sha256`: hash of `raw_response` bytes, for tamper/integrity verification.

### 3.2 Extraction layer
Dataset unit = one `(compound, publication_id)` pair, deterministically derived from the source layer.
Fields per record:
- `publication_id`, `score`, `compound`, `capped`, `total_hits_reported`, `extraction_cap` (nullable),
  `extraction_run_id`, `page_number` (back-pointer into the source layer), `row_index`.

Global `publication_id` uniqueness is **not** required — the same patent can legitimately surface
under multiple compound queries. Uniqueness is enforced **per compound**:
`unique(publication_id | compound=c) == rows_extracted(compound=c)`.

### 3.3 Derived layer
Enrichment (`bulk_publications`), family-level dedup, jurisdiction filtering — explicitly out of this
contract's scope. Governed by whatever contract that later work defines; this spec does not
anticipate it.

---

## 4. Run Identity & Immutability

Every extraction run gets a stable identity, never reused:

```text
extraction_run_id   — unique per run (e.g. ISO-date + compound + sequence)
contract_version     — "extraction_contract_v1"
compound_id
```

All raw files and derived rows for a run carry `extraction_run_id`. **Re-extracting a compound never
overwrites a prior run's artifacts** — a new run gets a new `extraction_run_id`, a new raw bundle, and
a new derived artifact. This directly enables the Brentuximab-style repair pattern going forward:
compare two runs' artifacts explicitly, rather than mutating one in place.

---

## 5. Pagination & Count-Reconciliation Invariants (hard-fail)

### 5.1 Uncapped (`capped == false`)
```text
rows_extracted(compound=c)        == total_hits_reported(compound=c)
unique(publication_id | compound=c) == rows_extracted(compound=c)
pages_extracted(compound=c)       == ceil(total_hits_reported(compound=c) / page_size)
```
where `rows_extracted` means **extraction-layer records for that compound**, not raw API rows — the
raw response may carry nested/metadata content that isn't itself an extraction record.

This is precisely the check that would have caught Brentuximab's 2,612/2,613 gap immediately, with no
independent re-pull needed.

### 5.2 Capped (`capped == true`)
```text
extraction_cap is declared before the first API call for this run
extraction stops at min(total_hits_reported, extraction_cap)

if total_hits_reported >= extraction_cap:
    rows_extracted == extraction_cap
    cap_binding == true
else:
    rows_extracted == total_hits_reported
    cap_binding == false
```
This closes the gap your review flagged: `rows_extracted <= cap` alone would let a truncated 731/1,000
run pass silently. The contract requires exact equality against whichever bound actually applies, and
records which one did (`cap_binding`).

### 5.3 Pagination consistency
```text
pagination_consistency.mode = "sequential_single_run"
```
required: one continuous session, fixed query/params, pages pulled sequentially, no
pause/resume/restart. Per-page trace recorded: `page_number`, `offset`, `requested_page_size`,
`returned_rows`, `first_publication_id`, `last_publication_id`.

### 5.4 Declared residual risk — not eliminated
```text
pagination_consistency.provider_index_stability = "unverified"
```
Carried as a **permanent caveat** in every run's provenance record. Sequential single-run pagination,
count reconciliation, and per-compound dedup **reduce** exposure to live-index drift (the same failure
mode documented for INVENES: results reordering between pages/sessions) but do **not** mathematically
eliminate it — a mid-run reorder can, in principle, swap one record for another and still leave
`unique == total_hits` passing. The contract states this explicitly rather than implying a guarantee
it cannot make:

> We constrain our acquisition procedure to sequential single-run pagination, while provider-side
> index stability remains unverified.

---

## 6. Retroactive v0.1 Audit

Four-state vocabulary per invariant: `PASS` / `FAIL` / `NOT_APPLICABLE` / `LEGACY_UNVERIFIABLE`. One
vocabulary — no separate "LEGACY_UNAVAILABLE" state; a missing raw archive is reported as
`LEGACY_UNVERIFIABLE` like any other invariant the historical artifact cannot provide evidence for.
**The audit never regenerates or backfills v0.1's missing evidence** — a `LEGACY_UNVERIFIABLE` finding
stays `LEGACY_UNVERIFIABLE` permanently; re-pulling the raw layer after the fact would be a new
acquisition, not a historical record, and would contaminate the baseline.

Expected output per compound, computed from what v0.1's CSVs actually contain
(`publication_id`, `score`, `compound`, `capped`, `total_hits_reported`):

| Invariant | Expected verdict | Why |
|---|---|---|
| `raw_source_archive` present | `LEGACY_UNVERIFIABLE` (all 12) | No raw JSON was kept for this pass |
| `count_reconciliation` (rows==total_hits, unique==rows) | `PASS` (all 12, post-repair) | CSV columns are sufficient evidence; this is the exact check that catches Brentuximab-shaped gaps |
| `pages_extracted == pages_expected` | `LEGACY_UNVERIFIABLE` (all 12) | No page-level trace recorded |
| `pagination_consistency.mode` | `LEGACY_UNVERIFIABLE` (all 12) | No session log |
| Query documented (human-readable) | `PASS` (all 12) | README documents the exact query per compound |
| Query documented (machine-readable request metadata) | `LEGACY_UNVERIFIABLE` (all 12) | Not captured in this pass |
| Cap semantics (Cytarabine only) | `PASS` | `total_hits_reported=19075`, `extraction_cap` implicitly 1,000, `cap_binding=true`, all recorded in the CSV |

The committed `audit/v0.1_conformance_report.json` is a **baseline record**, not a certification —
its purpose is to make legacy gaps explicit rather than silently assume v0.1 satisfies a contract it
predates.

---

## 7. Tooling & Error Handling

- `validate_extraction_contract.py`: pure functions (no file I/O), take parsed structures, return a
  list of `(invariant_id, verdict, detail)` tuples. Deterministic — same input always produces the
  same verdicts.
- `check_extraction_run.py`: CLI. Loads a future run's raw bundle + extraction-layer output, calls the
  validator, **hard-fails** (non-zero exit, prints every violated invariant) on any violation. Never
  silently accepts partial data, never patches or fills in gaps — mirrors this repo's existing
  `scripts/check_docs_correctness.py` convention.
- `audit_minesoft_origin_v0_1.py`: CLI, read-only, writes `audit/v0.1_conformance_report.json`. Does
  not exit non-zero on `LEGACY_UNVERIFIABLE` findings (expected for a pre-contract artifact) — only on
  an unexpected `FAIL` (e.g. if `count_reconciliation` regressed from what §6 predicts).
- **Not wired into CI.** This is a post-acquisition gate against an external provider response bundle;
  CI cannot reproduce a live Minesoft extraction. `validate_extraction_contract.py` is pure and
  deterministic, so its synthetic-fixture tests (`test_extraction_contract.py`) *can* run in CI later
  without making live extraction a CI dependency — deferred, not designed against.

---

## 8. Testing

`test_extraction_contract.py`: assert-based self-check (`if __name__ == "__main__":`), no pytest,
against synthetic fixture bundles:
1. A passing uncapped run.
2. A Brentuximab-shaped uncapped run (rows_extracted 1 short of total_hits_reported) — must `FAIL`
   `count_reconciliation`.
3. A capped run where `total_hits_reported >= extraction_cap` — must require `rows_extracted ==
   extraction_cap`, `cap_binding == true`.
4. A capped run where `total_hits_reported < extraction_cap` — must require `rows_extracted ==
   total_hits_reported`, `cap_binding == false`.
5. A run missing its raw-archive bundle — must report `LEGACY_UNVERIFIABLE`, not `FAIL`, since the
   distinction only applies to legacy (pre-contract) runs; a *future* run missing its raw archive
   should `FAIL` instead — the fixture set covers both cases to keep this distinction from collapsing.

---

## 9. Out of Scope

- Minesoft enrichment (`bulk_publications`) contract — a separate, later spec once Lydia's two
  decisions (geographic scope, Cytarabine exhaustive-vs-capped) land.
- Family-level dedup contract.
- Any modification to `minesoft_origin_2000_2025/` v0.1.
- CI wiring (deferred, see §7).
