# First product vertical: descriptive screens for the white-space study (contract)

**Status:** Contract for the first vertical, to be reviewed before any code is written. Nothing is implemented by this document.
**Date:** 2026-10-21
**Checks:** [ADR 0036](../adr/0036-technology-white-space-scientific-scope.md) (non-claims, C3, §9) · [corpus exposure](oepm-corpus-exposure.md) · [omission sensitivity](oepm-omission-sensitivity.md) · the descriptive briefing and the section map (pull request #142)
**Scope:** What the first screens show, from which data, under which rules, and how it is accepted. **Descriptive only: no ranking, no score, no predictive claim, no new endpoint.**

The product and the study advance separately. **Showing results is not validating the method:** the front page describes measurements that already exist and is not evidence that the predictive approach works; no heading, caption or layout may suggest it is. This vertical shows what the study has already measured; it does not make any claim that the study has not earned, and it does not select parameters of the pre-registration.

---

## 1. What the first release shows

One page with six parts, in this order:

1. **Overview of the corpus and its limits.** What the corpus is (OEPM bibliographic publications, 2000–2025), how many publications it holds against the OEPM's own inventory, and the documented limitations (C3).
2. **Coverage.** Present and absent publications by year, with the year and the kind group (`T*`, `Y`, others) explicit; the whole of 2010 and the kind-`Y` publications of 2000–2009 stand out. Every chart states its denominator (the inventory's publications of that year) and its period.
3. **Section map.** Share of IPC subclass pairs already seen together, by pair of sections, at the origins 2006 and 2022, with **one colour scale for both maps** and a legend. Each cell gives the count behind it.
4. **What moves the counts.** The descriptive sensitivity at the development origins, stated as a change of the problem, not as the effect of the omissions.
5. **Traceability.** For every chart: the versioned result it is drawn from, the SHA-256 of that file, the corpus identity (the 26 hashed files), the Authority File used, and the pull request that produced it.
6. **Status of the white-space function.** A visible statement: «White spaces predictivos: no disponible. Pendiente de validación científica». It links to nothing that ranks anything.

## 2. Rules the text and the charts must obey

* An observed absence is **never** called an opportunity, a gap to exploit, a candidate or "promising". The page states that an absence is not an opportunity.
* No claim of predictive capacity, anywhere, including headings, tooltips and the title of the page.
* The effect of the absent publications on any result is not estimated; the page says it cannot be identified from the data, and it does not attribute to the random simulation what it cannot show about the kind-`Y` omission.
* The source is attributed visibly: «Origen de los datos: Oficina Española de Patentes y Marcas». Nothing suggests that the OEPM participates in, sponsors or supports the product.
* A figure is shown only as the versioned result states it: the browser does not recompute, aggregate or invent any metric.
* One colour scale for charts that are compared; colour is never the only carrier of meaning (values, patterns and labels accompany it).
* Language: Spanish.

## 3. Data

* Inputs are the versioned JSON results of this repository: the corpus exposure, the descriptive sensitivity and the section density, plus the corpus identity (`config/whitespace/oepm_biblio_2000_2025.json`). The section density arrives with pull request #142.
* They reach the frontend as static files, copied by a script from `docs/whitespace`; a test requires the copies to be identical to the originals, so the screens cannot drift from the documents. No endpoint is added and the backend is unchanged.
* The SHA-256 shown in the traceability panel is computed from the same file at build time and checked by a test.

## 4. Structure (Clean Architecture of the frontend)

* `domain`: types of the results and the fixed texts that carry the rules of section 2.
* `application`: pure functions from a result to what a chart draws (series, scale, the common colour scale); no DOM.
* `infrastructure`: the loader of the static data.
* `components`: the page and its six parts, as inline SVG and HTML. No chart library: the charts of this release are bars and a matrix, and a library is reconsidered when a concrete interactive need appears.

## 5. Decisions taken at review

1. **Relation to the current screen.** The new page is the front page; the matcher of demands and assets stays reachable at its own address, with its implementation and the deployed links unchanged. Retiring it needs a separate decision.
2. **Navigation.** A single page with anchors; no router and no new dependency. Independent flows would be evaluated when they appear.
3. **Dependency on #142.** The section map is built on the versioned results that #142 introduces, without duplicating calculations or replacing them with estimates. Implementation starts when #142 is merged and stable in `main`.

## 6. Acceptance

* Typecheck, lint, build and all tests pass; the built page renders at desktop and phone width without horizontal scroll.
* Tests: the copies of the data are identical to the versioned results; the traceability hashes match; the mandatory texts are present (attribution, "an absence is not an opportunity", the unavailable status) and forbidden formulations are absent; the common colour scale is applied to both maps; headings, landmarks, text alternatives for the SVG and keyboard focus are present.
* Visual review at desktop and phone width, and the Playwright journey of the page run against a local server. The journey of the matcher, which was not run when the old agent UI was removed (#143), is run too and must pass.
* The diff adds no endpoint, no ranking and no library, and changes no figure of the study.
* The page makes no claim that the ADR does not make, and nothing on it can be read as a validation of the predictive method.
