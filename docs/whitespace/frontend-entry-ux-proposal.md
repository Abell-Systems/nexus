# Frontend: proposal to make the entry page a tool people want to use (draft)

**Status:** Draft proposal for review. **Decisions of the owner's review, 2026-10-27:** option **A approved as the design direction** (not the texts, not the implementation); **B parked** (reconsidered only if the evaluation of A finds a problem that the current contract cannot solve; changing the role of `/` needs an explicit contract decision); **C out of scope** (no merging of the two searches without its own contract proposal); the **limits and parameters stay visible** next to each list (no fold by default) until the reading of «beside the list» is documented and decided; **H1, H2 and H3 were then approved (2026-10-27) and are implemented in draft #197; H4 (the label of example symbols) and the example symbols are not approved and are not in #197; H5 (skip link) is not approved as implemented text and goes in the second pull request**; the first implementation pull request is **option A alone** (draft #197, which also uses four neutral field labels, «Subclase IPC», «Sección IPC», «Ninguna» and «Buscar», kept provisionally and subject to checking that each control's text matches its behaviour), the quick wins go in a **second** one with their own tests. This document stays a draft and authorises no code. Documentation only: it changes no code, no contract and no ADR, approves no text, and shows no candidate to anyone. Every contract change it would need is named as such and is **not** made here. All Spanish wording is a proposal.
**Date:** 2026-10-27
**Checks:** [vertical 1 contract](product-vertical-1-contract.md) §1–§2 · [vertical 2 contract](product-vertical-2-contract.md) · [vertical 3 contract](product-vertical-3-contract.md) §2–§4 · [sheet experience proposal](vertical-3-sheet-ux-proposal.md) · [acceptance record](vertical-3-acceptance-status.md)
**Scope:** The entry page of the frontend (`/`) and the way its sections lead to the search of unobserved pairs. The matcher (`/matches`) is out of scope except for one note (§7).

## 1. What the audit of 2026-10-27 found, in short

