# Scientific interpretation of the corrected classification — the denominator problem

Source: `screening_table_consolidated.csv` (tag `paper-data-milestone-2026-09-22`,
merged into `main` at `00eec15`). No new data acquired for this analysis — it
recomputes the same 872-family classification along a different axis (rate,
not count) and adds confidence intervals.

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
ranks **6th of 12**, behind five compounds with much smaller search
universes. See `figures/figure10_relevance_rate_by_compound.png`.

## 2. But most of those higher rates are not statistically trustworthy

Confidence intervals were computed with the Wilson score interval (appropriate
for small-sample proportions, unlike the normal approximation). Five
compounds — Enfortumab vedotin (n=6), Plitidepsin (n=4), Omega-3 acid ethyl
esters (n=4), and Polatuzumab vedotin (n=9) — have intervals 45–60 percentage
points wide. A single re-classified family in Plitidepsin's or Omega-3 acid
ethyl esters' screened set (n=4) would swing the rate by 25 points. **Their
rate estimates are imprecise and insufficient to support a comparative claim
against Cytarabine** — not evidence that the true rate is either higher or
lower, just too little data to say.

**Eribulin mesylate is the one exception worth taking seriously.** Although
its own CI [24.6%, 66.3%] is still fairly wide (n=18), it does not overlap
Cytarabine's [15.2%, 20.9%] at all — the separation between the two
intervals is large enough that this looks like a genuine rate difference,
not an artifact of the four smaller-n compounds' imprecision. This is the
strongest rate-based finding in the dataset and supports a qualitative
follow-up investigation into what distinguishes Eribulin's 8 relevant
families from Cytarabine's 123 — not a causal explanation the current data
can establish on its own (e.g. whether Eribulin's more specific compound
name structurally yields fewer Incidental-Mention Markush-list hits than a
60-year-old generic name like "cytarabine" is a hypothesis to test against
the evidence, not a conclusion drawn here).

## 3. Cytarabine's own rate is not anomalously low relative to the rest of the corpus

A natural worry: is Cytarabine's huge screened universe (690, 72% of the
total 952 compound-family observations) dragging down an otherwise-strong
corpus-wide relevance signal? Checked directly:

- Pooled rate across all 12 compounds: 161/952 = **16.9%**
- Pooled rate **excluding Cytarabine** (the other 11 compounds combined):
  38/262 = **14.5%**
- Cytarabine's own rate: **17.8%**

Cytarabine's rate is actually *slightly above*, not below, the rest of the
corpus's pooled rate. So the dominant narrative should not be that
Cytarabine's huge numbers make its rate estimate unreliable or diluted —
the opposite is true: its rate estimate is the most statistically precise
one in the dataset (tightest CI, by far the largest n)
and it sits squarely in the middle of the distribution, not as an outlier.
What *is* true is that Cytarabine's absolute count (123) so dominates the
161 compound-family total that any unweighted, per-compound summary
statistic (e.g. "average relevance rate across compounds" = 25.5%, pulled up
by the noisy small-n compounds) would misrepresent what the corpus actually
shows. The median per-compound rate (14.6%) is a better summary and sits
close to both Cytarabine's rate and the ex-Cytarabine pooled rate.

## 4. Classification composition (denominator context for "157 relevant families")

Of the 872 unique Spain-relevant families found across all 12 compounds:
- 91 Directly Relevant (10.4%)
- 66 Indirectly Relevant (7.6%)
- 712 Incidental Mention (81.7%)
- 3 Uncertain (0.3%)

The 81.7% Incidental Mention rate is itself a finding: for a generic,
60-year-old chemotherapy name like Cytarabine appearing in patent claims
mostly as one item in long Markush-style drug lists, this is expected and
matches the pre-registered concern from the original jurisdiction-pull
README (which predicted ~78% Incidental based on the earlier, smaller
23-family sample — the full-scale result, 81.7% for Cytarabine specifically
and 81.7% corpus-wide, essentially confirms that prediction rather than
overturning it).

## 5. What this means for the paper, and what it doesn't

**Supports:** stating both the absolute count and the rate whenever
Cytarabine's dominance is discussed (already done in the Figure 4 prose per
the manuscript integration), and flagging Eribulin mesylate's higher,
statistically distinguishable rate as worth a follow-up qualitative note.

**Does not support:** re-ranking compounds by rate as if it were a more
"correct" measure than absolute count — for 5 of the 6 compounds with rates
above Cytarabine's, the sample size makes the rate estimate too unreliable
to rank confidently. Rate and count answer different questions (propensity
vs. volume) and the paper should present both, not pick one as authoritative.

**Does not, by itself,** justify a new data pull. This analysis is entirely
a recomputation of the already-frozen 872-family classification; it doesn't
identify a gap that more Minesoft data would close (the small-n compounds
are small because their real-world screened universe is small — Plitidepsin
genuinely only had 4 Spain-relevant families to screen, not because of an
incomplete search).

## Artifacts produced

- `figures/figure10_relevance_rate_by_compound.png` — rate per compound with
  95% Wilson CI, n annotated, n<30 vs n>=30 flagged by color (dataviz skill:
  validated palette, secondary encoding via visible n-labels since color
  alone should never carry the "reliable vs. not" distinction).
