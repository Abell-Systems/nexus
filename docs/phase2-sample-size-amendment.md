# Phase 2 Sample Size Amendment: N=60 (pre-registered) → N=39 (available)

**Status:** Closed (2026-09-07), **corrected twice (2026-09-07)**. This is a
**methodological amendment record**, kept separate from
`docs/empirical-study-protocol.md` §3.2 by design: the protocol's frozen pre-registered
target ($|\mathcal{D}| = 60$) and its artifact
(`data/experiments/power_analysis_wilcoxon.json`) are not rewritten or restated here as
if they had always said 39. This document records what happened *after*
pre-registration, not a correction to it.

> **Correction history:**
> 1. This amendment originally closed at **N=48** (merged as PR #53), counting 5
>    EEN-sourced records that pass ADR 0003 origin verification but were never checked
>    against the pre-registered content-completeness criterion (§4.1).
> 2. Corrected to **N=43** (submitted as PR #54: 41 InnoGet + 0 EEN + 2 Lombardia) once
>    that check was applied to EEN and found all 5 fail it.
> 3. PR #54's own review found that N=43 still hadn't actually run the 41 InnoGet
>    records through the real content-completeness check — it had only asserted they
>    would pass. Running the real `InnoGetExtractor` → `DefaultOriginResolver` →
>    `InnogetHtmlNormalizer` pipeline over all 41 found 1 with no description at all and
>    3 more under the protocol's literal 25-word threshold. Corrected to **N=39**: 37
>    InnoGet + 0 EEN + 2 Lombardia.
>
> Full finding for each step: `docs/phase2-demand-acquisition-audit.md`. Every prior
> figure and its sensitivity artifact (N=48, N=43) is retained unmodified as part of the
> trail, not deleted.

## What was pre-registered

`docs/empirical-study-protocol.md` §3.2: $|\mathcal{D}| = 60$, the minimum $N$ at which
the pre-registered Monte Carlo power analysis reaches $\widehat{\text{Power}}(N) \ge 0.80$
for the pre-registered minimum effect $\theta = 0.2$ (small). Frozen at
`data/experiments/power_analysis_wilcoxon.json` before any Phase 2 result existed.

## What acquisition actually produced

A source feasibility search for real, Spain-origin, `Technology request`-construct
demands was run against predefined acceptance criteria (public reproducible access,
compatible demand construct, origin verified by the real `DefaultOriginResolver`/ADR
0003, deduplicable identifier, and — enforced from the second correction onward —
content completeness per §4.1, checked by actually running the real production
extraction/normalization pipeline rather than assumed from platform structure). Full
source-by-source record: `docs/phase2-demand-acquisition-audit.md`.

Eleven candidate sources were evaluated. Two yield usable, content-complete,
empirically-verified records — InnoGet (37 of 41 origin-verified) and the Lombardia
regional mirror of the EEN Partnering Opportunities Database (2 net new after exact
`POD Reference` deduplication, both independently confirmed to carry a substantive
`Abstract`) — for **39** verified, deduplicated, content-complete Spain-origin demands.
The EEN Partnering Opportunities Database's own site yielded 5 origin-verified records,
none of which carry a substantive technical description. The remaining eight sources
yielded zero usable records: construct mismatch, inactive sites, or gated behind
authentication.

This is recorded as **the observed acquisition ceiling under the evaluated public
sources and the stated acceptance criteria** — not a claim about the total worldwide
population of Spanish technology demands, and not evidence of insufficient search
effort.

## What was not done to reach 60

* The Spain-origin eligibility criterion was not relaxed.
* No observation was fabricated or imputed.
* No incompatible demand construct (e.g. a funding-consortium partner search) was mixed
  in to pad the count.
* `config/policies/data/jurisdiction_policy.json` was not edited to reclassify ambiguous
  or foreign records as Spanish.
* `data/experiments/power_analysis_wilcoxon.json` was not modified.
* The content-completeness criterion (§4.1) was not relaxed, reinterpreted, or waived
  for records with genuine but short technical text (InnoGet's 3 borderline records, all
  under the 25-word line, were excluded rather than exempted) once the gap was found.
* The count was not asserted from platform-level structure ("InnoGet pages generally
  have descriptions") in place of running the actual per-record check, once that
  shortcut was identified as insufficient.

## Sensitivity check

A power computation under the **identical** frozen design (same seed, calibration,
$\alpha = 0.05$, $B = 10{,}000$ Monte Carlo iterations, $\theta = 0.2$) was run for
$N = 39$: `data/experiments/power_analysis_wilcoxon_n39_sensitivity.json`.

| $N$ | $\widehat{\text{Power}}$ |
|---:|---:|
| 60 (frozen) | 0.8164 |
| 48 (superseded — see correction 1) | 0.725 |
| 43 (superseded — see correction 2) | 0.674 |
| 39 (available, corrected) | 0.6216 |

The sensitivity artifact's calibrated location (`0.17333984375`) is identical to the
frozen artifact's and to both superseded ones, confirming this is the same design
evaluated at a different $N$, not a re-fit or re-calibration of the effect.

## Consequence for interpretation

Phase 2 proceeds with $|\mathcal{D}| = 39$. The reduction in power to detect the
pre-registered small effect ($\theta = 0.2$) relative to the $N=60$ design — roughly 20
points — is an explicit, declared limitation of any confirmatory result drawn from this
corpus, not a silent deviation. It is also, at this point, a large enough gap that it is
reasonable for the next step to include an explicit discussion with the study owner of
whether $N=39$ remains an acceptable basis for a confirmatory Phase 2 test, or whether
the reduced power changes what kind of claim the study can support — that discussion is
intentionally not resolved unilaterally here.

The corpus-freeze step (planned next) will materialize exactly these 39 records
(demand_id, source, canonical URL, title, description, posted/discovery date, origin
evidence, and — for EEN/Lombardia-sourced records — the shared `POD Reference`) into a
hashed, frozen dataset artifact, reusing the same `InnoGetExtractor` /
`DefaultOriginResolver` / `InnogetHtmlNormalizer` pipeline used for this verification
rather than re-deriving the numbers by hand.
