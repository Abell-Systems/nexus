# INVENES Population Adequacy Probe — Repeat Run Closure

**Status:** Closed as pre-registered decision rule dictates: **SCENARIO_A_SIGNAL**
**Date:** 2026-09-15
**Pre-registration:** `docs/phase2-invenes-population-adequacy-probe-preregistration.md`
(unchanged — same script, same 10 queries, same sampling rule, same decision
thresholds; no criteria touched between the first run and this one)
**First run:** `docs/phase2-invenes-population-adequacy-probe-closure.md`
(closed `OPERATIONALLY_CONSTRAINED_UNRESOLVED` at `1da5703`)

## 1. What happened

Exact re-run of `experiments/oepm/population_adequacy_probe.py`, unmodified,
one day after the first attempt. Unlike the first run, the OEPM-side rate
limit did not fire this time: all 40/40 referencias harvested successfully.

## 2. Result, exactly as the pre-registered rule requires

Per §4 of the pre-registration, harvesting completed in full, so the rule
applies its A/B/inconclusive branch (not the operationally-constrained
branch this time):

- **Included: 11/40 attempted (27.5% yield).**
- `>= 8 included (>= 20% threshold)` → **SCENARIO_A_SIGNAL**.
- Dispositions: 11 included, 15 excluded_kind_code, 14 excluded_missing_text.
- Per-query included counts are uneven (0 to 3), consistent with query-level
  variance already observed in prior batches, not a new pattern.

Full report: `data/experiments/oepm_v1/invenes_population_adequacy_probe.json`
(overwrites the first run's file at this same path; the first run's exact
content remains recoverable in git history at `1da5703`, consistent with how
`build_oepm_corpus.py` and `coverage_characterization.py`'s outputs are
version-controlled by commit rather than by parallel filenames).

## 3. Disposition

> **§11.3: PASS (unchanged).**
> **Corpus scalability: SCENARIO_A_SIGNAL** — this specific-multi-word-query
> strategy sustains a yield (27.5%) above the pre-registered 20% threshold on
> a complete, uninterrupted 40-attempt sample. Per the pre-registration's own
> recommendation for this branch: reaching N>=60 needs roughly 7-8 more
> capped sessions of similar size (~300 total attempted) under the same
> query-design strategy — feasible via slow, multi-session pacing, not
> immediately achieved by this one probe.
> **Throughput ceiling:** did not fire this run — the rate limit is
> confirmed intermittent/session-dependent, not a fixed count, consistent
> with the "cleared once, didn't clear twice more" observation from the
> first run.
> **#104: still blocked.** This probe qualifies the *strategy*, not the
> corpus itself — N=60 net-included records have not yet been acquired, only
> shown to be plausibly reachable. Scaling the acquisition itself, and
> deciding when the corpus is safe to hand to #104, are follow-on decisions
> not taken by this closure.

## 4. Non-goals (unchanged from pre-registration)

- Does not modify either prior batch's frozen data or reports.
- Does not itself scale the acquisition to N>=60 — that is a follow-on,
  explicitly deferred decision.
- Does not touch #104 or ADR 0036.
