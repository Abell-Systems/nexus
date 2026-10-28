# State of the art for Nexus: reading notes (working draft)

**Borrador de trabajo; no constituye una revisión bibliográfica cerrada.**

**Status:** Working draft of reading notes. It is **not** a closed literature review, **not** a claim about Nexus's performance or superiority, and it decides nothing: whether Nexus stays a descriptive tool or adds a predictive line remains open and tied to [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) (E7). No code, ADR or product decision changes here.
**Date:** 2026-10-28
**Scope:** (1) what two papers read through an extraction tool measure (Youn et al. 2015 and Fenoaltea et al. 2026), and a third (Kim et al. 2016) that is identified but **not yet read**; (2) a first, partial look at commercial products; (3) how each differs from Nexus. Out of scope for this first delivery: the EBT at UCA, intellectual property of the code and licences of the OEPM data for commercial use. None of those is addressed by this note.

## 0. How to read the tags

Every statement carries one tag.

| Tag | Meaning |
|---|---|
| **[S]** | **Primary source.** What the paper or the vendor says explicitly. **Caution:** the text of each paper was obtained through a web-fetch extraction tool (HTML or PMC version), and the quotes of 125 characters or fewer come from that extraction. The assistant read the extraction; no one has compared it with the published PDF. Treat every [S] as «to be checked against the original before citing». |
| **[I]** | **Own inference.** A comparison between methods, corpora, classification levels, or a relation to ADR 0038. It is ours, not the source's. |
| **[V]** | **Pending verification.** Something not checked against the original, an inconsistency the text does not resolve, or a limit that cannot be confirmed. |

## 1. Reading matrix

| | Youn et al., 2015 | Fenoaltea et al., 2026 (arXiv 2605.04875) | Kim et al., 2016 |
|---|---|---|---|
| Reference | Youn, Strumsky, Bettencourt, Lobo. *Invention as a combinatorial process: evidence from US patents.* J. R. Soc. Interface 12(106), 20150272. doi:10.1098/rsif.2015.0272 | Fenoaltea, Santoro, De Marzo, Aroyehun, Tacchella. *Anticipating Innovation Using Large Language Models.* arXiv:2605.04875v1 | Authors as listed by the search result: Kim, Cerigo, Jeong, Youn. *Technological novelty profile and invention's future impact.* EPJ Data Science 5, 8 (2016), doi:10.1140/epjds/s13688-016-0069-1; preprint arXiv:1512.06169 **[V]** |
| Question | **[S]** Relative importance of new technologies versus combining existing ones | **[S]** Forecasting «the emergence of new technological combinations» | **[V]** Not read. A search summary says that an invention is unconventional if a pair of its codes is unlikely together given past statistics, and that novelty relates to citations |
| Data | **[S]** US patents, 1790–2010, by application year | **[S]** European Patent Bulletin, English-language patents; 1,302,500 patents; fine-tuning 1980–2005, test 2006–2024 | **[V]** Not read |
| Classification | **[S]** USPTO technology codes, **not IPC** (474 classes, about 161,000 codes) | **[S]** IPC at **group** level, 7,200 codes; the authors say this «inevitably coarse-grains» the space | **[V]** Not read |
| Unit | **[S]** The patent as the carrier of a set of codes | **[S]** Pairs of IPC codes | **[V]** Not read |
| Novelty | **[S]** Code or set of codes not used before. **[V]** The text gives no rule for counting «new» per year | **[S]** First co-occurrence of two codes; stricter version: more than a null expectation (following Tacchella et al., 2020) | **[V]** Not read |
| Null model | **[S]** No expected co-occurrence under independence. A comparison with random choice among all possible combinations (probability of a repeat of about 10⁻⁴ for T = 10,000 against about 40 % observed) and the remark that a random walk would give a Poisson-like distribution; **qualitative, no simulation or test stated**. The combinatorial upper bound C_max is defined, **[V]** its formula was not in the extracted text | **[S]** Chung–Lu bipartite null model (section 2) | **[V]** Not read |
| Validation | **[S]** Descriptive laws (for example C ≈ αP, α ≈ 0.6); no prediction | **[S]** Temporal split; two set-ups (section 2) | **[V]** Not read |
| Stated limits | **[S]** The gap between possible and realized combinations is beyond scope; silent on quality of invention | **[S]** Group level is coarse; pairs only. **[V]** The extraction found no confidence intervals, seeds or code and data availability statement | **[V]** Not read |

## 2. Fenoaltea et al.: methods as extracted

All of this section is **[S]** unless marked, from the HTML version of arXiv 2605.04875v1, and every formula is **[V]** until compared with the PDF.

