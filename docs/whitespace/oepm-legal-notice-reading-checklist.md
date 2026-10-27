# OEPM legal notice: reading checklist for the storage decision of the identifier lists (draft)

**Status:** Draft working aid for a person. It decides nothing, it is **not** the reading that gate 5 asks for, and it is not legal advice. Its purpose is to make that reading short and precise, and to keep the literal text apart from any interpretation.
**Date:** 2026-10-27
**Checks:** [gate 5](../operations/adr-0037-gate5-licences-and-retention.md) §3 (OEPM OpenData row), G4, §8.3 · [E5 storage options](vertical-3-e5-storage-options.md) §2, §6 · [contract](product-vertical-3-contract.md) §5, §6, §9.1 · ADR 0038 E8
**Source:** `https://sede.oepm.gob.es/eSede/datos/es/aviso-legal/` (the address recorded in gate 5). Fetched on 2026-10-27.

## 1. How to use this document

1. Open the page above yourself and read the notice in full. The quotes in §2 were **extracted by an automated fetch and summarised by a model**; they are not verified. For each quote, mark whether it appears **word for word** in the page (§2, last column). A quote that does not appear is struck out.
2. Answer the questions of §3 in your own words, citing the sentence of the notice each answer rests on.
3. Fill in §5 (who read it, when, what version of the page).
4. Do not fill in the «effect on the decision» column of §4 unless the answer is clear from the quotes; if it is not, write «counsel».

## 2. Sentences extracted from the notice (to be verified by the reader)

| # | Topic | Sentence as extracted (Spanish) | Word for word in the page? (yes / no / differs) |
|---|---|---|---|
| 1 | Scope | «permiten la reutilización de los documentos sometidos a ellas para fines comerciales y no comerciales» | |
| 2 | Activities | «La reutilización autorizada incluye, a modo ilustrativo, actividades como la copia, difusión, modificación» | |
| 3 | Rights | «Esta autorización conlleva, asimismo, la cesión gratuita y no exclusiva de los derechos de propiedad intelectual» | |
| 4 | Activities | «autorizándose la realización de actividades de reproducción, distribución, comunicación pública o transformación» | |
| 5 | Condition: no distortion | «Está prohibido desnaturalizar el sentido de la información.» | |
| 6 | Condition: source | «Debe citarse la fuente de los documentos objeto de la reutilización.» | |
| 7 | Condition: wording | «Origen de los datos: Oficina Española de Patentes y Marcas» | |
| 8 | Condition: date | «Debe mencionarse la fecha de la última actualización de los documentos objeto de la reutilización» | |
| 9 | Condition: sponsorship | «No se podrá indicar, insinuar o sugerir que la OEPM, titular de la información reutilizada, participa, patrocina o apoya» | |
| 10 | Condition: metadata | «Deben conservarse, no alterarse ni suprimirse los metadatos sobre la fecha de actualización» | |
| 11 | Responsibility | «se realizará por parte de los usuarios o agentes de la reutilización bajo su propia cuenta y riesgo» | |
| 12 | OpenData | «Todos los datos que se publican en el portal OpenData son reutilizables.» | |
| 13 | Law | Ley 37/2007, de 16 de noviembre (reutilización de la información del sector público); Real Decreto 1495/2011, de 24 de octubre; «el régimen sancionador previsto en el artículo 11 de la Ley 37/2007» | |

The extraction found **no version number and no date for the notice** itself; the only date on the page was the copyright line «© Oficina Española de Patentes y Marcas, 2026». Gate 5 recorded the same absence on 2026-10-22.

What the extracted sentences suggest, **as the assistant's reading and not as a finding**: the notice appears to authorise reproduction, distribution and public communication, commercial included, under conditions that are the same whether the files are in Git or elsewhere. This is consistent with the repository's own reading in gate 5 §3 (not reviewed by counsel).

## 3. Questions the reader answers

| # | Question | Why it matters for the storage decision |
|---|---|---|
| Q1 | Does the notice authorise **distributing and publicly communicating** the publication identifiers and publication dates of OEPM documents, as lists per IPC subclass? Which sentence says so? | Both options publish them: in Git (public repository) or in a store the build fetches. |
| Q2 | Are the lists «documentos sometidos a ellas», or a **transformation** (a derived selection and reordering of fields)? Does the notice cover both? | The lists are derived from the bibliographic records, not copies of them. |
| Q3 | Which conditions must travel **with the lists themselves** (attribution wording, last-update date, no-distortion, no-sponsorship)? Is it enough that the page that shows them states these, or must the files carry them? | The files could be fetched or copied without the page. |
| Q4 | Condition 10 asks that the **update-date metadata be preserved**. Do the OEPM files carry an update-date metadata field that the lists would drop? (Gate 5 notes that the date the repository records is the **download date**, not the OEPM's update date.) | Possible non-compliance that exists today for any derived table, independent of Git. |
| Q5 | What does article 11 of Ley 37/2007 (régimen sancionador) attach to a breach of the conditions? | Sets how costly a mistake in the first publication would be. |
| Q6 | The page shows no version or date. How will the reading be **anchored** (date of reading, a saved copy and its hash)? | A later change of the notice must be detectable. |
| Q7 | Is **counsel's review** needed before publishing in a public repository, given that gate 5 records that counsel has not reviewed it? | Git history is not rewritten (decision on record): a file committed stays. |

## 4. Where the answers feed the decision (no recommendation here)

| If the reading says | Then, for the storage options of [the options document](vertical-3-e5-storage-options.md) |
|---|---|
| Q1 yes, Q3 satisfiable by what the page and a header field carry, Q5 and Q7 raise no objection | The legal condition that made B provisional is lifted; the choice between A (in Git) and B (outside) goes back to the technical criteria of §4–§5 there (weight of history, new moving parts, fail-closed fetch). |
| Q1 yes, but a condition cannot travel with a file in Git, or counsel is needed | B stays, and the manifest/fetch design of §6 there applies; the question is then who may fetch. |
| Q1 unclear or no | Neither option is implemented; the lists wait for counsel. Nothing is committed or published. |

The owner decides; this table only shows which way each answer points.

## 5. Record of the reading (to be filled in by the reader)

| Field | Value |
|---|---|
| Name of the reader | |
| Date and time of the reading | |
| Address read | |
| Saved copy of the page (path) and its SHA-256 | |
| Version or date shown by the page | |
| Answers Q1–Q7 | |
| Counsel review requested? | |
| Decision of the owner on storage | |
