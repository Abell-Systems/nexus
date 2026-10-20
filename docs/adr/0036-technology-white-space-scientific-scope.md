# ADR 0036: Technology White-Space Discovery — Scientific Scope and Operational Definition

**Status:** Proposed
**Date:** 2026-10-20
**Scope:** Fixes the scientific question, the universe of inference, the operational definition of a white-space candidate, the temporal design and the evaluation protocol for the first white-space experiment on the OEPM bibliographic corpus, and lists what remains undecided. **Documentary only — no code, no dependency, no contract, no test and no existing document is changed.** Nothing in this ADR claims that a detector works; no detector exists yet.

Companion documents: [Audit of `main`](../whitespace/architecture-audit.md) · [OEPM corpus characterization](../whitespace/oepm-biblio-corpus-characterization.md)

---

## 1. Context

Nexus was built to match technology demands to patents. The matching question rests on an assumption that linguistic similarity between a demand and a patent indicates that the patent can solve the need, and a demand and a patent are not classified on a common scheme. The pivot replaces the central question: instead of *which available technology fits this demand*, the question becomes *which technology areas show signals of under-explored combinations that deserve investigation*. Matching is not abandoned; it is demoted from conclusion to a possible auxiliary validation tool.

The audit of `main` ([architecture-audit.md](../whitespace/architecture-audit.md)) found reusable ingestion, storage and provenance machinery, and one existing white-space score (`application/landscape/metrics.py`) that rests on unvalidated weights, depends on a demand signal and labels clusters as opportunities. It is left untouched by this ADR.

The first experiment uses a corpus that can be obtained at no cost: the OEPM OpenData bibliographic files for 2000–2025 ([corpus characterization](../whitespace/oepm-biblio-corpus-characterization.md)). This ADR takes that corpus's properties, including its gaps, as constraints on the design.

Guiding principle: Nexus must discover and justify potential opportunities, not manufacture convincing coincidences. An observable gap in data is not an opportunity, and the absence of documents does not show that nobody is working on something.

## 2. Scientific question

> **Q.** Using only documents published by the OEPM up to year *t*, can pairs of IPC subclasses that have never been classified together on a single document up to *t* be ranked so that those that are classified together for the first time in publications of years *t*+1…*t*+*h* are found more often than by simple rules?

The event being predicted is a **first co-classification in an OEPM publication** (FCP). It is not the first appearance of a technological combination in the world, nor the emergence of an invention (see §6.2).

Q tests whether a detector's ranking carries predictive signal about a combination event. That is a **necessary check** on a detector, not evidence that its candidates are innovation opportunities. A positive answer would not show commercial value, novelty beyond this corpus, feasibility, or that the combination arose because Nexus pointed at it. A negative or inconclusive answer is a valid result and will be reported as such.

## 3. Universe of inference

The corpus is the set of documents **published by the OEPM** in 2000–2025 with 2010 absent: 711,547 records, of which 72.0 % are translations of European patents validated in Spain, 14.8 % national patents and 13.3 % national utility models (corpus characterization §3).

Conclusions may be drawn about **combinations of IPC subclasses on documents published by the OEPM**. They may not be drawn about:

* Spanish applicants or Spain's technological capability (the corpus is not selected on applicant);
* world technology or world white spaces;
* unpublished filings, which for EP translations are a large and unobserved part of recent activity (mean publication lag 6.9 years);
* demand, markets, adoption or transfer.

## 4. Which white-space phenomena are in scope

| Phenomenon (brief) | In this ADR |
|---|---|
| Knowledge white space: areas or combinations scarcely represented in the analysed corpus | **In scope**, as the candidate definition of §5.4 |
| Innovation white space: combinations whose joint evolution deserves exploration | **In scope** only as a candidate *hypothesis generated for review*; Q evaluates predictability, not value |
| Transfer white space: knowledge exists but no application or adoption can be established | **Out of scope.** It requires a second source with its own annotation scheme and a methodological justification not made here |

No demand data, business needs, publications or projects are used.

## 5. Units and definitions

### 5.1 Observation

One publication (one XML document) with: identifier, kind code, publication date, application date, earliest priority date when a claim exists, applicants, inventors, title, IPC classification entries with version, and provenance (source file, SHA-256, position in the archive). The source adapter must keep the raw values; derived values (for example "filing year") are computed downstream and labelled as derived.

### 5.2 Technology unit

