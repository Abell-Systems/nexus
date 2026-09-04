# Empirical Research Protocol: Matching Industrial Innovation Demands with Domestic Patent Publications

**Target Publication:** *World Patent Information* (Elsevier)  
**Document Type:** Formal Scientific Experimental Protocol  
**Document Version:** 1.0.0 (Pre-Registered Frozen Experimental Protocol)  
**Date:** 2026-09-03  
**Authors:** Valentín Liñeiro; Lydia Bares  
**Affiliation:** Abell Systems  
**Status:** Pre-Registered Frozen Experimental Protocol (Immutable Methodological Specification)  

---

## 1. Introduction & Scientific Context

Open innovation ecosystems increasingly rely on digital marketplaces and intermediary brokers (e.g., InnoGet, INDUSAC, Enterprise Europe Network) where industrial enterprises publish articulated technology demands (*market-pull signals*). Concurrently, national patent offices—such as the Spanish Patent and Trademark Office (*Oficina Española de Patentes y Marcas*, OEPM)—and regional authorities publish exhaustive domestic patent gazettes and open datasets (*technology-supply signals*).

Bridging these two distinct information spaces presents an acute information retrieval (IR) challenge:
1. **Linguistic & Structural Asymmetry:** Industrial technology demands are formulated in problem-centric, operational, and commercial vernacular (e.g., "seeking biodegradable surfactant for low-temperature washing at 15–25 °C"), whereas patent documents are structured around formal legal-technical claims, abstract taxonomic nomenclature, and defensive drafting styles.
2. **Jurisdictional & Temporal Grounding:** Domestic enterprises and innovation agencies frequently require visibility into the domestic prior-art and technological base (e.g., jurisdiction `ES`), subject to strict temporal constraints (whether a patent publication was publicly accessible prior to the demand solicitation).
3. **Rigorous IR vs. Legal Distinction:** Algorithmic ranking tools must explicitly distinguish between **technological relevance / prior-art candidate retrieval** and **authoritative legal determinations of patentability (novelty and inventive step under EPC Art. 54/56 or Spanish Patent Law 24/2015)**.

This empirical research protocol formalizes the experimental design, dataset provenance, candidate generation mechanisms, multi-strategy ranking architectures, expert annotation procedures, evaluation metrics, statistical tests, and reproducibility standards required for submission to *World Patent Information*.

---

## 2. Research Questions & Hypotheses

To avoid confounding recall in candidate generation with early precision in rank optimization, the study formally decomposes the matching problem into two sequential, decoupled evaluation tiers: **First-Stage Candidate Retrieval** and **Second-Stage Ranking/Fusion over a Shared Fixed Candidate Pool**.

```text
                    DEMAND QUERY d
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
           BM25        Semantic       CPC
          top-100       top-100      top-100
             │            │            │
             └────────────┼────────────┘
                          ▼
                    RQ1 RETRIEVAL
             Recall@10 / Recall@50 / Recall@100
                          │
                          ▼
                  P_shared (UNION)
             P_lex ∪ P_sem ∪ P_cpc (No Hybrid in Pool)
                          │
                          ▼
                    HUMAN JUDGING
             G_d^pool = ground truth pool
                          │
                ┌─────────┼─────────┐
                ▼         ▼         ▼
              BM25      Dense     Hybrid
                │         │         │
                └─────────┼─────────┘
                          ▼
                     RQ2 RANKING
                       nDCG@10
                          │
                          ▼
                 H1: Hybrid vs Best
                Single-Signal Baseline
```

### 2.1 Research Questions (RQs)

* **RQ1 (First-Stage Candidate Retrieval Efficacy):** To what extent do individual retrieval strategies (lexical BM25, dense semantic representations, and automated/curated taxonomic classification search) succeed in retrieving technologically relevant domestic patent publications into candidate sets ($\mathcal{P}_{\text{lex}}, \mathcal{P}_{\text{sem}}, \mathcal{P}_{\text{cpc}}$), and where does complementarity among retrieval baselines occur when evaluated on pool-based recall ($\text{Recall}@K$ over the judged pool)?
* **RQ2 (Second-Stage Ranking & Early Precision):** Conditional on a shared, fixed candidate pool ($\mathcal{P}_{\text{shared}}$), which ranking strategy or multi-signal fusion approach places highly relevant patent publications at the top of the ranked list, optimizing early precision on our primary endpoint ($\text{nDCG}@10$) and secondary endpoints ($P@5$, $\text{MRR}$)?
* **RQ3 (Temporal & Jurisdictional Eligibility):** How does the strict enforcement of temporal prior-art eligibility (filtering patents published prior to the demand solicitation date) impact candidate pool yield and rank stability across distinct industrial sectors?
* **RQ4 (Domain Heterogeneity & Value of Human Curation):** Does matching efficacy vary systematically across distinct technological domains (e.g., consumer chemistry, industrial machinery/IoT, metallurgy, renewable energy storage), and how much measurable ranking gain ($\Delta_{\text{curation}} = \text{nDCG}_{\text{curated}} - \text{nDCG}_{\text{auto}}$) is added by expert-assisted classification curation ($C_d^{\text{curated}}$) over fully automated classification ($C_d^{\text{auto}}$)?

### 2.2 Formal Hypotheses & Primary/Secondary Endpoints

#### Endpoints Hierarchy:
* **Primary Endpoint:** $\text{nDCG}@10$ (Normalized Discounted Cumulative Gain at rank 10), evaluating graded technological relevance ($0$–$3$) and logarithmic rank discounting at the head of the ranked list.
* **Secondary Endpoints:** $\text{MRR}$ (Mean Reciprocal Rank), $P@5$, $P@10$, $\text{Recall}@10$, $\text{Recall}@50$ (pool-based recall).

#### Hypotheses & Invariance Rules:
* **Hypothesis 1 ($H_1$ — Primary Confirmatory Hypothesis on Hybrid Ranking Efficacy):**  
  The hybrid ranking strategy achieves a statistically significantly higher $\text{nDCG}@10$ than the **best single-signal baseline** ($S_{\text{best\_single}}$).  
  *Strict Comparator Selection Rule:* **The primary comparator $S_{\text{best\_single}}$ is determined exclusively from the Phase 2 development split ($\mathcal{D}_{\text{dev}}$)**, defined as:
  $$S_{\text{best\_single}} = \arg\max_{b \in \{\text{lex}, \text{sem}, \text{cpc}\}} \text{mean}_{d \in \mathcal{D}_{\text{dev}}}(\text{nDCG}@10_b)$$
  **The test split ($\mathcal{D}_{\text{test}}$) remains completely untouched until final evaluation.** Phase 1 results are used solely for methodological pipeline validation and cannot determine the primary comparator.  
  *Statistical Test:* Paired two-tailed Wilcoxon signed-rank test on $\mathcal{D}_{\text{test}}$ at pre-specified significance level $\alpha = 0.05$.  
  *Secondary Comparisons:* Comparisons of the hybrid strategy against the remaining individual baselines are treated as secondary analyses with Benjamini-Hochberg False Discovery Rate (FDR) multiplicity adjustment.
