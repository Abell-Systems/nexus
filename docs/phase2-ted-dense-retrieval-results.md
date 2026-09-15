# #104 Dense Retrieval — Execution Results

```text
QUESTION:  Per docs/phase2-ted-dense-retrieval-diagnostic-contract.md, what
           does dense retrieval (limit_per_method=20, min_threshold=0.0)
           over the frozen embedding artifact actually produce for the 30
           Dev demands, and does it materially change candidate-space
           coverage vs. BM25, especially on the 11 demands BM25 left empty?
INPUT:     data/experiments/phase2_v4/ted_at_scale_dense_embeddings_v1.json
           (frozen, checkpoint 3) + the same 30 Dev demands, 63-patent
           corpus, and 108-pair BM25 gold set used throughout #104.
METHOD:    experiments/phase2/run_dense_retrieval.py -- DuckDbDenseSemanticRetriever
           (existing, unmodified) fed by a lookup-based TextEmbedder over
           the frozen vectors (no live computation). Asserts model/revision/
           dimension/patent-count/threshold match the contract before
           running anything; would BLOCK and stop on any mismatch (none
           occurred).
OUTPUT:    data/experiments/phase2_v4/ted_at_scale_dense_retrieval_results.json
           -- per-demand pools, candidate scores, BM25-overlap provenance.
VALIDITY:  No new annotation performed. Pairs outside the 108-pair gold set
           are reported as unscored, never assigned an inferred relevance.
STATUS:    CLOSED -- retrieval executed, no evaluation/annotation performed.
```

## 1. Headline numbers

| | Value |
|---|---:|
| Demands with non-empty dense pool | **30/30** |
| Total dense (demand, patent) pairs | 600 (30 × 20, `limit_per_method`) |
| Pairs overlapping BM25's existing 108-pair pool (already gold-scored) | **47** |
| Pairs dense-exclusive, **new and unscored** | **553** |

## 2. Read this "30/30" correctly — it is not a coverage result yet

BM25's `9/30` (`docs/phase2-ted-pool-coverage-results.md`) means "at least
one candidate judged relevant (gold≥1)." Dense's `30/30` means something
structurally different: with `min_threshold=0.0` (the retriever's own
existing default, fixed in the contract, not raised), **every eligible
patent scores above threshold**, so every demand's pool is bounded only by
`limit_per_method=20` — it is a near-mechanical consequence of the
threshold choice, not evidence that dense retrieval found 30 topically
relevant candidate sets. Of the 600 dense pairs, only 47 have any gold
judgment at all (borrowed from BM25's pool by coincidence); the other 553
are **unscored**, not "irrelevant" — no judgment is claimed for them, per
the contract.

## 3. The question that matters: the 11 BM25-zero-pool demands

| | 11 BM25-zero-pool demands | 19 BM25-non-empty demands |
|---|---:|---:|
| Dense pool size (each) | 20/20 (all 11) | 20 (typically) |
| Dense pairs overlapping BM25's gold-scored pool | **0** | 47 |
| Demands with ≥1 overlapping (already-scored) candidate | 0/11 | 13/19 |

**Every one of the 11 demands BM25 left completely empty now has a
full 20-candidate dense pool.** This is the concrete answer to the user's
question: dense retrieval *does* materially change candidate-space
*structure* on exactly the demands BM25 couldn't touch — but **none of
those 220 new pairs (11×20) have a gold judgment**, so whether any of
them are actually relevant is unknown, not yet measurable. This is the
honest, precise version of "dense changes coverage": it changes what
*exists in the pool*, not (yet) what is *known to be relevant*.

For the 19 demands BM25 already covered, dense's pool substantially
overlaps in only 13/19 demands (47 pairs total, out of up to 19×20=380
possible) — most of dense's pool for these demands is also new/unscored.

## 4. No recall, no coverage-at-gold≥1 claim for dense (yet)

Per the contract's estimand (§4): computing a "dense coverage" or "dense
yield" number the same way BM25's was computed would require judging at
least a sample of the 553 unscored pairs — not done here. Any such number
right now would either be silently `0/30` (technically true but
misleading, since it measures gold-scorable overlap, not dense's actual
candidate quality) or fabricated. Neither is reported.

## 5. What this motivates, not decides

The 553 unscored pairs — concentrated on exactly the demands/patents BM25
couldn't reach — are the natural candidate set for a possible incremental
blind-annotation round, if the user decides to pursue one. **Not started
here.** Whether dense's semantic representation is actually finding
relevant technology for the 11 previously-uncovered demands, or just
filling pools with near-threshold noise (since `min_threshold=0.0` accepts
everything), is exactly what that annotation would answer — and is
currently unknown in either direction.

## 6. Non-goals

- Does not compute dense coverage/yield/recall against the gold set.
- Does not annotate any of the 553 new pairs.
- Does not merge dense and BM25 into a combined pool.
- Does not modify BM25's 9/30, CPC's 0/30, or the CPV→NACE scope-gate.
- Does not decide whether an incremental annotation round should happen.
