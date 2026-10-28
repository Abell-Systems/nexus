# State of the art for Nexus: reading notes (working draft)

**Borrador de trabajo; no constituye una revisión bibliográfica cerrada.**

**Status:** Working draft of reading notes. It is **not** a closed literature review, **not** a claim about Nexus's performance or superiority, and it decides nothing: whether Nexus stays a descriptive tool or adds a predictive line remains open and tied to [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) (E7). No code, ADR or product decision changes here.
**Date:** 2026-10-28 (second pass the same day: Kim et al. read in full; formulas of Fenoaltea et al. checked against the arXiv PDF)
**Scope:** (1) what two papers read through an extraction tool measure (Youn et al. 2015 and Fenoaltea et al. 2026), and Kim et al. 2016, read in full from the arXiv v1 PDF in the second pass; (2) a first, partial look at commercial products; (3) how each differs from Nexus. Out of scope for this first delivery: the EBT at UCA, intellectual property of the code and licences of the OEPM data for commercial use. None of those is addressed by this note.

## 0. How to read the tags

Every statement carries one tag.

| Tag | Meaning |
|---|---|
| **[S]** | **Primary source.** What the paper or the vendor says explicitly. **Caution:** the text of each paper was obtained through a web-fetch extraction tool (HTML or PMC version), and the quotes of 125 characters or fewer come from that extraction. The assistant read the extraction; no one has compared it with the published PDF. Treat every [S] as «to be checked against the original before citing». **Second pass:** the arXiv PDFs of Fenoaltea et al. and Kim et al. were also converted to plain text with `pypdf` and read directly by the assistant (not through a summarising tool); Youn et al. is still known only from the PMC HTML through the extraction tool. The arXiv v1 of Kim et al. is dated 2015; the published version (EPJ Data Science 2016) may differ and was not read. |
| **[I]** | **Own inference.** A comparison between methods, corpora, classification levels, or a relation to ADR 0038. It is ours, not the source's. |
| **[V]** | **Pending verification.** Something not checked against the original, an inconsistency the text does not resolve, or a limit that cannot be confirmed. |

## 1. Reading matrix

| | Youn et al., 2015 | Fenoaltea et al., 2026 (arXiv 2605.04875) | Kim et al., 2016 |
|---|---|---|---|
| Reference | Youn, Strumsky, Bettencourt, Lobo. *Invention as a combinatorial process: evidence from US patents.* J. R. Soc. Interface 12(106), 20150272. doi:10.1098/rsif.2015.0272 | Fenoaltea, Santoro, De Marzo, Aroyehun, Tacchella. *Anticipating Innovation Using Large Language Models.* arXiv:2605.04875v1 | Kim, Cerigo, Jeong, Youn. *Technological novelty profile and invention's future impact.* EPJ Data Science 5, 8 (2016), doi:10.1140/epjds/s13688-016-0069-1; **read here: arXiv:1512.06169v1** (19 Dec 2015) |
| Question | **[S]** Relative importance of new technologies versus combining existing ones | **[S]** Forecasting «the emergence of new technological combinations» | **[S]** Assess the novelty of each pair of codes in a patent against «what would be expected if the combinations were randomly configured», and relate it to the patent's future citations |
| Data | **[S]** US patents, 1790–2010, by application year | **[S]** European Patent Bulletin, English-language patents; 1,302,500 patents; fine-tuning 1980–2005, test 2006–2024 | **[S]** US utility patents up to December 2014 (8,884,909; those with two or more codes, 80.3 %, are analysed); citations from the NBER data, 1976–2001 after the five-year window |
| Classification | **[S]** USPTO technology codes, **not IPC** (474 classes, about 161,000 codes) | **[S]** IPC at **group** level, 7,200 codes; the authors say this «inevitably coarse-grains» the space | **[S]** USPC codes, **not IPC**: 473 classes, 16,087 subclasses, 168,743 codes (as the PDF states); results at class and subclass level |
| Unit | **[S]** The patent as the carrier of a set of codes | **[S]** Pairs of IPC codes | **[S]** Pairs of codes within a patent; per-patent profile (median, minimum and difference of the pair z-scores) |
| Novelty | **[S]** Code or set of codes not used before. **[V]** The text gives no rule for counting «new» per year | **[S]** First co-occurrence of two codes; stricter version: more than a null expectation (following Tacchella et al., 2020) | **[S]** A pair is atypical if its z-score is negative: observed co-occurrences below the null expectation. Binary «new / not new» is called insufficient |
| Null model | **[S]** No expected co-occurrence under independence. A comparison with random choice among all possible combinations (probability of a repeat of about 10⁻⁴ for T = 10,000 against about 40 % observed) and the remark that a random walk would give a Poisson-like distribution; **qualitative, no simulation or test stated**. The combinatorial upper bound C_max is defined, **[V]** its formula was not in the extracted text | **[S]** Chung–Lu bipartite null model (section 2) | **[S]** Hypergeometric null: random arrangement of codes among patents preserving code usage and the number of patents (section 4) |
| Validation | **[S]** Descriptive laws (for example C ≈ αP, α ≈ 0.6); no prediction | **[S]** Temporal split; two set-ups (section 2) | **[S]** Association with citations (top 5 % within five years); descriptive, not a forecast of new pairs. Hit probability up to almost 9 % for the best category |
| Stated limits | **[S]** The gap between possible and realized combinations is beyond scope; silent on quality of invention | **[S]** Group level is coarse; pairs only. **[V]** The extraction found no confidence intervals, seeds or code and data availability statement | **[S]** The null model «does not account for inventions having a single code and for when a code is created»; citations outside the data are missed |