* **Hypothesis 2 ($H_2$ — Retrieval Complementarity in Candidate Generation):**  
  The union of dense semantic retrieval and taxonomic classification retrieval ($\mathcal{P}_{\text{sem}} \cup \mathcal{P}_{\text{cpc}}$) provides higher pool-based $\text{Recall}@50$ than lexical BM25 alone ($\mathcal{P}_{\text{lex}}$), evaluated on the independently judged candidate pool $\mathcal{G}_d^{\text{pool}}$.  
  *Exhaustive Union Breakdown:* To empirically pinpoint the exact source of retrieval complementarity, the study reports the complete family of recall metrics:
  $$\text{Recall}@K \in \{R_{\text{lex}}, R_{\text{sem}}, R_{\text{cpc}}, R_{\text{lex}\cup\text{sem}}, R_{\text{lex}\cup\text{cpc}}, R_{\text{sem}\cup\text{cpc}}, R_{\text{lex}\cup\text{sem}\cup\text{cpc}}\}$$
* **Exploratory Hypothesis / Secondary Analysis ($H_3$ — Signal Attribution across Domains):**  
  In exploratory ablation analysis, the relative marginal contribution of dense semantic similarity ($\Delta_{\text{sem}}$) will be higher in interdisciplinary or linguistically novel demands, whereas taxonomic CPC concordance ($\Delta_{\text{cpc}}$) will contribute more heavily in mature, highly standardized sectors with rigid chemical or metallurgical nomenclature.

---

## 3. Two-Phase Empirical Study Architecture

To ensure scientific integrity and eliminate the risk of premature claims or fabricated evidence, this study is strictly structured into two distinct sequential phases:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: METHODOLOGICAL VALIDATION & PILOT BENCHMARK                             │
│ • Dataset: Frozen ES Pilot-16 Patent Snapshot (15 publications) + 3 Verified     │
│   InnoGet Demands                                                                │
│ • Relevance Ground Truth: Partial judgment — 23 of 45 possible demand-patent    │
│   pairs annotated (see ADR 0006/0007 for the designed handling of unjudged      │
│   pairs via Judged@K and UNCERTAIN)                                             │
│ • Objective: Validate data pipelines, normalizers, candidate retrieval,         │
│   scoring algorithms, primary/secondary metric formulas, and audit trail.        │
│ • Scope: Methodological Proof-of-Harness (NO GENERAL SCIENTIFIC CLAIMS).        │
└────────────────────────────────────────┬─────────────────────────────────────────┘
                                         │ Validated pipeline & contracts
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: FULL EMPIRICAL STUDY & SCIENTIFIC EVALUATION                            │
│                                                                                  │
│   ┌───────────────────────────────────┐    ┌───────────────────────────────────┐ │
│   │        DEVELOPMENT SPLIT          │    │            TEST SPLIT             │ │
│   │ • S_cpc & Ranker Weight Tuning    │    │ • Completely untouched            │ │
│   │ • Selects S_best_single Baseline  │    │ • Final confirmatory inference    │ │
│   │ • Hyperparameter Optimization     │    │ • Primary test: Hybrid vs Best    │ │
│   └───────────────────────────────────┘    └───────────────────────────────────┘ │
│                                                                                  │
│ • Demand Sample Size (|D|): Sized via pre-registered Wilcoxon power analysis     │
│ • Patent Corpus (|P|): Scaled across OEPM domestic gazette publications          │
│ • Candidate Pool: Union of top-100 baselines (BM25, Semantic, CPC; NO HYBRID)   │
│ • Annotation: Blinded independent multi-expert annotation on G_d^pool            │
│ • Primary Metric: nDCG@10 (Hybrid vs. Best Single Baseline on Test Split)        │
│ • Secondary Metrics: MRR, P@5, P@10, Recall@10, Recall@50                        │
│ • Scope: Paper-Ready Evidence Base for World Patent Information.                │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Phase 1 — Methodological Validation / Pilot Benchmark
* **Purpose:** Verify the technical correctness of the end-to-end experimental apparatus.
* **Data Footprint:** The frozen, content-addressed `ES Pilot-16` corpus (15 verified OEPM publications) and 3 verified InnoGet demand calls, sealed under ADR 0006's byte-exact SHA-256 provenance model (`data/evaluation/dataset_pilot_benchmark.json`/`.manifest.json`/`.sha256`).
* **Relevance Assessment:** **Partial judgment** — 23 of the 45 possible demand-patent pairs (3 demands × 15 patents) are annotated, not exhaustive. This is not a shortfall to be corrected here: ADR 0007 defines `Judged@K` and the `UNCERTAIN` relevance grade specifically to make incomplete judgment an explicit, reportable epistemic state (`UNKNOWN != NEGATIVE`) rather than a silently absorbed one.
* **Deliverables:** Unit and integration verification, deterministic pipeline execution, cryptographic manifest auditing, automated calculation of $\text{nDCG}@10$, $P@K$, $R@K$, $\text{MRR}$, and automated machine-readable export (`json`/`csv`/`md`).
* **Reporting Boundary:** Phase 1 results are strictly reported as **methodological validation / pilot benchmark**. Phase 1 **must never be used to claim statistical superiority of one retrieval strategy over another**.