**Primary unit: the IPC subclass** (four characters, for example `B01D`). The corpus contains 660 distinct subclasses.

Justification, with its status:

* IPC is the only classification present in the dataset (99.6 % of records; CPC is a different OEPM dataset). *Measured.*
* At subclass level the number of possible pairs is 217,470 (660 choose 2) and 48.7 % of records carry two or more distinct subclasses, which gives thousands of first co-classifications per origin (corpus characterization §7). *Measured.*
* A finer unit (main group) would multiply the unit count and thin the counts per pair; a coarser one (the 35 WIPO technology fields of the frozen concordance) would merge areas that matter. These expectations are **not measured** here; both units are sensitivity analyses (§8.6) rather than assumptions.
* Whether subclass assignments are stable across IPC revisions is **not verified** (P5).

A pair is **co-classified** on a document when both subclasses appear among its IPC entries. A document counts at most once per pair. Which IPC entries count (all entries, or only those flagged as inventive) is undecided (P5).

### 5.3 What is evidence and what is inference

| Evidence (observed in a source, with provenance) | Inference (produced by an algorithm or by us) |
|---|---|
| A document was published on a date with given IPC entries | A subclass is "active" |
| A pair of subclasses is, or is not, co-classified on documents published up to *t* | A pair is "unexplored" or "under-represented" |
| A pair is first co-classified in a given year | A score, rank or candidate status |
| Counts of documents per subclass and year | An expected count under a null model |
| | Any statement that a candidate "deserves investigation" |

A candidate's record must keep the two apart.

### 5.4 Candidates

All definitions refer to an origin year *t* and use only documents published in or before *t*.

* A subclass is **active at *t*** if it appears on at least *m*_min distinct documents published up to *t*.
* **Type A candidate (never observed).** A pair of active subclasses, not co-classified on any document published up to *t*.
* **Type B candidate (surprising absence).** A pair of active subclasses whose expected number of co-classifications up to *t* under the null model of §5.5 is at least *e*_min and whose observed number is zero (or, in a variant, at most *n*_max).

Type A alone is not a white-space definition: the great majority of type A pairs involve subclasses that are too rare for zero to be informative. Type B states why an absence is notable. Neither type is a similarity or a "few matches" criterion.

A type A or type B pair becomes a **research candidate** only if all of the following hold, each checkable from the record:

1. it satisfies the type A or type B definition at *t*, with the parameters of its configuration;
2. its evidence section lists the documents (identifiers and dates) that make each subclass active and the counts used by the null model;
3. it carries the baseline score and the method's score with the method and configuration versions;
4. it carries the uncertainty statement of §8.5 and the limitations of §9;
5. it is generated from a configuration and a corpus identified by hash, so that it can be reproduced.

The research-candidate status says that a pair is worth an expert's attention. It is not a probability of success, of realization, or of commercial value, and no such interpretation may be displayed.

*m*_min and *e*_min are parameters, not constants of the method. Their values may be chosen only on development origins (§6.3) from a grid declared in advance (P2).

### 5.5 Null model — required properties

The null model supplies the expected co-classification count of a pair. The choice among implementations is pending (P1). Whatever is chosen must:

* preserve for each subclass its number of documents, and for each document its number of subclasses (a degree-preserving randomisation of the document × subclass incidence);
* randomise within publication-year strata, so that corpus growth and changing document mix do not create expected counts that never existed;
* use only years observed (2010 enters no rate; §6.4);
* be applied identically to every origin;
* be used to **rank**, not to claim significance: with about 146,000 candidate pairs per origin, no p-value is reported as evidence of a "real" gap.

## 6. Temporal design

### 6.1 The two axes

| | Publication date | Priority date (application date when no claim) |
|---|---|---|
| Present | 100 % of records | Priority claim in 66.1 %; application date in 100 % |
| Meaning | When the document became public in Spain | Proxy for when the invention was first filed |
| Information available at *t* | By construction: documents published up to *t* | Not by construction: documents filed up to *t* are published later; the information set at *t* must still be defined by publication |
| Lag | EP translations: mean 6.9 years from filing; national: 1.2 | Filing-year cohorts of EP translations are right-truncated: estimated 93 % complete for 2013, 78 % for 2016, 49 % for 2019, 8 % for 2022 |
| Date resolution | 24 dates per year until 2008 | Application dates are daily |
| Effect of the 2010 gap | Directly absent | Spread over filing years 2003–2010 of documents that would have been published in 2010 |

