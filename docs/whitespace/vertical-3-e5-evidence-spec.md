# Vertical 3: specification of the evidence sheet of a pair (E5), draft

**Status:** Draft specification for review. Documentation only: it implements nothing, decides nothing that belongs to the owner, and does not modify [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) or the [contract](product-vertical-3-contract.md). Where it meets a gap or an ambiguity it says so as an **open decision (D1…)** instead of choosing.
**Date:** 2026-10-27
**Checks:** ADR 0038 E3, E5, E6 · contract §3, §5, §6, §6.1, §8, §9.1 · texts T05, T07, T20–T22 of the texts proposal (#184) · storage options (#183, provisional) · acceptance record (#188)
**Scope:** What opening a pair must show, which of it the data already carry, which it does not, and the acceptance criteria. Phases C and D of the UX proposal (technical problem, research sheet) are out of scope, and no score, rank or hypothesis generation is part of the sheet.

## 1. What the rules require

ADR 0038 E5 (mandatory content of every candidate): the documents (identifiers and dates) that make each subclass active, and the counts used for the expected count; the corpus identity and the SHA-256 of the corpus files and of the result used; the identifier of the configuration; the limitations of ADR 0036 §9 and C3; and the sentence that an absence in the observed corpus is not an opportunity.

Contract §5 turns it into: both symbols; documents per subclass up to 2025 and by publication year; documents with both (0 by definition); the expected count and its terms (the per-year contributions); the corpus identity, the SHA-256 of the result and the configuration identifier; the limits of §3; and the activity evidence of each subclass, the **full list** of its publication identifiers with dates, loaded on demand (§9.1: the 20-identifier reading is withdrawn; a shorter list is an ADR amendment, not an interface choice). M4 (manual) requires that the evidence be enough to **recompute the expected count by hand for one pair**.

## 2. Element by element: what exists today

Checked on 2026-10-27 against `docs/whitespace/oepm-unobserved-pairs-results.json` (top-level keys: `origin`, `min_documents`, `e_min`, `quantity`, `formula`, `decimals`, `documents_per_year`, `active`, `counts`, `pairs`, `corpus`).

| Element of the sheet | Source of the rule | In the data today | What is missing |
|---|---|---|---|
| Both symbols | contract §5 | Yes (the pair key) | — |
| Documents per subclass up to 2025 | contract §5 | Yes: `active[symbol]` | — |
| Documents per subclass **by publication year** | contract §5, §6 | **No.** Only the total per year of the whole corpus (`documents_per_year`) | A per-subclass, per-year count, «observed years only» (contract §6). |
| Documents with both | contract §5 | By definition 0 for an unobserved pair | Text T21 (approved). |
| Expected count | ADR E3 | Yes: `pairs[a][b]`, 9 decimals | — |
| **Terms** of the expected count (per-year contributions n_i(y)·n_j(y)/N(y)) | contract §5; M4 | **No.** N(y) is present; n_i(y) and n_j(y) are not | The per-subclass per-year counts above (see D1). |
| Corpus identity and SHA-256 of the corpus files | ADR E5 | Yes: `corpus.source_id` and 26 file hashes | — |
| SHA-256 of the result used | ADR E5 | Yes: in `provenance.json`, which the loader already uses | To be shown on the sheet. |
| Authority File identity (hash) | contract §6 («recorded like the other results») | **No** in this result (the exposure result carries `authority_file`) | To be added to the result or shown from the exposure result (D2). |
| **Identifier of the configuration** | ADR E5; contract §5 | **No** identifier. The result carries the parameters (`origin`, `min_documents`, `e_min`) but no identifier, no generating script and no commit | The ADR does not define what the identifier is (D3). |
| Limitations of ADR 0036 §9 and C3 | ADR E5; contract §3, §5 | Text T07 exists on the list screen | To be repeated on the sheet. |
| «Absence is not an opportunity» sentence | ADR E5 | Yes: T05 (allowlisted, verbatim) | To be shown on the sheet. |
| **Full list of publication identifiers and dates per active subclass** | ADR E5; contract §5, §6, §9.1 | **No.** Not generated, not stored, not served | Everything: generation under O4, store, delivery, manifest (see §5 and #183). |

## 3. Open decisions that block the specification

* **D1. How the terms are shown.** The contract says the browser «filters and sorts; it computes no metric» (§3) and M4 requires enough evidence to recompute the expected count by hand. Two readings: (a) the sheet receives, per subclass, the counts by year, and the browser **displays the per-year products** n_i(y)·n_j(y)/N(y) as arithmetic on verified inputs, with a visible check that their sum equals the stored expected count; (b) the per-year terms are precomputed for every pair and shipped. (b) is large (about 149,000 unobserved pairs times the years in which both have documents). (a) is small, but is arithmetic in the browser, which the contract's wording could be read to forbid. Which reading is allowed is a contract interpretation for the owner; it is not decided here. If (a) is chosen and the displayed sum differs from the stored value, the sheet must say so and not show a number as if it agreed.
* **D2. Authority File hash.** Add it to the unobserved-pairs result (a new version of the result, regenerated and re-hashed) or show it from the exposure result. Either way the sheet shows what the data record, and not more.
* **D3. What the «identifier of the configuration» is.** ADR 0038 names it but does not define it. Candidates, to choose among: the parameters themselves in a canonical form (`origin`, `min_documents`, `e_min`, the formula name); a hash of those parameters plus the generating script's path; the generating commit. None is chosen here, and the sheet must not invent one.
* **D4. Where the identifier lists live and how they reach the image.** Provisional in #183 (outside Git, verified fetch, fail closed), conditional on a person reading the OEPM legal notice; three points open (store location, delivery to the read-only image, regeneration). The sheet depends on this; this specification does not resolve it.

## 4. Behaviour of the sheet

1. Opened from a row of the list. The sheet does not replace the list state (the chosen subclass, section, type and sort stay).
2. Always visible without further data: the two symbols, documents per subclass (`active`), documents with both (T21), the stored expected count, the result's SHA-256, the corpus identity and file hashes, the configuration identifier (once D3 is decided), the limits (T07), the absence sentence (T05) and the Authority File identity (once D2 is decided).
3. Loaded on demand when the sheet opens, **through the verified loader and nothing else**: the per-year counts of the two subclasses (once they exist) and the identifier list of each subclass (once D4 is decided). Each file has its own entry in the manifest of the bundle.
4. States, all distinct and none sharing a path that renders results: loading (T14); load error (T18, with retry); integrity error (T19); list not available (T22, once approved); everything in place. A partial result is never presented as complete: if one subclass's list cannot be shown, the sheet says which one and shows no activity evidence for it. What remains visible in that case (counts already verified) is a decision for the review of the texts, not of this document.
5. The lists are shown in full, ordered by date and identifier, with a count of identifiers; a list of up to 2.44 MB (the largest, `A61K`, measured in #183) must not block the page: it is loaded when requested and rendered without freezing the interface (the technique is an implementation matter, but the acceptance criterion E5-8 below tests the behaviour).
6. No field of the sheet is a score, rank, colour scale or label of quality. No sentence on the sheet states or suggests that the pair is an opportunity, and none turns the expected count into a probability (§4 of the contract; M3).

## 5. Acceptance criteria

«Automated» means a test that fails if the behaviour breaks. «Manual» means a scenario run and recorded by a named person; it is not satisfied by tests.

| Id | Criterion | Kind |
|---|---|---|
| E5-1 | Opening a pair shows both symbols, documents of each subclass up to 2025, T21, the stored expected count and the limits and absence sentences verbatim | Automated |
| E5-2 | The sheet shows documents per subclass by publication year, taken from verified data, with 2010 absent and never zero | Automated (needs the per-year data) |
| E5-3 | The per-year terms and their sum are shown; the sum equals the stored expected count to the stored decimals; if it does not, the sheet shows the discrepancy instead of the number | Automated (depends on D1) |
| E5-4 | The corpus identity, the 26 file hashes, the result's SHA-256 and the configuration identifier are shown and equal the recorded values | Automated (depends on D2, D3) |
| E5-5 | The identifier list of each subclass is complete: its length equals the count in the manifest and it contains no identifier twice | Automated (depends on D4) |
| E5-6 | Every file the sheet reads goes through the verified loader; a changed byte in a list or in the per-year data shows T19 and no evidence; a 404 shows T18 | Automated, plus a repeat of the M8 procedure for these files |
| E5-7 | The states of §4.4 render different texts and none shares a code path that renders results | Automated |
| E5-8 | Opening the largest list does not block input for the user (measured and stated, not asserted) and no list is requested before the sheet opens | Automated plus a recorded measurement |
| E5-9 | The forbidden-formulation checks of the contract pass on every state of the sheet, including accessible names | Automated; M3 manual |
| E5-10 | Following the evidence, a person can recompute the expected count of one pair by hand and reach the stored value | Manual (M4) |
| E5-11 | The sheet is reachable by keyboard, readable at phone width, and the notices are not hidden | Manual (M6) |

## 6. What this specification does not do

It does not choose among D1–D4, does not approve T22, does not generate or store any list, does not touch the nginx barrier, and does not make #187 conforming to E5. #187 stays an intermediate increment until the criteria above are met or the owner amends E5 through an ADR.