### 3.2 Phase 2 — Full Empirical Study
* **Purpose:** Provide the empirical evidence and statistical power necessary to answer RQ1–RQ4 and test $H_1$–$H_2$.
* **Reproducible *A Priori* Power Analysis Procedure:**
  * Because statistical hypothesis testing for $H_1$ is performed using the paired two-sided Wilcoxon signed-rank test across independent demands, sample size is determined through a reproducible simulation-based procedure.
  * **Pre-Registered Power Analysis Artifact:** An *a priori* power analysis is executed using the dedicated script:
    `scripts/power_analysis_wilcoxon.py`
  * **Simulation Parameters & Protocol:**
    * **Test Specification:** Paired two-sided Wilcoxon signed-rank test.
    * **Significance Level:** $\alpha = 0.05$.
    * **Target Statistical Power:** $1 - \beta = 0.80$.
    * **Standardized Effect Size:** $\theta = \text{median}(\Delta) / \text{IQR}(\Delta)$ for the paired $\text{nDCG}@10$ differences $\Delta = \text{nDCG}@10_{\text{hybrid}} - \text{nDCG}@10_{\text{best\_single}}$.
    * **Distributional Specification:** Zero-inflated continuous distribution bounded in $[-1, 1]$, modeling ties (zero differences) and skewed metric gains observed in IR benchmarks.
    * **Monte Carlo Iterations:** $B = 10,000$ simulation runs per candidate sample size.
    * **Random Seed:** Pinned at fixed initialization seed.
    * **Candidate Sample-Size Range:** Evaluated systematically across candidate grid $|\mathcal{D}| \in [15, 100]$.
    * **Decision Rule:** Select the minimum sample size $N_{\min} = \min \{N \mid \widehat{\text{Power}}(N) \ge 0.80\}$.
  * **Binding Rule:** The resulting minimum demand sample size $|\mathcal{D}|$ is frozen as a machine-readable pre-registered artifact **before inspecting any Phase 2 test outcomes**. No numerical $N$ is manually inserted into the protocol until the script is executed and verified.
  * **Patent Corpus Size ($|\mathcal{P}|$):** The patent corpus will be scaled across OEPM gazette publications to provide adequate candidate coverage and domain diversity.
* **Development vs. Test Split Protocol:**
  * Demands $\mathcal{D}$ are partitioned into a **Development Split ($\mathcal{D}_{\text{dev}}$)** (e.g., 40%) and a **Test Split ($\mathcal{D}_{\text{test}}$)** (e.g., 60%), stratified by industrial sector.
  * $\mathcal{D}_{\text{dev}}$ is used exclusively for tuning ranker weights $(\alpha, \beta, \gamma)$ and determining the primary comparator $S_{\text{best\_single}}$.
  * $\mathcal{D}_{\text{test}}$ remains completely untouched until final confirmatory evaluation.

---

## 4. Materials, Dataset Lineage & Provenance

### 4.1 Industrial Innovation Demands ($\mathcal{D}$)

* **Source Authority:** InnoGet Open Innovation Network & INDUSAC EU Horizon Project.
* **Extraction Protocol:** Structured API/web capture of demand solicitations with verified Spanish industrial enterprise participation or originating in Spain (`country == 'Spain'`).
* **Attributes per Demand Record ($d \in \mathcal{D}$):**
  * `id`: Canonical identifier (e.g., `INNOGET-2292`).
  * `title`: Concise title of the industrial need.
  * `description`: Expanded technological problem statement, operating parameters, and constraints.
  * `posted_date`: ISO 8601 publication date ($t_{\text{demand}}$).
  * `url`: Verifiable primary source hyperlink.
  * `sector`: Industrial domain classification (Consumer Chemistry, Sanitary/Materials, Industrial IoT/Energy, Metallurgy, Biotechnology, etc.).
* **Demand Inclusion Criteria:**
  1. Contains a substantive technical problem description (minimum 25 words).
  2. Identifies specific operational constraints or target technical metrics.
  3. Formally active or concluded with preserved archival record.
* **Demand Exclusion Criteria:**
  1. Pure business partnership or marketing requests lacking technical specifications.
  2. Solicitations with ambiguous or unidentifiable problem definitions.

### 4.2 Demand Classification Modalities: Automated ($C_d^{\text{auto}}$) vs. Expert-Assisted ($C_d^{\text{curated}}$)

To prevent data leakage, circularity, and unmeasured human curation bias, the assignment of CPC/IPC technological symbols to demands is formally structured into **two distinct, pre-registered modalities**:

```text
Demand Document d
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
[ Primary Modality: Automated Classification ]   [ Sensitivity Modality: Expert-Assisted Concordance ]
- Deterministic regex / concordance rules        - Pre-registered expert taxonomic review
- Zero human intervention during matching        - Fully blinded to model retrieval results
- Generates: C_d^(auto)                          - Generates: C_d^(curated)
- Primary baseline for all main comparisons      - Sensitivity configuration evaluating human curation
       │                                         │
       └────────────────────┬────────────────────┘
                            │
                            ▼
              [ Frozen Classification Schema ]
                 demand_cpc_mapping_audit.json
                            │
                            ▼
              Retrieval & Ranking Evaluation
```

1. **Primary Configuration — Automated Baseline ($C_d^{\text{auto}}$):** Fully automated, rule-based extraction derived solely from demand text $T_d$ using public WIPO/EPO concordance tables and deterministic regex mappings. This serves as the primary configuration for all confirmatory tests, evaluating an unassisted algorithmic pipeline.
2. **Sensitivity Configuration — Expert-Assisted Classification ($C_d^{\text{curated}}$):** Independent, pre-registered expert classification conducted by patent specialists blinded to model retrieval results. The study explicitly documents human effort (expert hours) to measure the empirical value of human curation:
   $$\Delta_{\text{curation}} = \text{nDCG}@10(S_{\text{cpc}}^{\text{curated}}) - \text{nDCG}@10(S_{\text{cpc}}^{\text{auto}})$$
   answering the research question of how much measurable value is added by human expert curation over fully automated taxonomic mapping.
3. **Audit Trail:** Every assigned classification records its rule, source keywords, and modality in `demand_cpc_mapping_audit.json`. Reclassification after inspecting retrieval results is strictly prohibited.

### 4.3 Domestic Patent Publications Corpus ($\mathcal{P}$)

* **Documentary Scope & Jurisdictional Definition:**
  * To eliminate legal and documentary ambiguity regarding *domestic patent publications*, the corpus is strictly restricted to official publications issued under the direct administrative jurisdiction of the Spanish Patent and Trademark Office (OEPM):
    1. **Spanish National Patents:** Granted patents and published applications under Ley de Patentes 24/2015 (`ES...A1`, `ES...B1`, `ES...B2`).
    2. **Spanish Utility Models (*Modelos de Utilidad*):** Published utility models (`ES...U`).
    3. **European Patent Translations Validated in Spain:** Strictly OEPM gazette publications of European patent translations (*traducciones de patentes europeas concedidas con efectos en España*, designated as `ES...T3`). Regional `EP...` publications without verified OEPM `ES...T3` national gazette publication numbers are excluded to maintain uniform national jurisdiction and language properties.