The missing priority claims (33.9 %) are concentrated in national first filings (87 % of national patents, 96 % of utility models, 12 % of EP translations), which is consistent with application date = priority date for first filings. This is a hypothesis, not a verified fact.

### 6.2 What the publication axis measures

On the full corpus, **84–90 % of the type A candidates that become positive on the publication axis were already filed by *t***: their documents carry an application or priority year at or before the origin and became public afterwards. This is 84 % at *t* = 2013, 89 % in 2016, 90 % in 2019 and 89 % in 2022. In 75–85 % of positives every contributing document is an EP translation. On national documents alone the corresponding share is 29–38 %, and the lag is short (median one year, 90th percentile three).

Consequently an FCP event on the publication axis is mostly the *disclosure in Spain* of combinations already filed, not the emergence of a combination after *t*. This does not make the experiment meaningless, since predicting what will become public is a legitimate task. It makes any wording such as "emerging combination" unjustified for the primary analysis. These figures are exploratory (corpus characterization §7).

### 6.3 Decision: primary axis, sensitivity, and no silent mixing

* **Primary analysis:** the publication axis, for both the information set (documents published up to *t*) and the outcome (first co-classification in a document published in *t*+1…*t*+*h*). It can be reproduced from the files alone and has no truncation inside 2000–2025. The construct is named FCP, never "emergence".
* **Sensitivity S1, filing-year outcome:** the information set stays defined by publication up to *t*; the outcome is dated by the earliest priority-or-application year of the documents carrying the pair. It is evaluable only on cohorts judged at least 90 % complete: filing years up to 2013 for EP translations (on the full corpus this is in practice the development origins 2003 and 2006) and up to 2022 for national documents (origins up to 2019: 2013, 2016, 2019).
* **Mandatory diagnostic D1:** for every analysis, the share of positives whose earliest filing year is at most *t*.
* A result is always reported with its axis. An analysis never uses one axis for the information set and a different axis for the outcome without saying so, and a table never mixes results from the two axes.

### 6.4 Origins, horizon and truncation

* Horizon *h* = 3 years (sensitivity: 2 and 5). An origin is admissible only if all of *t*+1…*t*+*h* are observed years inside 2000–2025: *t* ≤ 2022 for *h* = 3.
* No origin whose horizon contains 2010: origins 2007, 2008 and 2009 are excluded.
* **Development origins** (choosing among pre-declared options, estimating effect size): *t* = 2003 and 2006. Their history is short (four and seven years).
* **Confirmatory origins:** *t* = 2013, 2016, 2019, 2022. Horizons (2013,2016], (2016,2019], (2019,2022], (2022,2025] do not overlap, none contains 2010, and each has a three-year follow-up in full. The 2022 horizon contains the 2023 drop in EP translations (corpus characterization G2) and is therefore reported with and without that year.
* Origins 2010–2012, 2014–2015, 2017–2018, 2020–2021 may be reported as supplementary and descriptive, but not as confirmatory, because overlapping horizons are not independent.

### 6.5 The 2010 gap

No document in the corpus is dated 2010, and none before 2011-01-10 in 2011. The absence is a property of the source and must not be read as the absence of technological activity.

1. 2010 is **missing, not zero**. Series carry a missing value for 2010; no rate, trend, growth or persistence feature may treat it as zero or interpolate across it silently.
2. No origin has 2010 in its horizon (§6.4).
3. For origins from 2010 onward the *history* contains the gap, so some pairs that were in fact co-classified only in 2010 will appear unseen and may be reported as FCP when they next occur. For comparison years with ordinary volume this affects roughly 2–6 % of the positives (corpus characterization §7). This is stated as an expected order of magnitude, not a correction.
4. **Sensitivity S2:** repeat the confirmatory evaluation hiding in turn each of several ordinary years from the history (a leave-one-year-out check) and report how much the metrics move. A conclusion that depends on that movement is not accepted.
5. The OEPM will be asked about 2010. If the missing records are obtained, the experiment is rerun and compared; the first run is not replaced.
6. Activity thresholds and normalisations count observed years only.

### 6.6 Date resolution

Year is the only unit of time in this ADR. Finer analyses would not be comparable across the 24-date regime of 2000–2008 and daily dates from 2009–2011 on.

## 7. Hypotheses

