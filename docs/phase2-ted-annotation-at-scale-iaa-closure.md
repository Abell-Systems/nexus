# #104 At-Scale Dual Annotation — IAA Closure

```text
QUESTION:  Having independently annotated the 108-pair at-scale batch
           (docs/phase2-ted-annotation-at-scale-batch-generation.md), what is
           the inter-annotator agreement, and which pairs need adjudication?
INPUT:     data/annotations/ted_at_scale_annotation_{valentin,lydia}.csv --
           108/108 rows each, independently completed, 0-3 scale.
METHOD:    experiments/phase2/compute_iaa_at_scale.py: row-by-row alignment
           check (demand_id + publication_id must match in the same order),
           per-annotator distribution, 4x4 confusion matrix, Cohen's kappa
           (unweighted and quadratic-weighted -- the scale is ordinal),
           disagreement listing. Read-only with respect to both CSVs.
OUTPUT:    data/annotations/ted_at_scale_iaa_report.json -- full distributions,
           confusion matrix, both kappa values, and the 12 disagreeing pairs
           ready for adjudication.
VALIDITY:  Both annotators worked independently before comparison (per
           docs/annotation/ted_at_scale_annotation_instructions.md); this
           script performs no annotation itself, only alignment and
           agreement statistics.
STATUS:    CLOSED. Adjudication of the 12 disagreements is the next step,
           not performed here.
```

## 1. Results

- **108/108 pairs** aligned cleanly (same demand_id + publication_id in the
  same row order in both CSVs) -- no row-order or identifier mismatch.
- **Exact agreement: 96/108 (88.9%)**.
- **Within-one agreement: 108/108 (100%)** -- no disagreement exceeds 1 point
  on the 0-3 scale; there is no case where one annotator said 0 and the other
  said 2 or 3, or vice versa.
- **Cohen's κ (unweighted): 0.597** -- moderate agreement (Landis & Koch
  bands: 0.41-0.60 moderate, 0.61-0.80 substantial; 0.597 falls inside the
  moderate band, 0.003 short of the 0.60 substantial threshold).
- **Cohen's κ (quadratic-weighted): 0.916** -- almost perfect, reflecting
  that every disagreement is adjacent on the ordinal scale, not a category
  reversal.

| Valentín \ Lydia | 0 | 1 | 2 | 3 |
|---|---:|---:|---:|---:|
| **0** | 88 | 0 | 0 | 0 |
| **1** | 7 | 0 | 1 | 0 |
| **2** | 0 | 3 | 2 | 0 |
| **3** | 0 | 0 | 1 | 6 |

Distribution is heavily skewed toward 0 for both annotators (Valentín 88/108,
Lydia 95/108) -- consistent with the corpus-scale finding
(`docs/phase2-ted-annotation-at-scale-batch-generation.md` §2) that a
63-patent corpus produces thin, often marginal candidate pools against
30 independent demand topics.

## 2. The 12 disagreements

All 12 are |diff|=1, clustered around the 0/1 boundary (9 of 12) and the
1-2/2-3 region (3 of 12) -- no 0-vs-3 reversals. Full list with titles in
`data/annotations/ted_at_scale_iaa_report.json`'s `disagreements` array.
Two demands (`814207-2025`, `315512-2025`) account for 6 of the 12
disagreements between them -- worth watching in adjudication for whether
that reflects genuine ambiguity in those specific demands' technical scope
rather than annotator inconsistency in general.

## 3. Non-goals (this step)

- Does not adjudicate the 12 disagreements -- that is a separate step
  (discussion between the two annotators, or a third-party tie-break,
  per whatever adjudication rule gets pre-registered before it happens).
- Does not modify either annotator's primary CSV.
- Does not touch the corpus or the candidate-pool generation in response to
  the skewed 0-heavy distribution -- that distribution is itself a result
  (thin corpus coverage), not a defect to fix retroactively.
- Does not freeze a gold set yet -- gold set = exact-agreement pairs +
  adjudicated disagreements, produced only after adjudication.