* **Source Authorities:**
  * Oficina Española de Patentes y Marcas (OEPM) — *Boletín Oficial de la Propiedad Industrial* (BOPI) open data portal.
  * European Patent Office (EPO) — Open Patent Services (OPS 3.2 API), filtered by OEPM national gazette concordance.
* **Temporal Coverage:** Document grant and publication dates between 2016-01-01 and 2024-12-31.
* **Attributes per Patent Document ($p \in \mathcal{P}$):**
  * `publication_id`: Canonical gazette publication number (e.g., `ES-2849102-B2`, `ES-2754890-T3`).
  * `application_number`: Official administrative filing number (e.g., `P202030431`).
  * `country_code`: Fixed national publication authority (`ES`).
  * `kind_code`: Gazette publication kind code (`A1`, `B1`, `B2`, `U`, `T3`).
  * `title`: Official title in Spanish.
  * `abstract`: Official patent abstract in Spanish.
  * `assignees`: Registered patent applicants / owners.
  * `inventors`: Certified inventors.
  * `filing_date`: Official application filing date ($t_{\text{file}}$).
  * `publication_date`: Official gazette publication date ($t_{\text{pub}}$).
  * `priority_date`: Earliest priority date claimed ($t_{\text{prio}}$).
  * `classifications_cpc`: Full list of assigned CPC symbols (subclass, main group, subgroup).
  * `classifications_ipc`: Full list of assigned IPC symbols.
  * `forward_citation_count`: Observed domestic/international forward citations ($f_p$). Strictly `None` if unobserved (`None != 0`).
  * `backward_citation_count`: Documented search report prior-art citations ($b_p$). Strictly `None` if unobserved.
  * `invenes_url`: Official OEPM Invenes database deep-link.
  * `verification_status`: Independent provenance verification state.

### 4.4 Content-Addressed Cryptographic Integrity

To guarantee absolute experimental reproducibility, all datasets are content-addressed:
* Raw source payloads are stored immutably with SHA-256 verification sidecars.
* Normalized datasets are written to Apache Parquet (`patents/part-0000.parquet`).
* A cryptographic manifest (`manifest.json`) records the exact sorted partition part hashes, total record counts, and canonical `dataset_content_sha256`.
* Prior to experiment execution, the runner recomputes the SHA-256 digest of the dataset file and terminates immediately upon any checksum mismatch.

---

## 5. Decoupled Two-Stage Methodology: Candidate Retrieval vs. Ranking

The experimental architecture strictly decouples **First-Stage Candidate Retrieval** from **Second-Stage Ranking/Fusion over a Shared Fixed Candidate Pool**:

### 5.1 Stage 1: Candidate Retrieval Efficacy (RQ1)

* **Objective:** Evaluate how effectively each independent first-stage baseline generates high-recall candidates from the full corpus $\mathcal{P}$.
* **Independent Candidate Sets:** For each demand $d$, generate the top-$N_{\text{retrieve}}$ documents ($N_{\text{retrieve}} = 100$ in Phase 2):
  * $\mathcal{P}_{\text{lex}}(d) = \text{top-}100 \text{ patents by } S_{\text{lex}}$
  * $\mathcal{P}_{\text{sem}}(d) = \text{top-}100 \text{ patents by } S_{\text{sem}}$
  * $\mathcal{P}_{\text{cpc}}(d) = \text{top-}100 \text{ patents by } S_{\text{cpc}}^{\text{auto}}$ (or $S_{\text{cpc}}^{\text{curated}}$ in sensitivity runs)
* **Independent Evaluation of Baselines and Uniones:** Report pool-based recall $\text{Recall}@K$ ($K \in \{10, 50, 100\}$) independently for each set and each pairwise/triplet union against judged pool $\mathcal{G}_d^{\text{pool}}$:
  $$\{R_{\text{lex}}, R_{\text{sem}}, R_{\text{cpc}}, R_{\text{lex}\cup\text{sem}}, R_{\text{lex}\cup\text{cpc}}, R_{\text{sem}\cup\text{cpc}}, R_{\text{lex}\cup\text{sem}\cup\text{cpc}}\}$$
* **Shared Pool Construction (No Hybrid Ranker in Pool Generation):**  
  The shared candidate pool for human judging and second-stage ranking is constructed strictly from the union of the first-stage retrieval baselines:
  $$\mathcal{P}_{\text{shared}}(d) = \mathcal{P}_{\text{lex}}(d) \cup \mathcal{P}_{\text{sem}}(d) \cup \mathcal{P}_{\text{cpc}}(d)$$
  > [!IMPORTANT]
  > **Strict Separation Rule — No Leakage from Hybrid Ranker:**  
  > The Hybrid Ranker ($S_{\text{hybrid}}$) **is strictly prohibited from contributing documents to $\mathcal{P}_{\text{shared}}(d)$ or the human annotation pool**. The candidate pool is fixed purely by the first-stage retrieval baselines. Stage 2 ranks this fixed candidate subset.

### 5.2 Stage 2: Second-Stage Ranking over the Shared Fixed Pool (RQ2)

