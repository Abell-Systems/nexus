# INVENES Coverage/Scalability Characterization — Closure

**Status:** Closed (partial data, honestly disclosed)
**Date:** 2026-09-14
**Scope:** Answers ADR 0035 §11.3's follow-up question — before scaling
acquisition toward N≥60, can INVENES alone provide a corpus large enough and
complete enough for the study? — via `experiments/oepm/coverage_characterization.py`,
kept strictly separate from `build_oepm_corpus.py`'s smoke-test batch.

## 1. Method

8 deliberately generic, domain-diverse queries (materials, pharma, agriculture,
textiles, combustion engines, food packaging, optics, batteries) — **not** the
3 TED-topic-aligned queries `build_oepm_corpus.py` used for the retrieval
smoke test, and disjoint from its 40 referencias by construction, per the
explicit instruction not to let the smoke-test queries become the scientific
sample. For each query, INVENES's own reported "Number of results" was
recorded, and page-1 (up to 20) referencias were harvested and classified
under the same ADR 0035 §3/§9 rules as the smoke-test batch.

## 2. What was obtained

135 referencias were queued; **45 were actually harvested** before a real,
reproducible rate limit/block from OEPM's infrastructure stopped further
progress (confirmed in isolation, outside this script, on a URL that had
previously succeeded — see `rate_limit_disclosure` in the report). The
remaining 90 are marked `not_harvested`, not silently dropped.

Full report: `data/experiments/oepm_v1/invenes_coverage_characterization.json`
(+ per-record detail in `..._records.json`).

## 3. Findings

- **Inclusion rate on this batch: 3/45 harvested (6.7%), 3/135 attempted (2.2%)**
  — far lower than the smoke-test batch's 8/40 (20%). The gap traces to query
  style, not corpus size: short generic terms surface disproportionately old
  (pre-2000-numbering) records, and **39/45 (87%) of this batch's harvested
  records had no "Resumen" (abstract) field** — the same missing-text pattern
  ADR 0035 §11.3 already flagged, now confirmed to worsen sharply for older,
  generically-queried records rather than being an isolated fluke.
- **Kind-code distribution** (of 45 harvested): A1=36, U=5, T3=1, A2/A3/A6=1
  each — dominated by application publications, consistent with the earlier
  finding.
- **No exact duplicate `publication_id`s** across the 8 queries.
- **Sum of INVENES's reported "Number of results" across the 8 queries:
  182,245** — explicitly **not** a usable eligible-population estimate (heavy
  query overlap, includes PCT/EP-ES/foreign records); reported for context
  only, per the report's own caveat.
- **A practical throughput ceiling, not a population ceiling**: both this run
  and `build_oepm_corpus.py`'s earlier run independently hit the same
  approximately-40-45-requests-per-window block. This is now itself the
  dominant characterization finding — it constrains acquisition *pacing*, not
  necessarily the *size* of the eligible population.

## 4. Interpretation — a third scenario, not just A/B

The proposed A ("INVENES has enough population") vs. B ("INVENES has a
practical ceiling, look elsewhere") framing turns out to conflate two
independent constraints this data separates:

- **Query specificity/era targeting** drives *yield* (6.7% generic vs. 20%
  topic-specific in the two batches gathered so far) — a corpus-construction
  strategy question, not a source-adequacy question.
- **Request pacing** drives *throughput* — an operational constraint
  (~40-45 requests/window), independent of how many eligible records exist.

Neither constraint, on its own, currently supports declaring INVENES
insufficient (scenario B) — but neither supports declaring it straightforwardly
sufficient (scenario A) either, since no run has yet sustained enough volume
to test population adequacy directly.

## 5. Disposition

> **§11.3: PASS — ingestion feasibility demonstrated** (unchanged).
> **Corpus scalability: NOT YET DETERMINED — characterized, not resolved.**
> Two independent, now-quantified constraints (query yield ~7-20%; throughput
> ~40-45 req/window) must both be designed around before any N≥60 acquisition
> attempt, not just "queried more."
> **#104: still blocked.**

## 6. Non-goals

- Does not attempt to scale past this characterization sample.
- Does not resolve whether to keep pursuing INVENES or open a second source —
  left as the next decision, informed by §4 above.
- Does not touch `build_oepm_corpus.py`'s frozen smoke-test corpus or its
  retrieval smoke test result.
