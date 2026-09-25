# Phase 2 #102 TED Multidimensional Independence Audit & #103 Freeze — Closure

**Status:** Closed. `N_power = 65 ≥ 60` — **gate PASSES**. Corpus and Dev/Test split
frozen.

---

## 0. Arithmetic clarification, checked before anything else

The rejection counts reported for #101d's TED acquisition were `29
OUT_OF_TEMPORAL_WINDOW + 21 CONTENT_TOO_SHORT = 50`, against a total of `42` unique
rejected records. Verified directly against `candidates_rejected.json`, not assumed:

```
21 records: OUT_OF_TEMPORAL_WINDOW only
13 records: CONTENT_TOO_SHORT only
 8 records: both simultaneously
= 42 unique rejected records (matches total)
= 50 non-exclusive reason mentions (29 + 21, matching the reported breakdown)
```

`experiments/phase2/audit.py`'s "Rejection Reason Breakdown" sums per-reason
occurrences across records (a record with two reasons increments both counters) —
documented behavior, not a partition, and not a defect. Audit `PASSED` stands.

## 1. Acquisition denominator, stated plainly (not made to disappear)

671 raw TED notices harvested (`Innovation partnership` procedure, `Competition`
notice type). Of those:
- **557 mapping errors**: 509 use TED's pre-eForms template (predominantly 2016–2022
  notices; eForms became mandatory ~November 2022), which the current
  `TedCandidateMapper` cannot parse — a real, disclosed limitation of the current
  extractor, not a scientific exclusion of that population. 48 are Change
  notices/Corrigenda, correctly excluded per ADR 0034 §3.3.
- **114 mapped**, **72 accepted**, **42 rejected** (§0).

The 509 pre-eForms notices are not recovered here. #102 does not need them — the
2024–2025 temporal window already excludes nearly all of that population — but a
future extension of the temporal window backward would require extending the mapper
first, not simply re-running acquisition.

## 2. #102: multidimensional independence audit (`experiments/phase2/audit_ted_independence.py`)

Run against the 72 TED-accepted candidates. Sealed:
`data/experiments/phase2_v4/ted_independence_audit.json` (+ sha256).

### 2.1 Organization axis (ADR 0029, unmodified)

```
INDEPENDENT:     65
PSEUDOREPLICATE:  7
UNKNOWN:          0
```

100% of accepted records had `organization_raw` populated (vs. 0% for EEN/POD) — no
`UNKNOWN` at all on this axis, a first for this study. Six organizations repeated
(mostly German/Polish public housing and energy utilities, plus two French and one
Spanish public body), collapsing 13 records into 6 independent representatives + 7
pseudoreplicates via the existing, unmodified deterministic tie-break rule.

### 2.2 Sector axis — descriptive, structural, non-exclusionary

Method: each notice's own CPV (Common Procurement Vocabulary) **division** (first 2
digits of the `BT-262-Procedure` main classification) — an observed, structured field
on the source record itself, never text-similarity or embedding-derived. Evaluated
over the 65 `INDEPENDENT` demands only (the set that determines `N_power`).

**17 distinct CPV divisions**, no concentration warning: largest share is division
`72` (IT services) at 27.7% (18/65), followed by `45` (construction) at 20.0% and `73`
(R&D services) at 16.9% — all below ADR 0031 §2.4's 0.35 warning threshold. Per that
same section, this is reported, not enforced; nothing was excluded on this basis.

### 2.3 Technology-family axis — descriptive, structural, non-exclusionary

Method: full 8-digit CPV code, same source field, same non-inference principle.

**41 distinct CPV codes** among 65 independent demands; the most common single code
(`72000000`, generic IT services) accounts for 12/65 = 18.5% — below threshold, no
warning.

### 2.4 Duplicate-industrial-problem axis — explicitly NOT evaluated

No structural, non-inferred signal for duplicate-problem detection exists in TED's raw
evidence (no shared framework-agreement identifier or equivalent observed across
independent organizations). Per ADR 0029 §3.2's circularity reasoning (text-similarity
or embedding-based matching would use signals correlated with the relevance judgments
this study evaluates), no heuristic was substituted. **This is recorded as an open,
disclosed limitation of this closure — not an assumption that no duplicates exist.**
Consistent with the instruction that produced it: `UNKNOWN` (here, "not evaluated") is
preferable to a manufactured deduplication.

### 2.5 Result

Sector, family, and the undecided duplicate-problem axis do not reduce
`N_power` — per ADR 0031 §2.4, concentration monitoring is descriptive; duplicate-
problem was left unresolved rather than heuristically forced to a count.

$$N_{\mathrm{power}} = 65 \ge 60 \implies \textbf{PASS}$$

## 3. Composition: TED and EEN/POD are NOT combined into N=141

The existing #101d EEN/POD pool (`data/experiments/phase2_v3`, 76 accepted,
`organization_raw = None` for all 76, `N_power` contribution = 0, per #102's earlier
EEN/POD closure) is **not merged** with the TED-independent corpus. The frozen TED
corpus manifest (`ted_freeze_manifest_v1.json`) records this explicitly
(`not_combined_with`), so the corpus cannot be silently mis-cited as N=141 independent
observations. EEN/POD's 76 remain a separate, distinctly-labeled dataset; whether they
serve any auxiliary/Dev role is not decided here.

## 4. #103: freeze (`experiments/phase2/freeze_ted_corpus.py`)

Sealed artifacts, all in `data/experiments/phase2_v4/` with sha256 sidecars:

- **`ted_independent_corpus_v1.json`**: the 65 `INDEPENDENT` demands (pseudoreplicates
  excluded — `organization_aware_split`'s own contract forbids them in the partition
  universe).
- **`ted_devtest_split_v1.json`**: organization-aware, CPV-division-stratified split.
  `dev_fraction=0.5`, `base_seed=42` (same convention as `devtest_split_v2.json`),
  `unknown_split_policy="dev_only"` (moot here — 0 `UNKNOWN`).
- **`ted_freeze_manifest_v1.json`**: full provenance — hashes, per-stratum counts,
  organization-overlap check (verified empty).

Result: **Dev = 30, Test = 35**, zero cross-partition organization overlap (verified
programmatically, not merely asserted).

## 5. What is genuinely different now

Every prior milestone in this chain (#101b → #101c → #101d → #102's EEN/POD closure →
ADR 0033 → ADR 0034) produced *infrastructure* — a pipeline proven to work, repeatedly
finding it had nothing to run on. This is the first closure in the chain that produces
a **frozen, audited, organization-independent corpus with $N \ge 60$** and a clean,
leakage-free Dev/Test split ready for #104.

## 6. Not decided by this document

- Whether EEN/POD's 76 (`UNKNOWN` organization) serve any auxiliary role.
- The pre-eForms 509-notice mapper gap (§1) — not pursued unless a future window
  extension needs it.
- The duplicate-industrial-problem axis (§2.4) — remains genuinely open.
- #104 (dual annotation + κ) itself — the next milestone, not started here.
