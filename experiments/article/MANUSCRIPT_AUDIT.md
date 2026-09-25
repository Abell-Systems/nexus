# Manuscript audit — stale dependencies on the old Espacenet/227-family dataset

Audit only. No manuscript text, Figures 1/2/3/5/6, or Table 3 were modified. No
new data was acquired. Source of truth for the corrected analysis is
`minesoft_spain_2000_2025_classification/screening_table_consolidated.csv`,
frozen at tag `paper-data-milestone-2026-09-22` (commit `df4f3c8`).

## File audited

Three `.docx` versions exist in this directory with identical mtimes (checked
out together, so mtime doesn't indicate recency):
- `full paper marine policy.docx`
- `full paper marine policy (updated charts).docx`
- `full paper marine policy (updated charts+text).docx` — **audited**, as the
  name implies it's the most complete/current version. **Confirm this is
  correct before editing** — if the three have diverged content, the other two
  need the same audit.

## Findings, in manuscript order

### 1. Abstract — data-source claim now incomplete
> "Using data from the Espacenet database, the research maps the spatial
> distribution of patents..."

Once Table 2 is replaced with Minesoft-derived numbers, this sentence
undersells the actual methodology — the paper will draw on two sources
(Espacenet for Figs. 1/2/3/5/6 and Table 3; Minesoft for Table 2 and Figs.
7–9). Needs a methodology-transition sentence, not just a fix.

### 2. Methodology, Table 1 — compound-list scope mismatch
Table 1 (approved marine drugs, source: Marine Pharmacology, updated 2024-04-10)
lists **14** compounds, including two that are **not** among the 12 compounds
in the Minesoft pull:
- Disitamab Vedotin
- Tisotumab vedotin-tftv

So Figures 7–9 / new Table 2 cover 12 of the 14 approved drugs in Table 1. This
should be stated explicitly wherever the new figures are introduced — silently
presenting 12-compound results next to a 14-compound Table 1 would look like
an unexplained gap.

### 3. Table 2 and its surrounding paragraph — direct replacement target
Old values (Espacenet, all-jurisdictions patent counts, not relevance-filtered):
Brentuximab vedotin 115, Cytarabine 36, Trabectedin 26, Vidarabine 18,
Ziconotide 18, Plitidepsin 12, Omega-3 acid ethyl esters 8, Polatuzumab
vedotin 5, Omega-3 carboxylic acid 4, Enfortumab vedotin 2, Eribulin mesylate
2, Lurbinectedin 1.

Replacement data is ready: `figures/table2_relevant_by_compound.csv` (Spain
Directly+Indirectly Relevant families per compound, 2000–2025, corrected
methodology). **Note the unit changes**: old Table 2 = raw patent count,
any jurisdiction, no relevance filter. New table = relevance-classified
**families** with Spanish jurisdiction only. These are not comparable
numbers — the prose introducing the new table must say so, not just swap
the figures in place.

### 4. Figure 3 prose — will directly contradict the new Table 2
> "The leading compound in total number of patents, Brentuximab vedotin, as
> well as for Polatuzumab vedotin and Enfortumab vedotin, the marine organisms
> are Mollusk/Cyanobacterium."

Under the corrected classification, **Cytarabine leads** (123 of 161
compound-family pairs) by a wide margin; Brentuximab vedotin has only 7. This
sentence's factual claim ("leading compound") will be **false** once Table 2
is replaced, even though Figure 3 itself (the organism radial diagram) is out
of scope and staying untouched. The prose needs rewording independent of the
figure — this is a text-only fix, not a figure change.

### 5. Figure 4 prose — same contradiction
> "The three leading compounds are dedicated to cancer treatments. The largest
> compound, Brentuximab vedotin, is vastly used for Anaplastic large T-cell
> systemic malignant lymphoma and Hodgkin's disease treatments, while
> Cytarabine is dedicated to Leukemia."

Same issue as #4: "largest compound" claim contradicts the new ranking.
Text-only fix, Figure 4 (disease-area alluvial) itself stays untouched.

### 5b. Cytarabine's dominance needs investigation, not just restatement
Per the review that produced this classification: 123 of Cytarabine's 690
screened families are Directly/Indirectly Relevant, vastly more than any
other compound in absolute terms — but Cytarabine's screened universe (690)
is also ~13–380x larger than every other compound's. Whether Cytarabine's
*rate* of relevance (123/690 ≈ 17.8%) is actually higher or lower than other
compounds' rates is a separate, unanswered question (e.g. Eribulin mesylate:
8/18 ≈ 44%; Trabectedin: 6/53 ≈ 11%). The manuscript should report both the
absolute count and this rate distinction — reporting only "Cytarabine leads"
without the rate context could itself read as a skewed headline given how
much of that count is an artifact of Cytarabine being a 60-year-old generic
chemotherapy name with a huge screened universe.

### 6. Table 3 (Spanish region) and Table 5 (Spanish companies) — pre-existing internal inconsistency, not introduced by this audit
Table 3 totals 1 (Andalusia) + 2 (La Coruña) + 14 (Madrid) + 1 (Valencia) =
**18** patents, which doesn't reconcile with old Table 2's Brentuximab-alone
count of 115, let alone the "217 patents" Spain figure in the Figure 1/2
prose. This mismatch predates this audit and predates the Minesoft work
entirely — flagged for awareness, out of scope per the current instruction
(Table 3 not to be touched).

### 7. Legal status percentages (72% X / 32% Y / 26% P / 3% E) — untouched, no new conflict
These numbers (tied to Figure 6 and repeated in the Discussion) come from
Patent Search Report categories in the Espacenet-based dataset. Nothing in
this session's work touches legal-status data, so no contradiction is
introduced — left as-is per instruction.

### 8. Minor pre-existing issue, unrelated to this correction
Table numbering skips from **Table 3** to **Table 5** — no Table 4 exists
anywhere in the manuscript. Pre-existing, not caused by or related to the
dataset correction; noting for completeness only.

## Summary — what needs prose changes when Table 2 is integrated

Text-only edits required (no figure/table image changes beyond the already-
built Table 2 replacement):
1. Abstract: add a sentence on the two-source methodology / correction.
2. Methodology: state the 12-vs-14-compound scope explicitly.
3. Table 2 intro paragraph: swap values, and state the new unit (Spain-only,
   relevance-classified families) is not comparable to the old (all-jurisdiction
   raw patent counts).
4. Figure 3 prose: remove/reword the "leading compound... Brentuximab vedotin"
   claim (organism figure itself unchanged).
5. Figure 4 prose: remove/reword the "largest compound... Brentuximab vedotin"
   claim (disease-area figure itself unchanged).
6. Add the 91/66/712/3 classification breakdown and the 157-vs-161
   (unique families vs. compound-family pairs) distinction wherever the new
   figures are introduced.
7. Add the Cytarabine absolute-count-vs-rate distinction (point 5b) rather
   than reporting the raw count alone.

Not touched, not modified, no new data acquired: Figures 1, 2, 3, 5, 6, Table 3,
Table 5, legal-status statistics.
