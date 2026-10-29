# Technology topic map: product design

**Status:** Approved by the owner on 2026-10-29 as the design to plan from. The approval covers this design only: it resolves no D4 or E7 decision, approves no exposure of real candidates, validates no threshold, and claims nothing about patentability. D4 stays unresolved until the owner has read the OEPM legal notice and recorded it; the two named roles of section 13 are still open.
**Date:** 2026-10-29
**Origin:** two throwaway prototypes (batteries, solar) built and reviewed on 2026-10-28/29. They live outside git; this document keeps what was learned from them.
**Relates to:** [ADR 0036](../../adr/0036-technology-white-space-scientific-scope.md) · [ADR 0038](../../adr/0038-exploratory-white-space-product-track.md) · [vertical 3 acceptance status](../../whitespace/vertical-3-acceptance-status.md) · [decisions of 2026-10-28](../../whitespace/descriptive-article-outline.md)

Marks used: **[Owner]** decided or confirmed by the owner; **[My call]** a choice made while writing, open to change; **[Open]** undecided.

## 1. Intent and why

The existing page reads as a scientific report: it is written to defend what it measures, not to help someone decide where to look. **[Owner]** wants a product: patent intelligence that helps a person understand a technology area and decide where to look next, in language anyone can follow.

The owner is not a patent expert, and "if it cannot be understood without domain knowledge it is not usable" is the test for every screen.

## 2. Users

- **[My call]** The first user is a non-expert who arrives with a topic ("batteries", "solar") and wants a map: is it growing, what is it about, what does it mix with, who is in it, what is rarely combined.
- **[Open]** Who the first real users are (an IP firm, an R&D department, a researcher looking for lines). Two or three people doing technology watch are to be asked to use the prototype before this is decided.

## 3. Goals, non-goals, anti-goals

**Goals**
- A person with no patent background understands each screen without help and can answer, after two minutes on a topic: is it growing, what are its main parts, who is in it.
- Every figure is traceable to the versioned corpus, as in vertical 3.
- Caveats are said once, clearly, not scattered.

**Non-goals**
- No claim that anything is novel, patentable, free to operate, valuable or an opportunity. **[Owner]** decision of 2026-10-28; ADR 0036/0038.
- No ranking, score or "best candidates" list (ADR 0038, explorer contract).
- No prediction; that stays a later phase with its own protocol.
- No data other than the OEPM corpus 2000–2025.

**Anti-goals (a failure even if it works)**
- A client reading "hueco patentable" and acting on it.
- A polished page that hides that 85 % of battery documents are translations of European patents, or that one applicant makes 56 % of the 2024–2025 battery documents.
- Plain-language names that sound authoritative and are wrong.

## 4. Constraints

- **Corpus:** documents published by the OEPM 2000–2025, 2010 absent; 707,985 O4 units. Fields available: title, applicants, inventors, IPC (subgroup truncated to two digits), publication/filing/priority dates, kind. Not available: abstract, claims or description text, citations, patent families, CPC.
- **Reading limits:** the date is the OEPM publication date; EP translations are published about 7 years after filing on average, so recent years describe what was published in Spain, not current research.
- **IPC changes over time:** H01M 2 was replaced by H01M 50 (2021.01); H01L 31 moved to H10F (2025.01; in this corpus H10F appears only in 2025, 21 documents); F24J 2 became F24S (2018.01, group-to-group transfer not verified). A topic definition must list the old and new codes.
- **Governance:** E7 (who may see real candidates) is deferred and D4 (reading of the OEPM legal notice) has no owner. Until both are resolved, no real list of never-co-classified pairs is shown, and the Nginx barrier stays.
- **Architecture:** the repository's Clean Architecture (domain, application, infrastructure), tests named `shouldXWhenY`, integrity of served data as in vertical 3 (versioned result, SHA-256 checked at load).

## 5. The experience

**[Owner]** approved a three-level structure after seeing it clickable.

1. **Entry.** One question, "¿Qué tecnología te interesa?", with a search box and the available topics. **[Owner]** If the typed topic does not exist, the page says "No tenemos ese tema todavía." and nothing else.
2. **Topic summary.** One sentence with the main answer and four large buttons: ¿Cómo evoluciona? · ¿De qué trata? · ¿Quién está? · Pistas sin explorar.
3. **Detail views, one question each.** At most five items visible and a "Ver N más" fold. Each opens with a sentence that answers the question, then the chart or list.
4. **"Cómo leer esto"** reachable from every view (a dialog), holding the general caveats: corpus, translations, publication date, 2010 gap, nothing here says what is new or patentable.
5. Breadcrumbs on every view. No long single-scroll page.
6. **[My call]** Spanish only for now. All user text lives in one module, so that a second language can be added later without touching the views.
7. **[My call]** The topic map is a new route that coexists with the existing explorer. The explorer, its contract and the Nginx barrier are untouched.

