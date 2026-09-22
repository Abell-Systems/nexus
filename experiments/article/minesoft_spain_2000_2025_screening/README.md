# CEIMAR / Minesoft Origin — Spain 2000–2025 patent screening

## Status: screened, per Lydia's Patent Screening Protocol (2026-09-17)

This is a fresh, separate extraction — **not** the global `../minesoft_origin_2000_2025/`
snapshot (which is frozen and untouched). It answers the two open methodological
questions from that checkpoint for this specific run: geographic scope = **Spain
only**, Cytarabine = **exhaustive** (the Spain filter made the cap moot — see below).

## Query

For each of the 12 target compounds:

```
tac=(<compound name>) AND pd>2000 AND pd<2026 AND cc=ES
```

- Same `tac=` (Title+Abstract+Claims) full-text field and `pd>2000 AND pd<2026`
  date window as the global v0.1 pull, plus `cc=ES`.
- `cc=ES` matches publications with Spanish country code — this includes both
  Spanish-office-originated documents (patent-office source) and **"T3" Spanish
  translations of validated European patents** (docdb source), which is how a
  family with EP-only protection still shows up as a Spanish national document.
  Confirmed empirically (first hit for Brentuximab vedotin was `ES-2724408-T3`,
  a T3 EP-validation document) and consistent with the original 227-family
  Espacenet-based master dataset's own methodology.
- **This is a much narrower population than "the compound's publication-number
  prefix is ES-"** would suggest — cross-checked against the global v0.1 IDs and
  confirmed `cc=ES` returns the identical count, so no broader interpretation
  was available from this data source without enrichment.

## Per-compound universe sizes (Spain, 2000–2025)

| # | Compound | numFound (cc=ES) | Rows pulled |
|---|---|---:|---:|
| 01 | Brentuximab vedotin | 19 | 19 |
| 02 | Cytarabine | 2 | 2 (exhaustive) |
| 03 | Trabectedin | 2 | 2 |
| 04 | Vidarabine | 1 | 1 |
| 05 | Ziconotide | 0 | 0 |
| 06 | Plitidepsin | 1 | 1 |
| 07 | Omega-3 acid ethyl esters | 0 | 0 |
| 08 | Polatuzumab vedotin | 1 | 1 |
| 09 | Omega-3 carboxylic acid | 0 | 0 |
| 10 | Enfortumab vedotin | 0 | 0 |
| 11 | Eribulin mesylate | 0 | 0 |
| 12 | Lurbinectedin | 0 | 0 |
| **Total** | | **26** | **26** |

**This is a real, surprising finding, not a bug**: 26 Spain-matched publications is
far smaller than the ~217/227-family Spain footprint in the *old* 1988–2019
Espacenet-based master dataset. The two datasets are not measuring the same
thing — the old dataset was built top-down from a curated ES publication-number
list expanded to full patent families (any family member counts, and the
compound doesn't need to appear in title/abstract/claims text at all), while
this pull is bottom-up from `tac=` full-text search restricted to `cc=ES`
publications only (a family can easily have Spanish protection with the
compound named only in a non-ES family member, e.g. the EP or WO publication,
and never be found by this method). **Flagged for Lydia's judgment**: this
method under-counts Spain-relevant families relative to the original dataset's
definition of "Spain-relevant," and that gap should be understood before this
26-family universe is treated as "Spanish marine-drug patent activity."

## Screening methodology (per Lydia's Patent Screening Protocol)

- Unit of analysis: **patent family** (`docdbfamilyid`), not publication.
  26 publications consolidated into **23 unique families** (2 Brentuximab
  vedotin families and 1 Cytarabine/Vidarabine family each had 2 matching
  publications).
- Evidence used: full claim text (`claims`, not just `firstclaims`) and
  description text (`descriptions`, first ~20,000 chars) pulled via
  `bulk_publications` (`bibonly=false`) for every family, then searched for the
  compound name and its inflections to locate and quote the exact context of
  every mention — never classified from title/abstract alone, and never from
  external knowledge or a web search (the protocol's absolute rule 1 and 4).
- No records or families were added beyond what `tac=... AND cc=ES` returned;
  none were deleted; original publication and family identifiers were kept
  as returned by Minesoft.
- Classification followed the protocol's five-way scheme (Directly Relevant /
  Indirectly Relevant / Incidental Mention / Not Relevant / Uncertain) using
  the evidence standard in the protocol's §5: is the compound *substantively
  connected to the claimed or disclosed invention*, not merely named somewhere
  in the document. Every "Incidental Mention" classification in
  `screening_table.csv` is backed by a quoted Markush-style drug list (10 to
  250+ items) in which the target compound is one undifferentiated entry among
  many — the pattern the protocol's §4C and §8 specifically call out.
- No record was left **Uncertain**: full claims + description text was
  sufficient evidence for all 23 families. Two families were flagged
  **Human_Review = Yes** for a borderline Indirectly-Relevant-vs-Incidental
  call (see `screening_table.csv` evidence column) — not because the evidence
  was insufficient, but because the classification judgment itself is
  genuinely close and protocol §12 requires such cases to be surfaced, not
  resolved silently.

## Output

`screening_table.csv` — the full family-level table, columns per the
protocol's §9 spec (Family_ID, Publication_Numbers, Compound, Relevance_Class,
technology/application flags, Evidence, Confidence, Human_Review).

## Summary (per protocol §13)

- Publications screened: **26**
- Patent families screened: **23**
- Directly Relevant: **3** families (2× Brentuximab vedotin, 1× Polatuzumab
  vedotin)
- Indirectly Relevant: **2** families (1× Trabectedin, 1× Plitidepsin) — both
  flagged for human review
- Incidental Mention: **18** families
- Not Relevant: **0**
- Uncertain: **0**
- Families per compound: Brentuximab vedotin 17, Cytarabine 2 (1 shared with
  Vidarabine), Trabectedin 2, Vidarabine 1 (shared), Plitidepsin 1,
  Polatuzumab vedotin 1. Ziconotide, Omega-3 acid ethyl esters, Omega-3
  carboxylic acid, Enfortumab vedotin, Eribulin mesylate, Lurbinectedin: 0
  families each in the Spain-restricted 2000–2025 window as queried.
- Families requiring human review: **2** (see above)

Percentages are not reported, per protocol §13 ("do not calculate percentages
unless the underlying counts are available") — the small universe size makes
percentages of limited statistical value here regardless.

## What this is NOT

- **Not a replacement for the global `minesoft_origin_2000_2025/` v0.1 snapshot**,
  which remains frozen and untouched as a separate audit artifact.
- **Not a resolution of the Spain-scope-vs-global decision for the rest of the
  project** — this run answers it only for this specific screening exercise, at
  Lydia's direction in this session. The broader roadmap decision (documented
  in the v0.1 checkpoint) is still open.
- **Not merged with `../patentes_CEIMAR_master.xlsx`** (227 families,
  1988–2019, Espacenet-sourced) — kept separate, consistent with the project's
  standing rule to keep the pre-2000-2025 base and the new extraction
  independent until a deliberate consolidation step.
