# #104 dense-exclusive stratified sample -- generation results

Spec: docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md

## What ran

1. `experiments/phase2/sample_dense_exclusive_stratified.py` -- read the frozen
   dense-retrieval results (sha256 `f9ddde0756830f07f88020efa562471ef3bedbe3b9785891e2bde0da1c469d60`,
   matches the value the design spec was frozen against), verified the 553/220/333
   population counts, recomputed the demand allocation and confirmed it matches
   the spec's pre-registered tables exactly (no drift), drew the seed=104 sample.
2. `experiments/phase2/generate_dense_exclusive_stratified_annotation_batch.py` --
   blind-exported the 66 selected pairs via the existing `build_annotation_batch`.
3. `scripts/export_dense_exclusive_stratified_annotation_csv.py` -- wrote three
   blank CSVs (template/valentin/lydia), 66 rows each.

## Result

- 66 pairs selected: 26 from Stratum A (BM25-zero-pool), 40 from Stratum B.
- Re-run from the manifest step onward is byte-for-byte identical (verified).
- No annotation has occurred yet -- `judgment` columns are blank in all three CSVs.
- This artifact is disjoint from the 108-pair gold set (0 overlap, verified).
  It overlaps `180c5f7`'s parked 220-pair batch by construction on Stratum A
  (26/66 pairs -- Stratum A's population IS that batch's 220 pairs), which is
  harmless because that batch carries no labels (blank CSVs only, never
  annotated).

## Next step (not done here)

Independent dual annotation (Valentín + Lydia) on the blank CSVs, under the
same 0-3 contract as the gold set, followed by adjudication of any
disagreements and application of the pre-registered decision rule
(spec SS9): count relevant (score >=1) among the 66; >=14 rejects H0.
