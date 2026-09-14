# INVENES Population Adequacy Probe — Closure

**Status:** Closed as pre-registered decision rule dictates: **OPERATIONALLY_CONSTRAINED / UNRESOLVED**
**Date:** 2026-09-14
**Pre-registration:** `docs/phase2-invenes-population-adequacy-probe-preregistration.md`

## 1. What happened

Per the pre-registered design: 10 independent, specific, multi-word technical
queries, first 4 non-PCT referencias each (40 total, fixed in advance). One
deviation, decided before any classification outcome was observed: the
"see first latest publications" toggle proved unreliable to script
(intermittent HTTP 504 on resubmit) and was dropped; the underlying sampling
rule (first 4 non-PCT, as returned) was otherwise unchanged.

Harvesting hit the same OEPM-side rate limit/block observed in both prior
batches, this time after **18/40** referencias — worse than the 45/135 the
coverage-characterization batch achieved, consistent with the block window
not having fully cleared since that run.

## 2. Result, exactly as the pre-registered rule requires

Per §4 of the pre-registration: *"Rate-limited before the 40 are harvested:
Marked operationally constrained / unresolved, not forced past."* That rule
fires here. The partial data is reported, not discarded, but **no A/B
conclusion is drawn** — forcing one would be exactly the "keep sorting the
limit" behavior this probe was designed to avoid.

Full report: `data/experiments/oepm_v1/invenes_population_adequacy_probe.json`.

Partial data (18/40 harvested):
- **4 included (10% of 40 attempted, 22% of 18 harvested)** — the harvested-only
  rate is close to the smoke-test batch's 20% and well above the
  coverage-characterization batch's 6.7%, suggesting the "specific multi-word
  query" strategy change is directionally working, but N=18 is too small to
  treat as confirmatory.
- 7 excluded_kind_code (T1/T2/T3 — several queries ("algoritmo de detección de
  fraude", "revestimiento anticorrosivo") returned EP-ES-heavy result sets
  before hitting the block).
- 7 excluded_missing_text.
- Per-query harvested counts are uneven (4/4 for the first 4 queries, 0/4 for
  the last 4) — an artifact of hitting the rate limit partway through, not a
  property of those specific queries.

## 3. Disposition (unchanged framing, now with one more data point)

> **§11.3: PASS (unchanged).**
> **Corpus scalability: NOT YET DETERMINED.** This probe neither confirms nor
> rules out population adequacy — it is inconclusive by design, exactly as
> pre-registered, because the rate limit fired before the capped sample
> completed.
> **Throughput ceiling: now observed three times** (build_oepm_corpus.py:
> blocked then cleared on retry at ~40; coverage_characterization.py: blocked
> at 45/135; this probe: blocked at 18/40) — the ceiling is real, reproducible,
> and appears to vary run-to-run depending on how recently prior requests were
> made, not a fixed count.
> **#104: still blocked.**

## 4. What this probe does answer

Even though it cannot settle population adequacy, it strengthens one thing:
the **query-design lever is real** — 4/18 (22%) on specific multi-word
queries vs. 3/45 (6.7%) on generic single/double-word queries, on comparably
small samples. That is now two independent, disjoint batches pointing the
same direction, though neither alone is a statistical comparison.

## 5. Next decision (not taken here)

Per the "no simultaneous (a)+(b)" instruction, this closure does not
recommend opening a second source. The honest state is: query design looks
promising, throughput is the binding constraint, and a repeat of this exact
probe (same pre-registration, same decision rule) after deliberately waiting
out the rate-limit window is the next logical step before concluding A, B, or
opening a second source. That wait was not attempted in this session.

## 6. Non-goals

- Does not modify either prior batch's frozen data or reports.
- Does not retry the probe within this session (would violate the
  pre-registration's single-capped-attempt design and the "not sorting the
  limit" principle).
- Does not decide between scaling INVENES further and opening a second
  source — deferred.
