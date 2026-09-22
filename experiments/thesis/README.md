# Patent panel — Andalusian public universities, 1997-2026 (Minesoft Origin)

## What this is

A descriptive, standalone patent-family panel for the 8 public universities of
Andalusia, built from Minesoft Origin via the `minesoft` MCP server, motivated
by Lydia Bares's 2022 doctoral thesis (UCA, *"Producción de conocimiento
tecnológico en los organismos públicos de investigación de Andalucía y sus
consecuencias sobre la actividad científica"*, defended 2026-03-17 — thesis
data window unknown, source: https://produccioncientifica.uca.es/documentos/62b68f43730a524af85b3522).

**This is NOT a replication or extension of the thesis's econometric panel.**
The thesis's exact unit of analysis, date window, and institution list are
unknown (not available to this session) and were not asked of Lydia before
this was built. Per explicit decision, this dataset is published as an
independent descriptive series, not framed as continuing or reconciling with
her original numbers. If a real extension is wanted later, get her unit of
analysis and cutoff year first — don't back-fit this panel to it.

## Query

For each institution:

```
pa=(<institution name>)
```

`get_stats`, `f1=publicationyear`, `f2=assignees_name_probable`,
`group=minesoftfamily`. The `f2` breakdown was used only to confirm the
dominant assignee-name variant per year (e.g. "University of Cádiz" vs.
"Universidad de Cadiz") — no cross-institution dedup was performed beyond
that per-institution assignee check.

## Scope decisions

- **8 public Andalusian universities only**: Cádiz, Sevilla, Granada, Málaga,
  Córdoba, Jaén, Huelva, Almería, Pablo de Olavide.
- **CSIC excluded, deliberately.** `pa=(consejo superior de investigaciones
  cientificas)` returns 20,314 publications — the whole national CSIC, not
  its Andalusian centers (Zaidín, ICMAN, IAA, Estación Biológica de Doñana,
  etc.). Minesoft's `corporatetree` for CSIC lists only 13 subsidiaries
  nationally, and only one (Instituto de la Grasa, Sevilla) is in Andalusia —
  an incomplete list, not usable as a filter. More fundamentally, CSIC
  patents are almost certainly all assigned under the single national legal
  entity ("Consejo Superior de Investigaciones Científicas"), not per
  internal institute, so no assignee-name query can isolate the Andalusian
  share. Isolating it would require enriching all ~20k CSIC publications via
  `bulk_publications` and filtering by inventor address/city — out of scope
  here, per explicit decision to exclude rather than force it.
- The 1997-1999 CSIC years showed an anomalous spike (1,940 / 1,166 / 595
  families vs. ~300-800/year in 2000s) — consistent with a historical bulk
  digitization artifact, not real patenting activity. Another reason CSIC was
  left out rather than included "with a note."

## Known data-quality caveats (not cleaned in this pass)

- Per-year counts use each institution's **dominant name variant only**
  (e.g. "University of Cádiz"); minor spelling variants seen in the raw
  `assignees_name_probable` breakdown (e.g. "Universidad de Cadiz",
  "Universidad De Cordoba Uco") were folded in by the underlying
  `assignees_name_probable` field itself, not independently re-verified
  row by row.
- `minesoftfamily` grouping (not `extendedfamily`, unlike the
  `minesoft_global_2000_2025_family_jurisdictions/` pass in `experiments/article/`)
  — a different family-level unit than that other pass; do not compare counts
  across the two without checking this.
- No relevance/subject-matter filtering — every patent family with the
  institution as an assignee, of any technology field, is counted. Lydia's
  thesis may have scoped differently (e.g. by field, by department).

## File

`panel_andalusian_universities_1997_2026.csv` — columns `Institution`,
`Year`, `Simplefamily_count`.

## Next step (not done here)

Before this can be framed as an update to the thesis rather than a parallel
series: get from Lydia the thesis's unit of analysis (patent family vs.
application vs. publication), institution list (does it include CSIC's
Andalusian centers, and if so how did she scope them), and date cutoff.