* **Fairness Invariant:** To isolate ranking and fusion efficacy from retrieval pool composition, **all second-stage rankers score and rank the exact same candidate pool $\mathcal{P}_{\text{shared}}(d)$**. No ranking model is permitted to query outside $\mathcal{P}_{\text{shared}}(d)$.
* **Scoring Components within $\mathcal{P}_{\text{shared}}(d)$:**
  1. **Lexical Scoring ($S_{\text{lex}}$):** Okapi BM25 ($k_1 = 1.5, b = 0.75$) computed over Spanish-stemmed unigrams/bigrams, normalized via min-max scaling across $\mathcal{P}_{\text{shared}}(d)$ to $[0, 1]$.
  2. **Dense Semantic Scoring ($S_{\text{sem}}$):** Cosine similarity between dense embeddings ($\mathbf{e}_d, \mathbf{e}_p$) computed using multilingual sentence transformer (`paraphrase-multilingual-mpnet-base-v2`). Scaled monotonically to $[0, 1]$ ($S_{\text{sem}}^{\text{norm}} = (S_{\text{sem}} + 1) / 2$) strictly for range compatibility in additive linear fusion.
  3. **Taxonomic CPC Scoring ($S_{\text{cpc}}^{\text{auto}}$ and $S_{\text{cpc}}^{\text{curated}}$):** Hierarchical concordance:
     $$S_{\text{cpc}}(d, p) = \max_{c_1 \in C_d, c_2 \in C_p} \text{sim}_{\text{CPC}}(c_1, c_2)$$
     $$\text{sim}_{\text{CPC}}(c_1, c_2) = \begin{cases} 
     1.00 & \text{if full subgroup match (e.g. } C11D1/02 = C11D1/02) \\ 
     0.75 & \text{if main group match (e.g. } C11D1 = C11D1) \\ 
     0.50 & \text{if subclass match (e.g. } C11D = C11D) \\ 
     0.25 & \text{if section match (e.g. } C = C) \\ 
     0.00 & \text{otherwise} 
     \end{cases}$$
     *Primary Ranking Configuration:* Employs $S_{\text{cpc}}^{\text{auto}}(d, p)$.  
     *Sensitivity Ranking Configuration:* Employs $S_{\text{cpc}}^{\text{curated}}(d, p)$.
  4. **Hybrid Ranker ($S_{\text{hybrid}}$):** Linear combination:
     $$S_{\text{hybrid}}(d, p) = \alpha \cdot S_{\text{lex}}(d, p) + \beta \cdot S_{\text{sem}}(d, p) + \gamma \cdot S_{\text{cpc}}^{\text{auto}}(d, p)$$
     *Phase 1:* Heuristic pilot weights $\alpha = 0.35, \beta = 0.45, \gamma = 0.20$.  
     *Phase 2:* Weights tuned strictly on $\mathcal{D}_{\text{dev}}$ via 5-fold cross-validation grid search ($\alpha + \beta + \gamma = 1.0; \alpha, \beta, \gamma \ge 0$), and applied frozen to $\mathcal{D}_{\text{test}}$.

### 5.3 Patent Eligibility Rules & Temporal Prior-Art Criterion

The protocol strictly enforces:
1. **Jurisdiction Eligibility:** $p.\text{country\_code} == \text{'ES'}$.
2. **Text Availability:** $p.\text{abstract} \neq \emptyset \land p.\text{title} \neq \emptyset$.
3. **Temporal Prior-Art Eligibility Rule ($\Phi_{\text{temporal}}$):**
   $$\Phi_{\text{temporal}}(p, d) = \begin{cases} 1 & \text{if } t_{\text{pub}, p} < t_{\text{demand}, d} \\ 0 & \text{otherwise} \end{cases}$$
   Evaluated both with strict temporal filtering ($\mathcal{P}_{\text{eligible}} = \{p \in \mathcal{P} \mid \Phi_{\text{temporal}}(p, d) = 1\}$) and unconstrained matching to measure temporal yield degradation.

---

## 6. Definition of Technological Relevance & Expert Annotation Protocol

### 6.1 Crucial Scientific Distinction: Technological Relevance vs. Legal Validity

> [!IMPORTANT]
> This protocol explicitly and strictly differentiates **Technological Relevance** from **Legal Patentability (Novelty / Inventive Step)**.
> 
> * **Technological Relevance:** The degree to which a patent document discloses technical mechanisms, formulations, structures, or methodologies that address, overlap with, or teach solutions relevant to the technological requirements articulated in an industrial demand.
> * **Legal Novelty / Inventive Step:** Formal judicial and administrative determinations governed by statutory criteria (e.g., EPC Articles 52, 54, 56; Ley de Patentes 24/2015 Arts. 4, 6, 8) requiring strict single-document novelty destruction (*lack of novelty*) or non-obviousness over cumulative state of the art to a person skilled in the art.
> 
> **Scientific Assertion Rule:** The paper shall **never** claim that algorithmic matches determine legal invalidity, patentability, or freedom-to-operate, unless accompanied by certified judicial or patent attorney examinations. All metrics evaluate **information retrieval for technological problem-solution alignment**.

### 6.2 Graded Technological Relevance Scale (0–3)

Each demand–patent pair $(d, p)$ is evaluated on an ordinal 4-level scale ($g \in \{0, 1, 2, 3\}$). In addition, human annotators may assign an administrative state `UNCERTAIN` which is kept strictly outside the numerical scoring scale.

| Relevance Grade ($g$) | Descriptive Category | Detailed Operational Definition | Example in Corpus |
|---|---|---|---|
| **0** | **Irrelevant** | No discernible technological relationship. Patent operates in an unrelated domain and shares no applicable functional mechanism. | Demand: Liquid detergent (`C11D`).<br>Patent: Brass alloy machining (`C22C`). |
| **1** | **Domain / Sector Related** | Belongs to the broader industrial domain or sector, but discloses no technical solution or mechanism that addresses the demand's specific functional requirements. | Demand: Low-temperature detergent (`C11D`).<br>Patent: Microencapsulation of fragrance (`C11D3/50`) without surfactant cleaning activity. |
| **2** | **Technologically Relevant** | Substantive technological overlap. Discloses materials, processes, or systems that partially address the technical problem, or provide related technical teachings. | Demand: Kitchen sink greywater recycling (`E03C`).<br>Patent: Smart sink with proximity sensor and thermal control (`ES-2901234-A1`). |
| **3** | **Directly Addressing Demand** | Direct technological alignment. Discloses solutions, operating parameters, formulations, or architectures that directly tackle the primary technical requirements of the demand. | Demand: Cold-water biodegradable detergent (`INNOGET-2292`).<br>Patent: Liquid enzymatic biodegradable detergent for room-temperature wash (`ES-2849102-B2`). |
| *N/A* | **`UNCERTAIN`** | *Annotation State Only (Outside 0–3 Scale).* Assigned when disclosure ambiguity, missing full-text specifications, or conflicting domain interpretations preclude definitive scoring. Follows formal adjudication protocol. | Patent document with incomplete abstract or ambiguous claims under review. |

### 6.3 Mathematical Treatment & Resolution of `UNCERTAIN` Annotations

To ensure mathematical rigor and prevent annotator ambiguity from distorting quantitative evaluation:

```text
[ Initial Annotation: UNCERTAIN ]
               │
               ▼
   [ Expert Adjudication Loop ]
  Senior Patent Examiner / Lead Reviewer
               │
       ┌───────┴───────┐
       ▼               ▼
 Resolved?        Unresolved?
       │               │
       ▼               ▼
Assign g in {0,1,2,3}  [ STRICT PROTOCOL ]:
                       1. Exclude from primary benchmark calculation.
                       2. Document separately in annotation audit trail.
                       3. Include in sensitivity analysis (worst-case g=0 vs best-case g=1).
                       4. NEVER convert automatically to false 0.
```

