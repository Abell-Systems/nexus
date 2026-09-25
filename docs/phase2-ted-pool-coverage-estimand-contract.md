# #104 Candidate-Pool Coverage — Estimand Contract

```text
QUESTION:  With the gold set frozen, what does "how well does the BM25+CPC
           pool perform" actually mean, precisely enough to compute before
           any number is called anything?
INPUT:     data/annotations/ted_at_scale_gold_set_v1.json (108 judgments) +
           data/annotations/ted_at_scale_annotation_batch.json (pool_sizes,
           zero_pool_demand_ids, 30-demand Dev denominator).
METHOD:    Define three distinct metrics before computing any of them (this
           doc); implement and run only after the definitions are fixed.
OUTPUT:    This contract. No numbers computed here.
VALIDITY:  Written before metric code exists, so the definitions are not
           fitted to whatever the numbers turn out to be.
STATUS:    PRE-REGISTERED. Execution is the next, separate step.
```

**CORRECTION (`docs/phase2-ted-pool-coverage-diagnostic.md` §1, found after
this contract's own execution was complete):** "BM25+CPC" below should be
read as **BM25-only** -- the CPC retriever never received a populated
taxonomy policy and contributed zero candidates to the pool. The estimand
definitions themselves (§2) are retrieval-strategy-agnostic and remain
valid as written; only the label is corrected.

## 1. Why this is needed

The gold set was built **only over the 108 pairs the BM25+CPC pool actually
retrieved** (`docs/phase2-ted-annotation-at-scale-batch-generation.md`,
`docs/phase2-ted-annotation-gold-set-freeze.md`). No annotator judged any of
the ~1,830 non-retrieved (demand, patent) pairs (30 demands × 63 patents,
minus the 108 retrieved). That fact has one direct consequence: **there is
no way to know, from this gold set alone, whether a relevant patent exists
outside the pool for any given demand.** Calling a metric computed here
"recall" — in the classical IR sense of *relevant retrieved / relevant
total* — would silently smuggle in an unverified assumption: that the pool
already contains every relevant patent, i.e. that pool "relevant total" =
gold "relevant total". That assumption is exactly what an exhaustive
judgment (all 63 patents × each demand) would test, and it hasn't been
done.

## 2. Three metrics, three different estimands

### 2.1 Demand-level pool coverage rate

**Definition:** the fraction of the 30 Dev demands for which the BM25+CPC
pool contains **at least one** candidate whose gold judgment meets a
relevance threshold.

- Denominator: **30** — the full Dev partition, not 19. The 11 zero-pool
  demands (`docs/phase2-ted-annotation-at-scale-batch-generation.md` §2)
  are included and automatically score as *not covered* (a pool of size 0
  cannot contain a relevant candidate). This is deliberate: coverage is a
  property of (corpus, retrieval strategy, demand universe) jointly, and
  excluding the zero-pool demands from the denominator would hide exactly
  the corpus-sparsity finding already disclosed.
- Two thresholds reported, not one picked arbitrarily: `gold >= 1`
  (marginally relevant or better) and `gold >= 2` (a real problem
  component or better) — the annotation guide draws a real line there
  ("mismo barrio" vs. "mismo edificio"), so collapsing to a single cutoff
  would discard information.
- This metric says: *for how many demands did the pool surface something
  worth an annotator's attention at all* — it does not say the pool
  surfaced the *best* available patent, only that it surfaced *a*
  qualifying one.

### 2.2 Pool relevance yield (NOT "recall")

**Definition:** among the 108 retrieved (demand, patent) pairs, what
fraction have `gold >= threshold` — i.e., of what the pool actually
returned, how much of it was judged relevant.

- This is a **precision-flavored** statistic over the retrieved set, not a
  recall statistic — it says nothing about what the pool missed.
- Explicitly disclaimed name: **"pool relevance yield"**, never "recall",
  anywhere this is reported (paper included) — the corpus/pool construction
  does not license a recall claim, per §1.

### 2.3 Relevance distribution among retrieved candidates

**Definition:** the full 0/1/2/3 histogram over the 108 gold judgments
(already computed: 0→94, 1→3, 2→5, 3→6,
`data/annotations/ted_at_scale_gold_set_v1.json`). Reported per-demand as
well as pooled, since a pooled histogram can hide that one or two demands
(e.g. `454027-2024`, `89204-2025` — the two 20-candidate pools) may
dominate the counts.

## 3. What would license an actual recall claim (not done here)

A defensible recall estimate needs an independent, exhaustive judgment
covering patents the pool did **not** retrieve — e.g. a random or
stratified sample of (demand, patent) pairs outside each demand's pool,
annotated the same way, to estimate how many relevant patents the pool is
missing. That is new annotation work, not implied by this contract, and is
explicitly **out of scope** here. If it is ever done, it gets its own
pre-registration (query/sample design, size, stopping rule — same
discipline as `docs/phase2-invenes-scaled-acquisition.md`), not folded
silently into this one.

## 4. Non-goals

- Does not compute anything — implementation and execution are a separate,
  following step under this contract's definitions.
- Does not introduce dense/semantic retrieval or ADR 0036 — deferred until
  these three metrics are computed and interpreted.
- Does not modify the corpus, gold set, or candidate pools to improve any
  of these numbers.