Stated before any detector is run; each can fail.

* **H1 — signal beyond popularity.** On the confirmatory origins, at least one ranking from a pre-declared family (null-model residual of §5.5; common-neighbour and Adamic–Adar scores on the co-classification graph; a growth-trend score) has a higher AUC-PR than the popularity baseline *B1*.
* **H2 — surprising absence adds information.** Among candidates matched on popularity, type B candidates have a higher rate of FCP than type A candidates that are not type B.
* **H3 — robustness.** The direction of the H1 result does not reverse under the sensitivity set of §8.6.

No hypothesis claims that the ranking identifies opportunities. Popularity may already explain most of the signal; if so H1 is not supported, and that outcome is reported as the finding. **Unresolved** is an allowed outcome.

## 8. Evaluation protocol

### 8.1 Task

At each origin *t*: the candidate pool is the type A pairs of active subclasses; the positives are the pool pairs with FCP in *t*+1…*t*+*h*; a detector assigns each pool pair a score computed from documents published up to *t* only; the ranking is compared with the realised outcome.

### 8.2 Baselines (declared in advance)

| Id | Baseline | Definition |
|---|---|---|
| B0 | Random | uniform random order of the pool; expected AUC-PR equals the positive rate |
| B1 | Popularity | product of the two subclasses' document counts up to *t* (preferential attachment) |
| B2 | Persistence | the empirical FCP rate observed at origin *t*−*h* within the popularity-decile cell of the pair, applied to the pair; uses only outcomes completed by *t* |
| B3 | Trend | product of the recent growth rates of the two subclasses' yearly document counts over the last three observed years |
| B4 | Common neighbours / Adamic–Adar | classical link-prediction scores on the co-classification graph up to *t* |

B2 is undefined for the development origin 2003 (no earlier origin) and is then omitted, not imputed.

### 8.3 Metrics

* **Precision@K** and **recall@K**, with *K* fixed in advance at 100 (a review-sized list), 1,000 and 5,000, together with lift over the positive rate.
* **AUC-PR** (average precision) over the whole pool, which is the headline metric because positives are about 1–2 % of the pool.
* ROC-AUC may be reported as secondary and must not be used to decide H1.

### 8.4 Temporal validation

* Forward chaining: every score for origin *t* is computed from documents published up to *t*; nothing is refitted using a later year.
* Parameters are chosen on development origins only. Confirmatory origins are evaluated once per pre-registered configuration.
* Every feature function of the future implementation takes the origin year as an explicit argument and must reject later data; a test that fails when a later document influences a score is a requirement of the implementing pull request.
* The strongest baseline for H1 is picked on the development origins and then fixed.

### 8.5 Uncertainty

* The unit of resampling is the **subclass**: subclasses are drawn with replacement and all pairs among drawn subclasses are kept, because pairs sharing a subclass or a document are not independent. Differences from baselines are computed within each resample (paired). The number of resamples and the interval type are fixed in the pre-registration.
* The intervals are approximate and are reported as such. Confirmatory conclusions rely on the four non-overlapping origins; the number of origins is too small for a formal test across origins, so results are reported per origin.
* A candidate record states: the score and its baseline score, the counts behind the null model, and that the interval of the method's metric overlaps or not with the baseline's.

### 8.6 Sensitivity analyses

Unit (main group; WIPO technology fields), *m*_min grid (10, 20, 50), *e*_min grid, horizon (2, 3, 5), IPC entries used (P5), corpus restriction to national documents only, axis (S1), hidden-year check (S2), exclusion of 2023 from the 2022 horizon, deduplication rule (P4). Conclusions are stated only where they survive.

### 8.7 Human review

A sample of top-ranked candidates, drawn after the metrics are fixed, will be reviewed by domain experts who do not see the method, the rank or the score. The review judges plausibility and interest, not truth; it cannot validate the ranking. The sampling rule, the number of reviewers and the rating scale are to be fixed in the pre-registration (P3).

### 8.8 Reporting of errors and biases

The report documents: false positives (high-ranked pairs without FCP; non-realisation within three years does not show that a pair is uninteresting or wrong); false negatives (positives never ranked high, broken down by document kind and subclass area); and coverage biases (EP translations, the 2010 gap, the 2023 dip, the 24-date regime of 2000–2008, the absence of families and of CPC).

### 8.9 Power

