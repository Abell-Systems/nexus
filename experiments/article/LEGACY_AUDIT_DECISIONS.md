# Decision PR — legacy artifacts (Figures 1/2/3/5/6, Tables 3/5)

Follow-up to `LEGACY_AUDIT.md` (#107, merged). That document was audit-only;
this one makes explicit retain/revise/retire calls per artifact. No
manuscript edits are made here — this is the decision record the manuscript
edit(s) should follow, each as its own separately reviewed change.

**Standing principle, per review of #107:** a "no reproducible source data"
finding proves the artifact **cannot currently be independently audited**
from what's archived in this repository. It does not prove the artifact's
numbers are wrong. These are kept as two distinct claims throughout.
Similarly, no missing dataset (applicant homogenization, PSR categories,
regional tags) is reconstructed with present-day heuristics and presented as
the original analysis in this document — where a path to recovery exists,
it's named as a separate, explicitly-labeled future task, not done here.

## Decisions

### Retain: Figure 1 (world map), Figure 2 (Europe map)

Reproducible from `patentes_CEIMAR_master.xlsx` + `make_charts.py`; the
"217 patents, Spain" prose figure reproduces exactly. No action needed
beyond the methodology-description correction in `LEGACY_AUDIT.md` §0 (two
Minesoft pulls, not an Espacenet/Minesoft split) — a text-only fix for a
future manuscript-methodology PR, not implemented here.

### Retain: Figure 6 (legal status)

Reproducible and correctly captioned (`legal_status_summary`: Active 198 /
Expired-Lifetime 26 / Expired-Fee-Related 2 / Withdrawn 1). The figure
itself is sound.

### Separately address: the PSR X/Y/P/E paragraph (adjacent to Figure 6, not part of it)

This is a distinct problem from Figure 6 and should be decided independently
of it. The manuscript's Discussion states "72% X... 32% Y... 26% P... 3% E"
(Patent Search Report prior-art categories) — a classification for which
**no source file exists anywhere in this repository**, checked directly:
none of `patentes_CEIMAR_master.xlsx`, `exports/A`–`G`, or the Minesoft
classification tables contain an X/Y/P/E field or anything resembling one.
This is not a "not yet reconciled with new data" issue like Table 2 was —
it is a claim with **zero archived support**, legacy or new. Two honest
options for a future manuscript PR: (a) caveat the paragraph explicitly as
undocumented in the project's archive, or (b) remove it if the PSR analysis
cannot be re-run or the original source recovered. Not decided here — this
document identifies the problem and its severity (no source ≠ Table 2's
"different source, needs updating" situation), leaves the choice to a
manuscript-editing PR.

### Revise (not retire) — investigated further here: Figure 5 / Table 5

**New finding beyond `LEGACY_AUDIT.md`:** partial reconciliation was
attempted (read-only, no manuscript or data changes) to see whether Table
5's "Solicitante homogeneizado" figures are recoverable via corporate-name
normalization of the archived `applicants` field. Result: **partially, not
fully, explicable.**

- Un-year-filtered (all 227 families, not `make_charts.py`'s 2000–2026
  subset), raw `applicants` field: **Pfizer (8), Cellectis (7), 4D Pharma
  Research Limited (6), F. Hoffmann-La Roche AG (3) match Table 5's numbers
  exactly.** This confirms Table 5 was very likely built from the same
  underlying pull, unfiltered by year, with some name handling applied.
- But merging every recognizable corporate-name variant present in this
  file (e.g. "BAYER PHARMA AKTIENGESELLSCHAFT" + "BAYER INTELLECTUAL
  PROPERTY GMBH" + "BAYER AKTIENGESELLSCHAFT" = 11; "PHARMA MAR, S.A." +
  "PHARMA MAR, S.A.U." + "PHARMA MAR S.A., SOCIEDAD UNIPERSONAL" = 7) still
  **does not reach** Table 5's reported values (Bayer AG 10, Pharma Mar SA
  9) — short by 1 and 2 respectively. Merck (16 in this file, only one
  spelling present) is short by 5 against Table 5's 21. Merging the
  `assignees` field in addition to `applicants` changes nothing (identical
  totals), ruling out "applicants vs. assignees field choice" as the
  explanation.
