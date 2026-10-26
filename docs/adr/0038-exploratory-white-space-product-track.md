# ADR 0038: Exploratory White-Space Candidates in the Product, Outside the Study

**Status:** Proposed
**Date:** 2026-10-26
**Scope:** Allows the product to show **candidates** of the kind defined in [ADR 0036](0036-technology-white-space-scientific-scope.md) §5.4 (pairs of IPC subclasses never co-classified in the observed corpus), with an expected-count ordering, **as an exploratory feature that is not a result of the study**. It states the conditions under which this does not contaminate the study, and what changes in C2 of ADR 0036 and in the [vertical 2 contract](../whitespace/product-vertical-2-contract.md). **This ADR is documentary: it changes no code, dependency, contract or test.** Writing any detector code waits for its acceptance and for a vertical 3 contract (§7).

Companion documents: [Gap review of the MVP](../whitespace/mvp-gap-review.md) · [Decision note for Lydia](../whitespace/nota-lydia.md)

---

## 1. Context

The owner decided on 2026-10-26 that the MVP to give to Lydia is a **product that searches for white spaces in the OEPM corpus**, not the descriptive page. What exists today (vertical 1 and 2) is descriptive: for a chosen subclass it says which pairs have or have not been seen, with counts, ordered alphabetically by default, with no score and no ranking.

Three rules in the repository stand in the way:

* **C2 (ADR 0036 §12.2):** no detector, null-model code, baseline code or confirmatory evaluation is implemented or run before the pre-registration is closed. It is not closed: O2 (smallest useful AUC-PR difference and the power analysis), O3, and the two viability conditions of §8.11 (cost of the null model; a confirmed panel of at least six experts) are open.
* **Vertical 2 contract:** no score, no ranking by merit, no predictive claim. Its context section already says that a ranking "needs its own decision and an ADR change before any code". This ADR is that decision.
* **ADR 0036 §9 and §5.4:** an absence is not an opportunity; "research candidate" is not a probability of success, of realisation or of commercial value, and no such reading may be displayed.

The study's job is to find out whether a ranking predicts first co-classifications better than simple rules. The product's job is to let a person explore absences. This ADR keeps the two apart.

## 2. Decision

A separate **exploratory track** may show type A and type B candidates (ADR 0036 §5.4) of the **current corpus**, with an ordering by a stated descriptive quantity, under the rules E1–E8. It is not evidence for H1–H3, it does not use the study's code or outputs as its own, and the study's protocol is unchanged.

C2 of ADR 0036 is amended as follows: *it applies to the study's detector, null model, baselines and evaluation; the exploratory track of ADR 0038 is not covered by it, provided E1–E8 hold.* Nothing else in ADR 0036 changes.

## 3. Rules of the track

**E1. Candidates.** Those of ADR 0036 §5.4 with *m*_min = 20 and *e*_min = 1, the values fixed by design in §8.11 (P2). They are not tuned. The sensitivities *m*_min ∈ {10, 50} may be offered as filters, never as a search for a better value.

**E2. Reference year and data.** The candidates are computed from all documents of the versioned corpus up to **2025**, which is not an origin of the study (development 2003 and 2006; confirmatory 2013, 2016, 2022). The product therefore uses no outcome of any study origin, and nothing it shows can be used to choose among study options. The 2010 gap, the 2023 drop of EP translations and the other limits of C3 apply as in the study and are stated.

**E3. Expected count.** The quantity is the **expected number of co-classifications under independence within publication years**:

  E(i, j) = Σ over observed years *y* of n_i(y) · n_j(y) / N(y)

where n_i(y) is the number of documents (O4: the publication identifier, with the union of the subclasses of its earliest date) published in year *y* that carry subclass *i*, and N(y) is the number of documents published in *y*. Years not observed (2010) are skipped and never counted as zero. A pair is a candidate when it satisfies the type A or type B definition of §5.4 with the fixed values of E1.

It is a **descriptive reference under independence**. It is named exactly that, in its own module, and is **not** called F1, a null model or a baseline, and it is **not equivalent** to the study's null model (degree-preserving, curveball, 10,000 randomisations; P1), whose cost is still unmeasured (viability condition 1 of §8.11) and which is not pre-empted or approximated here. The two may differ. If the study's null model is later implemented, the product may switch to it only by a new ADR.

**E4. Ordering.**
* The **default order is alphabetical by symbol, always**, as in the explorer.
* The user may **choose** to sort by the expected count (E3, descending), by documents, or by symbol. The sort by expected count is labelled with the exact column name and carries a visible notice that it is not a prediction. It is never the initial order and is never presented as "best".
* Not allowed: a composite score, a rank labelled as likelihood, probability, potential, attractiveness or value, a p-value or a confidence statement, relevance labels, and any "top N" or "opportunities" wording (ADR 0036 §5.4 and §8.5).
* Making that order the default, or highlighting it as a result, needs an explicit later review and an ADR change.

