# Scientific interpretation of the corrected classification — the denominator problem

Source: `screening_table_consolidated.csv` (tag `paper-data-milestone-2026-09-22`,
merged into `main` at `00eec15`). No new data acquired for this analysis — it
recomputes the same 872-family classification along a different axis (rate,
not count), adds confidence intervals, and a formal significance test for the
one contrast large enough to support it.

**Non-independence note.** Some patent families match more than one
compound's search (4 of the 872 unique families), so the 952 per-compound
rows this analysis is built from — and any pooled or per-compound count
derived from them — are **not mutually exclusive, independent observations**.
This is fine for descriptive per-compound rates and for the one specific
two-proportion test below (Eribulin and Cytarabine's screened sets do not
overlap with each other), but any future test that pools across compounds or
treats the 952 rows as an i.i.d. sample would need to account for this.

## 1. The headline "Cytarabine leads" is an absolute-count artifact, not
   necessarily a relevance-propensity finding

| Compound | Screened (n) | Relevant (k) | Rate | 95% Wilson CI |
|---|---:|---:|---:|---|
| Enfortumab vedotin | 6 | 4 | 66.7% | [30.0%, 90.3%] |
| Plitidepsin | 4 | 2 | 50.0% | [15.0%, 85.0%] |
| Omega-3 acid ethyl esters | 4 | 2 | 50.0% | [15.0%, 85.0%] |
| Polatuzumab vedotin | 9 | 4 | 44.4% | [18.9%, 73.3%] |
| Eribulin mesylate | 18 | 8 | 44.4% | [24.6%, 66.3%] |
| **Cytarabine** | **690** | **123** | **17.8%** | **[15.2%, 20.9%]** |
| Trabectedin | 53 | 6 | 11.3% | [5.3%, 22.6%] |
| Brentuximab vedotin | 67 | 7 | 10.4% | [5.2%, 20.0%] |
| Ziconotide | 18 | 1 | 5.6% | [1.0%, 25.8%] |
| Vidarabine | 81 | 4 | 4.9% | [1.9%, 12.0%] |
| Omega-3 carboxylic acid | 1 | 0 | 0.0% | [0.0%, 79.3%] |
| Lurbinectedin | 1 | 0 | 0.0% | [0.0%, 79.3%] |

By absolute count, Cytarabine dominates (123 of 161 compound-family
observations, 76%). By **rate** — the fraction of each compound's screened
Spain-relevant universe that turned out substantively relevant — Cytarabine
ranks **6th of 12**, behind five compounds with smaller screened universes.
See `figures/figure10_relevance_rate_by_compound.png`.

## 2. Four of those five higher rates are too imprecise to compare; one — Eribulin — is formally tested

Confidence intervals were computed with the Wilson score interval (appropriate
for small-sample proportions). Four compounds — Enfortumab vedotin (n=6),
Plitidepsin (n=4), Omega-3 acid ethyl esters (n=4), and Polatuzumab vedotin
(n=9) — have intervals 45–60 percentage points wide. A single re-classified
family in Plitidepsin's or Omega-3 acid ethyl esters' screened set (n=4)
would swing the rate by 25 points. **Their rate estimates are imprecise and
insufficient to support a comparative claim against Cytarabine** — not
evidence that the true rate is either higher or lower than Cytarabine's,
just too little data to say either way.

**Eribulin mesylate vs. Cytarabine is the one contrast large enough to test
formally**, rather than relying on the visual heuristic of non-overlapping
confidence intervals (which is not itself a significance test). Fisher's
exact test on the 2×2 table (Eribulin: 8/18 relevant; Cytarabine: 123/690
relevant) gives:

- Odds ratio 3.69, **p = 0.0093** (two-sided)
- Risk difference: +26.6 percentage points, 95% CI [3.5, 49.8]
- Risk ratio: 2.49, 95% CI [1.45, 4.28]

This supports treating Eribulin's higher rate as a genuine difference rather
than sampling variation — but the confidence intervals on the effect size are
themselves wide (risk difference as low as 3.5 points, risk ratio as low as
1.45), reflecting that n=18 is still a small sample. This is a **rate
difference worth qualitative investigation** into what distinguishes
Eribulin's 8 relevant families from Cytarabine's 123 (e.g. whether Eribulin's
more specific compound name yields fewer Incidental-Mention Markush-list
hits than a 60-year-old generic name like "cytarabine" is a hypothesis to
test against the evidence, not a conclusion this analysis establishes).
Reproducible in `figures/eribulin_vs_cytarabine_test.txt`.

