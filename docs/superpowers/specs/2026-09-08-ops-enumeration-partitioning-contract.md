# OPS Enumeration Partitioning Contract (PR-E0.1)

**Status:** Draft — presented for approval before any code is written.
**Depends on:** ADR 0020 (`docs/adr/0020-experimental-corpus-architecture-demand-times-patent.md`, approved), PR #57 (merged, `99fbaa5`) — the fixture-testable PatentCorpus construction pipeline this contract extends.
**Does not touch:** ADR 0020 itself (not amended by this document — the scientific architecture it fixes is unchanged; this is purely the mechanism that makes it executable against a real, rate/volume-limited API), PR-E1, `AnnotationPoolEligibilityPolicy`, `CandidatePoolBuilder`.

## 1. Purpose

PR-E0 (#57) built `PatentCorpus`'s construction pipeline and made its enumerability requirement explicit and testable: `fetch_all_ops_batches` returns the full set of batches covering EPO OPS's own `total-result-count`, or raises — never a partial fetch silently treated as complete. But `scripts/freeze_patent_corpus.py::main()` issues that verification against ONE unpartitioned CQL query spanning all 6 jurisdictions × the full 10-year window, and is documented (in `main()`'s own docstring, per PR #57's final review) as unable to complete a real run: the true universe (~10⁷ candidates before grants-only filtering, since CQL cannot reliably filter grants-only — see `ops_query.py`) vastly exceeds what pagination can retrieve.

Investigating EPO OPS's actual limits (2026-09-08, web research — see §7 for confidence caveats) surfaced the real, harder constraint driving this: **OPS caps any single query's retrievable results at 2000 total, via `Range`, regardless of what `total-result-count` reports.** A query whose `total-result-count` is 50,000 will not yield 50,000 records through pagination no matter how `max_records` is tuned — OPS will not deliver records past its own 2000-result ceiling. This is not a tuning parameter of our own pagination code; it's an external hard limit. This document specifies how `PatentCorpus` construction can still enumerate its full ADR-0020-defined universe under that ceiling: by partitioning the universe into sub-queries small enough to each be individually enumerable (`total-result-count ≤ 2000`), and only accepting the union of those partitions as `eligible_available_records` if every partition demonstrably enumerated completely.

## 2. Scope

**In scope:** the partitioning contract itself — the invariants a partition tree must satisfy, the partitioning axes allowed, the terminal states (enumerable / needs subdivision / non-enumerable), and how the union of partitions feeds into the existing `select_frozen_patents` → `sha256(publication_id)` selection (unchanged from PR #57). Also in scope: the conceptual `partition(...)` function's contract and the test suite that proves it against synthetic `total-result-count` values, entirely without live OPS credentials.

**Out of scope:**
- The concrete behavior of a live `Range` request that exceeds OPS's 2000 ceiling (4xx error? truncated page? clamped `total-result-count`?) — genuinely unknown without live credentials (see §6), and this contract is deliberately written not to depend on that answer.
- Actually running a live OPS ingestion (PR-E0.2, later).
- Any change to ADR 0020, PR-E1, or the science already fixed there.
- Any partitioning axis beyond jurisdiction/date (see §4 — this is a hard boundary, not a placeholder).

## 3. The problem, restated precisely

`fetch_all_ops_batches` (PR #57) already answers: *"is a single query's advertised universe fully retrievable?"* — yes, if pagination covers `total-result-count` before `max_records`/API limits are hit; no, it raises. What it cannot answer on its own: *"is the query's advertised universe retrievable AT ALL?"* — no, whenever `total-result-count > 2000`, independent of `max_records`. A single unpartitioned query over ADR 0020's full inclusion contract (EP/US/JP/CN/KR/WO × grants × 10-year window) has a `total-result-count` far above 2000, so `fetch_all_ops_batches` will always raise on it — correctly (fail-closed), but uselessly, since no tuning of the existing pipeline resolves it. The fix is upstream of pagination: split the query into small enough pieces *before* calling `fetch_all_ops_batches` on each, so each individual call has a fighting chance of `total-result-count ≤ 2000`.

## 4. Partitioning axes: jurisdiction → year → month, and no further

Per ADR 0020 §2's inclusion contract, the only properties that legitimately determine `P`'s composition are jurisdiction, grant status, and publication date — never topic, CPC, title content, or anything demand-adjacent (ADR 0020 §1, demand-blindness). This contract inherits that boundary for its *partitioning axes* — jurisdiction and publication-date granularity (year, then month) — but explicitly **excludes grant status as a partitioning axis**, for a reason distinct from (and in addition to) demand-blindness: §1/§3 already established that CQL cannot reliably filter grants-only across offices. A "jurisdiction × date × grant" partition would silently assume OPS can answer a query it cannot reliably answer. Grant-only remains what it already is in the existing pipeline (PR #57): a downstream inclusion predicate applied by the normalizer/`allowed_kind_codes` after retrieval, never a query-partitioning key. See §5.1 for how this composes with coverage.

The hierarchy is fixed at exactly three levels, evaluated top-down, subdividing only as far as needed:

```text
jurisdiction (EP, US, JP, CN, KR, WO)  — 6 root partitions, ADR 0020 §2's fixed list
    └── year (within the 10-year window)   — subdivide only if the jurisdiction-level total-result-count exceeds the OPS retrieval ceiling (§5.3)
          └── month                         — subdivide only if the year-level total-result-count exceeds the ceiling
```

**No fourth level.** If a single jurisdiction-month partition still exceeds the ceiling, this contract does not invent a finer axis (day-of-month, doc-number prefix, etc.) to force enumerability. That case is a `NON_ENUMERABLE` terminal state (§5.4) requiring an explicit human decision, not an automatic deeper recursion — recursing indefinitely on unspecified axes is exactly the kind of ad hoc mechanism this contract exists to avoid.

**Leaf semantics: half-open publication-date intervals, not calendar labels.** A "month" leaf is not an informal calendar bucket — it is the interval `[start_date, end_date)` where `start_date` is the first day of that month and `end_date` is the first day of the following month, so a `publication_date` belongs to exactly one leaf with no ambiguity at month boundaries. The two edges of the overall 10-year window are the exception: the window's own start and end are closed on both sides — `window_start ≤ publication_date ≤ window_end` — matching ADR 0020 §2's "10 years preceding the freeze cutoff date" (inclusive of the cutoff day itself). The first and last leaves of a jurisdiction's partition tree are therefore clipped to `[window_start, first_full_month_start)` and `[last_full_month_end, window_end]` respectively, not full calendar months, whenever the window doesn't align exactly to month boundaries. Partitioning at year granularity uses the same half-open convention (`[YYYY-01-01, (YYYY+1)-01-01)`), clipped identically at the window's two edges. This is a statement of intended meaning for the implementation to satisfy — it does not prescribe how CQL itself expresses a half-open interval (a `pd within` clause, or two comparisons, or another mechanism — an implementation-time choice against `ops_query.py`'s existing conventions).

## 5. The `partition(...)` contract: five invariants

A conceptual function — `partition(universe) -> tree of leaf partitions` — governs construction. Whatever its eventual concrete signature (specified at implementation time, not here), it must satisfy:

1. **Coverage — over the CQL query space, not the full contractual universe directly.** Partitioning decomposes the *query space* CQL can actually express: jurisdiction × publication-date window. The union of all leaf partitions' CQL queries must retrieve every record satisfying `jurisdiction ∈ {EP,US,JP,CN,KR,WO} ∧ window_start ≤ publication_date ≤ window_end` — grants and non-grants alike, since (per §4) OPS cannot reliably narrow this further. Partitioning MUST NOT exclude any record satisfying the grant-only criterion by how it slices jurisdiction/date, and MAY retrieve records outside that criterion (pending applications, utility models, etc.) when OPS cannot separate them. The grant-only inclusion criterion is applied afterward, unchanged from the existing pipeline, so the two contracts compose as:

   ```text
   eligible_available_records
       = { normalized records that survived the pipeline }
         ∩ { grant-only inclusion criterion (allowed_kind_codes, PR #57) }
         ∩ { jurisdiction ∈ {EP,US,JP,CN,KR,WO} ∧ window_start ≤ publication_date ≤ window_end }
   ```

   The partition tree's coverage obligation is only over the third set (its own query space); the second set is enforced exactly where PR #57 already enforces it, not by this contract.

2. **Disjunction.** Leaf partitions do not overlap by construction (a jurisdiction × year × month cell is claimed by exactly one leaf, per §4's half-open interval semantics — no `publication_date` falls into two leaves). Cross-partition duplicate `publication_id`s are still possible in practice (e.g. a document indexed under more than one date field by OPS) and are resolved exactly as today, downstream, by `select_frozen_patents`'s dedup (PR #57's hard-fail-on-divergent-content policy applies identically here — partitioning changes nothing about that step). Partition boundaries are never used as a deduplication mechanism.

3. **Eligible for enumeration, vs. enumerated completely — two distinct conditions.** A leaf partition is *eligible for enumeration* when its OPS-reported `total-result-count` is at or below the OPS retrieval ceiling — a configured constant of the OPS adapter (`OPS_RETRIEVAL_CEILING`, working value 2000 per §7; **not** hardcoded into this domain-level contract, which only refers to "the ceiling"). A partition whose `total-result-count` exceeds the ceiling MUST be subdivided per §4's hierarchy before any attempt to enumerate it, and never has its own records fetched directly. Eligibility is necessary but not sufficient: a partition only counts as **enumerated completely** once `fetch_all_ops_batches` (PR #57, unchanged) has actually returned its full verified batch set for that partition's query. The two-stage flow is:

   ```text
   OPS-reported total-result-count ≤ OPS_RETRIEVAL_CEILING?
       no  → subdivide (§4) and re-evaluate each child
       yes → "eligible for enumeration"
               ↓
             fetch_all_ops_batches(leaf's CQL query)
               ↓ (raises on missing/drifting total-result-count, or ceiling violated mid-fetch)
             "enumerated completely" — this leaf's records are usable
   ```

4. **Fail-closed.** If a partition cannot be shown to enumerate completely — either because subdivision per §4 is exhausted (a month-level partition still exceeds the ceiling: `NON_ENUMERABLE`) or because any leaf's own `fetch_all_ops_batches` call raises (missing/drifting `total-result-count`, or an unexpected API failure) — the ENTIRE construction run fails. There is no partial acceptance: `eligible_available_records` must never be computed from a partition tree containing an unresolved `NON_ENUMERABLE` or failed leaf. This mirrors PR #57's `fetch_all_ops_batches` atomicity fix at the whole-universe level: either the full, verified universe is available, or nothing is.

5. **Order-independence.** The frozen `PatentCorpus`'s content must not depend on the order in which partitions are enumerated, the order OPS delivers results within a partition, or how a partition above the ceiling happened to be subdivided (e.g. whether January was fetched before February). This is already guaranteed downstream by `select_frozen_patents`'s `sha256(publication_id)` ordering (ADR 0020 §3, unchanged) — this invariant just makes explicit that partitioning must not introduce a new order-dependent step upstream of it (e.g. an early-partition-wins dedup shortcut would violate this; there is no such shortcut — see invariant 2).

## 6. Deliberately deferred: behavior at the retrieval-ceiling boundary

What actually happens when a `Range` request would retrieve past OPS's real ceiling — an explicit error, a truncated/empty page, a `total-result-count` that itself gets clamped — is unknown without live credentials, and this contract does not guess. Invariant 3 (§5) only requires that a partition's *advertised* `total-result-count` (read from its own biblio-search response, exactly as `parse_total_result_count` already does) be checked against `OPS_RETRIEVAL_CEILING` *before* any enumeration attempt — so in the well-behaved case, no partition ever legitimately approaches that boundary during automated construction; the boundary is avoided by construction, not handled at the boundary. The one required behavior at implementation time: a partition eligible for enumeration gets enumerated normally via the existing (already correct, atomic) `fetch_all_ops_batches`; nothing new needs to be built to handle an in-flight boundary crossing, because invariant 3 prevents attempting one. The empirical question (what if OPS's real behavior near the ceiling differs from its own advertised `total-result-count` in some edge case) becomes a live-credential integration test in PR-E0.2, not a design dependency here.

## 7. Confidence note, and where the ceiling constant lives

The working values — 2000 as `OPS_RETRIEVAL_CEILING`, 100 as the per-page size — come from web research (WebSearch/WebFetch against community client libraries — Python/Go/Ruby/R EPO OPS wrappers — which consistently cite them) during this document's drafting, not from a verbatim quote of EPO's own OPS v3.2 Reference Guide PDF (not fetchable via the tools available in this session). Multiple independent third-party sources agree, which is reasonable but not primary-source confidence.

**These are OPS-adapter configuration, not domain-model constants.** This contract (§4, §5) intentionally never hardcodes `2000` — it refers only to "the OPS retrieval ceiling," a named constant/parameter that belongs beside `fetch_all_ops_batches`'s existing `max_records` in the infrastructure layer (`infrastructure/sources/patent/`), the same layer that already owns `page_size`/`max_records`. Contract tests pin its *current, working* value (so a wrong guess is caught immediately rather than silently propagating), but the partitioning invariants themselves (§5) hold for any ceiling value — correcting the constant later, once PR-E0.2's live integration test confirms or refutes it, does not touch the domain contract, `PatentCorpus`'s schema, or ADR 0020's science.

## 8. What this enables, concretely

Once `partition(...)` exists and is proven against the five invariants (via fixture/synthetic `total-result-count` tests, no live credentials — same discipline as PR #57's Tasks 1-7), `scripts/freeze_patent_corpus.py::main()` changes from issuing one CQL query to the pipeline below. Grant status is deliberately absent from the partitioning step (§4) — it re-enters exactly where PR #57 already put it, after retrieval:

```text
jurisdiction/date partition (this document)
        ↓
OPS retrieval (fetch_all_ops_batches, PR #57, unchanged)
        ↓
normalization (OepmXmlNormalizer, PR #57, unchanged)
        ↓
grant-only inclusion (allowed_kind_codes, PR #57, unchanged)
        ↓
dedup (select_frozen_patents, PR #57, unchanged — hard-fails on divergent content)
        ↓
sha256(publication_id) ordering (ADR 0020 §3, unchanged)
        ↓
N_final = min(target_n, eligible_available_records) (ADR 0020 §4, unchanged)
        ↓
freeze (PR #57, unchanged)
```

Nothing about `PatentCorpus`'s schema, `select_frozen_patents`'s dedup/selection logic, or ADR 0020's science changes — only how the raw universe gets fetched from an API that cannot answer one giant query, and cannot answer even a per-jurisdiction query grants-only.
