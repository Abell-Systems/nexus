# Redesign: pure SRS sampling for the 553 dense-exclusive pairs

Status: design frozen, pending implementation.

Supersedes SS5–SS8 of `docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md`
(stratum-proportional allocation, then equal-per-demand allocation within
each stratum). That document's SS1–SS4 (background, primary estimand,
population/strata definition, power calculation) and SS9–SS12 (decision
rule, annotation protocol, disclosed limitations, next steps) remain valid
and are carried forward unchanged except where SS8 of *this* document
extends the disclosed-limitations section. This document replaces only the
*allocation and selection mechanism*.

## 1. Why this redesign exists

Independent code review of PR #113 found that equal-per-demand allocation
within each stratum (2026-09-23 design SS6) gives pairs from small-pool
demands a higher per-pair inclusion probability than pairs from large-pool
demands in the same stratum — up to ~2x spread within Stratum B (0.10 to
0.222). The pooled exact-binomial decision rule (SS9) does not account for
this, and the original design's disclosed-limitations section (SS11) did
not mention it. This is a distinct threat to the estimator's unbiasedness,
separate from the already-disclosed clustering/publication-repetition
caveats.

No draw has happened against the 2026-09-23 design. No annotation exists.
This redesign replaces the allocation/selection mechanism before either
occurs — the problem was caught while still fully reversible, per
[[feedback_methodological_rigor]] Rule 4.

## 2. Decision: pure simple random sampling (SRS), no stratified allocation

Two approaches were considered:

- **(Rejected) Design-weighted estimation** — keep stratified/equal-per-demand
  allocation, switch to a Horvitz–Thompson-weighted estimator and re-derive
  the test under a design effect. Preserves demand-balancing but adds real
  statistical machinery for no corresponding gain here.
- **(Chosen) Pure SRS** — draw n=66 pairs uniformly at random from the flat
  553-pair population, full stop. Every pair gets the same inclusion
  probability by construction. Strictly simpler than the rejected
  alternative: no allocation step, no per-stratum capacity checks, no
  design weights, no re-derived variance.

Pure SRS was chosen because it is the cleaner design for this experiment:
one flat population, one sampling operation, one deterministic seed, and it
removes the unequal-inclusion-probability problem by construction rather
than by correcting for it after the fact.

## 3. Inclusion probability

For every one of the N=553 dense-exclusive pairs, independent of stratum or
demand:

**π = n/N = 66/553 ≈ 0.11934**

This is the single number the manifest must record and the estimator
assumes. There is no per-demand or per-stratum variation to track for the
selection mechanism itself (Stratum A/B membership is retained as
descriptive metadata only — see SS5).

## 4. Selection procedure

1. Build the flat population: all 553 dense-exclusive pair identifiers
   (`demand_id`, `publication_id` pairs) from the frozen source data (same
   sources as the 2026-09-23 design SS3: `ted_at_scale_dense_retrieval_results.json`
   and `ted_at_scale_pool_coverage_metrics.json`), each pair carrying its
   Stratum A/B label derived the same way as SS3 defined it (BM25-zero-pool
   demand vs. BM25-nonempty-pool demand).
2. Sort the flat population deterministically (by `demand_id`, then
   `publication_id`) before any RNG call — required for bit-for-bit
   reproducibility regardless of input ordering, same discipline as the
   2026-09-23 design's per-demand pre-sort.
3. Draw exactly n=66 pairs without replacement using a single
   `random.Random(seed=104)` instance (same seed as the 2026-09-23 design,
   reused for continuity — it was never tied to the old allocation
   mechanism, only disclosed as fixed before any script was written).
4. No allocation step. No per-demand or per-stratum quota. No largest-
   remainder rounding. `largest_remainder_allocation` and the per-demand
   loop in `select_stratified_sample` (`experiments/phase2/dense_exclusive_sampling.py`)
   are deleted, not deprecated — nothing in the new design calls them.

## 5. Stratum A/B: retained as diagnostics only

After the draw, each of the 66 sampled pairs is tagged with its Stratum
A/B label (a lookup against the frozen population, not a selection input).
The manifest reports how many of the 66 landed in each stratum as a
descriptive statistic. **This number is not pre-registered as a target and
is not used to accept, reject, or adjust the draw** — SS2 of the
2026-09-23 design already established that stratification here is a
sampling-design concern, not a second hypothesis test, and that framing is
unchanged: the strata just no longer drive the mechanism, only the report.

## 6. Sample size and decision rule: unchanged

n=66, one-sided exact binomial test, H0: p=14/108≈0.1296, H1: p1=0.25,
α=0.05 target, achieved n=66/c=14/α_actual=0.0415/power=0.8013 — all
carried forward from the 2026-09-23 design SS4 and SS9 without
recalculation. The power calculation in that document never referenced the
allocation mechanism; it depends only on n, p0, p1, and the significance
target. Removing the stratified allocation does not change any of its
inputs.

