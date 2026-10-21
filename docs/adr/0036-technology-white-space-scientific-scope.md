# ADR 0036: Technology White-Space Discovery — Scientific Scope and Operational Definition

**Status:** Accepted
**Date:** 2026-10-20
**Acceptance:** takes effect when the pull request that sets this status is merged. It accepts a research contract (what will be done and reported) under the conditions of §12.2. It does not validate the hypotheses of §7, which are what the experiment may refute.
**Scope:** Fixes the scientific question, the universe of inference, the operational definition of a white-space candidate, the temporal design and the evaluation protocol for the first white-space experiment on the OEPM bibliographic corpus, and lists what is accepted, what stays open and under which conditions. **This ADR is documentary: it changes no code, dependency, contract or test.** The source adapter that followed it is pull request #130. Nothing in this ADR claims that a detector works; no detector exists yet.

Companion documents: [Audit of `main`](../whitespace/architecture-audit.md) · [OEPM corpus characterization](../whitespace/oepm-biblio-corpus-characterization.md)

---

## 1. Context

Nexus was built to match technology demands to patents. The matching question rests on an assumption that linguistic similarity between a demand and a patent indicates that the patent can solve the need, and a demand and a patent are not classified on a common scheme. The pivot replaces the central question: instead of *which available technology fits this demand*, the question becomes *which technology areas show signals of under-explored combinations that deserve investigation*. Matching is not abandoned; it is demoted from conclusion to a possible auxiliary validation tool.

The audit of `main` ([architecture-audit.md](../whitespace/architecture-audit.md)) found reusable ingestion, storage and provenance machinery, and one existing white-space score (`application/landscape/metrics.py`) that rests on unvalidated weights, depends on a demand signal and labels clusters as opportunities. It is left untouched by this ADR.

The first experiment uses a corpus that can be obtained at no cost: the OEPM OpenData bibliographic files for 2000–2025 ([corpus characterization](../whitespace/oepm-biblio-corpus-characterization.md)). This ADR takes that corpus's properties, including its gaps, as constraints on the design.

Guiding principle: Nexus must discover and justify potential opportunities, not manufacture convincing coincidences. An observable gap in data is not an opportunity, and the absence of documents does not show that nobody is working on something.

## 2. Scientific question

> **Q.** Using only documents published by the OEPM up to year *t*, can pairs of IPC subclasses that have never been classified together on a single document of the observed corpus up to *t* be ranked so that those that are classified together for the first time in publications of years *t*+1…*t*+*h* are found more often than by simple rules?

**"Never" always means "never within the observed corpus"**: publications from 2000 up to *t*, with 2010 missing. The corpus does not allow saying that a pair never co-occurred before 2000, during 2010, in a document not published by the OEPM, or in an unpublished filing.

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

One **source record** (one XML document in an archive) with: identifier, kind code, publication date, application date, **every** priority date the source states (the earliest is derived downstream), applicants, inventors, title, IPC classification entries with version, level and value, the anomalies found in optional fields (with their raw value), and provenance (source file, SHA-256, position in the archive). The source adapter keeps the raw values; derived values (for example "filing year") are computed downstream and labelled as derived. This is the contract implemented in `domain/models/whitespace.py`.

### 5.1.1 Source record, publication identifier, document and analytical unit

Three things are called "document" or "publication" in the first version of this ADR and in the exploratory counts. They are not the same, and every count in the experiment must say which one it uses.

* **Source record.** One XML as it appears in the archives, with its provenance. The adapter keeps every one.
* **Publication identifier.** Country, number and kind code (`doc_id`); with the publication date it forms the **publication key**. An identifier does not identify content: some keys occur in more than one source record (3,371 extra records), and in 19 of those keys the copies state different IPC subclasses. Some identifiers also appear with more than one publication date (185).
* **Document.** A publication identifier, counted once, at its earliest publication date. This is what "distinct documents" means in the activity condition of §5.4. It is the literal reading of the term and the one under which the printed counts of the characterization are reproduced; whether an alternative (counting the publication key) would change anything at the thresholds of P2 has **not** been measured.

