# ADR 0019: Annotation-Pool Temporal Eligibility Under Unknown Demand Posting Date

**Status:** Proposed
**Date:** 2026-09-08
**Scope:** Resolves a data-availability gap discovered while planning PR-E (candidate pool + blind dual annotation + IAA dry-run, `docs/superpowers/specs/2026-09-08-pr-e-candidate-pool-blind-annotation-iaa-design.md`): the frozen Phase-2 demand corpus (`data/evaluation/dataset_phase2_demand_corpus_n39.json`, N=39) has `posted_date: null` for all 39 demands, which would make `DefaultPatentEligibilityPolicy` reject every candidate as temporally ineligible. Doc only — no code, no candidate pool, no annotation.

---

## Context

`DefaultPatentEligibilityPolicy.evaluate()` (`infrastructure/matching/eligibility.py`), used by the three live retrieval implementations of `PatentCandidateRetriever` (`DuckDbBM25Retriever`, `DuckDbCPCRetriever`, `DuckDbDenseSemanticRetriever`), rejects a candidate as `EXCLUDED_TEMPORAL` whenever either `demand.posted_date` or `patent.publication_date` is missing or unparseable — it has no notion of an "unknown, not excluded" state. This mirrors correct, conservative behavior for live matching, where an unresolvable temporal comparison should not silently pass a candidate through.

Verified against the real N=39 corpus: **0 of 39 demands have a non-null `posted_date`.** Not an extraction bug — checked at the source:

- InnoGet (37/39 demands): `application/ingestion/extractors/innoget_extractor.py` never populates `metadata["posted_date"]`; live-fetching a source page (e.g. `INNOGET-1605`) confirms InnoGet's technology-call pages show only a "Deadline," never a posting/publication date.
- Open Innovation Lombardia (2/39 demands, `LOMBARDIA-860`/`947`): live-fetched confirms the page shows only "EXPIRATION DATE." The `external_reference` field (e.g. `TRES20250806011`) contains a date-shaped substring, but the page does not label it as a publication date — treating it as one would be an unverified inference, which ADR 0013's observed-evidence-only rule forbids.
- `docs/phase2-demand-acquisition-audit.md` mentions "validity dates" only for the EEN/POD source, which was excluded from N=39 for a content-completeness gap (commit 58bb191) — not applicable to the 39 real records.
- No prior extraction snapshot exists; N=39 was frozen 2026-09-07, the only extraction that has ever run for it.

**Wayback Machine (`web.archive.org`) CDX check**, run against all 39 source URLs: 6 demands have a confirmed, real archived-capture timestamp (`INNOGET-1625`: 2023-09-28, `1689`: 2023-06-10, `1932`/`1935`: 2020-10-26, `1972`: 2023-06-01, `2258`: 2024-07-23). A capture proves the page existed **at latest** at the capture timestamp — it is a real, observed fact, and a valid conservative upper bound on `posted_date` (`t_demand ≤ t_capture`), never a substitute for the true posting date. The remaining 33 are inconclusive (Archive.org had an intermittent outage during the check — some empty results are unretried failures, not confirmed absent captures), so Wayback coverage is real but partial and must not be treated as resolving the corpus.

**Existing precedent in this codebase for "unknown ≠ excluded":** `application/evaluation/runner.py::_filter_temporally_eligible_patents` (ADR 0018, sealed-evaluation-runner layer) already implements exactly this asymmetry — its docstring states "a patent stays eligible whenever either date is missing (undecidable, not excluded)." That function operates over an already-annotated, sealed dataset to decide `strict`/`unconstrained` re-scoring; it has no equivalent at the live-retrieval layer, and `temporal_pool_mode` itself does not apply to annotation-pool construction (there is no "unconstrained annotation pool" — see PR-E spec §5 correction).

This ADR resolves a distinct, narrower question: what a *new annotation-pool candidate generator* should do when the demand date needed to evaluate `t_pub < t_demand` is structurally unknown.

## Decision

### 1. `DefaultPatentEligibilityPolicy` is unchanged

The live-retrieval eligibility policy keeps rejecting on missing dates exactly as it does today. This ADR does not touch it, and does not change behavior for `DuckDbBM25Retriever`, `DuckDbCPCRetriever`, or `DuckDbDenseSemanticRetriever` outside of PR-E.

### 2. A third eligibility outcome, scoped to annotation-pool construction: `TEMPORAL_UNKNOWN`

Distinct from the existing `EligibilityReason` values (`ELIGIBLE`, `EXCLUDED_TEMPORAL`, `EXCLUDED_JURISDICTION`, `EXCLUDED_MISSING_TEXT`):

```text
ELIGIBLE           — t_pub < t_demand, both dates known, condition holds
EXCLUDED_TEMPORAL  — both dates known, condition fails (t_pub >= t_demand)
TEMPORAL_UNKNOWN   — t_demand (or t_pub) unresolvable — condition is
                     undecidable, not failing. The candidate is NOT
                     excluded from the annotation pool.
```

`UNKNOWN` must never be interpreted as, converted to, or scored equivalently to `ELIGIBLE`. A candidate pool entry carries its temporal outcome explicitly; nothing downstream may collapse the three-way distinction into a boolean. **`TEMPORAL_UNKNOWN` is an eligibility outcome, not an exclusion reason** — it must not be read as "excluded, for an unknown reason."

### 3. A new, narrowly-scoped policy: `AnnotationPoolEligibilityPolicy`

Implements `PatentEligibilityPolicy` (same protocol `DefaultPatentEligibilityPolicy` implements) but is a **separate class**, used only by `CandidatePoolBuilder` for PR-E's annotation-pool construction:

```text
AnnotationPoolEligibilityPolicy.evaluate(patent, demand):
    jurisdiction / text-availability checks:  same as DefaultPatentEligibilityPolicy
    demand.posted_date known AND patent.publication_date known:
        t_pub < t_demand  → ELIGIBLE
        t_pub >= t_demand → EXCLUDED_TEMPORAL
    demand.posted_date unknown OR patent.publication_date unknown:
        → TEMPORAL_UNKNOWN (included in pool, marked)
```

`CandidatePoolBuilder` receives this (or any `PatentEligibilityPolicy`) as an explicit injected dependency — it does not choose, default, or infer which policy to use (ADR 0005 explicit-injection; see PR-E spec §5 contract 1).

### 4. Wayback Machine capture as optional tightening evidence, never a `posted_date` substitute

Where a confirmed archived-capture timestamp exists for a demand's `source_uri` (obtained via the Wayback CDX API, not inferred from any other field), it MAY be supplied to `AnnotationPoolEligibilityPolicy` as an explicit upper bound (`t_demand ≤ t_capture`) alongside — never instead of — the corpus's own `posted_date`. This can only ever *narrow* the `UNKNOWN` set: since `t_demand ≤ t_capture`, establishing `t_pub < t_capture` is sufficient to establish `t_pub < t_demand`, for some otherwise-undecidable pairs. It can never produce an `ELIGIBLE` verdict from a `t_pub` that is not strictly before the captured bound, and it must never be written back into `posted_date` on the frozen corpus or any derived artifact as if it were the true posting date.

### 5. `temporal_validity` is annotation metadata, not a filter

Every `Candidate` in the pool built by `CandidatePoolBuilder` carries its `EligibilityReason` (`ELIGIBLE` / `TEMPORAL_UNKNOWN`) through to the blind-export boundary as internal provenance. It is **not** shown to annotators (per the PR-E spec's blind boundary — annotators judge technical relevance, not temporal eligibility) and does not gate whether a candidate enters the pool for `TEMPORAL_UNKNOWN`. It is retained so that PR-F can later decide, per demand, which subset of judgments is admissible under a genuinely strict temporal evaluation — without re-running annotation.

## What this ADR does not do

- Does not change `DefaultPatentEligibilityPolicy`, or any live-matching/retrieval behavior outside PR-E's annotation-pool construction path.
- Does not implement `CandidatePoolBuilder`, `AnnotationPoolEligibilityPolicy`, the `TEMPORAL_UNKNOWN` enum value, or the Wayback-lookup integration — deferred to the PR-E implementation plan, per this repository's contract-then-test-then-code discipline (ADR 0013 §3, ADR 0016/0018 precedent).
- Does not reintroduce or repurpose ADR 0018's `temporal_pool_mode` (`strict`/`unconstrained`) — that field remains scoped to the sealed-evaluation-runner's re-scoring of an already-annotated dataset and is not plumbed into annotation-pool construction.
- Does not decide what PR-F does with `TEMPORAL_UNKNOWN`-marked judgments (include with a caveat, exclude from the strict-temporal analysis, etc.) — that is a PR-F-scoped decision, made when PR-F's evaluation design is brainstormed.
- Does not fix the underlying `posted_date` data gap for the corpus at large, and does not claim Wayback resolves it — 33/39 demands remain without any real temporal evidence after this ADR.
- Does not annotate anything, generate any candidate pool, or make any efficacy claim.

## Consequences

### Positive

- Unblocks PR-E without fabricating data: every eligibility outcome remains traceable to either the corpus's own `posted_date`/`publication_date` fields or a real, independently verifiable Wayback capture timestamp.
- Keeps the live-retrieval eligibility policy (`DefaultPatentEligibilityPolicy`) and its existing tests untouched — zero risk to current matching behavior.
- Preserves the three-way distinction (`ELIGIBLE`/`EXCLUDED_TEMPORAL`/`TEMPORAL_UNKNOWN`) end-to-end into the annotation artifact, so PR-F is not forced to guess which judgments came from a temporally-verified pair.
- Consistent with an existing pattern already accepted elsewhere in this codebase (ADR 0018's runner-layer "undecidable, not excluded" semantics), rather than inventing a new methodological stance from scratch.

### Negative

- Introduces a second, annotation-pool-specific eligibility policy class alongside `DefaultPatentEligibilityPolicy`, with an overlapping but not identical decision table — a future reader must not assume they behave the same way.
- `TEMPORAL_UNKNOWN` candidates make up an unknown, possibly large, fraction of the annotation pool (33/39 demands have zero temporal evidence today) — PR-F inherits an open question about how much of the dry-run's (and later the full-scale) ground truth is usable for a strict temporal-eligibility evaluation.
- The Wayback CDX lookup depends on an external service (observed to have intermittent outages during this investigation) — it is optional supplementary evidence, not a dependency PR-E can rely on being available or complete.

## Enforcement

A future PR-E implementation is **non-compliant** with this ADR if it:

1. Modifies `DefaultPatentEligibilityPolicy`'s behavior or its existing tests to accommodate missing dates.
2. Lets `CandidatePoolBuilder` default, infer, or hard-code which eligibility policy it uses, rather than receiving one as an explicit injected dependency.
3. Treats `TEMPORAL_UNKNOWN` as equivalent to `ELIGIBLE` anywhere — in pool construction, blind export, annotation, or IAA computation.
4. Writes a Wayback capture timestamp into `posted_date` on the frozen corpus, the annotation pool, or any derived artifact, or otherwise represents it as an observed posting date rather than an upper bound.
5. Exposes `temporal_validity`/`EligibilityReason` to annotators across the blind-export boundary defined in the PR-E spec.
6. Reuses or repurposes ADR 0018's `temporal_pool_mode` field or its `strict`/`unconstrained` vocabulary for annotation-pool construction.