## 3. Cytarabine's own rate is not anomalously low relative to the rest of the corpus

A natural worry: is Cytarabine's huge screened universe (690, 72% of the
total 952 compound-family observations) dragging down an otherwise-strong
corpus-wide relevance signal? Checked directly:

- Pooled rate across all 12 compounds: 161/952 = **16.9%**
- Pooled rate **excluding Cytarabine** (the other 11 compounds combined):
  38/262 = **14.5%**
- Cytarabine's own rate: **17.8%**

Cytarabine's rate is actually *slightly above*, not below, the rest of the
corpus's pooled rate (both descriptive figures — see the non-independence
note above on treating these as inferential comparisons). Its rate estimate
is the most statistically precise one in the dataset (tightest CI, by far
the largest n), not a diluted one. What *is* true is that Cytarabine's
absolute count (123) so dominates the 161 compound-family total that an
unweighted, per-compound average would overweight the small-n compounds
(e.g. an unweighted mean of the 12 per-compound rates is 25.5%, pulled up by
the noisy small-n compounds). The median per-compound rate is 14.6%,
providing a complementary unweighted summary of the per-compound
distribution — descriptively close to both Cytarabine's rate and the
ex-Cytarabine pooled rate, though which summary (pooled, median, or
unweighted mean) is the right one to report depends on the specific question
being asked (total-volume signal vs. typical-compound signal).

## 4. Classification composition (denominator context for "157 relevant families")

Of the 872 unique Spain-relevant families found across all 12 compounds:
- 91 Directly Relevant (10.4%)
- 66 Indirectly Relevant (7.6%)
- 712 Incidental Mention (81.7%)
- 3 Uncertain (0.3%)

This corpus-wide 81.7% (712/872, all 12 compounds combined) is consistent
with the ~78% expectation reported in the earlier jurisdiction-pull analysis
(`minesoft_global_2000_2025_family_jurisdictions/README.md`). That earlier
figure was itself an already-observed rate from a smaller, all-compound
23-family `cc=ES` sample (18/23 Incidental, dominated by Brentuximab
vedotin's 17 families, not Cytarabine-specific) — an exploratory
expectation carried forward from an earlier, smaller pull, not a
prospectively pre-specified prediction. "Consistent with" is the accurate
characterization; the two figures answer the same corpus-wide question on
different sample sizes, not a prediction-vs-confirmation pair. (Cytarabine's
own Incidental rate in the new data, 565/690 = 81.9%, is close to the
corpus-wide 81.7% by coincidence of scale — Cytarabine is 79% of the
872-family universe — not because the old 78% figure was about Cytarabine
specifically.)

## 5. What this means for the paper, and what it doesn't

**Supports:** stating both the absolute count and the rate whenever
Cytarabine's dominance is discussed (already done in the Figure 4 prose per
the manuscript integration), and reporting Eribulin mesylate's higher rate —
now backed by a formal test, not just non-overlapping intervals — as worth a
follow-up qualitative note.

**Does not support:** re-ranking compounds by rate as if it were a more
"correct" measure than absolute count — for 4 of the 5 compounds with rates
above Cytarabine's, the sample size makes the rate estimate too imprecise to
compare. Rate and count answer different questions (propensity vs. volume)
and the paper should present both, not pick one as authoritative.

**Does not, by itself,** justify a new data pull. This analysis is entirely
a recomputation of the already-frozen 872-family classification; it doesn't
identify a gap that more Minesoft data would close (the small-n compounds
are small because their real-world screened universe is small — Plitidepsin
genuinely only had 4 Spain-relevant families to screen, not because of an
incomplete search).

## Artifacts produced

- `figures/figure10_relevance_rate_by_compound.png` — rate per compound with
  95% Wilson CI, n annotated. Color flags n≥30 vs n<30 as a labeling
  convention, not a statistical claim of precision — the interval width
  itself is what shows precision.
- `figures/relevance_rate_by_compound.csv` — the underlying rate/CI table.
- `figures/eribulin_vs_cytarabine_test.txt` — the formal two-proportion test
  output (Fisher's exact, risk difference, risk ratio).
- `figures/build_relevance_rate_analysis.py` — reproduces all three above
  from `screening_table_consolidated.csv`.