The analytical unit depends on the operation:

| Operation | Unit | Rule for repeated or differing copies |
|---|---|---|
| Activity of a subclass (§5.4) | Document (publication identifier) | Counted once, at its earliest publication date, with the **union** of the subclasses stated by the source records of that date (decision O4) |
| Co-classification of a pair, seen and outcome | Source record | A pair is co-classified if **one** source record states both subclasses; subclasses stated by different copies are never combined into a pair. Each pair counts once per document in rates (decision O4) |
| Publication lag and filing-year statistics | Source record | Repeats kept; a sensitivity on distinct publication keys is reported (decision O4) |

**Decision O4 (copy policy and unit of activity).** The unit of the activity count is the **publication identifier**, not the publication key: a publication is counted once however many times it is republished or repeated in the archives. When source records of that identifier at its earliest date differ, the document contributes the **union** of their subclasses. Reasons, which do not depend on any result: (a) the same publication is never counted twice; (b) no copy is chosen arbitrarily; (c) activity only decides whether a subclass passes a threshold, so a union that states a classification no single copy states cannot create a pair. Pairs are the opposite case and the rule is the opposite: a pair requires one source record that states both subclasses, and copies are never combined into a pair, because that would invent a co-classification. The alternative of keeping each copy as a separate observation is rejected because it counts one publication several times.

*Known consequence.* The degree-preserving null model of §5.5 (P1, still open) works on a document × subclass incidence; the incidence of a document is its union, whereas its pairs come from single records. For the 19 documents whose copies differ this is not exactly consistent. P1 must state explicitly how the incidence is built; its effect is not assumed to be negligible, and the pre-registration includes the alternative construction (incidence from single records) as a sensitivity. The 19 documents are a small share of the 708,176 publication keys, but that is a description of size, not a measured effect.

*Evidence used, and its limits.* Pull request #132 (merged) measured, on the 26 files, two things. (1) Activity: the sets of active subclasses at origins 2006–2022 (full corpus) and the four national origins are identical whether the first copy, the last copy or the union contributes. (2) Pairs: its first run kept only the first record of each publication key when forming pairs, and that single change produced one more candidate pair and one more positive at origin 2013 (also in the national subcorpus) and no difference elsewhere. The decision above rests on the reasons given, not on these results; they cover the counts and origins named and say nothing about other statistics, so the sensitivity by copy policy stays part of the protocol (§8.6).

