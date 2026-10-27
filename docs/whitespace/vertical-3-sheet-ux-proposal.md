# Vertical 3: experience proposal for the evidence sheet of a pair (draft)

**Status:** Draft proposal for review. It changes no contract, no ADR and no code, and shows no candidate to anyone. **Update 2026-10-27:** in the review of this proposal the owner approved the direction, the texts S1, S2, S3 and S5, and a local prototype of the partial sheet (draft #193); **S4 was not approved** (it stands in for T22, which is decided in #184, not here), and the amendment for IPC titles was not opened. The approval of a text is of its content, not of an implementation or of the language and accessibility tests. The other Spanish wording below stays a proposal.
**Date:** 2026-10-27
**Checks:** [vertical 3 contract](product-vertical-3-contract.md) §3–§5, §8 · the E5 evidence specification (`vertical-3-e5-evidence-spec.md`, draft in #189, not on `main`) · [acceptance record](vertical-3-acceptance-status.md) · ADR 0038 E4–E7
**Scope:** How the sheet that opens from a row of the list should read and look, built on the data and rules that exist. It is the design basis for a **local** prototype of a *partial* sheet (no identifier lists, so it does not satisfy E5). Nothing here exposes anything; the nginx barrier stays.

## 1. The question the sheet answers

> What does this pair let me state, what evidence is behind it, and what would I have to check before interpreting it?

The sheet is a reading aid for a researcher, not a recommendation. It never says that a pair deserves attention; it shows what the corpus contains and what it does not, and lets the person decide.

## 2. Rules the design must respect (they limit what the brief asks for)

| Wish | Rule that bounds it | Consequence |
|---|---|---|
| Show each subclass with its description | Contract §3: «Only symbols are shown; no IPC titles (as in vertical 2)» | The sheet shows symbols only. Adding titles or descriptions is a **contract amendment**, not a design choice. |
| Say why the pair «deserves to be examined» | ADR 0038 E4, contract §4: no recommendation, no «oportunidad», no «atractivo»; the forbidden list includes *recomendado*, *mejor*, *potencial* | The sheet states **what is shown**, never whether to pursue it. The idea of «worth examining» stays in the researcher's hands. |
| A colour scale or emphasis on high expected counts | Contract §4: no colour scale that encodes the expected count as better or worse; no rank or position badge | One neutral palette. The expected count is a number with its terms, not a signal. |
| Compute and show things in the browser | Contract §3 and the rules of the per-year terms (#190) | The only client arithmetic is the reconstruction of the per-year terms and their sum; it feeds nothing else. |
| Share a link to a view | Contract §2: no link carries a sort by expected count as a result | The sheet has no shareable state beyond the default. |
| Look attractive | Spanish, phone width without horizontal scroll, keyboard operation, notices not hidden (M6) | Visual quality is judged against those, and by the visual review of the exposure gates. |

## 3. Reading order of the sheet (one column, top to bottom)

1. **What is compared.** The two symbols, side by side; documents of each up to 2025; «Documentos observados con ambas subclases: 0» (T21, approved); the absence sentence (T05, allowlisted, verbatim).
2. **Activity over time.** For each subclass, documents per publication year, in two small charts that share the same year axis and scale so they can be compared by eye. The years without any document in the corpus (2010) are drawn as a **labelled gap**, never as zero. Under each chart, the data table (as the coverage chart of the page already offers), for keyboard and screen reader users.
3. **How the expected count arises.** A short sentence defining it as the co-classifications that would be expected if the two subclasses were independent within each year; the table of the observed years (year, documents of A, documents of B, documents of the year, term), the sum, and the stored value beside it with the word *concordante* or the discrepancy state defined in #190. The formula appears once, in words and symbols.
4. **Documents behind the activity (D4).** Reserved block. In the partial sheet it states, plainly, that the lists of identifiers are not available yet (text pending approval, see §5); with D4 it shows the lists, loaded on demand.
5. **Where the numbers come from.** Corpus identity and the SHA-256 of its 26 files (collapsed by default), SHA-256 of the result, configuration identifier with its parameters in words, identity of the OEPM inventory taken from the exposure result and labelled as such. Attribution and download date as in vertical 1.
6. **Limits and cautions.** The limits of the corpus (T07), the parameters fixed by design (T04), and a short list of **things to check before interpreting** (§5), written as neutral prompts.

The pair stays reachable from the list without losing the list's state (chosen subclass or section, type, sort). Closing the sheet returns focus to the row it came from.

## 4. Visual direction

* A calm, scientific look: generous whitespace, one typeface family with a clear scale, numbers in tabular figures, a single neutral palette plus one accent used for focus and links only.
* Charts are discreet and honest: bars or lines on a zero baseline, the same scale for A and B, no 3D, no gradient, no decoration; every chart has a title, a description and its data table.
* The expected count has no special emphasis on the list or on the sheet; sorting by it keeps the existing notice.
* Reuse the page's existing components and styles (cards, tables, the coverage chart's pattern) before adding any; no new dependency.

## 5. Texts the sheet would need (S1, S2, S3 and S5 approved on 2026-10-27; S4 not approved)

Already approved and reusable: T05, T04, T07, T21, T09 column names, T18/T19 states. New, to be reviewed against the forbidden list of the contract:

| Id (proposal) | Where | Proposed text | Note |
|---|---|---|---|
| S1 (approved) | Block 3, definition | «El esperado bajo independencia es la suma, año a año, de documentos de A × documentos de B ÷ documentos del año.» | Uses the column's approved name in full. |
| S2 (approved) | Block 3, agreement | «La suma reconstruida coincide con el valor almacenado.» / «La suma reconstruida no coincide con el valor almacenado: se muestra la diferencia.» | The discrepancy state of #190; the stored value is never replaced. |
| S3 (approved) | Block 2, gap | «Sin publicaciones en el corpus este año.» | For 2010; never a zero. |
| S4 (**not approved**) | Block 4 | «Las listas de identificadores de las subclases aún no están disponibles en esta vista.» | Stands in for T22, which is not approved; the partial sheet cannot claim E5. |
| S5 (approved, subject to the forbidden-words check) | Block 6, prompts | «Antes de interpretar: ¿el periodo y el tipo de documento cubren lo que busca? ¿Los símbolos se usan igual en otras fuentes? ¿Qué documentos hay en cada subclase?» | Neutral questions; no word of the forbidden list. To be checked by the test and by M3. |

## 6. A partial sheet as an intermediate increment

The data for blocks 1, 2, 3 and 5 exist on `main` (`documents_by_year`, `configuration`, the corpus hashes, `expectedTerms`). Block 4 does not exist (D4). A **local prototype** of the sheet with S4 in block 4 is therefore possible without new data, and it is an **intermediate increment that does not satisfy E5** and must not be exposed. It is built in draft #193, tested with the real file and labelled as such in its pull request.

What it cannot do: M4 (the person recomputes one pair by hand) is satisfiable for the terms, but E5's «activity evidence of each subclass» (the full lists) is not; so the acceptance record keeps E5 as not met.

## 7. Decisions and open points

* **Panel (E7/M7).** Whether Lydia, or anyone, may take part in the human review of the study is **pending**. While it is, **no candidate is shown to anyone**; the prototype is looked at only by the people who build it, locally. This document does not decide it.
* **Titles of the subclasses.** Wanted by the brief, not allowed by the contract; an amendment would be needed and is not proposed here.
* **Texts.** S1, S2, S3 and S5 approved on 2026-10-27, subject to the forbidden-words check (run in #193 on the sheet's text and accessible names) and to M3; S4 is not approved and is to be resolved together with T22 in #184. The prototype in #193 uses S4 and therefore cannot be merged until then.
* **Store of the lists (D4, #183).** Open; the partial sheet does not depend on it.
* **Exposure.** Unchanged: gates of the contract (§7–§9), the owner's authorisation, tailnet only, barrier intact.
