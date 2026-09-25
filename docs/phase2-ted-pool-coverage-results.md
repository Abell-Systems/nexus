# #104 Pool-Coverage Results

```text
QUESTION:  Under the fixed estimand contract
           (docs/phase2-ted-pool-coverage-estimand-contract.md), what are
           the three metrics' actual values?
INPUT:     data/annotations/ted_at_scale_gold_set_v1.json (108 judgments) +
           ted_at_scale_annotation_batch.json + ted_devtest_split_v1.json.
METHOD:    experiments/phase2/compute_pool_coverage_metrics.py -- exact
           implementation of the pre-registered definitions, no new
           thresholds or denominators introduced here.
OUTPUT:    data/annotations/ted_at_scale_pool_coverage_metrics.json.
VALIDITY:  Computed only after the estimand contract was committed
           (eec6135); numbers below were not known when the definitions
           were fixed.
STATUS:    CLOSED.
```

**CORRECTION (`docs/phase2-ted-pool-coverage-diagnostic.md` §1):** every
"BM25+CPC" reference below should be read as **BM25-only** --
`DuckDbCPCRetriever` never received a populated taxonomy policy and
contributed zero candidates across all 30 Dev demands. The numbers
themselves are unaffected; the retrieval-strategy label they were computed
under is corrected here.

## Results

### 1. Demand-level pool coverage rate (denominator = 30, full Dev split)

| Threshold | Demands covered | Rate |
|---|---:|---:|
| gold ≥ 1 (marginally relevant+) | 9/30 | **30.0%** |
| gold ≥ 2 (real component+) | 8/30 | **26.7%** |

Only one demand drops out between the two thresholds — nearly everything the
pool surfaced as "marginally relevant" for at least one demand was in fact
also judged "relevant" (component-level) for that same demand. The 11
zero-pool demands are automatically uncovered at both thresholds and are
included in the denominator, per the contract.

### 2. Pool relevance yield (NOT recall)

| Threshold | Relevant pairs | Yield |
|---|---:|---:|
| gold ≥ 1 | 14/108 | **13.0%** |
| gold ≥ 2 | 11/108 | **10.2%** |

Of everything the BM25+CPC pool actually retrieved, roughly 1 in 8-10 pairs
was judged relevant. This says nothing about what the pool failed to
retrieve — per the contract, no recall claim is made or implied.

### 3. Relevance distribution among retrieved candidates

Pooled: 0→94 (87.0%), 1→3 (2.8%), 2→5 (4.6%), 3→6 (5.6%).

Per-demand distribution (`data/annotations/ted_at_scale_pool_coverage_metrics.json`
`per_demand_relevance_distribution`) shows the 6 gold=3 judgments spread
across 4 distinct demands: `89204-2025` (×3), `140590-2024` (×1),
`368294-2025` (×1), `454027-2024` (×1). Two of the four are the large
20-candidate pools (`89204-2025`, `454027-2024`), but the other two are
small pools (11 and 1 candidates) — high-relevance hits are not an artifact
of pool size alone.

## Interpretation

- **Coverage is low but non-trivial**: roughly 3 in 10 Dev demands get at
  least one plausible candidate from a 63-patent corpus via BM25+CPC. Given
  the corpus size, this is consistent with — not contradicted by — the
  sparsity already disclosed at batch-generation time.
- **Pool composition is heavily skewed toward 0**, expected given the
  corpus's small size relative to 30 independent technical topics.
- **No recall claim is possible or made** — a genuine limitation of this
  round, not a hidden one. Extending the corpus (more INVENES acquisition
  sessions) would raise the denominator's power for both coverage and any
  future recall estimate, but that is a separate, explicit decision, not
  implied by this result.

## Non-goals (this step)

- Does not introduce dense/semantic retrieval, ADR 0036, or any corpus/query
  change in response to the low coverage numbers.
- Does not attempt a recall estimate — see the estimand contract §3 for what
  that would actually require.
- Does not weight or re-rank the pool by these results.