**[Owner, confirmed 2026-10-29]** The first button is renamed from "¿Crece?" to "¿Cómo evoluciona?", because the data supports counts of publications per year, not a growth claim.

**[My call]** Sentence templates are generated from the data with guards: the "one applicant dominates" clause appears only when one applicant is at least 30 % of the last two years; otherwise the page says no company dominates. Numbers use the Spanish thousands separator. Other rules: the peak is the year(s) with the most documents (ties all named); five applicants and five neighbours are visible and the rest fold; figures are rounded to whole numbers; sub-areas may overlap and the page says so.

### Content per view

| View | Answers | Contents |
|---|---|---|
| ¿Cómo evoluciona? | How many documents are published per year, and how has that number changed? | Descriptive only: the yearly average for 2000–2009, 2011–2023 and 2024–2025, each next to the share of EP translations in that period; the peak year(s); a bar chart by year with the 2010 gap marked; when one applicant dominates, its share drawn in another colour; reminder that the axis is publication in Spain. The text never says "crece" or "decrece": a comparison of three averages is not a trend. |
| ¿De qué trata? | What are its parts and what does it mix with? | Sub-areas with plain names and one-line descriptions; neighbouring technologies by co-classification. |
| ¿Quién está? | Who patents? | Applicants with the largest number of documents, variants of known names merged. |
| Pistas sin explorar | What is combined less than expected? | Observed-but-rare combinations with their expected count (see section 7). |

## 6. Topics and names

- **[My call]** A topic is a hand-written definition: a list of IPC subclasses or main groups (current and superseded), a plain name, a description for each sub-area, and plain names for neighbouring subclasses. The catalogue starts with batteries and solar.
- Plain names were checked against the official IPC 2026.01 scheme titles by two subagents (2026-10-29). Corrected names are in the prototype source, not yet in the repository. **[Open]** A sector expert still has to review them before a client sees them. F01K was not verified.
- **[My call]** Definitions and plain names live in one versioned definition file per topic in the repository, reviewed by a person. Its identifier goes into the result's configuration, so changing a name or a code changes the version. Each name carries a `reviewed` flag; a build for clients refuses topics with unreviewed names, a development build shows them marked.
- **[Owner, 2026-10-29]** A new topic is added by hand: we write the codes and names and a sector expert reviews them before publication. A template filled in by an expert stays a possible later step. **[Open]** Who the sector reviewer is. Topic quality depends entirely on the definition (batteries is one subclass and reads sharply; solar mixes four areas and reads more loosely).
- Some topics cannot be built from this corpus: "precision agriculture" lives at subgroup level (A01B 79/005) and subgroups are truncated.
- **Applicants [My call].** Merging rules live in a versioned file, each with its pattern, the canonical name, the reason and a date. A rule matches whole normalised names or whole-word prefixes, never a bare substring (a substring rule once merged every "Politécnica" university under Madrid). The original name stays attached to every merged count for traceability. Names no rule resolves stay separate. Tests cover collisions and false positives (for example Universidad Politécnica de Madrid vs de Valencia or de Cataluña). A systematic normalisation remains **[Open]**.

### Topic semantics (contract the build must fix as tests)

- **Unit:** the O4 unit, with the union of the subclasses and main groups of its earliest publication date. Everything below counts units, never records.
- **Membership:** a unit belongs to a topic if at least one of its IPC entries matches at least one code of the definition. It is counted once for the topic however many codes match. A unit belongs to a sub-area under the same rule applied to that sub-area's codes.
- **Overlap:** sub-areas may overlap, so their counts may add up to more than the topic total. Every code of a definition belongs to exactly one sub-area.
- **Invariants:** each sub-area count ≤ the topic count; the union of the sub-areas equals the topic; the topic count is the same whatever the order of the codes; the counts are reproducible from the corpus hash and the definition identifier.
- **Neighbours:** a subclass X is a neighbour of T if the same unit carries X; the subclasses named in the definition are excluded. Counts are units.
- **Historical codes:** each definition lists current and superseded codes with the IPC version that introduced or removed them and the source checked (H01M 2→50, 2021.01, verified; H01L 31→H10F, 2025.01, verified; F24J 2→F24S, 2018.01, group-to-group transfer not verified). Unverified mappings are marked in the definition file and in the topic's notes.

