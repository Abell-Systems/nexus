# INVENES Population Adequacy Probe — Pre-Registration

**Status:** Pre-registered, not yet executed
**Date:** 2026-09-14
**Scope:** A single, predefined, capped acquisition attempt to determine
whether INVENES can plausibly produce ≥60 net-included domestic patent
records under a legitimate, reproducible acquisition strategy — before any
further scaling. Written and committed *before* execution, so the decision
rule cannot be adjusted after seeing results.

## 1. What changed from the prior two batches

- `build_oepm_corpus.py`'s smoke-test batch (3 queries, TED-topic-aligned):
  8/40 included (20%).
- `coverage_characterization.py`'s batch (8 queries, generic single/double-word
  terms): 3/45 harvested (6.7%) -- old, abstract-less records dominated.

Neither batch was *designed* to test population adequacy; both were
byproducts of other goals (smoke test, generic coverage sketch). This probe
is the first batch built specifically to answer: **can a deliberate
acquisition strategy sustain the yield needed to reach N>=60?**

## 2. Query design (fixed in advance)

10 independent, specific, multi-word technical phrases (not single/double
generic nouns -- the coverage batch's failure mode), spanning diverse domains,
none overlapping with either prior batch's query text:

1. sistema de refrigeración por absorción
2. dispositivo de monitorización de constantes vitales
3. método de reciclaje de baterías de litio
4. estructura modular de vivienda prefabricada
5. sistema de purificación de aire mediante fotocatálisis
6. algoritmo de detección de fraude en transacciones
7. revestimiento anticorrosivo para estructuras metálicas
8. sistema de riego automatizado por goteo
9. dispositivo de asistencia para movilidad reducida
10. método de fabricación aditiva de piezas metálicas

All 10 use INVENES's "see first latest publications" toggle (biases toward
recent, more-likely-to-have-an-abstract records -- a deliberate strategy
choice, not post-hoc filtering).

## 3. Sampling rule (fixed in advance, no manual curation)

The first 4 non-PCT referencias returned per query, in the order INVENES
returns them = 40 referencias total, matching the empirically observed
~40-45-requests-per-window ceiling from the two prior batches. No result is
excluded except PCT (a pre-existing, ADR-0035-independent rule, not specific
to this probe).

## 4. Decision rule (fixed in advance)

Applied to however many of the 40 are actually harvested before any rate
limit interrupts the run:

- **>= 8 included (>=20% yield, matching or beating the smoke-test batch):**
  Scenario A signal. At this rate, reaching N=60 needs ~7-8 more capped
  sessions of the same size (~300 total attempted) -- feasible via slow,
  multi-session pacing. Recommendation: proceed to a scaled, paced
  acquisition plan under this query-design strategy.
- **< 4 included (<10% yield):** Scenario B signal, consistent with the
  coverage-characterization batch. Recommendation: stop investing in INVENES
  query refinement; open a second legitimate source instead.
- **4-7 included (10-20%):** Inconclusive. Recommendation: one further capped
  batch of the same design before deciding -- not open-ended iteration.
- **Rate-limited before the 40 are harvested:** Marked **operationally
  constrained / unresolved**, not forced past. Whatever partial data exists
  is still reported (attempted/harvested/included), but no A/B conclusion is
  drawn from an incomplete run.

## 5. Non-goals

- Does not modify `build_oepm_corpus.py`'s frozen smoke-test corpus, its
  retrieval smoke test, or `coverage_characterization.py`'s report.
- Does not attempt a second acquisition session in the same sitting if the
  first is rate-limited -- that would violate the "not sorting the limit"
  principle this probe exists to respect.
- Does not open a second source itself -- that is a follow-on decision,
  contingent on this probe's outcome.