This holds **only if the frozen population is still N=553** at draw time.
If PR #112's TED construct-validity gate changes what's eligible upstream
and the population size changes, SS4's power calculation must be re-run
against the new N before any draw — this redesign does not pre-approve a
population change, per the existing sequencing decision (#112 → repopulate
→ #113 redesign → amend preregistration → draw), already satisfied by this
being a redesign, not a draw.

## 7. Deterministic sampler requirements

- **Frozen population hash**: the sampler computes a sha256 of the exact
  553-pair population it draws from and records it in its own manifest —
  this *establishes* the freeze at generation time (there is no pre-
  existing external hash to check against; `ted_at_scale_dense_retrieval_results.json`
  has no `.sha256` sidecar today). Any later script that reads the same
  source data (e.g. a future blind-export or gate-evaluation step) must
  then verify its current sha256 against this manifest's recorded value
  before proceeding — the same record-then-verify pattern already built
  for the TED construct-validity manifest chain
  (`build_ted_construct_validity_control_sample.py` → downstream scripts),
  not a new pattern invented here.
- **Explicit seed**: 104 (SS4 above), committed in the sampler's source,
  not passed as a runtime default that could silently vary.
- **Exact sampled IDs**: the manifest lists all 66 `(demand_id,
  publication_id)` pairs by identity, not just counts.
- **Manifest with inclusion probabilities**: every sampled pair's record
  includes π=66/553 explicitly (a constant here, but recorded per-pair
  rather than only once globally, so the manifest is self-describing to a
  reader who doesn't also read this spec).
- **No annotation files generated by this work.** Blind CSV export (if any)
  is a separate, later step — this redesign's implementation plan produces
  the sampler and its manifest only, exactly as the original design's SS12
  scoped the original sampler.

## 8. Disclosed limitations (extends 2026-09-23 design SS11)

- **SRS without replacement is not literally n independent Bernoulli
  trials.** Equal inclusion probability removes the unequal-probability
  design problem this redesign exists to fix, but finite-population draws
  without replacement are negatively dependent (drawing one pair slightly
  lowers the conditional probability of drawing another). The exact
  binomial calculation in SS6 above is retained as the **pre-specified
  design-stage operating characteristic**, not a claim that the 66 draws
  are literally independent. This is the same class of approximation the
  2026-09-23 design already disclosed for within-demand clustering and
  cross-demand publication repetition (SS11) — carried forward and named
  explicitly here rather than assumed away by the switch to SRS. With
  n=66 drawn from N=553 (a sampling fraction of ~11.9%), the finite-
  population effect on the variance is small but real and not separately
  quantified in this design; a finite-population correction could be
  reported alongside the primary result but is not part of the
  pre-registered decision rule.
- Within-demand clustering and cross-demand publication repetition (the
  2026-09-23 design's own SS11 caveats) are unaffected by this redesign —
  SRS can still draw multiple pairs from the same demand or the same
  publication by chance; nothing here changes that risk's likelihood or
  its disclosure.
- The Stratum A/B diagnostic split (SS5 above) may land anywhere from
  0/66-to-66/0 in principle, though extreme splits are very unlikely given
  N_A=220/N_B=333 and n=66 drawn uniformly; the design does not bound this
  the way the old equal-per-demand mechanism implicitly did, and that
  trade-off is accepted deliberately in exchange for the simpler,
  unbiased-by-construction mechanism.

## 9. What happens next (not part of this design)

1. Write the implementation plan: a pure sampling function (flat-population
   draw, no allocation), a manifest-generation script (population hash,
   sampled IDs, per-pair inclusion probability, stratum diagnostic split),
   and tests (SS10).
2. No draw against the real 553-pair population until PR #112's TED
   construct-validity gate resolves and that population is confirmed
   stable (SS6 above).
3. Only then: amend the preregistration (dated note, mark the 2026-09-23
   design's SS5–SS8 superseded, do this before the new draw — same
   discipline as every other amendment in this project's history) and
   draw for real.

## 10. Required test coverage for the implementation plan

(Informational for the plan-writing step, not exhaustive test code.)

- Sample size is exactly 66.
- No duplicate pairs in the sample.
- Every sampled pair's identity exists in the frozen 553-pair population.
- Same seed + same population → bit-identical sample (reproducibility).
- Every sampled pair's recorded inclusion probability equals 66/553 exactly.
- The sampler's own manifest is the freeze point (records the population's
  sha256, per SS7). Any downstream script this plan or a later one adds
  that re-reads the same source data must verify its current sha256
  against that recorded value before proceeding, refusing (raising, not
  silently proceeding) on a mismatch — mirroring the TED construct-
  validity manifest chain's record-then-verify pattern, not a new
  invention. This spec does not itself define a "decision rule" script
  (SS9 above: the 66 pairs aren't drawn or annotated yet) — this
  requirement is forward-looking, for whatever later script evaluates the
  decision rule against real annotation results.