## 7. White spaces

- **What exists now:** "se combinan menos de lo que cabría esperar": subclasses observed together with the topic, fewer times than their size suggests, shown with "aparece N veces; por su tamaño cabría esperar unas M". They come from the observed corpus and show no candidate pair.
  - **Definition [My call, provisional parameters].** For a topic T and a neighbouring subclass X, over O4 units published in years with documents (2010 skipped, never counted as zero): observed O = units in T that also carry X; expected E = Σ_y n_T(y)·n_X(y) / N(y), the ADR 0038 E3 formula with n_T(y) the units of T published in year y, n_X(y) those carrying X, and N(y) all units of year y. Ratio = O / E. The prototype used corpus-wide frequencies, which ignore time; its figures are not results and are recomputed.
  - **Inclusion [My call, provisional heuristic, approved by the owner as an exploratory filter]:** O ≥ 30 and E ≥ 30 and ratio < 0.8. The minimum of observed co-classifications keeps out neighbours that are rare against the expectation only because they belong to an unrelated field. E ≥ 30 keeps the ratio from resting on small numbers; E = 0 is excluded (ratio undefined).
  - **What this list is not.** It lists observed neighbours that appear less often than their size suggests. It is **not** a list of never-co-classified pairs: O ≥ 30 excludes every pair with no or few observed co-classifications, and those stay behind the E7/D4 gate. The aggregate counts of such pairs obtained in the exploration do not authorise showing any of them.
  - **Not calibrated.** The thresholds are heuristics chosen after looking at batteries and solar, the same two topics that motivate them; they are not validated and the 0.8 line is arbitrary. A sector reviewer and a third topic that played no part in the choice are needed before they are frozen.
  - Meaning of the ratio: observed co-classifications divided by what independence within years would give. It describes the corpus; it says nothing about a technical reason or an opportunity.
    - Boundary cases to be fixed as tests before building: E and O just below and above 30, ratio 0.79 and 0.80, a year with no documents, a topic with no qualifying row (the view says so instead of showing an empty chart).
  - **Order: alphabetical by plain name.** The prototype sorted by ratio, ascending, which is a ranking in disguise and contradicts the no-ranking rule; it must not be repeated. The bar may show the ratio; the order does not encode it.
- **What is only a mock:** a block of never-co-classified pairs, with fictitious pairs and fictitious numbers, labelled everywhere as fictitious, in alphabetical order with no score. It tests wording only. Real pairs are not shown while E7 and D4 are open.
- **[Open, owner]** The criterion for which never-co-classified pairs a topic view may show. Constraints it has to respect: the expected count under independence (ADR 0038 E3, minimum 1), no ranking, aggregate or alphabetical presentation, and that most such pairs are technically meaningless (for example batteries with algae farming), so the filter is a scientific decision, not a design one.
- Each row, real or mock, says what is not known: whether it exists outside Spain or outside this corpus, and whether there is a technical reason it is not combined. Said once at the top of the view, with a short mark on each row.

## 8. Data and delivery (what the builder works from)

- **[My call]** The prototype code is reference only and is rewritten under the repository's architecture (the domain defines topic, sub-area and metric; the application computes them; infrastructure reads the corpus and writes the result). The prototype's extraction script for solar and the corrected names are in `.playwright-mcp/spike-src/` (not in git); the battery generator was lost and has to be written again from this section.
- **[My call]** Per-topic aggregate results computed offline from the versioned corpus by a script, served as static, versioned JSON with a SHA-256 checked at load, as in vertical 3. The browser computes no metric beyond presentation. Raw documents, titles and per-document identifiers are not served.
- The prototype computed, per topic: documents by year (O4 units by earliest publication year), sub-area counts, neighbour subclasses with counts and a ratio against corpus-wide frequency, and applicants. These definitions are the starting point and the builder may restructure them.
- Right now the corpus generator takes about three minutes per topic. Fine offline; a topic added at request time would need precomputation, not a live query.

## 9. Findings from the prototypes (facts, not claims about the product)

**Exploration of the inclusion thresholds (2026-10-29, exploratory evidence, not validation).** With E3 computed within years over O4 units, for batteries (5,676 documents) and solar (5,812):

