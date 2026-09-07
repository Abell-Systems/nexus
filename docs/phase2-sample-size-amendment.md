# Phase 2 Sample Size Amendment: N=60 (pre-registered) → N=43 (available)

**Status:** Closed (2026-09-07), **corrected (2026-09-07)**. This is a **methodological
amendment record**, kept separate from `docs/empirical-study-protocol.md` §3.2 by
design: the protocol's frozen pre-registered target ($|\mathcal{D}| = 60$) and its
artifact (`data/experiments/power_analysis_wilcoxon.json`) are not rewritten or restated
here as if they had always said 43. This document records what happened *after*
pre-registration, not a correction to it.

> **Correction history:** this amendment originally closed at N=48 (merged as PR #53).
> A follow-up content-completeness check (§4.1's substantive-description requirement,
> which the original acquisition audit never applied) found that the 5 EEN-sourced
> records counted toward that 48 do not independently satisfy it. Corrected: **N=43**.
> Full finding: `docs/phase2-demand-acquisition-audit.md`, "Post-closure correction:
> EEN content-completeness". The N=48 figure and its sensitivity artifact
> (`data/experiments/power_analysis_wilcoxon_n48_sensitivity.json`) are retained
> unmodified as part of the trail, not deleted.

## What was pre-registered

`docs/empirical-study-protocol.md` §3.2: $|\mathcal{D}| = 60$, the minimum $N$ at which
the pre-registered Monte Carlo power analysis reaches $\widehat{\text{Power}}(N) \ge 0.80$
for the pre-registered minimum effect $\theta = 0.2$ (small). Frozen at
`data/experiments/power_analysis_wilcoxon.json` before any Phase 2 result existed.

## What acquisition actually produced

A source feasibility search for real, Spain-origin, `Technology request`-construct
demands was run against predefined acceptance criteria (public reproducible access,
compatible demand construct, origin verified by the real `DefaultOriginResolver`/ADR
0003, deduplicable identifier, and — added after the correction below — content
completeness per §4.1). Full source-by-source record:
`docs/phase2-demand-acquisition-audit.md`.

Eleven candidate sources were evaluated. Two yield usable, content-complete records —
InnoGet (41) and the Lombardia regional mirror of the EEN Partnering Opportunities
Database (2 net new after exact `POD Reference` deduplication) — for **43** verified,
deduplicated, content-complete Spain-origin demands. The EEN Partnering Opportunities
Database's own site yielded 5 origin-verified records, none of which carry a
substantive technical description (see the correction note above) and are therefore not
counted. The remaining eight sources yielded zero usable records: construct mismatch
(funding-consortium partner search, funding-programme listings), inactive sites, or
gated behind authentication.

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
* The content-completeness criterion (§4.1) was not relaxed or reinterpreted to let a
  short title stand in for a substantive description, once the gap was found.

## Sensitivity check

A power computation under the **identical** frozen design (same seed, calibration,
$\alpha = 0.05$, $B = 10{,}000$ Monte Carlo iterations, $\theta = 0.2$) was run for
$N = 43$: `data/experiments/power_analysis_wilcoxon_n43_sensitivity.json`.

| $N$ | $\widehat{\text{Power}}$ |
|---:|---:|
| 60 (frozen) | 0.8164 |
| 48 (superseded — see correction) | 0.725 |
| 43 (available, corrected) | 0.674 |

The sensitivity artifact's calibrated location (`0.17333984375`) is identical to the
frozen artifact's, confirming this is the same design evaluated at a different $N$, not
a re-fit or re-calibration of the effect.

## Consequence for interpretation

Phase 2 proceeds with $|\mathcal{D}| = 43$. The ~14-point reduction in power to detect
the pre-registered small effect ($\theta = 0.2$) relative to the $N=60$ design is an
explicit, declared limitation of any confirmatory result drawn from this corpus — not a
silent deviation, and not a reason by itself to consider $N=43$ results uninformative.
The corpus-freeze step (planned next) will run InnoGet's 41 records through the real,
already-tested `InnogetHtmlNormalizer`, which independently enforces the same
content-completeness check; any further attrition found there will be recorded the same
way this correction was.
