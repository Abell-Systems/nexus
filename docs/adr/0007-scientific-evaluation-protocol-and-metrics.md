# ADR 0007: Scientific Evaluation Protocol and Metrics for Matching Validation

**Status:** Accepted  
**Date:** 2026-09-03  
**Scope:** `domain/models/evaluation`, `domain/protocols/evaluation`, `application/evaluation`, `infrastructure/evaluation`  

---

## Context

Under ADR 0004 (Matching Engine Contract & Evidence Assessment), ADR 0005 (Explicit Policy Injection & No Implicit Configuration), and ADR 0006 (Scientific Validation Dataset, Schema, and Evaluation Provenance), Nexus formalizes a strict decoupling between:
1. Authentic observed facts from primary patent and demand sources (`DataModality.OBSERVED`),
2. Versioned, externalized matching policies (`MatchingPolicyConfig`),
3. Cryptographically sealed, immutable evaluation datasets (`ValidatedDataset`), and
4. The deterministic matching engine (`MatchingEngine`).

While ADR 0006 provided the schema, integrity loader, and pilot corpus for evaluation datasets, it intentionally postponed the **evaluation execution protocol**, the **formal treatment of human annotation grades**, and the **mathematical definition of evaluation metrics**.

Without a binding engineering and scientific contract for the evaluation protocol:
1. **Ad-hoc or Shifting Relevance Binarization:** Developers might opportunistically adjust the threshold of what counts as "relevant" (e.g. including grade 1 as positive to artificially inflate recall, or excluding grade 2 to artificially inflate precision).
2. **Improper Handling of Epistemic Uncertainty (`UNCERTAIN`):** Treating annotator uncertainty (`RelevanceGrade.UNCERTAIN = -1`) as a negative/irrelevant label commits an epistemic fallacy (`UNKNOWN != NEGATIVE`), biasing evaluation metrics.
3. **Loss of Scientific Provenance:** Evaluation results produced without recording the exact Git commit, dataset SHA-256, and policy SHA-256 cannot be independently audited or reproduced.
4. **Coupling to Filesystem & Engine Corruption:** If the evaluation runner or metrics calculator accesses the filesystem directly, loads default files, or modifies the engine/policy to obtain higher scores, the benchmark ceases to be an independent measurement instrument.

---

## Decision

### 1. Fundamental Principle of Metric and Runner Independence

> **The evaluator is an independent auditor, not a component of the matching engine.**

1. The evaluation suite MUST measure the matching engine from the outside via explicit dependency injection.
2. The evaluator MUST NOT modify the benchmark dataset, fabricate labels, adjust policy parameters, or alter engine heuristics to improve scores.
3. Metrics calculation MUST be housed in an independent module decoupled from `domain/models/matching.py` and `application/matching/`.

---

### 2. Evaluation Unit and Alignment Pairs

The fundamental unit of evaluation is the **Demand-Patent Evaluation Item** $(d, p) \in \mathcal{D} \times \mathcal{P}$:
* A demand $d \in \mathcal{D}$ represents an authentic technological need.
* A candidate patent $p \in \mathcal{P}$ represents a published invention assessed against demand $d$.
* The ground of comparison is the set of expert annotations $\mathcal{A}$ associated with $(d, p)$, declared under `DataModality.EXPERT_LABELLED`.

---

### 3. Relevance Grade Semantics & Dual Operational Thresholds

Under ADR 0006, `RelevanceGrade` defines a 4-point discrete ordinal scale plus epistemic uncertainty:
* **Grade 0 (`IRRELEVANT`):** Out of domain, or unrelated technology.
* **Grade 1 (`DOMAIN_RELATED`):** Same technological sector, but does not solve the specific technical problem posed in the demand.
* **Grade 2 (`TECHNOLOGICALLY_RELEVANT`):** Substantively addresses core problem components, analogous mechanisms, or direct technical dependencies.
* **Grade 3 (`DIRECTLY_ADDRESSING`):** Directly targets the specific technical solution sought by the demand.
* **Grade -1 (`UNCERTAIN`):** Ambiguous prior art or insufficient expert consensus requiring deeper investigation.

To prevent opportunistic goalpost-shifting, Nexus defines two canonical, deterministic binary projections:

1. **Strict Target Alignment ($\tau_{\text{strict}}$):**
   $$\text{IsRelevant}_{\text{strict}}(g) = \begin{cases} \text{True} & \text{if } g = 3 \\ \text{False} & \text{if } g \in \{0, 1, 2\} \end{cases}$$
2. **Broad Technological Alignment ($\tau_{\text{broad}}$):**
   $$\text{IsRelevant}_{\text{broad}}(g) = \begin{cases} \text{True} & \text{if } g \in \{2, 3\} \\ \text{False} & \text{if } g \in \{0, 1\} \end{cases}$$

No in-code heuristic may invent custom thresholds outside these two canonical definitions.

---

### 4. Epistemological Invariant: Strict Treatment of `UNCERTAIN` (-1)

Under the core invariant **`UNKNOWN != NEGATIVE`** (ADR 0003, AGENTS.md §3):
1. Pairs labeled `RelevanceGrade.UNCERTAIN` (-1) represent absence of definitive expert evidence, NOT confirmed negative relevance.
2. For all standard precision, recall, and ranking metrics, items with grade `UNCERTAIN` MUST be **excluded from both true-positive and false-positive evaluation tallies**.
3. Every evaluation report MUST explicitly compute and report the **Uncertainty Rate** ($\text{UncertaintyRate} = \frac{|\mathcal{A}_{\text{uncertain}}|}{|\mathcal{A}|}$) as a primary epistemic health metric.
4. Any evaluation implementation that silently coerces `UNCERTAIN` to $0$ or treats it as negative is non-compliant and MUST raise an architectural test failure.

