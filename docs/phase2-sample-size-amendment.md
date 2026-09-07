# Phase 2 Sample Size Amendment: N=60 (pre-registered) → N=48 (available)

**Status:** Closed (2026-09-07). This is a **methodological amendment record**, kept
separate from `docs/empirical-study-protocol.md` §3.2 by design: the protocol's frozen
pre-registered target ($|\mathcal{D}| = 60$) and its artifact
(`data/experiments/power_analysis_wilcoxon.json`) are not rewritten or restated here as
if they had always said 48. This document records what happened *after* pre-registration,
not a correction to it.

## What was pre-registered

`docs/empirical-study-protocol.md` §3.2: $|\mathcal{D}| = 60$, the minimum $N$ at which
the pre-registered Monte Carlo power analysis reaches $\widehat{\text{Power}}(N) \ge 0.80$
for the pre-registered minimum effect $\theta = 0.2$ (small). Frozen at
`data/experiments/power_analysis_wilcoxon.json` before any Phase 2 result existed.

## What acquisition actually produced

A source feasibility search for real, Spain-origin, `Technology request`-construct
demands was run against predefined acceptance criteria (public reproducible access,
compatible demand construct, origin verified by the real `DefaultOriginResolver`/ADR
0003, deduplicable identifier). Full source-by-source record:
`docs/phase2-demand-acquisition-audit.md`.

Eleven candidate sources were evaluated. Three yielded usable records — InnoGet (41),
the EEN Partnering Opportunities Database (5), and its Lombardia regional mirror (2 net
new after exact `POD Reference` deduplication) — for **48** verified, deduplicated
Spain-origin demands. The remaining eight yielded zero usable records: construct
mismatch (funding-consortium partner search, funding-programme listings), inactive
sites, or gated behind authentication.

This is recorded as **the observed acquisition ceiling under the evaluated public
sources and the stated acceptance criteria** — not a claim about the total worldwide
population of Spanish technology demands, and not evidence of insufficient search
effort. A different set of sources or looser criteria might, in principle, surface more;
the eight rejections are exactly the record of what was tried and why it didn't count.

## What was not done to reach 60

* The Spain-origin eligibility criterion was not relaxed.
* No observation was fabricated or imputed.
* No incompatible demand construct (e.g. a funding-consortium partner search) was mixed
  in to pad the count.
* `config/policies/data/jurisdiction_policy.json` was not edited to reclassify ambiguous
  or foreign records as Spanish.
* `data/experiments/power_analysis_wilcoxon.json` was not modified.

## Sensitivity check

A power computation under the **identical** frozen design (same seed, calibration,
$\alpha = 0.05$, $B = 10{,}000$ Monte Carlo iterations, $\theta = 0.2$) was run for
$N = 48$: `data/experiments/power_analysis_wilcoxon_n48_sensitivity.json`.

| $N$ | $\widehat{\text{Power}}$ |
|---:|---:|
| 60 (frozen) | 0.8164 |
| 48 (available) | 0.725 |

The sensitivity artifact's calibrated location (`0.17333984375`) is identical to the
frozen artifact's, confirming this is the same design evaluated at a different $N$, not
a re-fit or re-calibration of the effect.

## Consequence for interpretation

Phase 2 proceeds with $|\mathcal{D}| = 48$. The ~9-point reduction in power to detect the
pre-registered small effect ($\theta = 0.2$) relative to the $N=60$ design is an
explicit, declared limitation of any confirmatory result drawn from this corpus — not a
silent deviation, and not a reason by itself to consider $N=48$ results uninformative.