## 2. Fenoaltea et al.: methods as extracted

All of this section is **[S]** unless marked, from the HTML version of arXiv 2605.04875v1, and every formula is **[V]** until compared with the PDF.

- **Null model.** The probability that patent *p* is connected to code *c* is P_pc = w_p · w_c / N, with w_c the degree of the code, w_p the degree of the patent and N the total number of links of the bipartite network. It preserves «the average number of connections for each patent and each technology».
- **Expected value, deviation, score.** E_cc' = Σ_p P_pc · P_pc'; σ_cc' = √(Σ_p P_pc · P_pc' · (1 − P_pc · P_pc')); Z_cc' = (O_cc' − E_cc') / σ_cc', with O_cc' the observed co-occurrences in the test window. The text says the co-occurrences follow a Poisson binomial distribution and cites Chung and Lu (2002) without derivation.
- **Realized pairs.** The z-score ranks the pairs, and the K pairs with the highest observed z-score get label 1; the rest, 0. K is not a single value: the class-imbalance ratio is fixed instead (0.005 % corresponds to about 10³ positives out of about 2 × 10⁷ possible pairs for the 2011–2015 test set), and the threshold is said to correspond to a p-value of about 10⁻⁵.
- **Context similarity (CS).** For the TechToken model, the average of the top x % (x = 1 % in the main text) of the cosine similarities among all pairs of token embeddings of the two codes. The PDF first calls CS «the overlap between their embeddings» and then defines it technically as a cosine similarity. The first extraction reported this as a conflict; on the PDF it reads as informal wording followed by the precise definition, so it is **not** recorded as an inconsistency.
- **Two evaluations.** (a) CS computed on 2006–2010 patents for pairs unseen until 2010, tested on five-year windows starting 2011–2015: the text says these results «are not strictly out of sample» (Llama 3.1 cut-off December 2023; BERT models fine-tuned on patents up to that date). (b) Stricter: CS from 2019–2023 patents, pairs unseen before 2024, tested on patents published in 2024; the text says none of the models was fine-tuned on the test patents.
- **Where 0.936 comes from.** Table 1, row «TechToken BERT (IPC)», column AUC-ROC at 0.005 % class imbalance, with the caption «code pairs from 2019–2023 that had never co-occurred before 2024», i.e. the **stricter** set-up (b). An earlier message of this session said it came from «the most favourable scenario»; that was wrong as far as the extraction shows.
- **[V]** Still unresolved in the PDF: the Methods say the fine-tuning used patents 1980–2005 «in order to keep some out-of-sample data (from 2006 to 2024)», while the text of the stricter set-up says all models were fine-tuned «with patents released in 2023 at the latest». Which fine-tuning corresponds to the 0.936 is therefore not settled by the text.
- **Checked against the PDF (second pass):** the connection probability, E, σ and Z formulas as written above; the 0.936 in Table 1 under the stricter set-up (pairs from 2019–2023 never co-occurring before 2024, test patents of 2024, class imbalance 0.005 %); the class imbalance fixed through a z-score threshold (about 10³ positives of about 2 × 10⁷ pairs for 2011–2015, p of order 10⁻⁵).
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

## 4b. Kim et al. 2016: the null closest to Nexus's

All **[S]** from the arXiv v1 PDF unless marked.

- **Null model.** Random arrangement of the codes among the patents, preserving code usage and the number of patents. For codes α and β with n_α and n_β occurrences among |P| patents, the number of co-occurrences is hypergeometric; the expected number is **μ_αβ = n_α · n_β / |P|** (their Eq. 3) and the variance σ²_αβ = μ_αβ · (1 − n_α/|P|) · (|P| − n_β)/(|P| − 1) (Eq. 4). z_αβ = (o_αβ − μ_αβ)/σ_αβ.
- **Time.** z-scores are computed on cumulatively growing sets P(t) of all patents up to year t.
- **Coarse-graining.** Class and subclass pairs are obtained by summing the code-level o, μ and σ² over the codes of the two classes or subclasses; they do not recompute the null at the coarse level.
- **Their remark on fine granularity.** Without that aggregation, code frequencies far below |P| make one co-occurrence exceed the expectation, so fine-grained codes «mostly» give positive z-scores and the novel pairs cannot be seen.
- **Limits they state.** The null does not handle single-code inventions or the creation date of a code.

**[I] Relation with Nexus (derived by us; to be checked by a second person).** Nexus's per-year term n_i · n_j / N(y) has the form of Kim's Eq. 3 applied to one year. The two differ in that Nexus **sums the per-year terms** over the years with documents, while Kim et al. evaluate one cumulative set P(t). Nexus does not compute a variance or a z-score. A pair with zero observations and an expected count of at least 1 is, in Kim's reading, one with a negative z-score; Nexus does not use that reading.

**[I] Relation with the Chung–Lu null of Fenoaltea et al.** If every patent has the same degree w, then N = w · |P| and P_pc = w · w_c / N = w_c / |P|, so E_cc' = Σ_p (w_c/|P|)(w_c'/|P|) = w_c · w_c' / |P|, which is Kim's Eq. 3. With heterogeneous patent degrees the two differ. This is an algebraic observation, not a numerical test, and says nothing about how large the difference is on real data. It does **not** make the Chung–Lu null equal to Nexus's annual sum.

