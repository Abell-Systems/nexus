# Legacy audit — Figures 1/2/3/5/6 and Tables 3/5

Scope: audit only, per the agreed plan after #103 → #105 → #106. No manuscript
edits, no new data. This checks each legacy artifact against what source data
actually exists in this repository and whether the manuscript's numbers
reproduce from it — a materially different, and more useful, question than
just "is it Espacenet or Minesoft."

## 0. Correction to the "Espacenet layer vs. Minesoft layer" framing

The proposed two-layer architecture (Espacenet layer → Figs 1/2/5/6 + Tables;
Minesoft layer → Table 2 + Figs 7–9) is **not quite what the data shows**.
`query_log.md` documents that the entire legacy dataset behind Figures 1, 2,
5, 6 and old Table 2 was itself built via **Minesoft** (`number_lookup` +
`bulk_publications`, dated 2026-09-14), not pulled from Espacenet directly.
Espacenet's actual role was narrower: it was (presumably, per the abstract's
claim — not independently verifiable in-repo) the source of the **input seed
list** of 247 Spanish publication numbers (`patentes_CEIMAR_original.xlsx`),
which Minesoft then resolved to families (228 unique, 1 duplicate-collapsed
to 227) and enriched with jurisdiction, legal-status, applicant, and citation
data (`patentes_CEIMAR_master.xlsx`, `exports/A`–`G`).

So the real architecture is two **Minesoft** pulls with different sampling
methods, not an Espacenet/Minesoft split:

- **Pull 1 (this legacy set):** seed = a curated list of 247 ES publication
  numbers (origin unverified in-repo, presumably Espacenet), enriched via
  Minesoft lookup. 227 unique families, priority years 1988–2019 (227 of
  228 raw rows; `make_charts.py` further filters to 2000–2026, dropping 10,
  leaving 217).
- **Pull 2 (`paper-data-milestone-2026-09-22`):** seed = 12 compound-name
  text searches against Minesoft directly (`tac=<compound> AND pd>2000 AND
  pd<2026`), family-level, corrected for jurisdiction, then classified.

