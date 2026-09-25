# Manuscript integration diff — corrected Minesoft classification

Applied to `full paper marine policy (updated charts+text).docx`. Backup of the
pre-edit file kept at `/tmp/paper_backup_before_edit.docx` (session-local, not
committed — the git history of this file is the durable record).

Scope: only the seven locations below were touched. **Not touched**: Figures
1, 2, 3, 5, 6 (as images), Table 3, Table 5, their underlying datasets, and no
new data was acquired. Figure 3 and Figure 4 as *images* are unchanged — only
the prose paragraphs discussing them were edited, because those paragraphs
made a factual ranking claim ("leading/largest compound") that is a direct,
mechanical consequence of the Table 2 replacement.

## 1. Abstract (paragraph 4)

**Before:** "Using data from the Espacenet database, the research maps the
spatial distribution of patents, ..."

**After:** "Using patent data from the Espacenet database, complemented by a
corrected, evidence-based relevance classification of Spain-relevant patent
families built from the Minesoft Origin database, the research maps the
spatial distribution of patents, ..."

## 2. New paragraph inserted after the Methodology's Espacenet-collection
   paragraph (new paragraph 54)

States: the Minesoft classification methodology (family-level search →
per-family claims/description screening → Directly/Indirectly Relevant/
Incidental/Uncertain), that it supersedes an earlier narrower cc=ES-filtered
search, and that it covers **12 of the 14** approved drugs in Table 1 —
naming the two not covered: **Disitamab Vedotin** and **Tisotumab
vedotin-tftv**.

## 3. Table 2 intro paragraph (paragraph 70, was 69)

**Before:** "Table 2 presents the compounds that generated patents in total
number of patents according to the analyzed data."

**After:** States the 12-compound scope, that the table now reports
Directly/Indirectly Relevant Spain-relevant families (superseding the old
Espacenet raw counts), and spells out the three units explicitly: **872**
unique Spain-relevant families found; **157** classified as substantively
relevant (91 Directly + 66 Indirectly); **161** compound–family observations
in the table itself (more than 157 because 4 families matched >1 compound's
search and are counted once per compound).

## 4. Table 2 rebuilt (4 columns instead of 2)

| Compound | Directly Relevant | Indirectly Relevant | Total Relevant |
|---|---|---|---|
| Cytarabine | 69 | 54 | 123 |
| Eribulin mesylate | 8 | 0 | 8 |
| Brentuximab vedotin | 5 | 2 | 7 |
| Trabectedin | 3 | 3 | 6 |
| Vidarabine | 1 | 3 | 4 |
| Polatuzumab vedotin | 4 | 0 | 4 |
| Enfortumab vedotin | 2 | 2 | 4 |
| Plitidepsin | 0 | 2 | 2 |
| Omega 3 acid ethyl esters | 2 | 0 | 2 |
| Ziconotide | 1 | 0 | 1 |
| Omega 3 carboxylic acid | 0 | 0 | 0 |
| Lurbinectedin | 0 | 0 | 0 |

Sourced from `figures/table2_relevant_by_compound.csv`, itself generated
deterministically from `screening_table_consolidated.csv` (tag
`paper-data-milestone-2026-09-22`). Old table (Espacenet raw counts,
Brentuximab vedotin 115 / Cytarabine 36 / ... / Lurbinectedin 1) removed.

## 5. Figure 3 prose (paragraph 75, was 74)

**Before:** "The leading compound in total number of patents, Brentuximab
vedotin, as well as for Polatuzumab vedotin and Enfortumab vedotin, the
marine organisms are Mollusk/Cyanobacterium."

**After:** Splits the organism-sharing fact (Brentuximab/Polatuzumab/
Enfortumab vedotin share Mollusk/Cyanobacterium origin — unaffected by the
correction, kept) from the ranking claim, now correctly stating **Cytarabine**
leads (123), followed by Eribulin mesylate (8) and Brentuximab vedotin (7).

## 6. Organism-group ranking prose (paragraph 81, was 80) — found during
   integration, not in the original audit

This paragraph's "second/third/fourth/fifth marine organism in total number
of patents" ranking is *also* mechanically derived from the old Table 2 (it
sums per-compound counts by organism group using Table 1's static
organism-to-compound mapping). Recomputed with the new counts, **the ranking
order itself flips**: Sponge (Cytarabine + Vidarabine + Eribulin mesylate =
135) now leads, ahead of Mollusk/Cyanobacterium (Brentuximab + Polatuzumab +
Enfortumab vedotin = 15) — the reverse of the old ordering, where
Mollusk/Cyanobacterium (122) led over Sponge (56). Tunicate (8), Fish (2),
and Cone snail (1) follow. This was a larger contradiction than the two
single-compound "leading/largest compound" sentences the original audit
caught, since it reorders all five organism groups, not just names one
compound — flagging explicitly since it goes beyond the two sentences named
in the task boundary, but is the same class of stale Table-2-dependent claim
and was left uncorrected it would have been a glaring internal
contradiction next to the new Table 2.

## 7. Figure 4 prose (paragraph 82, was 81)

**Before:** "The three leading compounds are dedicated to cancer treatments.
The largest compound, Brentuximab vedotin, is vastly used for..."

**After:** Corrects the ranking (Cytarabine 123, Eribulin mesylate 8,
Brentuximab vedotin 7) and adds the relevance-rate context requested: **17.8%**
for Cytarabine (123 of 690 screened) vs. **≈44%** for Eribulin mesylate (8 of
18 screened) — explicitly stating that raw family count and relevance rate
are different quantities. The rest of the paragraph (disease-area mapping for
Trabectedin, Ziconotide, Vidarabine, Plitidepsin, Omega-3 compounds) is
unchanged verbatim, since it concerns Figure 4's actual content
(disease areas), not patent-count ranking.

## Verification performed

- Re-opened the saved `.docx` with python-docx: 181 paragraphs (180 + 1
  inserted), 4 tables, no parse errors.
- Confirmed the new Table 2 (table index 1) has exactly the 12 rows above.
- Full-text scan for residual stale terms: `"largest compound"` — 0 hits
  (fully removed). `"leading compound"` — 2 hits, both the new, corrected
  sentences (Cytarabine). `"115"` — 2 hits, both legitimate and unrelated
  (Poland's patent count in the untouched Figure 2 prose; two reference
  page-number citations), no leftover stale Brentuximab-115 claim.
- `"Using data from the Espacenet database, the research"` (old abstract
  phrasing) — 0 hits, confirms the replacement landed and the old string is
  gone everywhere in the document, not just in the edited paragraph.

## Not addressed in this pass (per the stated boundary)

- Figures 1, 2, 3, 5, 6 as images — unchanged.
- Table 3 (Spanish region) and Table 5 (Spanish companies) — unchanged, and
  their pre-existing internal inconsistency with the old Table 2 (noted in
  `MANUSCRIPT_AUDIT.md` §6) is untouched, not caused by this pass.
- Legal-status statistics (72%/32%/26%/3%, Figure 6) — unchanged.
- The scientific interpretation of *why* Cytarabine and the Sponge organism
  group dominate — flagged with rate context in the prose, but the deeper
  analysis (is this a real biological/therapeutic signal, or mostly an
  artifact of Cytarabine's screened-universe size and its status as a
  60-year-old generic name) is the next milestone, not done here.