- **Conclusion:** Table 5 was not built purely from a naive count of this
  archived file's `applicants` column, even with generous name
  normalization applied. Either (a) it drew on additional family members or
  a broader pull not captured in `patentes_CEIMAR_master.xlsx` as archived,
  or (b) manual supplementation/correction was applied outside this
  pipeline. This is a genuine data-completeness gap, not merely a
  presentation difference.

**Decision:** Revise, not retire — the partial match (4 of 10 companies
exact) is strong enough evidence that Table 5 reflects a real, related
analysis worth keeping, not a fabricated or unrelated one. Recommended path
for a future task, explicitly scoped and separate from this document: (1)
attempt to locate or reconstruct the broader pull/homogenization mapping
Table 5 actually used (if recoverable, e.g. from external notes or a
prior working file not currently in this repo); if not recoverable, (2)
regenerate Figure 5 and Table 5 together from the archived data with a
clearly documented, reproducible homogenization method, **labeled explicitly
as a new reconstruction superseding the original Table 5**, not presented as
having recovered the original numbers.

### Revise or retire: Figure 3 (organism radial diagram)

Confirmed again: no compound or marine-organism column exists in any
archived file. This **does not mean the figure's counts are wrong** — it
means this repository cannot currently verify them. The manuscript prose
directly dependent on Table 2 rankings was already corrected in #103 (the
"leading compound" claims). The figure image itself (compound × organism
radial diagram) is a separate artifact from that prose and remains
unverifiable either way.

**Decision:** Revise. Retiring the figure outright would discard a
genuinely informative visualization (compound-to-organism structure, which
is static domain knowledge from Table 1, not itself a disputed count) over
a problem that's really about the counts layered onto it. Recommended path
for a future task: caveat the figure's caption/text to state plainly that
its underlying per-compound counts are not independently reproducible from
this repository's archive, while keeping the organism-grouping structure
(which *is* traceable to Table 1) intact.

### Revise or retire: Table 3 (Spanish region)

No sub-national region data exists in any archived file — `jurisdictions`
is country-level only (`ES`, not Madrid/Andalusia/etc.). This is a harder
case than Figure 3: Table 3's total (1+2+14+1=18) was already flagged in
`MANUSCRIPT_AUDIT.md` §6 as internally inconsistent with the 217-family
Spain count in Figure 1/2's own prose, *independent* of this new
reproducibility finding — two separate problems compounding on the same
small table.

**Decision:** Retire, pending a scoped decision on whether region-level
data is worth acquiring. Unlike Figure 3, there's no static, independently-
verifiable structure (like Table 1's organism mapping) to preserve by
caveating rather than removing — the entire content of Table 3 is
unreproducible counts with an internal consistency problem on top. If
region-level analysis is judged important to the paper's argument, it
should be a new, explicitly-scoped acquisition (region-tagging via
applicant/inventor address data, which Minesoft's `bulk_publications` can
provide but which was never captured for this purpose), not a retroactive
reconstruction from what's archived.

## Summary table

| Artifact | Decision |
|---|---|
| Figure 1 | Retain |
| Figure 2 | Retain |
| Figure 6 | Retain |
| PSR X/Y/P/E paragraph (near Fig. 6) | Separately address — caveat or remove, no source exists |
| Figure 5 / Table 5 | Revise — partially explicable, genuine data gap, needs a scoped reconstruction task, explicitly labeled as such |
| Figure 3 | Revise — caveat the counts, keep the (Table-1-traceable) organism structure |
| Table 3 | Retire, pending a scoped decision on acquiring region-level data |

## Explicitly not done in this document

No manuscript file was edited. No data was acquired or reconstructed. No
homogenization mapping was invented and applied. Each "Revise" decision
above names a future, separately-scoped task rather than executing one here.