**E5. Mandatory content of every candidate.** The documents (identifiers and dates) that make each subclass active, and the counts used for the expected count; the corpus identity and the SHA-256 of the corpus files and of the result used; the identifier of the configuration; the limitations of ADR 0036 §9 and C3; and the sentence that an absence in the observed corpus is not an opportunity. This is items 2 and 5 of §5.4 and the limitations of its item 4, without what belongs to the study (baseline score, method score, the uncertainty statement of §8.5).

**E6. Labels, empty states and language.** Every screen that lists candidates states, above the list: *Exploratory. Not validated. No ordering shown here is a prediction.* The study has not shown that any ordering predicts anything; the page says so and links ADR 0036. Empty states say what was filtered and that no candidate under these filters is not a finding. The forbidden formulations of E4 are tested negatively in the vertical 3 contract; the exact screens and texts are defined there.

**E7. Firewall with the study.**
* The track's code lives apart from anything the study will use; the study's pre-registered code is written separately and does not import it.
* No quality indicator of the product's ordering (precision, AUC-PR, "how many later appeared") is computed on any study origin, and no result of the product is used to adjust the study.
* The study's confirmatory origins stay unevaluated until the pre-registration is closed and frozen (A7).
* **Panel separation applies to anyone who may score**, not to one person. Before anyone is given access to the product's candidates, it is resolved and recorded whether that person may take part in the human review of §8.11 (P3). A person who may score does not see the candidates beforehand, or the panel's independence is lost. If access is needed, the role is settled first and the decision is written down.
* A negative or unresolved result of the study is shown in the product once known (ADR 0036 §7: "unresolved" is an allowed outcome).

**E8. Reproducibility and rights.** The candidates are produced offline from the versioned corpus into a versioned result file, with a test that recomputes the figures and the invariants against the existing section-density and pair results (as the explorer does). The corpus stays out of git (account-protected download). The OEPM reuse conditions apply (attribution, download date, no distortion; gate 5), and the OEPM consultation (P7) remains unsent: the product must not be published beyond the tailnet until the owner decides on the reuse question.

## 4. What changes and what does not

| Item | Change |
|---|---|
| ADR 0036 C2 | Scope narrowed to the study (§2 above). The rest of ADR 0036, its hypotheses, protocol and open items, is unchanged. |
| Vertical 2 contract | Unchanged: the explorer stays descriptive. Candidates go in a new vertical 3 with its own contract. |
| ADR 0037 | Unchanged. This track uses only the OEPM corpus; it does not touch the operational corpus or the Innoget demands, so gate 5 D2 does not block it. |
| Study pre-registration | Not closed by this ADR. O2, O3, P7 and the viability conditions stay open. |

## 5. What this does not do

It does not validate the ordering, does not close O2 (a decision of value for the users of a ranking), does not decide whether Lydia sits on the panel, and does not authorise publication outside the tailnet. It does not make "white space" a finding: the product shows absences in an observed corpus.

## 6. Risks and decisions

Decided by the owner on 2026-10-26, on the reviewer's assessment:

1. **Expected count:** independence within years (E3), with the formula stated and no claim of equivalence with the study's null model. *m*_min = 20 and *e*_min = 1 stay fixed.
2. **Panel:** the separation of E7 applies to anyone who may score.
3. **Ordering:** alphabetical by default; the expected-count order only by the user's explicit choice, with the exact column name and the notice (E4).

Risks that remain:

* **Reading as opportunity.** The main one. The mitigation is E4 to E6, in the page and in the briefing given to Lydia; it depends on how the output is presented and discussed. A sort chosen by the user is still a hierarchy on screen.
* **Sensitivity to the data.** The 2010 gap and the omissions (O5) move the counts; the effect on the expected count is not measured here.
* **Manual checks.** Automated tests do not replace the manual scenarios and the human visual review of the gate; they are run and recorded explicitly.

## 7. Next steps if accepted

1. A **vertical 3 contract** (what the screens show, the texts, the forbidden formulations, the tests), reviewed before code.
2. The code, in small pull requests: the expected-count module and its result file with tests; the screen; the forbidden-formulation tests extended to the new texts.
3. A human visual review, and a reading of the screen by the owner and Lydia against E6, before it is shown to anyone else.
4. Deployment to the existing staging only (tailnet), with the audit updated.

## 8. Acceptance

Takes effect when the pull request that sets the status to Accepted is merged. Until then no detector, expected-count or ordering code is written for the product.