The counts in the corpus characterization show that thousands of FCP positives exist at every origin. That shows **descriptive feasibility**. It does not show that any detector achieves a difference from a baseline that the data can detect. The minimum difference in AUC-PR that the confirmatory design can detect will be estimated from the development origins and the resampling procedure, and stated before the confirmatory run.

## 9. Limitations that prevent reading a result as a demonstrated opportunity

* An FCP event is a publication event in one national office, 72 % of it translations of European patents. It is not an innovation, a market, or a gap in world technology.
* Most publication-axis positives were filed before the origin (§6.2).
* Two documents may describe the same invention (translation plus national filing); no family identifier exists.
* IPC subclass co-classification reflects examiners' and applicants' classification practice, which changes over time and differs between kinds of document.
* A pair never co-classified may be so because it is impossible or uninteresting.
* A pair that later appears may do so by chance, by a classification-practice change, or for reasons unrelated to the signal.
* Success on Q would show predictability of a publication event. It would not show that Nexus caused or anticipated innovation, and the later appearance of a pair does not by itself show that Nexus discovered anything.
* The data are incomplete for 2010 and doubtful for the EP translations of 2023.

## 10. Decisions

### 10.1 Adopted by this ADR when it is approved

* **A1.** The question Q, the FCP event and the explicit non-claims of §2.
* **A2.** The universe of inference of §3.
* **A3.** The IPC subclass as primary unit; the document-level co-classification as the pair event.
* **A4.** The candidate structure of §5.4: type A and type B, conditions for a candidate for investigation, and no probability reading.
* **A5.** The publication axis as primary, S1 and D1 as mandatory companions, and no mixing of axes.
* **A6.** The treatment of the 2010 gap, the admissible origins, the development and confirmatory sets and the truncation rule.
* **A7.** The baselines, metrics, temporal validation and resampling unit of §8.
* **A8.** Hypotheses H1–H3, with "unresolved" as an allowed outcome.

### 10.2 Pending approval

| Id | Question | Why it is open |
|---|---|---|
| P1 | Which null-model implementation (randomisation by swaps, or an analytic approximation), and the form of the score | Needs a small comparison of cost and fidelity; constrained by §5.5 |
| P2 | The grids for *m*_min and *e*_min | The value 20 used in the descriptive counts has no scientific justification |
| P3 | The numeric success criterion for H1, the review protocol and the pre-registration format | Depends on the effect-size estimate of §8.9; proposed structure: a lower confidence bound above zero for the AUC-PR difference against the strongest baseline in at least three of the four confirmatory origins |
| P4 | Deduplication of repeated identifiers (3,562 repeats; 185 with different dates) and of translation plus national documents describing one invention | No family identifier in the source |
| P5 | Which IPC entries count (all, or inventive only) and whether the stored classification is the one assigned at publication (91.6 % of records carry version 2006.01) | Not verified; affects the unit's meaning |
| P6 | Treatment of the 2023 drop in EP translations (exclude, flag, or analyse on national documents) | Cause unknown |
| P7 | Consultation with the OEPM about the 2010 gap, the 2023 drop, the repeated identifiers, programmatic access, and the terms of the OpenData licence for derived products | Requires an external reply |
| P8 | Relation to the OEPM production-scale patent corpus contract proposed on the unmerged branches of pull requests #112 and #113 | Different purpose and acquisition route; whether to reconcile is a project decision. Numbers 0032–0035 are held by those branches |
| P9 | Whether to acquire the OEPM CPC dataset as a robustness check | Adds a second classification but not a second source of documents |
| P10 | Whether the primary analysis should instead be the national-document corpus on the filing axis | It removes the disclosure-delay confound (§6.2) at the cost of fewer positives (about 1,200 per origin against 2,100–3,200 on the confirmatory origins), and changes the universe of inference to national filings. The publication axis on the full corpus is adopted here because the brief for this work asks for the more complete coverage; the choice is flagged for explicit confirmation |

## 11. Consequences

* This ADR changes no code, test, dependency or contract; the landscape modules and the MVP are untouched, and no component is retired.
* It commits Nexus to a first experiment whose possible outcomes include "no better than popularity".
* It makes the following work depend on approval of this ADR: a source adapter for the bibliographic files that must reproduce every number of the corpus characterization from the files identified by hash; a data and domain contract for observations and candidates; a pre-registration; and the baselines.
* It names what a candidate record must contain, so that a later interface cannot present a bare score.