| Criterion | Batteries | Solar |
|---|---|---|
| O ≥ 1, E ≥ 30, ratio < 0.8 | 52 rows (35 with ratio < 0.2) | 47 rows (28 with ratio < 0.2) |
| O ≥ 10, E ≥ 30, ratio < 0.8 | 19 | 22 |
| O ≥ 30, E ≥ 30, ratio < 0.8 | 7 | 6 |

The first criterion lets in unrelated fields (medicines, packaging, telecommunications) with ratios near 0.01. The ratio threshold barely changes the count (ratios fall in two separate groups), so the minimum observed count is what decides. The figures were produced once by the author and not independently reproduced; the scripts are not in git.


- Batteries (H01M): 5,676 documents (0.8 % of the corpus); 85 % are EP translations; LG Energy Solution is in 22 % of them and 56 % of the 2024–2025 ones (none before 2022). Sub-areas: rechargeable batteries, electrodes, casings and connections, fuel cells.
- Solar (H01L 31, H10F, H10K 30, H02S, F24S, F24J 2, F03G 6): 5,812 documents; 44 % EP translations; no applicant above about 5 %. The same screens worked with a different profile.
- Both topics are 0.8 % of the corpus by coincidence.
- Two errors made and fixed during the prototypes show the risk: a text claimed recent years were under-represented when they were the highest, and a substring rule merged all "Politécnica" universities under Madrid. Generated sentences need tests against the data.

## 10. Scope of the first build

**[Owner confirmed 2026-10-29 that the fictitious block is not shipped; the rest is my call]** The first build delivers the three views with real data (¿Cómo evoluciona?, ¿De qué trata?, ¿Quién está?) and, in "Pistas sin explorar", only the real "menos de lo esperado" part. The fictitious block of never-co-classified pairs is **not** shipped: it stays a development fixture, so no fictitious data reaches a client. The result format does not carry a block of unobserved pairs until the criterion of section 7 exists.

## 11. Success and how it will be judged

- **[My call]** Two or three people who do technology watch use the prototype on a shared screen without explanation. The test is what they understand, what they ask, and what they miss; not whether they like it.
- **[My call]** The first phase counts as understood if at least two of three people answer correctly, without help and within two minutes, the three questions of section 3 for a topic they did not see before. With three participants this is a formative test, not evidence of general usability.
- **Protocol, fixed before the session [My call]:** (1) the exact questions, written per topic from the data (for example "¿Se publican más o menos documentos al año que a principios de los 2000?", "¿Cuál es la parte más grande de este tema?", "¿Qué empresa aparece más?"); (2) for each, the accepted answers, derived from the computed data; (3) one uniform instruction read to every participant, with no help from the moderator; (4) an observation sheet with time to answer, wrong or missing answers, where the person hesitated and what they said aloud; (5) what counts as an error, decided in advance.
- Sentence guards and merged names covered by tests (`shouldMentionDominantApplicantOnlyWhenAboveThreshold` style).
- Acceptance of exposure stays with ADR 0038; this document does not replace it.

## 12. Left to the builder

Technology choices inside the existing frontend and backend, file layout, chart implementation, how definitions and names are stored, accessibility details (keyboard, contrast, small screens), and the test strategy.

## 13. Decisions

Closed on 2026-10-29 **[Owner]**:
- The fictitious block of never-co-classified pairs is not shipped (development fixture only).
- The first button is "¿Cómo evoluciona?".
- A new topic is added by hand, with review by a sector expert.
- The inclusion criterion of the rare-combinations list is approved as a provisional exploratory filter (section 7); it is not validated.
- D4: the owner reads the OEPM legal notice himself and records the date and the reading. **D4 is not resolved until that is done.** This replaces the earlier plan of assigning another person.

Still open:
1. **Names for two roles.** The profiles are set below; nobody is named until their availability and independence are confirmed.
   - **Sector reviewer** of topic definitions and plain names: a person with experience in patents and technical knowledge of batteries or solar, able to judge whether the IPC codes and the names fit. Preferably someone who took no part in choosing the exploratory thresholds.
   - **First users** (usability): two or three people outside the development, not experts in patent classification. They judge whether they understand the map and its four views. They need no access to never-co-classified pairs.
   - **Separation of roles:** before any person who could assess candidates scientifically sees them, E7 is resolved and it is recorded whether that person may take part in the human review.
2. Whether any never-co-classified pair may ever be shown, and under which criterion (E7, after D4).
3. Calibration of the thresholds with a sector reviewer and a third topic.