Measured on `main` at `c683b6e`, running locally at 1280 px and 390 px, plus a reading of the code (an assistant's audit, not a test with people):

* The page reads as the **status report of a study**: title «Cobertura y ausencias del corpus de patentes», no action on the first screen, and the search of unobserved pairs is the **fifth of seven sections**, after about 4,400 px.
* **Two near-identical searches** (the subclass explorer of vertical 2 and the unobserved pairs of vertical 3) with the same placeholder and similar controls.
* In «Pares no observados» the controls come **after** a notice and three paragraphs of small grey text; the search sits below the fold at 900 px.
* Native, unstyled controls; two link colours (brand purple and the browser's blue); a thin default focus ring on this page (the matcher defines a 3 px one); navigation links 16 px high; 85 text elements under 13 px; no «skip to content» link.
* Good: contrast passes (navigation 6.2:1, secondary text 5.5:1), one `h1`, `lang="es"`, landmarks, accessible charts with data tables, no horizontal scroll at 390 px, explicit error states.

## 2. Constraints that bound any redesign

| Rule | Where | Consequence for the design |
|---|---|---|
| The front page has **six parts in this order**: overview, coverage, section map, what moves the counts, traceability, status of the white-space function | vertical 1 §1 | Reordering them, or moving the study off `/`, **needs an amendment of vertical 1**. |
| The page describes measurements; no heading, caption or layout may suggest that the method works; the status line «White spaces predictivos: no disponible. Pendiente de validación científica.» stays | vertical 1 intro, §1.6, §2 | A tool-first layout must still show that status line and must not frame results as findings. |
| The absence sentence appears wherever unobserved pairs are listed; the notice «Exploratorio. Sin validar…» is **above every list**; the fixed parameters and the limits are in a block **beside the list, not on another page** | vertical 3 §3, §4; ADR 0038 E6 | Cautions may be reorganised but not removed, and not moved to another page. Folding them into a section on the same page is a **reading** of «beside», to be confirmed by the owner. |
| The explorer is descriptive; vertical 2 is «unchanged» by vertical 3 | vertical 2 contract; ADR 0038 §4 | **Merging the two searches changes vertical 2** and needs its own decision. |
| No ranking, no score, no «top N», no recommendation wording, no colour scale on the expected count | vertical 3 §4; ADR 0038 E4 | A «featured» or «suggested» pair is not allowed in any hero. |
| Nothing is exposed; the static image answers 404 for the pairs data | acceptance record §6 | The redesign is built and judged locally. |

## 3. Three options

| Option | What it is | Contract change | Effort | Effect |
|---|---|---|---|---|
| **A. An entry block above the six parts** | A compact block at the top: what the tool does in one sentence, a search box and the section choice that **jump to** the pairs search, and a link to «Cómo se ha medido» (the six parts). The six parts keep their order and content. | None, if the status line and the notices stay as they are. | Small | The action is visible on the first screen. The page is still long. |
| **B. Two pages** | `/` becomes the tool (search, then the evidence sheet); the study moves to its own address (for example `/estudio`) with the six parts intact and linked from the tool. | Vertical 1: where the front page lives. | Medium | The product feels like a product; the study stays complete. |
| **C. Full reorder and merged search** | One search flow (observed and unobserved pairs) on one page, with the study as secondary content. | Verticals 1, 2 and 3. | Large | Best experience, highest risk of contradicting the contracts. |

**Decision (2026-10-27): A approved as direction; B parked; C out of scope.** The recommendation was: A now, then B after it has been evaluated with people. A changes no contract, can be built and judged in one small pull request, and tells us whether the first-screen action is what is missing. B follows only if A is not enough, and it needs the owner's decision on vertical 1. C is not proposed until the first two have been evaluated.

## 4. What option A looks like (wireframe, not a final design)

```
┌──────────────────────────────────────────────────────────────┐
│ ▲ ABELL SYSTEMS                      Cómo se ha medido  ·  …   │
│                                                              │
│  Pares de subclases IPC no observados en patentes españolas  │  ← proposal, not approved
│  Elija una subclase o una sección y vea qué combinaciones no │
│  aparecen juntas en el corpus de la OEPM hasta 2025.         │
│                                                              │
│  [ Buscar subclase  p. ej. G06N        ]  [ Sección  ▾ ]    │
│   Ejemplos:  G06N · A61K · H04L                              │  ← examples are not recommendations
│                                                              │
│  Exploratorio. Sin validar. Ningún orden mostrado aquí es    │  ← the E6 notice, visible
│  una predicción. White spaces predictivos: no disponible.    │  ← the status line of vertical 1
└──────────────────────────────────────────────────────────────┘
   (the six parts of vertical 1, unchanged, below; «Pares no observados» keeps its own notice and limits)
```

Design rules for the block and for the pairs section:

* **Search first, caution beside it.** Controls on one row where they fit (search, section, type, order), the notice visible above the list, and the limits and fixed parameters **visible** next to the list, as they are now. Any fold, even open by default, waits for the reading of «beside the list» to be documented and decided; this pull request does not decide it.
* **Initial state with a way in.** Clickable example symbols (neutral: chosen for being common, not for their results; the choice of examples is reviewed against «no recommendation») instead of a single line of text.
* **One link style** (brand purple, underlined), **one focus style** (the 3 px purple ring the matcher already defines), form controls with the brand's radius and borders.
* The two searches stay **distinct and named by what they answer**: «Pares observados de una subclase» (vertical 2) and «Pares no observados» (vertical 3), each pointing to the other. Merging them is option C.

## 5. Quick wins that change no contract

These can go in the same pull request as option A or in a separate one; none touches a mandatory text.

1. **Touch targets:** at least 24 px (WCAG 2.2 AA) and 40–44 px on phones for navigation links, `summary` elements and table buttons.
2. **Text size:** at least 12–13 px for chart and map labels, 14–16 px for reading text.
3. **Skip link** («Saltar al contenido») and a way back to the top on a page of about 4,400 px.
4. **One focus style and one link style** across the page and the matcher.
5. **Control styling** (selects, inputs, buttons) consistent with the brand; controls wrap predictably on phones.
6. **Matcher error state** (`/matches`): a retry action and a plain statement of the cause, in place of a bare red line.
7. **Print style** for the evidence and the traceability, so a person can keep what they looked at.

## 6. Texts this proposal would need

All are proposals and need the owner's approval, text by text, after reviewing their literal versions in context. **Forbidden-words check of 2026-10-27** (the closed list of the vertical 3 contract §4, as whole terms, without case or accents, singular and plural; an ad hoc script, not the test that will guard the screen): none of H1–H5 contains a listed word. That is a necessary check, not the approval, and says nothing about whether the wording suggests a recommendation, which only the review of the text in context can settle.

| Id | Where | Text | Note |
|---|---|---|---|
| H1 | Entry block, title | «Pares de subclases IPC no observados en patentes españolas» | Names what the tool shows; no «oportunidad», no «white space». |
| H2 | Entry block, sentence | «Elija una subclase o una sección y vea qué combinaciones no aparecen juntas en el corpus de la OEPM hasta 2025.» | Descriptive. |
| H3 | Link to the study | «Cómo se ha medido» | Neutral name for the six parts. |
| H4 | Examples | «Ejemplos de símbolos:» | The symbols themselves are chosen in review; they carry no meaning. |
| H5 | Skip link | «Saltar al contenido» | Standard. |

## 7. How we will know it worked

Not by opening a table, but by whether a person can complete tasks. Proposed evaluation, **with people, locally, none of whom is shown candidates before the panel decision of ADR 0038 E7 (still pending)**: for that reason the session uses the page as it is built with the real data only after that decision is recorded; before it, the evaluation covers the entry block, the navigation and the empty and error states, which show no pair.

Tasks (each timed and observed): find where to start; search a subclass; understand from the screen what a «par no observado» means; find the limits of the corpus; return to the top; do the first two on a phone. Measures: completion, time to first action, errors, and the person's own explanation of what the page does and does not claim. A usability session is the only evidence that the experience is «pleasant»; the audit above is not.

Matcher note: `/matches` could not be audited with data (it needs the API and the operational corpus, which stays out of git); only its error state and code were reviewed.

## 8. Decisions needed

* **Decided on 2026-10-27:** option A as direction; B parked; C out of scope; limits and parameters stay visible; first pull request is option A alone and the quick wins of §5 go in a second one, each with its own tests (keyboard and phone for the skip link, focus, text size and touch targets; the real error states for the matcher's retry; a print check that the limits, the provenance and the cautions are not hidden).
* **Still open:** the texts H1–H5 and the example symbols, approved separately and in context (a symbol must have an unambiguous meaning and suggest no classification, score or recommendation the system does not produce; no text may present an unobserved pair as an opportunity, a novelty or a conclusion on patentability; the explanation «Cómo se ha medido» must be reachable without hiding the methodological limits); the reading of «beside the list» if a fold is ever wanted; and who runs the evaluation and after which panel decision (E7).
* **Next step:** review the literal H1–H5 and the wireframe of §4 before authorising the implementation of the first pull request.
