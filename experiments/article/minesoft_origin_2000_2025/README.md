# CEIMAR / Minesoft Origin — 2000–2025 raw pull (IDs only)

## Status: IDs-only, not yet enriched

This directory holds the **first pass** of a new, parallel dataset requested by Lydia
(2026-09-16): a Minesoft Origin re-extraction of the same 12 compounds used in the
original marine-policy article, covering publication dates 2000–2025, methodology
matching her email (12 independent per-compound searches, no relevance filtering,
raw results kept, family-level dedup deferred to a later step).

This pass captures **publication IDs and relevance scores only** (`fl="pn"`), not full
bibliographic data (title, applicant, IPC/CPC, legal status, citations, family size).
It exists to size the problem before committing to full enrichment via
`bulk_publications`, which is a much larger operation (see "Next step" below).

## Query

For each compound:

```
tac=(<compound name>) AND pd>2000 AND pd<2026
```

- `tac` = Title + Abstract + Claims (the closest available field to Lydia's spec).
- `pd>2000 AND pd<2026` = publication date strictly between 2000 and 2026, i.e. the
  2000–2025 window (the Minesoft query grammar only supports strict `>`/`<`, not
  `>=`/`<=` or bracket ranges).
- Global scope (no jurisdiction filter) — Lydia's spec didn't restrict to Spain/ES;
  family-level dedup and jurisdiction analysis is deferred to the enrichment step.
- Sort: default (`score`, i.e. relevance) — same for every compound, including the
  capped Cytarabine pull (see below).

## Per-compound counts

| # | Compound | numFound (true total) | Rows saved | Capped? |
|---|---|---:|---:|---|
| 01 | Brentuximab vedotin | 2,613 | 2,613 | No — repaired, see Repair log |
| 02 | Cytarabine | 19,075 | 1,000 | **Yes — see below** |
| 03 | Trabectedin | 1,890 | 1,890 | No |
| 04 | Vidarabine | 2,067 | 2,067 | No |
| 05 | Ziconotide | 519 | 519 | No |
| 06 | Plitidepsin | 168 | 168 | No |
| 07 | Omega-3 acid ethyl esters | 81 | 81 | No |
| 08 | Polatuzumab vedotin | 723 | 723 | No |
| 09 | Omega-3 carboxylic acid | 13 | 13 | No |
| 10 | Enfortumab vedotin | 501 | 501 | No |
| 11 | Eribulin mesylate | 776 | 776 | No |
| 12 | Lurbinectedin | 270 | 270 | No |
| **Total** | | **~29,696** | **~28,621** | |

## Repair log

**2026-09-16 — Brentuximab vedotin, 1 missing ID found and fixed.** The initial pull
had 2,612 of 2,613 publication IDs (a manual-transcription gap, see prior note below,
kept for history). Repair method: re-ran the full paginated query
(`tac=(Brentuximab vedotin) AND pd>2000 AND pd<2026`, `fl="pn"`, `rows=50`,
`start=0,50,...,2600`, 53 calls) to get a fresh, complete 2,613-ID set; diffed it
against the stored CSV (`comm -23` on sorted unique ID lists) rather than trusting
another manual re-transcription. Missing ID: **`EP-3621652-A1`** (score 7.117646).
Appended as a new row (same schema: `compound=Brentuximab_vedotin`, `capped=False`,
`total_hits_reported=2613`), without touching or reordering the other 2,612 rows.
Post-repair verification: `01_Brentuximab_vedotin_ids.csv` now has exactly 2,613
data rows, all unique. No other compound file has been re-verified this way — the
gap was specific to this one file's original transcription, not a systemic issue,
but this file is now the only one independently double-checked against a second
fresh pull.

*(Original note, kept for history: 1 of the 2,613 publication IDs was lost during
manual transcription of the paginated API results into this dataset — a mechanical
copy error somewhere across 53 pages of 50 results each, not a data-quality issue in
the underlying Minesoft results. Now fixed, see above.)*

## Checkpoint — exploratory extraction v0.1 (frozen 2026-09-16)

**Enrichment (`bulk_publications`) is intentionally NOT run yet.** This directory is
frozen at the ID-only stage as a reproducible checkpoint pending two explicit
methodological decisions from Lydia — spending ~1,400+ more API calls to enrich a
universe whose geographic and compound scope aren't finalized would be premature:

1. **Geographic scope: global vs. Spain-restricted.** The current pull has no
   jurisdiction filter (see "Query" above). Whether the analysis is about *global*
   marine-drug patent activity or specifically *Spanish* activity changes which
   universe should be enriched.
2. **Cytarabine: exhaustive (19,075) vs. capped (1,000).** See "Cytarabine cap"
   below — this is a scientific call about whether generic-name noise belongs in
   the analysis, not something to default on.

Do not alter the 12 CSVs beyond the Brentuximab repair above (which fixes a data
-integrity bug, not a scope decision) until those two points are confirmed. Once
confirmed, the enrichment run should be scoped explicitly from this frozen ID
universe (filtered by jurisdiction first if Spain-restricted is chosen, to avoid
enriching IDs that will be discarded anyway).

## Cytarabine cap — read before using

Cytarabine is a ~60-year-old generic chemotherapy drug name, so a free-text
title/abstract/claims search picks it up in huge numbers of patents where it's
mentioned only as prior art, a comparator, or a combination-therapy component —
not necessarily a patent actually claiming Cytarabine itself. Its 19,075 raw hits
are ~64% of the entire 12-compound pull.

Per explicit instruction, this file contains **only the first 1,000 results, sorted
by relevance score** (Minesoft's default sort — the same sort used for every other
compound in this pull). **This is a capped diagnostic sample, not a statistically
representative one.** Because it's ordered by relevance rather than drawn randomly,
it cannot be used to estimate the composition (e.g. jurisdiction mix, applicant
mix, year distribution) of the full 19,075-document universe. Use it only to
gauge the noise/relevance profile of the Cytarabine retrieval, and to decide
whether exhaustive extraction for this compound is methodologically justified
before doing it (it would require ~382 additional paginated calls).

The true denominator (19,075) is preserved in the `total_hits_reported` column of
`02_Cytarabine_ids.csv` on every row, specifically so it isn't lost or confused
with the 1,000 rows actually present.

## File format

Each `NN_<Compound>_ids.csv` has columns:

- `publication_id` — Minesoft/DOCDB publication number (e.g. `US-20180098969-A1`)
- `score` — Minesoft relevance score for this query (not comparable across
  different compounds' queries, only within one compound's result set)
- `compound` — which of the 12 searches produced this row (a single publication ID
  can legitimately appear under more than one compound if it discusses several)
- `capped` — `True` only for Cytarabine; `False` for the other 11 (exhaustive)
- `total_hits_reported` — the query's true `numFound`, i.e. the denominator, even
  for the capped Cytarabine file (1,000 rows, but this column always reads 19,075)

## What this is NOT yet

- **Not enriched.** No title, applicant, assignee, IPC/CPC, legal status, priority
  date, family size, or citations — that's a separate, much larger step using
  `bulk_publications` (rate-limited to ~20 IDs/call based on the original 2026-09-14
  extraction's own notes; ~28,600 IDs here would be roughly 1,400+ calls even before
  any Cytarabine exhaustive extraction).
- **Not deduplicated by patent family.** The same invention can appear multiple
  times across jurisdictions (WO + EP + US + CN + JP + ...) — per Lydia's
  methodology, family-level dedup happens after enrichment, using each publication's
  `familydata`/`docdbfamilyid`, the same approach used in the original extraction
  (see `../query_log.md`, Fase 3).
- **Not merged with the old dataset.** `../patentes_CEIMAR_master.xlsx` (227
  families, Espacenet-sourced, priority years 1988–2019) is untouched and
  independent. This is a deliberately separate, parallel dataset so a genuine
  **1994–2023 (Espacenet) vs. 2000–2025 (Minesoft Origin)** comparison — and
  eventually a consolidated 1994–2025 base — can be built later without
  contaminating either source.

## Next step (not done here)

Enrichment via `bulk_publications` (`bibonly=true`, batches of ~20 IDs) to pull:
Family ID, publication numbers, application numbers, title, abstract, earliest
priority date, publication date, applicant, current assignee, inventors, priority
country, jurisdictions, CPC, IPC, legal status, forward/backward citations, family
size — plus the originating `compound` column, per Lydia's spec — followed by
family-level dedup. Given the scale (~28,600 non-Cytarabine IDs + a decision on
Cytarabine), this should be scoped and confirmed before running, not assumed.