## 5. What differs from Nexus

All **[I]** unless stated.

- **Question.** Nexus today describes IPC subclass pairs **not observed** in the OEPM corpus and an expected count under independence; it does not forecast that a pair will appear and does not call an absence an opportunity. Fenoaltea et al. forecast first co-occurrences; commercial products present gaps as opportunities (their own wording, [S]).
- **Scale and corpus.** Nexus: Spanish OEPM publications 2000–2025 with the 2010 gap, 621 active subclasses. Fenoaltea et al.: European Patent Bulletin in English, 1980–2024, about 7,200 groups.
- **Nulls: a hypothesis to investigate, not an equivalence.** The Nexus expected count sums over publication years the term n_i · n_j / N(y) (contract of vertical 3 §5). Kim et al.'s null has that form for one set of patents (section 4b). The Chung–Lu null sums over patents the product of two connection probabilities that depend on each patent's degree; it reduces to the same form only if all patents have the same degree (section 4b). The units (year against cumulative set against patent), the quantities preserved and the variance differ. Whether they give similar numbers on the same data is **untested**, and neither null must be equated with Nexus's annual sum. Whether the three answer the same statistical question is the point of the analytic comparison proposed next.
- **The 0.936.** It is a result the authors report for their model and set-up. It is **not** a reference for Nexus and says nothing about what Nexus would achieve.
- **Evaluation design.** Fenoaltea et al. label pairs as realized by z-score in a later window and score a predictor with AUC-ROC. A comparable test for Nexus would be a pre-registered temporal one on reserved origins (ADR 0038 E7); that is a possibility to study, not a plan.
- **Traceability.** Nexus documents the result hash, the configuration identifier and the reconstruction of the per-year terms. Whether the commercial products or these papers publish equivalents has **not** been investigated.

## 6. Pending for the next pass

1. Compare Youn et al.'s operational definition of novelty and C_max with the PDF (the publisher's site refused the download; the arXiv version 1406.2938 may serve).
2. Compare the published EPJ Data Science version of Kim et al. with the arXiv v1 read here.
3. Analytic comparison of the three expected counts (Nexus annual sum, Kim cumulative hypergeometric, Fenoaltea Chung–Lu): what each preserves, what question each answers, and whether an experiment is justified. Only then, if the owner decides it, a small reproducible experiment with metrics agreed beforehand.
4. Resolve with the authors' text, or leave stated, the unresolved fine-tuning range behind the 0.936.
5. If the owner decides it is useful, a comparative reading of the products with trial accounts.
