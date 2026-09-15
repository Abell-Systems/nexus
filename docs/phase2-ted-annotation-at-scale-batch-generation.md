# #104 At-Scale Annotation Batch Generation

```text
QUESTION:  Now that the OEPM technology corpus is qualified (63/60, ADR 0035
           SS3/SS9, frozen 2026-09-15), can a real dual-annotation batch be
           generated against the full Dev partition of the frozen TED demand
           corpus, superseding the #104 dry-run's protocol-validation-only
           scope?
INPUT:     data/experiments/phase2_v4/ted_independent_corpus_v1.json (65
           demands) + ted_devtest_split_v1.json (Dev: 30 demand_ids) +
           OEPM-INVENES-CORPUS-2026-V1 (63 domestic patents, Parquet).
METHOD:    experiments/phase2/generate_ted_annotation_at_scale.py: same
           CandidatePoolBuilder + BM25/CPC retrievers + blind-export pipeline
           as the dry-run (experiments/phase2/generate_ted_annotation_dry_run.py),
           pointed at the real frozen corpus (materialized into a DuckDB table
           from the canonical Parquet store) instead of the 16-patent pilot,
           and at the full 30-demand Dev partition instead of 8 hand-picked
           demands.
OUTPUT:    data/annotations/ted_at_scale_annotation_batch.json (+ .sha256):
           19/30 Dev demands with a non-empty eligible candidate pool, 108
           demand-patent pairs. CSV templates for independent dual annotation:
           ted_at_scale_annotation_{template,valentin,lydia}.csv.
VALIDITY:  Same retrieval/blind-export code already exercised by the dry-run
           (mechanics validated); this is the first run against the real
           corpus and the real Dev partition, not a new protocol.
STATUS:    BATCH GENERATED. Awaiting independent human annotation (not done by
           this session) before IAA/κ, adjudication, and gold-set freeze.
```

## 1. Retriever/corpus bridge

The dry-run's own limitation note said scaling required "ingesting a
production-scale OEPM corpus first (not done here)." `ADR 0035`'s corpus is
now frozen, but it lives in `ParquetCanonicalStore` (Parquet), while
`DuckDbBM25Retriever`/`DuckDbCPCRetriever` read a DuckDB `patents` table. This
run materializes the canonical Parquet store into an in-memory DuckDB table
matching the retrievers' expected schema (`resolve_patent_columns` already
supports the `publication_id`/`cpc_codes` naming used here) — no retriever
code was changed.

**Observation, not a defect:** each acquisition session's `build_corpus()`
re-ingests the complete cumulative included set (not just new records), so
the canonical store's raw Parquet parts contain duplicate rows per
`publication_id` across sessions (251 rows, 63 distinct). The materialization
step dedupes with `DISTINCT ON (publication_id)`; content is identical across
duplicates (same source HTML), so which duplicate survives is immaterial.

## 2. Disclosed finding: candidate-pool coverage at N=63

Running the full 30-demand Dev partition against the 63-patent corpus (BM25 +
CPC, `limit_per_method=20`, same setting as the dry-run) produces:

- **19/30 demands** (63%) with a non-empty eligible candidate pool — these
  form the annotation batch, 108 pairs total.
- **11/30 demands** (37%) with **zero** eligible candidates from either
  retriever — recorded by `demand_id` in the batch's `zero_pool_demand_ids`,
  not silently excluded from the record. This is a direct consequence of
  corpus size (63 patents cannot densely cover 30 independent technical
  topics), not a retrieval-code defect or an eligibility-policy artifact.
- Pool-size distribution across the 19 annotated demands: min 1, median ~3,
  max 20 (two demands saturate the 20-per-method cap).

This is reported as-is, per the same non-goals discipline already established
for the acquisition phase (`docs/phase2-invenes-scaled-acquisition.md` §5):
not routed around by relaxing eligibility, not patched by enlarging the
corpus mid-batch.

## 3. Methodological observation carried over from acquisition (session 6)

Documented here for reproducibility, since it bears on any future
re-acquisition: INVENES's live search-result ordering is **not stable
across sessions** (the OEPM database updates daily). Position/page in a
search result is not a stable reference to "population" — a query that
needed deep paging one day resolved entirely from page 1 the next, because
already-seen items had moved, not because the underlying population grew.
Any future scaled acquisition (e.g. to extend the corpus beyond 63) must
re-read live pages rather than assume position stability across days.

## 4. Non-goals (this step)

- Does not perform the annotation itself — that is independent human work
  (this session generated the batch and the blind CSV templates only).
- Does not compute IAA/κ, adjudicate, or freeze a gold set — those follow
  only after both annotators' CSVs are returned complete.
- Does not modify the corpus, the eligibility policy, or the demand corpus in
  response to the 11 zero-pool demands.
- Does not add a third retriever (dense/semantic) — ADR 0014 isolation still
  applies, same as the dry-run.
