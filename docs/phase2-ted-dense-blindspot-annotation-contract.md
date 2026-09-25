# #104 Dense Blind-Spot Annotation — Contract

```text
QUESTION:  Do the 220 dense candidates introduced by
           experiments/phase2/run_dense_retrieval.py precisely in BM25's
           blind spot (the 11 Dev demands for which BM25's pool was empty,
           docs/phase2-ted-dense-retrieval-results.md SS3) contain
           technology a human judges relevant, or are they near-threshold
           noise admitted by min_threshold=0.0?
INPUT:     The 220 (demand, patent) pairs tagged `dense_exclusive_new_unscored`
           AND `was_bm25_zero_pool=true` in
           data/experiments/phase2_v4/ted_at_scale_dense_retrieval_results.json
           -- exactly the 11 demand IDs listed in SS0 below, 20 candidates
           each. Nothing else. The 333 dense-exclusive candidates on the 19
           BM25-covered demands, and the 47 already-gold-scored pairs, are
           explicitly out of scope for this contract (per the closed
           dense-retrieval contract's SS5, "not touched").
METHOD:    Same blind double-annotation discipline already used for the
           108-pair gold set: infrastructure/annotation/blind_export.py
           (deterministic seeded shuffle, strips retrieval provenance/
           scores/method), same 0-3 relevance scale, same two independent
           annotators (Valentín, Lydia), same manual Cohen's kappa
           computation, same adjudication rule (disagreements resolved
           against the original written criterion, never recalibrated to
           fit outlier cases).
OUTPUT:    IAA report + adjudicated judgments for all 220 pairs, split by
           the 11 demands. A single number: how many of the 220 pairs score
           >=1 ("dense blind-spot relevance yield"), and how many of the 11
           demands get >=1 relevant candidate ("dense blind-spot coverage")
           -- reported on the same basis as BM25's 9/30 and 14/108, so the
           two are directly comparable, but never merged into one pooled
           statistic.
VALIDITY:  This measures dense's yield ONLY on BM25's blind spot -- it is
           not a general dense-vs-BM25 comparison (the other 333+47 pairs
           are untouched) and not a recall claim (no judgment exists for
           patents outside any retriever's pool, same limit as always).
STATUS:    PRE-REGISTERED. Not yet executed -- awaiting explicit go-ahead,
           same discipline as every prior #104 sub-experiment.
```

## 0. The exact 11 demands in scope

```text
122428-2024  146289-2024  158024-2024  221305-2025  273005-2025
410719-2024  588217-2024  642378-2025  654218-2024  794374-2025
820594-2025
```

11 × 20 = 220 pairs, verified against
`data/experiments/phase2_v4/ted_at_scale_dense_retrieval_results.json`
directly (not recomputed by hand) before writing this contract.

## 1. Why full 220, not a sub-sample

The user's own framing: these 220 pairs are *already* the minimal,
maximally-informative set (all of dense's activity in exactly the region
BM25 is blind). Sub-sampling them would trade statistical power for no
real savings — 220 pairs × 2 annotators = 440 judgments, the same order of
magnitude as the original 108-pair gold set's 216. No stratified sampling
within this stratum is needed: it is already naturally stratified by
demand (fixed at 20 candidates/demand, `limit_per_method=20`), so no
single demand can dominate the result by candidate count.

The remaining 333 dense-exclusive pairs on the 19 BM25-covered demands are
explicitly **not** annotated here — per the user's own sequencing, they
are secondary (characterizing complementarity, not the priority question)
and are deferred to a separate, later decision.

## 2. What "dense blind-spot relevance yield" does and doesn't mean

- **Does mean**: of the 220 candidates dense proposed where BM25 proposed
  nothing, how many a human independently judges relevant (score ≥1)? This
  is a direct, first-time measurement — no gold judgment existed for any
  of these 220 pairs before this experiment.
- **Does not mean**: "dense recall," "dense coverage of the full Dev set,"
  or anything comparable to a metric computed over all 30 demands — this
  stratum is exactly the 11 demands where BM25 had nothing, by
  construction. Extrapolating this yield to the other 19 demands, or to
  dense's overall behavior, is not supported by this design and will not
  be claimed.
- **Does not mean** BM25 vs. dense head-to-head on equal footing — BM25
  produced zero candidates here, so there is nothing to compare "yield"
  against on these same 11 demands; the only comparison possible is
  structural (0 candidates vs. up to 20 judged candidates), already
  reported in `docs/phase2-ted-dense-retrieval-results.md` SS3.

## 3. Annotation mechanics (identical to the closed gold-set process)

1. `blind_export.py` builds a shuffled, provenance-stripped batch of the
   220 pairs (deterministic seed, same as before).
2. Two independent CSVs, one per annotator, same 0-3 scale and criterion
   already written for the original 108-pair batch (no new criterion
   text) — reused verbatim so the scale means the same thing across both
   annotation rounds.
3. Manual Cohen's kappa (unweighted + quadratic-weighted), confusion
   matrix, disagreement list — same script pattern as
   `experiments/phase2/compute_iaa_at_scale.py`.
4. Adjudication of disagreements against the original written criterion
   only — never relaxed or tightened to fit an individual case, same rule
   the user set for the first adjudication round.
5. Freeze: a new sealed artifact (sha256), kept **separate** from
   `ted_at_scale_gold_set_v1.json` — this is a distinct stratum with a
   distinct sampling frame (BM25-blind-spot-only), not an extension of the
   original 108-pair gold set, and merging them would silently change what
   the original gold set's denominator means.

## 4. Non-goals

- Does not annotate the 333 dense-exclusive pairs on the 19 BM25-covered
  demands, or the 47 already-gold-scored shared pairs.
- Does not merge this new judgment set into `ted_at_scale_gold_set_v1.json`.
- Does not compute a pooled BM25+dense metric.
- Does not compute a "dense recall" number for the full 30-demand Dev set.
- Does not decide, based on this result, whether to extend annotation to
  stratum B (the 333 pairs) — that remains a separate, later decision.
- Does not touch ADR 0036.
