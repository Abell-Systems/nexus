# #104 Pool-Coverage Diagnostic

```text
QUESTION:  Per docs/phase2-ted-pool-coverage-results.md's own next-step
           framing, what characterizes the 9 covered vs. 21 uncovered
           demands, and where did each of the 14 gold>=1 positives come
           from (BM25, CPC, or intersection) -- corpus-insufficient vs.
           retrieval-insufficient vs. demand-nature?
INPUT:     data/annotations/ted_at_scale_gold_set_v1.json + a re-run of
           CandidatePoolBuilder against the frozen corpus/Dev split, this
           time inspecting each Candidate's retrieval_scores (which the
           blind-exported annotation data deliberately strips, PR-E spec).
METHOD:    Inline diagnostic scripts (not a new committed pipeline change),
           analysis-only -- no corpus, code, or gold-set modification.
OUTPUT:    This document.
VALIDITY:  Uses the same CandidatePoolBuilder/retriever code already run for
           the at-scale batch -- no new retrieval logic.
STATUS:    CLOSED -- surfaced a correction to how the prior results should
           be read, not a new experiment result of its own.
```

## 1. Correction: the pool was BM25-only, not BM25+CPC

`DuckDbCPCRetriever.retrieve()` calls `extract_demand_cpc_auto(demand,
policy=self._policy)`, and that function's own contract is: `symbols =
map_concept_to_cpc(...) if policy else []` (`duckdb_cpc.py` line 30) --
**with no policy injected, it always returns zero symbols**, by design
(ADR 0004/0005: "zero hardcoded dictionaries... all taxonomy mappings
require an explicitly injected MatchingPolicyConfig"). Neither
`experiments/phase2/generate_ted_annotation_dry_run.py` nor
`experiments/phase2/generate_ted_annotation_at_scale.py` constructed and
passed a `MatchingPolicyConfig` with a populated `concept_to_cpc_taxonomy`
to `DuckDbCPCRetriever` -- both scripts instantiated it with only
`eligibility_policy`, leaving `policy=None`.

Verified directly: `extract_demand_cpc_auto` on all 30 Dev demands returns
**0/30 non-empty symbol sets**, and the CPC retriever contributed **0/108**
pool candidates -- not zero relevant, zero candidates at all, across every
demand. No production-populated `MatchingPolicyConfig` with a real
`concept_to_cpc_taxonomy` exists anywhere in this repo outside test
fixtures.

**Consequence:** every number in
`docs/phase2-ted-pool-coverage-results.md` and the gold set it was computed
from reflects a **BM25-only pool**, not the "BM25+CPC" label used
throughout `docs/phase2-ted-annotation-at-scale-batch-generation.md` and
this doc's own predecessors. This is a labeling correction on already-frozen
artifacts, not a retraction of the numbers themselves (BM25 genuinely
produced exactly the 108 pairs annotated) -- but it changes what conclusion
those numbers support: they say nothing about CPC's contribution, because
CPC was never actually invoked.

Not fixed here: whether to construct a real taxonomy policy and re-run is a
separate decision, deliberately left to the user (this doc reports the
finding, it doesn't silently patch it in).

## 2. Coverage characterization: corpus-recall-zero vs. pool-precision-zero

Of the 21 uncovered Dev demands, two structurally different failure modes:

**11 "corpus/retrieval finds nothing" (zero-pool):** BM25 itself returns no
candidate at all for these demands (`docs/phase2-ted-annotation-at-scale-batch-generation.md`
§2's `zero_pool_demand_ids`). This is the corpus-sparsity failure mode.

**10 "finds something, none of it relevant" (non-empty pool, zero gold≥1):**
`104441-2025`, `137639-2024`, `200095-2024`, `22543-2024`, `264820-2024`,
`277089-2025`, `42938-2024`, `498443-2025`, `584867-2024`, `696940-2025` --
pool sizes 1-6. This is a lexical-precision failure mode: BM25 matched on
vocabulary overlap without matching the actual technical problem.

Roughly an even split (11 vs. 10) between "retrieval finds literally
nothing" and "retrieval finds something irrelevant" -- both failure modes
are real and comparably sized; neither dominates.

## 3. The 9 covered demands

| demand_id | pool_size | max_gold |
|---|---:|---:|
| 140590-2024 | 11 | 3 |
| 268550-2024 | 2 | 1 |
| 315512-2025 | 7 | 2 |
| 368294-2025 | 1 | 3 |
| 380300-2024 | 1 | 2 |
| 454027-2024 | 20 | 3 |
| 566290-2025 | 9 | 2 |
| 814207-2025 | 13 | 2 |
| 89204-2025 | 20 | 3 |

Pool size and max relevance are not correlated (two of the largest pools,
20 candidates each, do reach gold=3, but so do two of the smallest, 1
candidate each) -- a large pool is not what produces a relevant hit here;
lexical match to the right vocabulary is.

## 4. All 14 gold≥1 positives are BM25-only (uninformative given SS1)

Confirmed 14/14 `methods == ["lexical"]`, 0 CPC-only, 0 intersection. Given
§1, this is not evidence that "BM25 outperforms CPC" -- CPC was inert, so
there was no other channel to compare against.

## 5. Non-goals (this step)

- Does not construct a real CPC taxonomy policy or re-run the pipeline --
  that is a distinct, explicit decision for the user to make, not implied
  by this diagnostic.
- Does not retract or delete the existing gold set / results docs -- they
  remain valid as "BM25-only pool" results; only the label is corrected
  here.
- Does not open dense retrieval or ADR 0036.