*Implementation.* The reproduction (#132) used the first copy for activity because that reproduces the printed figures. Changing its default to the union is a code change with a regression test, made in its own pull request; it is not part of this one.

### 5.2 Technology unit

**Primary unit: the IPC subclass** (four characters, for example `B01D`). The corpus contains 660 distinct subclasses.

Justification, with its status:

* IPC is the only classification present in the dataset (99.6 % of records; CPC is a different OEPM dataset). *Measured.*
* At subclass level the number of possible pairs is 217,470 (660 choose 2) and 48.7 % of records carry two or more distinct subclasses, which gives thousands of first co-classifications per origin (corpus characterization §7). *Measured.*
* A finer unit (main group) would multiply the unit count and thin the counts per pair; a coarser one (the 35 WIPO technology fields of the frozen concordance) would merge areas that matter. These expectations are **not measured** here; both units are sensitivity analyses (§8.6) rather than assumptions.
* Whether subclass assignments are stable across IPC revisions is **not verified** (P5).

A pair is **co-classified** on a document when both subclasses appear among its IPC entries. A document counts at most once per pair. All IPC entries count in the primary analysis; counting only the entries flagged as inventive is a sensitivity (P5).

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

* A subclass is **active at *t*** if it appears on at least *m*_min distinct documents (§5.1.1) first published up to *t*.
* **Type A candidate (never observed in the corpus).** A pair of active subclasses not co-classified on any document of the observed corpus published up to *t*.
* **Type B candidate (surprising absence).** A type A pair whose expected number of co-classifications up to *t* under the null model of §5.5 is at least *e*_min. Type B is therefore a **subset of type A** (it can coincide with it if every type A pair meets the *e*_min condition): the observed number is exactly zero.

A variant admitting up to *n*_max observed co-classifications is **not part of this design**. Such pairs are not type A, are not eligible for FCP, and would need their own pool, their own event definition and their own denominator; if studied, it will be introduced by a later ADR.

Type A alone is not a white-space definition: the great majority of type A pairs involve subclasses that are too rare for zero to be informative. Type B states why an absence is notable. Neither type is a similarity or a "few matches" criterion, and "absent" always refers to the observed corpus (§2).

A type A or type B pair becomes a **research candidate** only if all of the following hold, each checkable from the record:

1. it satisfies the type A or type B definition at *t*, with the parameters of its configuration;
2. its evidence section lists the documents (identifiers and dates) that make each subclass active and the counts used by the null model;
3. it carries the baseline score and the method's score with the method and configuration versions;
4. it carries the uncertainty statement of §8.5 and the limitations of §9;
5. it is generated from a configuration and a corpus identified by hash, so that it can be reproduced.

The research-candidate status says that a pair is worth an expert's attention. It is not a probability of success, of realization, or of commercial value, and no such interpretation may be displayed.

*m*_min and *e*_min are parameters, not constants of the method. Their values may be chosen only on development origins (§6.4) from a grid declared in advance (P2).

### 5.5 Null model — required properties

The null model supplies the expected co-classification count of a pair. The choice among implementations is resolved in outline in §10.2 (P1). Whatever is chosen must:

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

* **H1 — signal beyond the strongest simple rule (primary).** Let *F* be the family of detector scores built on the null model of §5.5 (the residual alone, or the residual combined with a relatedness term on the co-classification graph; the exact members are fixed by the method decision, P1). One score from *F* and the strongest baseline among B0–B4 are each selected on the development origins and then frozen. On the confirmatory origins, the frozen score has a higher AUC-PR than the frozen baseline.
* **H1b — signal beyond popularity (secondary, always reported).** The same frozen score against the popularity baseline *B1*, whether or not *B1* was the strongest on the development origins.
* **H2 — surprising absence adds information.** Within the evaluation pool (the type A pairs), type B pairs have a higher FCP rate than the remaining type A pairs matched on popularity.
* **H3 — robustness.** The direction of the H1 result does not reverse under the sensitivity set of §8.6.

**Decision O2 (multiplicity).** H1 is the only primary hypothesis. H1b and H2 are secondary. H3 is a description of robustness and is not a test. Per confirmatory origin, each hypothesis is judged with the single inference procedure of §8.5 (percentile bootstrap over subclass resamples; the p-value is the share of resamples in which the difference is not above zero). H1 passes at an origin when p < 0.025, which is by construction the same event as the lower bound of the 95 % interval of P3 being above zero. H1b and H2 are adjusted together by Holm's procedure with a family level of 0.025 (the smaller p-value is compared with 0.0125 and, if it passes, the larger with 0.025); they are judged by these p-values, and any interval reported for them is the unadjusted 95 % interval and is labelled as such. A hypothesis is supported only if it passes at three of the four confirmatory origins, as in P3. The family, the levels and the procedure are fixed here, before any result; the number of resamples stays in the pre-registration. This is a descriptive rule across four origins, not a formal test across origins (§8.5).

No hypothesis claims that the ranking identifies opportunities. Popularity may already explain most of the signal; if so H1 and H1b are not supported, and that outcome is reported as the finding. **Unresolved** is an allowed outcome.

## 8. Evaluation protocol

### 8.1 Task

At each origin *t*: the **evaluation pool** is the set of type A pairs of active subclasses; type B pairs are a subset of that pool and are not a separate pool. The positives are the pool pairs with FCP in *t*+1…*t*+*h*. A detector assigns each pool pair a score computed from documents published up to *t* only, and the ranking is compared with the realised outcome. H2 compares type B pairs with the remaining pool pairs inside the same pool.

### 8.2 Baselines (declared in advance)

| Id | Baseline | Definition |
|---|---|---|
| B0 | Random | uniform random order of the pool; expected AUC-PR equals the positive rate |
| B1 | Popularity | product of the two subclasses' document counts up to *t* (preferential attachment) |
| B2 | Persistence | the empirical FCP rate observed at origin *t*−*h* within the popularity-decile cell of the pair, applied to the pair; uses only outcomes completed by *t* |
| B3 | Trend | product of the recent growth rates of the two subclasses' yearly document counts over the last three observed years |
| B4 | Common neighbours / Adamic–Adar | classical link-prediction scores on the co-classification graph up to *t* |

B2 is undefined for the development origin 2003 (no earlier origin) and is then omitted, not imputed.

**Decision O1.** B2 at the confirmatory origin 2013 would use the outcomes of origin 2010, whose history lacks the year 2010; B2 is therefore **omitted at 2013** and not imputed. At that origin the frozen baseline is the strongest among B0, B1, B3 and B4 on the development origins, chosen by the same rule and recorded in the pre-registration before the confirmatory run. If B2 is the frozen baseline at the other origins, the comparison at 2013 is with a different baseline; this is reported with the result, and the criterion of P3 still counts four origins. The reason is that the history of origin 2010 lacks a year and nothing establishes how to correct for it.

### 8.3 Metrics

* **Precision@K** and **recall@K**, with *K* fixed in advance at 100 (a review-sized list), 1,000 and 5,000, together with lift over the positive rate.
* **AUC-PR** (average precision) over the whole pool, which is the headline metric because positives are about 1–2 % of the pool.
* ROC-AUC may be reported as secondary and must not be used to decide H1.

### 8.4 Temporal validation

* Forward chaining: every score for origin *t* is computed from documents published up to *t*; nothing is refitted using a later year.
* Parameters are chosen on development origins only. Confirmatory origins are evaluated once per pre-registered configuration.
* Every feature function of the future implementation takes the origin year as an explicit argument and must reject later data; a test that fails when a later document influences a score is a requirement of the implementing pull request.
* **Selection of the strongest baseline** (H1, and the baseline at 2013 in the decision O1). The criterion is the AUC-PR on the development origins. Among B0–B4 it is computed on the one development origin at which all five are defined (2006), because B2 is undefined at 2003; at the confirmatory origin 2013, where B2 is omitted, the choice among B0, B1, B3 and B4 uses the mean of 2003 and 2006. A tie is resolved in favour of the lower baseline number. The choice is written into the pre-registration and fixed before any confirmatory origin is evaluated. Ranking five baselines on a single development origin is noisy; that limit is stated with the result.

### 8.5 Uncertainty

* **Single inference procedure.** Intervals and p-values come from the same *B* subclass resamples, with *B* a multiple of 40 so that 2.5 % of *B* is an integer. The interval is the percentile interval (2.5th and 97.5th percentiles by the nearest-rank rule) of the paired difference; the one-sided p-value is *k*/*B*, with *k* the number of resamples whose difference is not above zero. The lower bound is above zero exactly when *k*/*B* < 0.025, so the criterion of P3 and the test of H1 are the same event. The procedure is approximate: it makes no claim of exact coverage, and the confidence level has this operational meaning only.
* The unit of resampling is the **subclass**: subclasses are drawn with replacement and all pairs among drawn subclasses are kept, because pairs sharing a subclass or a document are not independent. Differences from baselines are computed within each resample (paired). The number of resamples (a multiple of 40) is fixed in the pre-registration; the interval type is the percentile interval defined next.
* The intervals are approximate and are reported as such. Confirmatory conclusions rely on the four non-overlapping origins; the number of origins is too small for a formal test across origins, so results are reported per origin.
* A candidate record states: the score and its baseline score, the counts behind the null model, and that the interval of the method's metric overlaps or not with the baseline's.

### 8.6 Sensitivity analyses

Unit (main group; WIPO technology fields), *m*_min grid (10, 20, 50), *e*_min grid, horizon (2, 3, 5), IPC entries used (all entries is primary; inventive entries only is a sensitivity, P5), document kind (EP translations only; national documents only), axis (S1), hidden-year check (S2), exclusion of 2023 from the 2022 horizon, copy policy and identifier-or-key unit (P4, O4). Conclusions are stated only where they survive.

### 8.7 Human review

A sample of top-ranked candidates, drawn after the metrics are fixed, will be reviewed by domain experts who do not see the method, the rank or the score. The review judges plausibility and interest, not truth; it cannot validate the ranking. The sampling rule, the number of reviewers and the rating scale are to be fixed in the pre-registration (P3).

### 8.8 Reporting of errors and biases

The report documents: false positives (high-ranked pairs without FCP; non-realisation within three years does not show that a pair is uninteresting or wrong); false negatives (positives never ranked high, broken down by document kind and subclass area); and coverage biases (EP translations, the 2010 gap, the 2023 dip, the 24-date regime of 2000–2008, the absence of families and of CPC).

### 8.9 Power

The counts in the corpus characterization show that thousands of FCP positives exist at every origin. That shows **descriptive feasibility**. It does not show that any detector achieves a difference from a baseline that the data can detect. The minimum difference in AUC-PR that the confirmatory design can detect will be estimated from the development origins and the resampling procedure, and stated before the confirmatory run. It depends on the smallest difference regarded as practically useful, which is a decision of value for the users of the ranking and not a statistical one (O2).

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

Two vocabularies are used in the tables of this section.

* **Evidence status.** *Reproduced*: recomputed from the 26 source files by the repository's adapter (pull request #130; 231 figures, reproduced after the errata of the characterization, which shows consistency and not independent validation). *Reproduced (#132)*: the same, for characterization §4.2 and §7, by pull request #132 (every printed figure reproduced after one documented correction; the printed numbers guided the choice between two readings of an ambiguous definition, so this is consistency and not independent validation); pull request #132 is merged. *Exploratory*: computed by a throw-away parser and not reproduced from the repository. *Design*: a choice, not a measurement. *Reasoned*: argued, not measured.
* **State.** *Accepted*. *Accepted, parameters open*: the structure is decided and named values are to be fixed in the pre-registration. *Open, action pending*. *Open, dependency*. *Deferred*.

### 10.1 Decisions adopted by this ADR

| Id | Decision | Evidence and its status | State |
|---|---|---|---|
| A1 | The question Q, the FCP event and the explicit non-claims of §2 | Design | Accepted |
| A2 | The universe of inference of §3 | 711,547 records; 72.0 % EP translations, 14.8 % national patents, 13.3 % utility models. *Reproduced* | Accepted |
| A3 | The IPC subclass as primary unit; document-level co-classification as the pair event | 99.6 % of records carry IPC, 660 subclasses, 48.7 % of records have two or more distinct subclasses. *Reproduced*. Thousands of FCP positives per origin (1.4–2.2 % of candidate pairs). *Reproduced (#132)* | Accepted |
| A4 | The candidate structure of §5.4: type A, type B, the conditions of a research candidate, no probability reading | Design | Accepted |
| A5 | The publication axis as primary, S1 and D1 as mandatory companions, no mixing of axes | The 84–90 % of publication-axis positives already filed at the origin, and the mean lag of 6.9 years. *Reproduced (#132)*; the 84–90 % is the permissive reading (at least one contributing publication filed by the origin), the strict reading (all of them) gives 82–88 %. The decision (publication axis, the FCP name, the diagnostics) does not depend on the exact figures; the wording of §6.2 does | Accepted |
| A6 | The treatment of the 2010 gap, the admissible origins, the development and confirmatory sets, the truncation rule | No record dated 2010, 381 records of 2011-01-10…13 in the file named 2010, the 2023 drop of EP translations, the 24-date regime of 2000–2008. *Reproduced*. The 2–6 % effect of the gap on positives (1.7–6.1 %, a counterfactual for a year of ordinary volume, not a measurement of 2010). *Reproduced (#132)* | Accepted |
| A7 | The baselines, metrics, temporal validation and resampling unit of §8 | Design. O1 is decided in §8.2; the smallest useful AUC-PR difference and the power remain open (O2) | Accepted, parameters open |
| A8 | Hypotheses H1–H3, with "unresolved" as an allowed outcome | Design | Accepted |

### 10.2 The ten questions of the first version, with their resolutions

A resolution fixes a protocol so that the experiment can refute the hypotheses; it does not turn a hypothesis into a fact.

| Id | Question | Resolution | Evidence and its status | State and consequence |
|---|---|---|---|---|
| P1 | Null model | Reference: degree-preserving bipartite randomisation of the document × subclass incidence, stratified by publication year. The cost and fidelity of an analytic approximation are compared before it is discarded. The result is a ranking score and is never read as a significance test | Design | **Accepted, parameters open.** The form of the score and of the relatedness term (the members of *F*, H1) is fixed before any null-model code is written |
| P2 | Thresholds | *m*_min ∈ {10, 20, 50}. A grid for *e*_min is declared before use. Values are chosen on development origins only and the configuration is frozen before the confirmatory origins are evaluated | The value 20 used in the descriptive counts has no scientific justification (stated in the characterization) | **Accepted, parameters open.** The grid values for *e*_min |
| P3 | Numeric success criterion | Primary: the lower bound of the paired 95 % percentile interval of the AUC-PR difference (§8.5) against the frozen strongest baseline is above zero in at least three of the four confirmatory origins. The absolute size of the improvement is reported as well: statistical significance is not practical usefulness | Design. The criterion is a descriptive rule across four origins, not a formal test (§8.5) | **Accepted, parameters open.** Number of resamples (a multiple of 40), human-review protocol, the smallest difference regarded as useful (O2); the treatment of H1, H1b and H2 together is decided in §7 |
| P4 | Repeated identifiers | Records sharing an identifier and a publication date are **not** necessarily identical, so they are not "exact repeats" and are not removed by this ADR. The units of §5.1.1 apply; the adapter keeps every record. The 185 identifiers with more than one publication date stay distinct publications for pairs and lag; a document counts once for activity. National documents and EP translations are not merged without a family identifier. Sensitivity by document kind and by copy policy (§8.6) | 3,371 repeated keys, 19 of them with differing subclasses; 185 identifiers with several publication dates. *Reproduced*. Insensitivity of the active sets to the copy policy at the origins measured: pull request #132 (merged) | **Accepted.** Replaces the first wording, which assumed that repeats were exact; the rule per operation is in §5.1.1 |
| P5 | IPC entries | All entries are the primary analysis, for continuity with the exploratory counts. Inventive entries only is a sensitivity. The uncertainty about historical IPC revisions stays stated | The first entry of a record carries 45 distinct raw version values (*Reproduced*); 91.6 % carry `2006.01` (published in the characterization, not among the 231 reproduced figures, so *Exploratory*). Whether stored classifications are those assigned at publication. *Not verified* | **Accepted.** The question of the classification date stays an explicit limitation |
| P6 | 2023 drop in EP translations | Observed records are kept and nothing is imputed. The 2022 horizon is reported with and without 2023, and the limitation appears in both results | 14,846 EP translations in 2023 against 24,965 (2022) and 27,712 (2024), national kinds stable. *Reproduced*. Cause unknown | **Accepted.** Depends on the reply to P7 only for the explanation |
| P7 | Consultation with the OEPM | To be done: the 2010 gap, the 2023 drop, the repeated identifiers, programmatic access and the reuse conditions. A favourable reply does not resolve the other limitations | The message is drafted and reviewed and **has not been sent** | **Open, action pending.** Does not block the next steps; 2010 stays missing until answered |
| P8 | Relation to the corpus contract on #112 and #113 | The retrieval corpus of the existing product and the bibliographic corpus of this experiment stay separate. Their acquisition contracts are reconciled before any shared infrastructure is introduced | Both pull requests are still open; numbers 0032–0035 are held by their branches | **Open, dependency.** Reconciliation precedes any shared infrastructure |
| P9 | CPC | Deferred. The IPC experiment is reproduced and evaluated first; CPC is considered afterwards if it would add a useful sensitivity that justifies its cost and access conditions | Not acquired | **Deferred** |
| P10 | Primary time axis | The publication axis on the full corpus, with the event always called FCP and never technological emergence. The filing-year diagnostic D1 and the sensitivity on national documents with a filing-year outcome are mandatory, and the latter is reported as answering a different universe of inference | The delay diagnostic and the national-documents counts. *Reproduced (#132)* | **Accepted, subject to C1.** The alternative primary analysis on national documents remains documented and available |

## 11. Consequences

* This ADR changes no code, test, dependency or contract; the landscape modules and the MVP are untouched, and no component is retired.
* It commits Nexus to a first experiment whose possible outcomes include "no better than the strongest simple rule" and "unresolved".
* It names what a candidate record must contain, so that a later interface cannot present a bare score.
* Approval of this ADR as a research contract is separate from approval of the methodological hypotheses of §7: the first fixes what will be done and reported, the second is what the experiment may refute.

### 11.1 Conditions on the source adapter that follows

The exploratory figures were produced by a parser that is not in the repository (corpus characterization §9), and no one has yet reproduced them independently. The adapter must close that gap. It must:

* verify the SHA-256 of the 26 files before reading them;
* keep the original values and the provenance of every record;
* group by the publication date of the record, never by the name or year of the file;
* document and test the handling of invalid XML, repeated identifiers and IPC entries;
* reproduce the tables and percentages published in the corpus characterization, and show any discrepancy instead of adjusting it;
* keep the original data out of git, as the access and distribution conditions require.

The adapter does not implement a detector and does not retire any component.

### 11.2 Status of those conditions after pull request #130

| Condition | Evidence | Status |
|---|---|---|
| Verify the SHA-256 of the 26 files before reading them | `OepmBiblioSource.read` calls `verify` first; a test checks that a wrong hash or a missing file aborts before any record is yielded | Met |
| Keep the original values and the provenance of every record | `SourceRecordProvenance` (file, hash, archive path); `SourceAnomaly` keeps raw values of unreadable optional fields | Met, with limits: 17 records contain bytes that are not valid UTF-8, replaced and flagged; 86 records are rejected, not recovered |
| Group by publication date, never by file name | A test with a file named 2010 that holds 2011 records; the figures are computed by publication date | Met |
| Document and test invalid XML, repeated identifiers and IPC entries | `test_oepm_biblio.py`; the rejected records are counted by reason (reproduction report §4) | Met. The 86 records with undefined entities remain a limitation of the source: the DTD that would define them is not distributed with the data |
| Reproduce the published tables and show any discrepancy | 231 figures of sections 3–6 and 8, reproduced after the errata of the characterization | **Met for sections 3–6 and 8.** For §4.2 and §7: met in the operational sense by pull request #132 (see C1), effective since it was merged |
| Keep the original data out of git | No OEPM file is tracked. The ignore rule for `data/raw/oepm_open/` is not part of that pull request nor of this one; it is a local change pending its own review | Met in the repository; protection against accidental addition not yet committed |

The expression that removes the `DOCTYPE` stops at the first `>`; it is not a general sanitiser of XML declarations. The tests show that specific hostile inputs are rejected without expansion or network access, not that the parser is safe against any hostile XML.

## 12. Acceptance

### 12.1 What is accepted

The decisions marked *Accepted* or *Accepted, parameters open* in §10, as the research contract for the first white-space experiment on the OEPM bibliographic corpus. Nothing in this ADR activates a detector, a threshold value, a null-model implementation or a confirmatory evaluation.

### 12.2 Conditions of the acceptance

* **C1.** The figures of the characterization §4.2 and §7, and the numbers of this ADR that come from them (§6.2, §6.5, the mean lag, the cohort completeness, the counts of positives), are reproduced from the repository, with explicit definitions, tests and visible discrepancies, before the pre-registration, which cannot be closed while C1 is unmet. If they differ materially, the decisions that cite them (the second claim of A3, A5, the estimate of A6, P10) are reopened.
  *Status: satisfied in this operational and documentary sense by pull request #132, effective since it was merged.* Every printed figure is recomputed from the adapter, the definitions and the one discrepancy found are documented, and the sensitivity claimed is in the reproducible flow. None differs materially, so no decision is reopened; the strict reading of §7.1 (82–88 %) is recorded beside the printed 84–90 %. This is **not** independent validation of the characterization, and it does **not** close O1–O4.
* **C2.** No detector, threshold value, null-model code or confirmatory evaluation exists before a pre-registration closes the open parameters of A7 and P1–P3 and the open items of §12.3.
* **C3.** The limitations stay explicit in every result: the 86 records with undefined entities, the 17 records with bytes that are not valid UTF-8, the 3 records with an unreadable priority date, the 2010 gap, the 2023 drop of EP translations, and the absence of families and of CPC. The reproduced figures show consistency with a corrected characterization, not independent validation of every parsing decision.
* **C4.** The acceptance covers the research contract. The hypotheses of §7 are not validated by it.

### 12.3 Open items for the pre-registration

* **O1.** *Decided* (§8.2): B2 is omitted at the confirmatory origin 2013 and the comparison there is with the strongest of B0, B1, B3 and B4 on the development origins.
* **O2.** *Multiplicity decided* (§7). *Open*: the smallest AUC-PR difference regarded as practically useful (a decision of value, to be taken by the users of the ranking), and the power analysis that depends on it and on the dispersion across subclasses observed on the development origins.
* **O3.** Whether the 86 records with undefined entities can be recovered, which requires the official DTD (reproduction report §4.1). Until then they remain rejected.
* **O4.** *Decided* (§5.1.1): the unit of activity is the publication identifier, with the union of the subclasses of its earliest date; pairs come from single source records. The code default (`copy_policy`) is changed in its own pull request.

### 12.4 Accepting, meeting the conditions, being ready to run

These are three different states, and this ADR reaches only the first.

| State | Meaning | Reached |
|---|---|---|
| Framework accepted | The questions, definitions and protocol of §§2–9 are the contract | Yes, when this status is merged |
| Conditions met | C1 satisfied (operationally; #132 is merged); O2 (smallest useful difference, power), O3 and the open parameters of A7 and P1–P3 closed | **No** |
| Ready to run the study | Pre-registration closed with the above; no pending change to the frozen protocol | **No** |

P7 (OEPM consultation) and P8 (#112/#113) do not block acceptance. P7 can change how the 2010 gap and the 2023 drop are explained; P8 matters only before shared infrastructure. Neither is a condition of the pre-registration unless the reply to P7 contradicts the treatment in A6 or P6, in which case those decisions are reopened.
