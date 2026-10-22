# Coverage-test protocol: gingivitis / oral-microbiome patent population

**Status:** PROTOCOL DRAFT — not frozen and not an ADR yet. With `τ` and the reference set still open it is not pre-registered; nothing is queried before §9 is closed.
**Date:** 2026-10-08
**Numbering:** unnumbered while draft. ADRs 0032–0035 already exist on other branches (`git log --all`), so the next free number is 0036; re-check before numbering.
**Scope:** decides whether a candidate source holds enough of the *worldwide* patent population on this topic for a gap analysis to be meaningful. It does not build the map, does not touch the operational corpus (`NEXUS-OPERATIONAL-CORPUS-V1`, "Demo coverage only"), and does not write an extractor.

---

## 1. Question

> Does this source contain enough of the worldwide patent population on gingivitis / periodontal health / oral microbiome for a low-density-zone analysis to be meaningful?

Answer is per source: `SUFFICIENT` or `NOT_SUFFICIENT`. Nothing else is reported as a verdict.

## 2. Probe (frozen at sign-off)

Source-neutral definition; each source gets a faithful translation, recorded verbatim in the run report.

* **Block C (classification):** CPC `A61Q11`, `A61K8`, `A61P1/02`.
* **Block T (text, title/abstract/claims where the source allows; English):** `gingivitis`, `periodontitis`, `periodontal disease`, `chlorhexidine`, `oral microbiome`, `oral microbiota`.
* **Arms:** `C AND T` (primary), `C` alone, `T` alone. Arms are reported separately; the primary arm is the one the verdict uses.
* **Window:** earliest priority year 2015–2024 inclusive. 2025–2026 are excluded from completeness claims because of the ~18-month publication lag; they may be shown, labelled incomplete.
* **Stop rule:** one execution per source. Any change of term, CPC, window or arm after seeing results is a **second probe** with a new ID; both are reported (§7).

## 3. Unit of analysis

Simple patent family, never publication. Each source's family definition is recorded (Minesoft `minesoftfamily`; EPO OPS DOCDB simple family). Family definitions differ, so cross-source comparisons are made on family counts and on shared member publications, not on family IDs.

## 4. Observed dimensions

Per family: earliest priority year, CPC (4-char and full), country of the earliest filing and of all members, applicant as normalised by the source (normalisation quality is itself recorded, not corrected).

Applicant concentration is **descriptive output only**. It is not a validity criterion: few dominant firms is a finding about the field, not a defect of the source.

## 5. Sufficiency conditions (all gating, all objective)

* **S1 — Known-item recall.** A reference set of families is fixed before any query to any source (§9), by someone who has not seen any source's results. A reference family is *eligible* iff, on its public record in a source **other than the one under test**, it carries a Block C CPC or a Block T term in title/abstract/claims; eligibility is decided and recorded at nomination time, never after querying. S1 passes iff the source returns at least `τ` of the eligible reference families under the primary arm. Ineligible families are listed and excluded up front; nothing is dropped after the fact. Recall is reported overall and per subset: `known_es_subset` (the 23 Spanish-derived families) is biased toward Spanish applicants, so **it is reported but does not count toward S1**; only the globally nominated subset does.
* **S2 — No truncation.** A query whose result count is at or above a result cap of the source is *truncated*, and a truncated result proves nothing about coverage (it shows potential truncation, not completeness). Caps are recorded from the source's documentation at run time (EPO OPS: per-search hit limit, believed 2,000; Minesoft: from the account). Pre-declared remedy, allowed because it is declared here: partition by priority year. S2 passes iff every partition used is strictly below the cap. Any partition still at the cap, or a cap that cannot be determined, is a fail.
* **S3 — Aggregation available.** The source can return, for the primary arm, counts by priority year, CPC and country without per-record fetching. If not, S3 fails for gap-map purposes.
* **S4 — Right of use.** Licence terms permit using the derived results in a report delivered to a third party. Evidence: the clause, quoted in the run report. Unknown counts as fail.

Descriptive diagnostics, **not gating**: year-by-year counts; arm overlap (`C` vs `T`); leave-one-term-out change in the primary family set; cross-source overlap if both sources are run.

Known limit of S1: it shows the source can retrieve what we already know exists, not that nothing else is missing. Where two sources are run, the overlap of their primary-arm family sets is also reported as a capture–recapture view of what both may be missing.

## 6. Discard criterion

If any of S1–S4 fails, the conclusion is `NOT_SUFFICIENT`: the source does not support a gap map for this topic. We stop. No broadened terms, no extra CPC, no relaxed `τ`. A different source or a second probe is the only continuation, and it is a new run (§7).

## 7. No post-hoc optimisation

* Terms, CPC, window, arms, reference set and `τ` are immutable after sign-off.
* Changes are allowed only as a **documented second probe**, with its own ID and the reason recorded *before* it runs; the first probe's result stays in the report.
* Results are never described as "gaps" or "white spaces" in this protocol's output. Coverage is a precondition for the map, not the map. Low density ≠ patentable, novel or free to operate.

## 8. Order of work

1. Sign off §9 → this document is frozen and committed.
2. Obtain access (Minesoft key; EPO OPS key/secret). Credentials are never committed.
3. Run the probe per source; write a run report with the verbatim queries, counts, S1–S4 outcome and licence quote.
4. Only if at least one source is `SUFFICIENT`: design the extractor and the topic corpus, stored apart from the operational corpus.

## 9. Open decisions before freezing

Freeze order: close `τ` and the reference set → Lydia validates the probe semantics against the Lacer challenge → number the ADR → commit the protocol on its own branch (not `main`) → only then credentials and queries.

| Decision | Owner | Note |
|---|---|---|
| `τ` (minimum share of eligible reference families recovered) | Valentín + Lydia | A pragmatic tolerance, not a statistical property. Value **and its justification** are written into this document before any query |
| Reference set: ≥ 20 globally known families nominated *without looking at the source* | Lydia / domain expert | Plus the Spanish-derived set (23 families from the operational corpus, incl. 4 Lacer EP) as a labelled subset |
| Term list and CPC list in §2 | Lydia | Confirm they match the Lacer challenge wording |
| Window | Valentín | Proposed 2015–2024 priority years |
