# Pre-registration design: stratified sample of the 553 dense-exclusive pairs

Status: design frozen, pending implementation (sampling script + annotation batch).
Supersedes: `180c5f7` (`feat/pr101b-corpus-expansion-acquisition`, "pre-register +
generate #104 dense blind-spot annotation batch") — that commit's 220-pair batch is
**parked as a historical/reproducibility artifact only**. It generated blank
annotation CSVs (no labels were ever filled in), so there is no contamination risk
from this design's sample overlapping it. Its full-stratum, no-sampling selection
mechanism does not correspond to this design and its output must not be reused as
data.

## 1. Background

`docs/phase2-ted-dense-retrieval-results.md` / `docs/roadmap.md:62-64` closed a
dense-retrieval diagnostic (ADR 0014's pinned multilingual model) over the 30 Dev
demands. Of 600 total dense pairs (top-20 per demand), 47 overlap the existing
108-pair BM25-derived gold set; the remaining **553 are dense-exclusive and
unscored** — no relevance has been inferred for any of them. The roadmap left this
explicitly undecided: "whether to annotate a sample of the 553 dense-exclusive
pairs."

The user's 2026-09-16 priority ordering (see project memory
`project_nexus_roadmap_priority_order`) mandated a **pre-registered stratified
sample**, not exhaustive annotation of all 553, before this question could be
closed.

## 2. Primary estimand

This design tests a single, explicit hypothesis: **whether the population
relevance rate among the 553 dense-exclusive pairs exceeds the BM25-derived
reference rate of 14/108 (≈0.1296)**, established by the frozen gold set
(`fa75753`, `data/annotations/ted_at_scale_gold_set_v1.json`, distribution
`{0: 94, 1: 3, 2: 5, 3: 6}`, relevant = score ≥1).

The stratification below is a **sampling design decision** — it exists to get an
efficient, demand-balanced, unbiased draw from the 553-pair population — and is
**not** a second hypothesis test. No formal per-stratum significance test is
pre-registered; per-stratum counts may be reported descriptively only.

## 3. Population and strata

Verified directly against the frozen `data/experiments/phase2_v4/
ted_at_scale_dense_retrieval_results.json` (`2abefb3`) and `data/experiments/
phase2_v4/ted_at_scale_pool_coverage_metrics.json` (`a37b82a`):

- **N = 553** dense-exclusive, unscored pairs across 30 demands.
- **Stratum A (BM25-zero-pool demands):** 11 demands where the BM25 pool was
  empty (`n_pool == 0` in the pool-coverage metrics). Each contributes exactly 20
  candidates (dense's `limit_per_method`). **N_A = 220.**
- **Stratum B (BM25-nonempty-pool demands):** the remaining 19 demands, each
  contributing between 9 and 20 dense-exclusive candidates. **N_B = 333.**
- N_A + N_B = 553, confirmed by direct computation over both source files.

## 4. Sample size (power calculation)

Exact one-sided binomial test (chosen over the normal approximation given the
project's established preference for exact counts, e.g. the pool-yield 14/108
figure):

- H0: p = 14/108 ≈ 0.1296 (gold-set reference rate)
- H1: p = p1 = 0.25 (minimum scientifically relevant effect: +12pp over the
  reference rate; not simply the largest number that "worked" — see §7 for the
  alternative values considered and rejected)
- α = 0.05 (one-sided), target power = 0.80

Smallest n satisfying both constraints, found by exhaustive search over n and
critical value c (reject H0 if the observed relevant count ≥ c):

**n = 66, c = 14, actual α = 0.0415, achieved power = 0.8013.**

(`scipy.stats.binom`, exhaustive search 10 ≤ n ≤ 200; computation is
reproducible from the parameters above.)

## 5. Allocation across strata

Proportional to stratum size, sampling fraction 66/553 ≈ 11.93%:

- n_A = round(220 × 66/553) = **26**
- n_B = round(333 × 66/553) = **40**
- n_A + n_B = 66.

## 6. Allocation within each stratum, across demands

Equal per demand within a stratum, largest-remainder rounding, capped at each
demand's actual pool size (no cap bound in this design), remainder assigned to
demands in ascending lexicographic order of `demand_id` (a fully deterministic,
disclosed tie-break rule — arbitrary in content, not in reproducibility).

**Stratum A (n_A=26, base 2/demand, 4 remainders):**

| demand_id | allocated | pool size |
|---|---|---|
| 122428-2024 | 3 | 20 |
| 146289-2024 | 3 | 20 |
| 158024-2024 | 3 | 20 |
| 221305-2025 | 3 | 20 |
| 273005-2025 | 2 | 20 |
| 410719-2024 | 2 | 20 |
| 588217-2024 | 2 | 20 |
| 642378-2025 | 2 | 20 |
| 654218-2024 | 2 | 20 |
| 794374-2025 | 2 | 20 |
| 820594-2025 | 2 | 20 |

**Stratum B (n_B=40, base 2/demand, 2 remainders):**

| demand_id | allocated | pool size |
|---|---|---|
| 104441-2025 | 3 | 19 |
| 137639-2024 | 3 | 20 |
| 140590-2024 | 2 | 16 |
| 200095-2024 | 2 | 20 |
| 22543-2024 | 2 | 19 |
| 264820-2024 | 2 | 19 |
| 268550-2024 | 2 | 18 |
| 277089-2025 | 2 | 17 |
| 315512-2025 | 2 | 19 |
| 368294-2025 | 2 | 19 |
| 380300-2024 | 2 | 20 |
| 42938-2024 | 2 | 20 |
| 454027-2024 | 2 | 10 |
| 498443-2025 | 2 | 20 |
| 566290-2025 | 2 | 16 |
| 584867-2024 | 2 | 20 |
| 696940-2025 | 2 | 19 |
| 814207-2025 | 2 | 13 |
| 89204-2025 | 2 | 9 |

## 7. Alternative p1 values considered and rejected

p1=0.30 (+17pp) was the first candidate but rejected as an arbitrarily
comfortable target rather than a minimum scientifically relevant effect.
p1=0.20 (+7pp) was rejected as too close to the reference rate to be
practically distinguishable from noise given this project's annotation scale.
No prior project precedent fixes a value for this specific proportion test —
`docs/empirical-study-protocol.md`'s θ=0.2 standardized effect is a different
design (paired Wilcoxon on nDCG gain) and does not transfer. p1=0.25 was
selected as the minimum increase that would justify the claim that dense
retrieval's exclusive candidates carry a materially different relevance
profile than BM25's pool.

## 8. Selection procedure within each demand

Uniform random draw without replacement from each demand's dense-exclusive
candidate list, using Python's `random.Random(seed=104)` (seed fixed and
disclosed here, before the sampling script is written or run — the milestone
label "#104" is reused as the seed for traceability, not for any statistical
property). Top-k-by-score selection was explicitly rejected: it would answer
"are dense's most-confident picks relevant?", a narrower and different
question than the population estimand in §2, and would bias the estimate
upward.

## 9. Decision rule

Count relevant pairs (score ≥1 on the existing 0–3 scale) among the 66 sampled
pairs, after adjudication.

- **≥14 relevant → reject H0; the observed dense-exclusive relevance rate
  provides evidence that the population rate exceeds the BM25-derived
  reference rate of 14/108.** This does not establish *why* BM25 missed these
  pairs, and does not by itself establish that dense retrieval is
  intrinsically superior — it tests only the prespecified enrichment
  hypothesis in §2.
- **<14 relevant → fail to reject H0.** Report as inconclusive/negative, a
  final, publishable outcome (per [[feedback_methodological_rigor]] Rule 4) —
  not retried, not rescoped, not treated as a reason to relax the threshold.

This is a **one-shot decision**: no optional stopping, no re-drawing, no
adjusting n or c after seeing any label.

## 10. Annotation protocol

Same discipline as the frozen 108-pair gold set and the (parked) 220-pair
batch: blind export (candidate identity visible, source method hidden),
independent dual annotation (Valentín + Lydia), 0–3 relevance scale,
disagreements adjudicated under the same contract used for the gold set. Kept
as its own sealed artifact — disjoint by construction from both the 108-pair
gold set and the parked 220-pair batch (per
[[feedback_methodological_rigor]] Rule 3).

## 11. Disclosed limitations

- **p0 is an estimate, not a known constant.** 14/108 comes from a finite
  sample and carries its own sampling uncertainty. The final analysis will
  report a confidence interval on p0 (e.g. Wilson) alongside the binomial
  test result, rather than treating 0.1296 as fixed truth.
- **Clustering within demands.** Pairs are nested within demands (up to 3
  pairs drawn from the same demand — see §6), the same structure the existing
  108-pair gold set already has. The exact binomial test in §4 assumes
  independent Bernoulli trials across all 66 pairs. Because that assumption
  is not strictly met, **the reported α=0.0415 and power=0.8013 are
  design-stage operating characteristics under the independence
  approximation, not guaranteed realized Type-I error or power under the
  true clustered population.** This is a known simplification consistent
  with existing project precedent (the gold set itself), not a new one
  introduced here, and is disclosed rather than hidden behind the p0-CI
  caveat above.

## 12. What happens next (not part of this design)

A deterministic sampling script implementing §5–§8 will be written next. It
must refuse to run unless the parameters in this document (n=66, n_A=26,
n_B=40, seed=104, the per-demand allocation table in §6) are already
committed to the repo — the script consumes this design, it does not decide
it.