1. **Resolution Step:** All `UNCERTAIN` assignments are submitted to an independent senior patent examiner / lead researcher for adjudication.
2. **Persistent Uncertainty Rule:** If adjudication cannot definitively resolve the technological relevance (e.g., due to unverified translation or missing claim specifications), the pair is **excluded from primary metric computation ($\text{nDCG}@10$, $P@K$, $\text{MRR}$)**.
3. **Audit & Sensitivity Reporting:** Unresolved items are reported explicitly in the annotation log and subjected to bounding sensitivity analysis (evaluating impact under lower bound $g=0$ versus upper bound $g=1$). **Under no circumstances is an unresolved `UNCERTAIN` record silently imputed as `0` in the primary ground truth.**

### 6.4 Blinded Independent Annotation Protocol & Disagreement Adjudication

1. **Candidate Pool Construction (Judged Pool $\mathcal{G}_d^{\text{pool}}$):**
   * The candidate pool for human annotation in Phase 2 is formed strictly by pooling and deduplicating the top-$K_{\text{pool}}$ ($K_{\text{pool}} = 100$) candidates from the first-stage retrieval baselines: $\mathcal{P}_{\text{lex}} \cup \mathcal{P}_{\text{sem}} \cup \mathcal{P}_{\text{cpc}}$. The hybrid ranker does not contribute to pool generation.
   * In Phase 1, $|\mathcal{P}| = 15$; the sealed annotation set covers 23 of the 45 possible demand-patent pairs (partial, not exhaustive — see ADR 0006/0007 for the designed treatment of unjudged pairs via $Judged@K$).
2. **Blinded Independent Annotation Procedure:**
   * Each demand–patent pair in the pool is evaluated independently by at least two domain experts (patent information specialists / engineers).
   * **Blinding Standard:** Annotators are strictly blinded to the retrieval method, model scores, and ranking provenance.
3. **Inter-Annotator Agreement (IAA) Metrics:**
   * **Cohen's Kappa ($\kappa$):** Computed for binary relevance ($g \ge 2$ vs. $g < 2$).
   * **Weighted Cohen's Kappa ($\kappa_w$) / Fleiss' Kappa:** Computed with quadratic weights to penalize larger grade discrepancies on the ordinal 0–3 scale.
   * **Threshold for Scientific Validity:** Minimum required agreement $\kappa_w \ge 0.70$.
4. **Disagreement Adjudication Standard:**
   * **Disagreements of one grade** (e.g., Annotator A assigns 2, Annotator B assigns 3) are **never averaged** into non-integer artificial scores. They are resolved through independent re-review and discussion; the final adjudicated integer grade is recorded.
   * **Disagreements of $\ge 2$ grades**, or where an annotator records `UNCERTAIN`, are referred directly to a senior patent examiner / lead researcher for binding integer adjudication.

---

## 7. Evaluation Metrics & Statistical Testing

### 7.1 Information Retrieval Metrics

For each query demand $d \in \mathcal{D}$ yielding a ranked list $L_d = [p_1, p_2, \dots, p_K]$:

#### 1. Primary Endpoint: Normalized Discounted Cumulative Gain at $K=10$ ($\text{nDCG}@10$)
Evaluates graded relevance with logarithmic rank discount:
$$\text{DCG}@K(d) = \sum_{i=1}^K \frac{2^{g(d, p_i)} - 1}{\log_2(i + 1)}, \quad \text{nDCG}@K(d) = \frac{\text{DCG}@K(d)}{\text{IDCG}@K(d)}$$
where $\text{IDCG}@K(d)$ is the ideal DCG obtained by sorting the ground truth pool by descending grade $g \in \{0, 1, 2, 3\}$.

> [!IMPORTANT]
> **Mathematical Treatment of Demands with No Relevant Documents ($\text{IDCG} = 0$):**  
> If for a given demand query $d$, the judged pool contains zero relevant documents ($g < 2$ for all candidates, yielding $\text{IDCG}@K(d) = 0$), $\text{nDCG}@K(d)$ is mathematically **undefined ($0/0$)**.
> 
> *Strict Protocol:* Such demands are **excluded from the primary $\text{nDCG}@10$ macro-average**, and the exact number of excluded zero-relevant queries is reported explicitly in the results table. As a sensitivity check, alternative imputations ($\text{nDCG} = 0.0$ and $\text{nDCG} = 1.0$) are evaluated and reported in supplementary materials.

#### 2. Secondary Endpoint: Precision at $K$ ($P@K$)
Measures the proportion of technologically relevant documents in the top $K$ retrieved:
$$P@K(d) = \frac{1}{K} \sum_{i=1}^K \mathbb{I}(g(d, p_i) \ge \tau)$$
* **Primary Relevance Threshold:** $\tau = 2$ (Technologically relevant or directly addressing).
* **Sensitivity Threshold:** $\tau = 3$ (Strictly directly addressing).
* Evaluated at $K \in \{5, 10\}$.

#### 3. Secondary Endpoint: Pool-Based Recall at $K$ ($\text{Recall}@K$)

Measures the fraction of technologically relevant documents in the judged pool $\mathcal{G}_d^{\text{pool}}$ retrieved in the top $K$:
$$\text{Recall}@K(d) = \frac{\sum_{i=1}^K \mathbb{I}(g(d, p_i) \ge \tau)}{|\{p \in \mathcal{G}_d^{\text{pool}} \mid g(d, p) \ge \tau\}|}$$

> [!IMPORTANT]
> **Mathematical Treatment of Zero-Relevant Ground-Truth Pool:**  
> If for a given demand query $d$, the judged pool contains zero relevant documents ($|\{p \in \mathcal{G}_d^{\text{pool}} \mid g(d, p) \ge \tau\}| = 0$), the denominator is zero, and pool-based recall is **mathematically undefined**.
> 
> *Strict Protocol:* Such demands are **excluded from the primary macro-averaged $\text{Recall}@K$**. The protocol strictly forbids silently imputing $\text{Recall} = 0$. The exact count of excluded zero-relevant demands is reported transparently and separately for each relevance threshold ($\tau = 2$ and $\tau = 3$).

* Evaluated at $K \in \{10, 50\}$.

#### 4. Secondary Endpoint: Mean Reciprocal Rank ($\text{MRR}$)

Measures the speed at which the first relevant document is encountered:
$$\text{RR}(d) = \begin{cases} 
\frac{1}{\min \{i \mid g(d, p_i) \ge \tau\}}, & \text{if at least one relevant document is retrieved in } L_d \\ 
0, & \text{otherwise} 
\end{cases}$$

