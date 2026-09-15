# CPV→CPC Concordance Feasibility — Closure

```text
QUESTION:  Per docs/phase2-cpv-cpc-concordance-feasibility-contract.md,
           does a reproducible CPV->NACE->IPC->CPC concordance chain
           activate on the frozen 30 Dev demands' real CPV codes?
INPUT:     data/experiments/phase2_v4/ted_dev_cpv_codes_v1.json (30/30
           demands, 89 distinct CPV codes) + Regulation (EC) No 2195/2002
           Annex III (the only official EU CPV<->NACE correspondence),
           read in full (434 pages) and searched programmatically.
METHOD:    Located and read the actual legal text of Annex III before
           digitizing anything; measured overlap between the 89 observed
           CPV codes / 30 demands and Annex III's real scope.
OUTPUT:    A scope ceiling, not a mapping -- see SS1.
VALIDITY:  Annex III's scope was verified directly against the regulation
           text (page-by-page search across all 434 pages), not assumed
           from a search-result summary.
STATUS:    CPV->CPC (general): SCOPE-FAILED / DEFERRED.
           CPV->CPC (construction subset, 9/30 demands): FEASIBLE AS A
           SEPARATE, NARROWER STUDY -- not executed here, not merged with
           any other #104 result if it is.
```

## 1. The scope-gate finding

Regulation (EC) No 2195/2002's Annex III, "Correspondence Table Between
CPV and NACE Rev. 1," is the **only official EU CPV↔NACE correspondence**.
Read in full: it covers **exclusively NACE Rev. 1 Section F
(Construction)** — no other NACE section appears anywhere in the annex.
Annex IV, which follows it, is CPV↔CN (Combined Nomenclature, EU customs
tariff codes) — an unrelated classification, not NACE.

Applied to the frozen 30 Dev demands' real CPV codes
(`data/experiments/phase2_v4/ted_dev_cpv_codes_v1.json`):

| | Result |
|---|---:|
| Dev demands with ≥1 CPV in division 45 (Construction) | **9/30 (30%)** |
| Distinct CPV codes (of 89) in division 45 | **13/89 (14.6%)** |

This is a **structural ceiling, not a data-quality issue**: 21/30 Dev
demands (70%) — including every demand whose dominant CPV is `72000000`
"IT services" (9/30 demands) or `73000000` "R&D services" (6/30 demands) —
have zero CPV codes the official concordance can resolve to *any* NACE
code, before NACE→IPC is even reached. Neither Schmoch (2003) nor Dorner &
Harhoff (2018) can rescue these 21 demands — the failure is upstream of
where either table would apply.

## 2. Disposition (per the user's explicit decision)

**`CPV→CPC (general, full Dev set): SCOPE-FAILED / DEFERRED`.** Not
`NOT_INFORMATIVE_FOR_THIS_CORPUS` — that verdict would overstate what was
learned; the mechanism wasn't tested against the corpus and found
uninformative, it was blocked one hop earlier by the legal scope of the
only official CPV-NACE source. The distinction matters for how this gets
cited in the paper: this is a documented scope limitation of the
official concordance for this demand set, not evidence against CPV→CPC
as a retrieval idea in general.

**`NACE→IPC variants (Schmoch 2003 / Dorner & Harhoff 2018): NOT
EVALUATED`** — deliberately, because upstream CPV→NACE coverage (30%
ceiling) makes evaluating them against the full Dev set uninformative.
Neither table has been acquired.

**Not digitized: Annex III's full CPV↔NACE(Construction) pair table.**
Acquiring ~hundreds of CPV/NACE pairs to demonstrate a ceiling already
established structurally would be wasted effort, per the user's explicit
call.

## 3. What remains open, explicitly not executed here

A **SUBSET FEASIBILITY study, construction-only** (the 9/30 demands whose
CPV falls in division 45) remains a legitimate, separate, narrower
experiment if pursued later: `9 demands → CPV division 45 → official
CPV-NACE(Construction) → NACE→IPC (Schmoch/Dorner&Harhoff) → IPC↔CPC →
63-patent corpus`. If run, it must be labeled **SUBSET FEASIBILITY —
CONSTRUCTION ONLY**, must never be presented as evidence that CPV→CPC
works for TED demands in general, and its coverage/yield numbers must
never be combined with BM25's 9/30 pool-coverage result as if directly
comparable — different mechanisms, different estimands. **Not started in
this session.**

## 4. Sequence closure

`BM25 pool-coverage → CPC channel diagnostic (0/30, exact-phrase
mismatch) → CPV extraction/audit (30/30, coarse tail) → CPV→NACE
scope-gate (SCOPE-FAILED/DEFERRED, 30% ceiling)`. Per the user's stated
reasoning, dense retrieval is the recommended next experiment — attacking
the one dimension not yet tested (multilingual semantic representation)
— but starting it is a separate, explicit decision, not implied by this
closure.

## 5. Non-goals

- Does not conclude CPV→CPC is a bad idea in general — only that the
  *official EU concordance*, applied to *this Dev set*, has a hard 30%
  ceiling before any NACE→IPC choice matters.
- Does not acquire Schmoch (2003), Dorner & Harhoff (2018), or the full
  Annex III table.
- Does not touch BM25, the corpus, the gold set, or #104's existing
  results.
- Does not start dense retrieval or ADR 0036.