This matters for the manuscript's methodology section, which currently
credits only Espacenet and (after #103) adds Minesoft as a second, separate
source — it should instead describe two Minesoft pulls with different seed
methods, one of which traces its seed list back to Espacenet.

## 1. Dependency matrix

| Artifact | Source file(s) in repo | Reproducible from repo? | Matches manuscript number? | Recommendation |
|---|---|---|---|---|
| Figure 1 (world map) | `patentes_CEIMAR_master.xlsx` + `make_charts.py` | **Yes** | **Yes** — reproduced ES=217 exactly, matching the "Spain (217 patents...)" prose | **Retain.** Reproducible and consistent. |
| Figure 2 (Europe map) | same | **Yes** | **Yes** — same 217-family, `jurisdictions` field | **Retain.** |
| Figure 3 (organism radial diagram) | none found | **No** | N/A (no source file to check against) | **Revise or retire.** No compound or marine-organism column exists anywhere in `patentes_CEIMAR_master.xlsx` or `exports/*`. The compound→organism mapping is Table 1 (static, from Marine Pharmacology), but the per-compound *patent counts* it's crossed with have no traceable source file in this repo at all — they were not captured when Figure 3 was originally built (rawgraphs.io, per the manuscript text). Already partially addressed in #103 (the "leading compound" ranking claim in the prose was corrected using the new Minesoft classification), but the figure image itself remains unreproducible from anything in-repo. |
| Figure 5 (top applicants) / Table 5 | `patentes_CEIMAR_master.xlsx` + `make_charts.py` (image) — but **not** the docx's Table 5 | Figure image: **yes**. Table 5 (word table): **no** | **No — figure and table actively disagree.** Figure 5 (regenerated): Merck Patent Gmbh 16, Pfizer 7 (year-filtered) or 8 (unfiltered), Bayer Pharma 7, Cellectis 7... Table 5 (docx): Merck Patent Gmbh **21**, Bayer AG **10**, Pharma Mar SA **9**, Pfizer **8**... — different counts *and* a different company set (Table 5 has AbbVie Biotherapeutics and Hummingbird Bioscience Holdings; the raw applicant list from `make_charts.py` does not surface either in the top 10). Table 5's header, "Solicitante homogeneizado," confirms it used a name-homogenization step (merging applicant-name variants, e.g. multiple Bayer/Pharma Mar entity spellings) that `make_charts.py`'s naive semicolon-split does not perform. That homogenization logic is not captured anywhere in this repo. | **Revise.** Figure 5 needs to either (a) implement the same homogenization Table 5 used, if that logic can be recovered/reconstructed, or (b) Table 5's numbers need to be re-derived from Figure 5's reproducible, documented method and the manuscript updated to match. Currently the paper contains two different, disagreeing counts of the same thing under different names, which is exactly the kind of inconsistency #103's audit was meant to catch — this one was missed because it's between a table and its own companion figure, not against Minesoft data. |
| Figure 6 (legal status) | `patentes_CEIMAR_master.xlsx` (`legal_status_summary`) + `make_charts.py` | **Yes**, for what it actually shows | **Not applicable — different classification than what the text describes.** Figure 6 plots `legal_status_summary` (Active 198 / Expired-Lifetime 26 / Expired-Fee-Related 2 / Withdrawn 1) — a patent **legal-status** breakdown. The manuscript's Discussion narrative ("72% X... 32% Y... 26% P... 3% E") describes **Patent Search Report (PSR) prior-art categories** (X/Y/P/E), an entirely different classification scheme with no source file anywhere in this repo. Figure 6 is correctly captioned ("Legal status of CEIMAR patent families") for what it shows, but the manuscript prose right below it is about something else the repo has no data for at all. | **Retain Figure 6 as-is** (it is reproducible and correctly captioned). **Flag the PSR X/Y/P/E prose as unsupported by any data in this repository** — not a Figure 6 problem, a missing-dataset problem for that specific paragraph. |
| Table 3 (Spanish region) | none found | **No** | N/A | **Revise or retire.** `patentes_CEIMAR_master.xlsx`'s `jurisdictions` field is country-level only (`ES`, not sub-national regions like Madrid/Andalusia). No file in this repo has region-level data. Also recall from `MANUSCRIPT_AUDIT.md` §6 (pre-existing, noted at the time): Table 3's own total (1+2+14+1=18) doesn't reconcile with Figure 1/2's 217-family Spain count anyway, independent of this new finding. |

## 2. Summary of what changed since the original two-layer proposal

- Figures 1 and 2: **confirmed clean** — reproducible, and the "217" figure
  in the prose is exactly reproduced. No action needed beyond documenting
  the corrected Minesoft-pull-methodology framing in §0.
- Figure 6: **confirmed clean** as a figure, but the manuscript's adjacent
  PSR-category narrative (72/32/26/3%) has zero traceable source data in
  this repo — this is a **new finding**, not previously flagged in
  `MANUSCRIPT_AUDIT.md`.
- Figure 5 / Table 5: **new finding** — these are not just "the same data
  presented twice," they are two different counts of the same thing that
  actively disagree, because Table 5 used an undocumented homogenization
  step Figure 5's regeneration script doesn't replicate.
- Figure 3 and Table 3: **confirmed** to have no reproducible source data in
  this repo (Figure 3 already partially known from #103's manuscript
  integration work; Table 3 is a new confirmation of the earlier suspicion
  in `MANUSCRIPT_AUDIT.md` §6).

## 3. Recommended next step (not done here)

This document is audit-only, per the agreed scope. The next step is a
**decision PR**: for each `Revise or retire` row above, decide explicitly
whether to (a) retire the artifact from the manuscript, (b) attempt to
recover/reconstruct the missing methodology (region-tagging, PSR
categorization, applicant homogenization) as a scoped task, or (c) caveat
the manuscript text to state plainly that the artifact's underlying data
is not independently reproducible from what's archived in this repository.
That decision — and any resulting manuscript edit — is deliberately not made
in this document.