$$\text{MRR} = \frac{1}{|\mathcal{D}|} \sum_{d \in \mathcal{D}} \text{RR}(d)$$

> [!NOTE]
> **Zero-Relevant Result Behavior for MRR:**  
> When no relevant document is retrieved in the ranked list for demand $d$, $\text{RR}(d)$ is explicitly defined as $0.0$. Consequently, **no demand is excluded from the $\text{MRR}$ macro-average merely because no relevant document is retrieved**.

### 7.2 Statistical Significance & Confidence Intervals

* **Mean Metric Estimation:** Macro-averaged across evaluated demands $d \in \mathcal{D}_{\text{test}}$.
* **Paired Bootstrap Confidence Intervals:** 95% bootstrap confidence intervals computed by resampling **complete demand queries** (with replacement, 10,000 resamples), preserving the paired performance observations of all evaluated methods across each demand. Individual patents are never resampled in isolation.
* **Primary Hypothesis Testing ($H_1$):**
  * Paired two-tailed **Wilcoxon signed-rank test** comparing $\text{nDCG}@10$ of the hybrid strategy against $S_{\text{best\_single}}$ (selected exclusively on $\mathcal{D}_{\text{dev}}$) evaluated on $\mathcal{D}_{\text{test}}$ at $\alpha = 0.05$.
  * **Multiplicity Correction:** Comparisons of the hybrid strategy against other individual baselines are adjusted using the Benjamini-Hochberg procedure controlling the False Discovery Rate (FDR) at $\alpha = 0.05$.

---

## 8. Ablation Study Design

To rigorously quantify the marginal contribution of each information signal, the evaluation harness executes systematic signal ablations against the full hybrid model over the shared fixed candidate pool $\mathcal{P}_{\text{shared}}$:

### 8.1 Frozen Full-Model Weights Protocol for Phase 2

1. The full Hybrid model weights $(\alpha, \beta, \gamma)$ are tuned exclusively on the Development Split $\mathcal{D}_{\text{dev}}$ using the automated configuration ($M_0$).
2. These weights $(\alpha, \beta, \gamma)$ are permanently frozen prior to test evaluation.
3. The baseline full Hybrid model $M_0$ is evaluated on the Test Split $\mathcal{D}_{\text{test}}$ using these frozen weights.
4. For component ablations $M_1$, $M_2$, and $M_3$, the specified signal is removed while **retaining the corresponding remaining $M_0$ weights** without re-normalizing or re-optimizing on the test set.
5. For the expert-assisted sensitivity hybrid configuration ($M_0^{\text{curated}}$), the model evaluates $\alpha \cdot S_{\text{lex}} + \beta \cdot S_{\text{sem}} + \gamma \cdot S_{\text{cpc}}^{\text{curated}}$ using **the exact same frozen weights $(\alpha, \beta, \gamma)$ obtained on $\mathcal{D}_{\text{dev}}$ for $M_0$**, substituting only $S_{\text{cpc}}^{\text{auto}}$ with $S_{\text{cpc}}^{\text{curated}}$ without any re-optimization.
6. **No independent test-set re-tuning** is performed for any ablation or sensitivity configuration.

### 8.2 Ablation Matrix

| Configuration ID | Active Signals | Weight Specification on $\mathcal{D}_{\text{test}}$ | Research Purpose |
|---|---|---|---|
| **$M_0$ (Full Hybrid)** | $S_{\text{lex}} + S_{\text{sem}} + S_{\text{cpc}}^{\text{auto}}$ | $\alpha \cdot S_{\text{lex}} + \beta \cdot S_{\text{sem}} + \gamma \cdot S_{\text{cpc}}^{\text{auto}}$ (frozen from $\mathcal{D}_{\text{dev}}$) | Primary baseline full tripartite model. |
| **$M_0^{\text{curated}}$ (Curated Hybrid)** | $S_{\text{lex}} + S_{\text{sem}} + S_{\text{cpc}}^{\text{curated}}$ | $\alpha \cdot S_{\text{lex}} + \beta \cdot S_{\text{sem}} + \gamma \cdot S_{\text{cpc}}^{\text{curated}}$ (identical frozen weights $\alpha, \beta, \gamma$) | Sensitivity configuration evaluating human curation value ($\Delta_{\text{curation}}$). |
| **$M_1$ ($\text{No-CPC}$)** | $S_{\text{lex}} + S_{\text{sem}}$ | $\alpha \cdot S_{\text{lex}} + \beta \cdot S_{\text{sem}}$ (un-renormalized, frozen weights) | Evaluates marginal loss from omitting classification signal. |
| **$M_2$ ($\text{No-Semantic}$)** | $S_{\text{lex}} + S_{\text{cpc}}^{\text{auto}}$ | $\alpha \cdot S_{\text{lex}} + \gamma \cdot S_{\text{cpc}}^{\text{auto}}$ (un-renormalized, frozen weights) | Evaluates marginal loss from omitting dense embedding signal. |
| **$M_3$ ($\text{No-Lexical}$)** | $S_{\text{sem}} + S_{\text{cpc}}^{\text{auto}}$ | $\beta \cdot S_{\text{sem}} + \gamma \cdot S_{\text{cpc}}^{\text{auto}}$ (un-renormalized, frozen weights) | Evaluates marginal loss from omitting keyword token signal. |
| **$M_4$ ($\text{BM25 Only}$)** | $S_{\text{lex}}$ | $1.0 \cdot S_{\text{lex}}$ | Isolated lexical baseline. |
| **$M_5$ ($\text{Dense Only}$)** | $S_{\text{sem}}$ | $1.0 \cdot S_{\text{sem}}$ | Isolated embedding baseline. |
| **$M_6$ ($\text{CPC Auto Only}$)** | $S_{\text{cpc}}^{\text{auto}}$ | $1.0 \cdot S_{\text{cpc}}^{\text{auto}}$ | Isolated automated taxonomic baseline. |
| **$M_6^{\text{curated}}$ ($\text{CPC Curated Only}$)**| $S_{\text{cpc}}^{\text{curated}}$ | $1.0 \cdot S_{\text{cpc}}^{\text{curated}}$ | Isolated expert-assisted taxonomic baseline. |

**Ablation Attribution Metric:**
$$\Delta_X = \text{nDCG}@10(M_0) - \text{nDCG}@10(M_0 \setminus X)$$