---

### 5. Primary and Secondary Evaluation Metrics

The evaluation protocol calculates deterministic metrics per demand $d$ and aggregates them macro-averaged across all demands:

#### Primary Metrics
1. **Precision@K ($P@K$):** Proportion of top-$K$ ranked patents that are relevant under threshold $\tau$:
   $$P@K = \frac{|\{p \in \text{TopK}(d) : \text{IsRelevant}(p)\}|}{K}$$
   Canonical evaluation MUST report $P@1$, $P@3$, and $P@5$.
2. **Recall@K ($R@K$):** Proportion of all known relevant patents for demand $d$ retrieved in the top-$K$:
   $$R@K = \frac{|\{p \in \text{TopK}(d) : \text{IsRelevant}(p)\}|}{|\{p \in \mathcal{P}_d : \text{IsRelevant}(p)\}|}$$
3. **Mean Reciprocal Rank (MRR):** Reciprocal rank of the first relevant candidate:
   $$\text{RR}(d) = \frac{1}{\min \{ \text{rank}(p) : p \in \text{TopK}(d) \land \text{IsRelevant}(p) \}}$$
   ($\text{RR} = 0.0$ if no relevant candidate is ranked).
4. **Normalized Discounted Cumulative Gain (nDCG@K):** Evaluates multi-level graded relevance ($g \in \{0, 1, 2, 3\}$) using logarithmic discount:
   $$\text{DCG}@K = \sum_{i=1}^K \frac{2^{g_i} - 1}{\log_2(i + 1)}, \quad \text{nDCG}@K = \frac{\text{DCG}@K}{\text{IDCG}@K}$$

#### Secondary Metrics
1. **Sufficiency Pass Rate:** Percentage of top-$K$ candidates classified as `EvidenceSufficiency.SUFFICIENT` by the engine.
2. **Uncertainty Coverage Rate:** Fraction of evaluation pairs flagged as `UNCERTAIN`.

---

### 6. Architecture of the Evaluation Runner (`EvaluationRunner`)

The runner executes as an independent application-layer orchestrator:

```text
┌─────────────────────────────────────────────────────────────┐
│                    EvaluationRunner                         │
│                                                             │
│ Inputs (Explicit Injection ONLY):                           │
│   - dataset: ValidatedDataset                               │
│   - engine: MatchingEngine                                  │
│   - policy: MatchingPolicyConfig                            │
│                                                             │
│ Execution:                                                  │
│   For each demand in dataset.dataset.demands:               │
│     1. Construct CandidatePool from dataset.patents         │
│     2. Invoke engine.evaluate(demand, pool, policy)         │
│     3. Align engine MatchAssessments with annotations       │
│     4. Compute per-demand metrics (P@K, R@K, MRR, nDCG@K)   │
│   Compute macro-averaged summary                            │
│                                                             │
│ Output:                                                     │
│   EvaluationRunReport (Frozen, Full Provenance Audit)       │
└─────────────────────────────────────────────────────────────┘
```

#### Invariants of `EvaluationRunner`:
1. **Zero Filesystem Access:** The runner receives `ValidatedDataset`, `MatchingEngine`, and `MatchingPolicyConfig` exclusively via method arguments. It contains no `open()`, `Path.read_*()`, or directory scanners.
2. **Immutable Output (`EvaluationRunReport`):** The output model is frozen and records:
   * `run_id`: Unique execution identifier.
   * `timestamp`: ISO 8601 UTC timestamp.
   * `engine_commit_hash`: Git commit SHA of the codebase executing the evaluation.
   * `dataset_id`, `dataset_version`, `dataset_sha256`: Cryptographic fingerprint of the dataset.
   * `policy_id`, `policy_version`, `policy_sha256`: Cryptographic fingerprint of the matching policy.
   * `demand_reports`: Dict of per-demand metrics.
   * `macro_summary`: Overall aggregated metrics for strict and broad thresholds.

---

## Consequences

### Positive
* **Scientific Reproducibility:** Anyone possessing the Git commit, dataset SHA, and policy SHA can reproduce the exact decimal metric values deterministically.
* **Anti-Gaming Invariant:** Strict mathematical separation of broad vs. strict relevance and exclusion of `UNCERTAIN` prevents inflation of accuracy figures.
* **Architectural Decoupling:** The matching engine knows nothing about the evaluation runner or metric formulas.

### Negative
* Stricter CI / validation burden: modifying engine scoring without verifying metrics will immediately highlight regressions in evaluation benchmarks.

---

## Enforcement

A Pull Request is **non-compliant** and MUST NOT be merged if:

1. The evaluation runner or metrics calculator imports or invokes filesystem operations (`Path("...")`, `open()`, etc.).
2. The evaluation protocol treats `RelevanceGrade.UNCERTAIN` (-1) as $0$ or negative in precision/recall calculations.
3. The evaluation runner accepts optional `dataset=None` or `policy=None` and loads fallbacks from disk.
4. An evaluation report omits the `dataset_sha256`, `policy_sha256`, or `engine_commit_hash`.
5. The matching engine is modified or tuned specifically against the pilot benchmark dataset in the same PR.

### Automated Test Requirements
The test suite MUST verify:
1. **Uncertainty Independence Test:** Proves that adding `UNCERTAIN` annotations does not degrade or inflate Precision@K or Recall@K.
2. **CWD & Filesystem Independence Test:** Proves that `EvaluationRunner` executes without touching disk and succeeds inside a read-only sandboxed environment.
3. **Deterministic Metric Verification:** Proves that known demand rankings produce exact mathematical P@K, MRR, and nDCG values.
4. **Provenance Audit Test:** Verifies that every `EvaluationRunReport` carries verified SHAs matching the injected dataset and policy.
