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
* **D2. Authority File hash.** Add it to the unobserved-pairs result or show it from the exposure result. Either way the sheet shows what the data record, and not more. §7 notes that the unobserved-pairs result does not read the Authority File.
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

## 7. Proposal for D1–D3, with recommendation (for the owner's decision)

Nothing in this section is decided. Each item gives the options, what was measured, and a recommendation. Measurements were made on 2026-10-27 with a scratch script (not committed) over the hash-verified corpus and the committed result.

### Measurements

* The per-subclass, per-year counts of the 621 active subclasses (O4 union, as `activity_counts(records, "union")` gives them) are **14,922 entries, 154,693 bytes as compact JSON, 35,648 bytes at zlib level 6**. Their per-subclass sums equal the `active` totals of the result.
* The corpus has **25 years with documents; 2010 is absent** from `documents_per_year`, so it can never appear as a zero term.
* For a sample (every pair whose first symbol is among the first 40 first-symbols of the result), the sum over years of n_i(y)·n_j(y)/N(y), rounded to 9 decimals, equals the stored expected count with **a maximum difference of 0**. For A01B and A01J it is 0.554177296 in both, with 25 non-zero terms. This shows the stored value can be reproduced from the per-year counts; it does not prove it for all 149,048 pairs.
* Precomputing the terms of every pair would mean up to 149,048 × 25 ≈ 3.7 million numbers. Not built or measured; at several bytes each it is tens of MB.
* The generating script and function read **only the bibliographic files**. The Authority File is not an input of the unobserved-pairs result (read in `report_oepm_unobserved_pairs.py` and `unobserved_pairs.py`). It is the inventory used by the 2025 completeness comparison.

### D1. How the terms are shown

| Option | What it is | Assessment |
|---|---|---|
| (a) Counts by year, terms displayed by the browser | The result gains the per-subclass per-year counts. The sheet multiplies and divides for display and shows that the sum equals the stored value | Small (about 0.15 MB, 36 KB compressed). Satisfies §5 (terms visible) and M4 (recomputable by hand). Needs the contract to say what «computes no metric» covers |
| (b) Precomputed terms per pair | Shipped with the result | Tens of MB, unmeasured; adds data nobody sorts or filters by |
| (c) Counts and N(y) only; the person computes | No terms shown | Does not satisfy §5 literally («its terms (the per-year contributions)») |

**Recommendation: (a)**, with these limits. The stored expected count remains the only value used to list, filter, sort and label. The per-year products are display arithmetic on verified inputs, never fed back into any order or filter. The sheet shows the sum next to the stored value; if they differ at the stored 9 decimals, it shows the discrepancy and not a number that looks consistent. **This needs a clarification of contract §3**, by the usual amendment process and not by the interface. Proposed wording, for review: «The browser filters and sorts the stored expected count and computes no other metric for listing, filtering, sorting or labelling. On the evidence sheet it may display the per-year contributions of a pair as arithmetic on the verified counts of the result, together with their sum compared with the stored value.»

### D2. Authority File hash

The contract (§6) says the Authority File hash is recorded «like the other results». For this result that sentence presupposes an input it does not have. Options: (a) add the hash to the result anyway; (b) show the Authority File identity on the sheet from the exposure result, as the inventory of the 2025 completeness comparison; (c) leave it out and correct §6.

**Recommendation: (b), plus a one-line correction of §6.** Adding the hash to a result that does not read the file (a) would claim a dependency that does not exist, which is the kind of provenance claim we avoid. The sheet's limits line already says the completeness is compared against the OEPM inventory; showing the inventory's name and SHA-256 there, taken from the exposure result and not from this one, is accurate. The §6 correction would read: «The corpus identity hashes are recorded in the result; the Authority File identity is recorded in the exposure result and shown with the completeness comparison.»

### D3. Identifier of the configuration

ADR 0038 names it and does not define it. What the ADR fixes in E1 as configuration is: the reference year, the minimum documents of an active subclass, the minimum expected count of the second type, plus the unit (O4) and the quantity (E3).

| Option | Identifier | Assessment |
|---|---|---|
| (a) Parameters in canonical form | A SHA-256 of the canonical JSON of `{schema, origin, min_documents, e_min, unit, quantity, decimals}`, shown with those parameters in words | Deterministic, readable, independent of Git. Does not identify the code |
| (b) (a) plus the script | Hash over the parameters and the bytes of the generating script | Identifies the code, but changes on any reformatting and mixes two things |
| (c) Generating commit | The commit that produced the result | Self-referential: the result is committed after it is generated, so the commit cannot be known inside it |

**Recommendation: (a), recorded in the result as `configuration: { id, parameters }`.** The code version is already identified by the result's own SHA-256 together with the tests that regenerate and compare it (contract §6), so the configuration id need not carry it. The sheet shows the id (a short prefix is acceptable if the full value is available) and the parameters in words. This is an interpretation of an undefined term; the owner confirms it or chooses another.

### How the three fit together

If the owner accepts the recommendations, D1 and D3 need **one regeneration** of the result (a new version with `documents_by_year` and `configuration`), one update of `provenance.json` and one frontend copy, in a single data pull request. D2 needs no data change. Order of work: (1) a documentation pull request with the contract clarifications (§3 wording for D1, §6 wording for D2) and the owner's decision on D3; (2) the data pull request, with invariants (per-subclass yearly sums equal `active`; 2010 absent; sum of terms equals the stored value, tested on a hand-computed fixture and on a sample of the real result; the new keys are covered by the hash test); (3) the sheet, over the verified loader. D4 (the lists) stays separate and does not block (1) or (2).
