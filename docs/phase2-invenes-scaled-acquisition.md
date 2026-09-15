# INVENES Scaled Acquisition — Corpus Qualification

```text
QUESTION:  Can INVENES actually produce N>=60 net-included domestic patent
           records (ADR 0035 SS3/SS9 exclusions applied), not just plausibly?
INPUT:     The same 10 pre-registered multi-word technical queries from
           docs/phase2-invenes-population-adequacy-probe-preregistration.md,
           each query's next unused referencias in INVENES's own result
           order (no new query design, no manual curation).
METHOD:    Repeat experiments/oepm/build_oepm_corpus.py's harvest -> classify
           (ADR 0035 SS3/SS9) -> ingest pipeline, in capped ~40-referencia
           sessions, across queries, until included_count >= 60 or the query
           set is exhausted.
OUTPUT:    Sealed canonical OEPM corpus (Parquet) + EnhancedManifest +
           exclusion manifest + acquisition-session ledger.
VALIDITY:  Same query-design strategy already validated at SCENARIO_A_SIGNAL
           (27.5% yield, N=40, uninterrupted); this is execution of that
           strategy, not a new experiment -- no criteria change permitted.
STATUS:    IN PROGRESS.
```

**Status:** in progress
**Date opened:** 2026-09-15
**Precondition:** `docs/phase2-invenes-population-adequacy-probe-repeat-closure.md`
closed `SCENARIO_A_SIGNAL` (11/40 included, 27.5% yield, complete uninterrupted
run) — this doc executes that result's own recommendation, it does not
re-derive it.

## 1. What this is, and isn't

This is **mechanical execution of an already-decided protocol**, not a new
experiment. No query wording changes, no yield optimization, no relaxing
ADR 0035's exclusion criteria to hit N=60 faster. If the target queries are
exhausted before N=60 is reached, that is reported as a real finding (see §5),
not routed around.

## 2. Referencia sourcing (mechanical, disclosed)

The population-adequacy probe used only the first 4 non-PCT referencias per
query. This acquisition continues down the **same 10 queries**, in the same
query order, taking each query's *next* unused referencias in INVENES's own
result order (positions 5, 6, 7, ... as returned) — never re-querying, never
picking non-sequential results, never swapping in a different query because
an earlier one looked more promising. Referencia IDs are read from the live
INVENES search UI (no scripted JSF search client exists — the search form is
stateful; this mirrors exactly how the probe's own `REFERENCIA_BY_QUERY` list
was originally compiled) and appended to
`experiments/oepm/scaled_acquisition_referencias.py` before any harvesting
begins for that session, so the referencia list for a session is fixed before
any classification outcome from that session is observed.

## 3. Session design

- **Session size:** ~40 referencias attempted per session, matching the
  empirically observed throughput ceiling (18-45 requests/window across four
  prior runs) — large enough to be efficient, small enough to reduce forcing
  past the rate limit.
- **Pacing:** one session per sitting; no immediate retry within a session if
  the rate limit fires (same rule as the probe's own non-goals).
  `InvenesHarvester`'s existing idempotent harvest (skips already-fetched
  referencias) means a rate-limited session can safely resume later without
  re-fetching.
- **Session ledger:** every session's attempted/harvested/included counts are
  appended to `data/experiments/oepm_v1/scaled_acquisition_sessions.json` —
  cumulative running total is the only thing the stopping rule reads.

## 4. Stopping rule (fixed in advance)

Stop and freeze (§6) the moment cumulative `included_count >= 60` **after**
running each session's records through the real ADR 0035 SS3/SS9
classification (`build_oepm_corpus.py:classify_records`) — not the probe's
lighter disposition check, which doesn't verify `publication_date` or
`country_code`. If the 10-query set is exhausted (no more results to page
through for any query) before N=60, that is reported as-is: query-set
exhaustion under this strategy, not extended by inventing new queries
mid-run — opening more queries at that point is a new decision, made after
seeing the exhaustion, not before.

## 5. Non-goals

- Does not change the 10 queries, the ADR 0035 SS3/SS9 exclusion rules, or
  the "sequential, as-returned" sampling rule mid-acquisition.
- Does not retroactively fold the probe's own included records (4 from the
  first run, 11 from the repeat) into this corpus — those referencias were
  drawn from the same queries' first-4 positions and are already covered by
  §2's "next unused" rule, so there is no overlap to resolve, but the probes'
  *purpose* (testing adequacy) stays distinct from this batch's purpose
  (building the frozen corpus) per the existing workstream-isolation rule.
- Does not touch #104, ADR 0036, or the demand-side corpus.
- Does not declare the corpus sufficient by extrapolation — only an actual
  post-classification `included_count >= 60` triggers freeze.

## 6. Freeze procedure (on N>=60)

Exactly ADR 0035 §10/§11 step 4: `build_corpus()`'s existing pipeline already
produces a sealed Parquet canonical store + `.sha256` + `EnhancedManifest` +
exclusion manifest. On the session that crosses N=60, run it once against the
full accumulated referencia set, record the crossing session number in the
ledger, and update `[[project_nexus_oepm_corpus_state]]` (agent memory) and
`docs/scientific-model.md` §5 (`TECHNOLOGY` row) to reflect qualification.
Only then does ADR 0035 §11 step 6 (#104 resumption) become unblocked.