- **Null model.** The probability that patent *p* is connected to code *c* is P_pc = w_p · w_c / N, with w_c the degree of the code, w_p the degree of the patent and N the total number of links of the bipartite network. It preserves «the average number of connections for each patent and each technology».
- **Expected value, deviation, score.** E_cc' = Σ_p P_pc · P_pc'; σ_cc' = √(Σ_p P_pc · P_pc' · (1 − P_pc · P_pc')); Z_cc' = (O_cc' − E_cc') / σ_cc', with O_cc' the observed co-occurrences in the test window. The text says the co-occurrences follow a Poisson binomial distribution and cites Chung and Lu (2002) without derivation.
- **Realized pairs.** The z-score ranks the pairs, and the K pairs with the highest observed z-score get label 1; the rest, 0. K is not a single value: the class-imbalance ratio is fixed instead (0.005 % corresponds to about 10³ positives out of about 2 × 10⁷ possible pairs for the 2011–2015 test set), and the threshold is said to correspond to a p-value of about 10⁻⁵.
- **Context similarity (CS).** For the TechToken model, the average of the top x % (x = 1 % in the main text) of all pairs of token embeddings of the two codes. **[V]** The Methods text also describes CS as «the overlap between their embeddings», which conflicts with the cosine-similarity definition used elsewhere; the text does not reconcile them.
- **Two evaluations.** (a) CS computed on 2006–2010 patents for pairs unseen until 2010, tested on five-year windows starting 2011–2015: the text says these results «are not strictly out of sample» (Llama 3.1 cut-off December 2023; BERT models fine-tuned on patents up to that date). (b) Stricter: CS from 2019–2023 patents, pairs unseen before 2024, tested on patents published in 2024; the text says none of the models was fine-tuned on the test patents.
- **Where 0.936 comes from.** Table 1, row «TechToken BERT (IPC)», column AUC-ROC at 0.005 % class imbalance, with the caption «code pairs from 2019–2023 that had never co-occurred before 2024», i.e. the **stricter** set-up (b). An earlier message of this session said it came from «the most favourable scenario»; that was wrong as far as the extraction shows.
- **[V]** The Data section says BERT fine-tuning used patents 1980–2005; the Results section says patents up to 2023. The text does not reconcile the two, so the training range of the model behind 0.936 is unclear.
- **[V]** The text says «decades in advance» in the abstract and «almost 20 years» in the body; the 20-year figure is an average read from a figure, not tabulated.

## 3. Youn et al.: methods as extracted

- **[S]** A combination is «the set of distinct combinations of codes used to describe inventions»; time is the application year. C(t) = αP with α ≈ 0.6 (about 60 % of new patents add a new combination). New-code growth slows after about 1870. Code-use frequencies have heavy tails (fit near x^−2.4). Narrow (same-class) combinations are about 44 % overall.
- **[V]** No operational rule for «new code» or «new combination» per year; no statement on whether discretionary and mandatory codes are treated differently; C_max (Eq. 3.2) was an image.
- **[I]** The paper is conceptual support for treating invention as combinatorial. It is **not** a methodological antecedent of Nexus: it uses USPTO codes, not IPC, and no expected count under independence.

## 4. Commercial products (first pass, vendor material only)

Nothing here was tested with an account; all of it is **[S]** from the vendors' own pages or **[V]** from aggregators, and absence of a feature in what was read is **not** evidence that the product lacks it.

| Product | What its own material says | Tag |
|---|---|---|
| PatSnap | Landscape tool in which clusters form «mountains» and gaps appear between clusters, formed by IPC and CPC commonality; white space described as limited patenting activity presented as openings for innovation | [S], [PatSnap blog](https://www.patsnap.com/resources/blog/rd-blog/ai-patent-whitespace-analysis-patsnap-eureka/), [PatSnap help](https://help.patsnap.com/hc/en-us/articles/115000409785) |
| Questel Orbit | White space analysis with a choice of how automated it is | [S], [Orbit page](https://www.questel.com/orbit-intelligence) |
| Derwent Innovation | Search by IPC, CPC, F-terms and dashboards [S], [Clarivate](https://clarivate.com/derwent/zh-hant/?p=40828). **Observation, not a vendor statement:** the search did not find a white-space feature in the material consulted | [S] for the first part; [V] for the absence |
| Lens.org | No white-space feature details found | [V] |

## 5. What differs from Nexus

All **[I]** unless stated.

- **Question.** Nexus today describes IPC subclass pairs **not observed** in the OEPM corpus and an expected count under independence; it does not forecast that a pair will appear and does not call an absence an opportunity. Fenoaltea et al. forecast first co-occurrences; commercial products present gaps as opportunities (their own wording, [S]).
- **Scale and corpus.** Nexus: Spanish OEPM publications 2000–2025 with the 2010 gap, 621 active subclasses. Fenoaltea et al.: European Patent Bulletin in English, 1980–2024, about 7,200 groups.
- **Nulls: a hypothesis to investigate, not an equivalence.** The Nexus expected count sums over publication years the term n_i · n_j / N(y) (contract of vertical 3 §5). The Chung–Lu null sums over patents the product of two connection probabilities that depend on each patent's degree. Both are sums of products of marginal frequencies, but the units (year against patent), the quantities preserved and the variance are different. Whether they give similar numbers on the same data is **untested**, and the Chung–Lu null must **not** be equated with Nexus's annual sum.
- **The 0.936.** It is a result the authors report for their model and set-up. It is **not** a reference for Nexus and says nothing about what Nexus would achieve.
- **Evaluation design.** Fenoaltea et al. label pairs as realized by z-score in a later window and score a predictor with AUC-ROC. A comparable test for Nexus would be a pre-registered temporal one on reserved origins (ADR 0038 E7); that is a possibility to study, not a plan.
- **Traceability.** Nexus documents the result hash, the configuration identifier and the reconstruction of the per-year terms. Whether the commercial products or these papers publish equivalents has **not** been investigated.

## 6. Pending for the next pass

1. Compare the extracted formulas of Fenoaltea et al. with the PDF, and resolve the two inconsistencies of section 2.
2. Read Kim et al. (2016) in full; the Springer page required an identity redirect, and the arXiv PDF could not be extracted.
3. Check Youn et al.'s operational definition of novelty and C_max in the PDF.
4. Compare the Chung–Lu expected counts with Nexus's expected counts on the same data, if the owner decides that this is worth doing.
5. If the owner decides it is useful, a comparative reading of the products with trial accounts.