> [!NOTE]
> **Scientific Interpretation Rule for $\Delta_X$:**  
> $\Delta_X$ measures the observed marginal contribution of removing signal $X$ **under the frozen full-model configuration**. This design explicitly isolates the contribution of each signal under the selected full-model weighting rather than estimating the independently optimized performance of a reduced architecture. Statistical uncertainty and cross-validation variability are reported separately; $\Delta_X > 0$ does not constitute a claim of universal causal necessity.

---

## 9. Error-Analysis Methodology (False Positives & False Negatives)

To provide qualitative depth suitable for *World Patent Information*, the empirical pipeline includes a structured diagnostic protocol for ranking discrepancies:

1. **False Positive ($\text{FP}$) Analysis (High Rank, Low Relevance):**
   * *Definition:* A patent ranked in the top 5 ($i \le 5$) with annotated ground-truth grade $g \le 1$.
   * *Categorization Taxonomy:*
     * **Lexical Polysemy / Spurious Overlap:** High word overlap with differing conceptual context (e.g., "cell" in biology vs. "battery cell").
     * **Over-Broad Classification:** Matching a high-level CPC code (e.g., general `G05B`) that fails to capture specialized functional constraints.
     * **Defensive Abstract Generalization:** Patent abstract intentionally vague or overly expansive, misleading dense semantic similarity.
2. **False Negative ($\text{FN}$) Analysis (Low Rank, High Relevance):**
   * *Definition:* A patent annotated with $g \ge 2$ that fails to appear in top 10 ($i > 10$).
   * *Categorization Taxonomy:*
     * **Patent-Domain Terminology Mismatch:** Demand uses colloquial industry jargon; patent uses formal patentese.
     * **Missing / Incomplete Classification:** Relevant patent classified under an unexpected secondary CPC group.
     * **Semantic Embedding Compression Loss:** Fine numerical thresholds or chemical details compressed out by dense sentence encoders.

---

## 10. Threats to Validity & Limitations

### 10.1 Internal Validity
* **Annotator Subjectivity:** Addressed via blinded independent evaluation, explicit 0–3 scoring rubrics with concrete examples, strict `UNCERTAIN` resolution protocol, non-averaging adjudication, and reporting of Kappa statistics.
* **Hyperparameter Tuning Bias:** Mitigated by tuning hybrid weights strictly on $\mathcal{D}_{\text{dev}}$ and freezing them before evaluating $\mathcal{D}_{\text{test}}$.

### 10.2 External Validity
* **Jurisdictional Focus:** The empirical study focuses on Spanish domestic publications (`ES` jurisdiction). While OEPM follows EPO examination guidelines and CPC classification standards, generalization to other jurisdictions (e.g., USPTO, JPO) requires further cross-jurisdiction validation.
* **Corpus Scale & Demand Sample Size:** The Phase 1 pilot corpus ($N=15$, partially annotated) represents an initial validation benchmark; Phase 2 sizes demands $|\mathcal{D}|$ via power analysis for paired non-parametric testing and scales corpus $|\mathcal{P}|$ for broad sector coverage.

### 10.3 Construct Validity
* **Relevance as a Proxy:** Technological relevance does not guarantee commercial feasibility, freedom to operate, or legal novelty. The paper explicitly clarifies this construct boundary.

---

## 11. Reproducibility Protocol & Artifact Standards

Every reported table, figure, and metric in the paper must be 100% reproducible by a third-party reviewer without manual editing:

```text
[Dataset Snapshot (Parquet + Manifest SHA-256)]
                     │
                     ▼
        [Frozen Experiment Config (YAML)]
                     │
                     ▼
           [Execution Runner (Python)]
                     │
                     ▼
          [Raw Result Logs (JSON/JSONL)]
                     │
                     ▼
    [Aggregate Metric Tables & Latex Snippets (CSV/MD)]
```

### Reproducibility Verification Standards:
1. **Source Tracking:** Git commit SHA recorded in all output metadata.
2. **Data Immutability:** SHA-256 hash verified before running.
3. **Execution Determinism & Environment Capture:** Random seeds are fixed where applicable; model versions, tokenizer versions, dependency lockfiles, hardware/runtime configurations, and deterministic execution flags are explicitly recorded in `metadata.json`.
4. **Zero Fabrication Guarantee:** If real datasets or expert ground truth are missing or incomplete, the pipeline halts with an explicit blocker notice rather than synthesizing mock evidence.

---

## 12. Paper Output Mapping to Elsevier Manuscript Structure

The machine-generated outputs of this protocol directly map to the standard *World Patent Information* structure:

1. **Section 1: Introduction** $\rightarrow$ Motivation, RQs (candidate retrieval vs. ranking), and distinction between technological matching and legal novelty.
2. **Section 2: Related Work** $\rightarrow$ Patent retrieval, semantic patent search, open innovation intermediaries.
3. **Section 3: Materials & Data** $\rightarrow$ Dataset statistics table, InnoGet demand lineage, OEPM domestic corpus provenance (national patents, utility models, and ES translations of EPs), and cryptographic verification.
4. **Section 4: Methodology** $\rightarrow$ Automated vs. curated demand classification, independent candidate retrieval, shared fixed candidate pool (no hybrid in pool), BM25, MPNet, CPC concordance, and hybrid ranking algorithms.
5. **Section 5: Experimental Setup** $\rightarrow$ Two-phase architecture, power analysis procedure for $|\mathcal{D}|$, pooling annotation protocol ($K_{\text{pool}}=100$), IAA $\kappa$, pool-based recall definitions, IDCG=0 exclusion rules, and primary/secondary endpoints.
6. **Section 6: Results** $\rightarrow$ Primary confirmatory endpoint ($\text{nDCG}@10$ of Hybrid vs. Best Single Baseline on test set), secondary metrics ($P@K, \text{MRR}, \text{Recall}@K$), paired bootstrap confidence intervals, Wilcoxon $p$-values, and ablation tables.
7. **Section 7: Discussion & Cross-Sector Analysis** $\rightarrow$ Sectoral performance breakdown ($C11D, E03C, G05B, C22C, H01M, C08L$).
8. **Section 8: Error Analysis** $\rightarrow$ Qualitative review of top false positives and false negatives (patent-domain terminology mismatch, classification breadth, embedding loss).
9. **Section 9: Threats to Validity & Limitations** $\rightarrow$ Internal, external, and construct validity discussions.
10. **Section 10: Conclusions & Future Work** $\rightarrow$ Summary of findings, implications for open innovation brokers and national IP offices.
