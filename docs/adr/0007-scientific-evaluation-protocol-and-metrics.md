# ADR 0007: Scientific Evaluation Protocol and Metrics for Matching Validation

**Status:** Accepted  
**Date:** 2026-09-03  
**Scope:** `domain/models/evaluation`, `domain/protocols/evaluation`, `application/evaluation`, `infrastructure/evaluation`  

---

## Context

Under ADR 0004 (Matching Engine Contract & Evidence Assessment), ADR 0005 (Explicit Policy Injection & No Implicit Configuration), and ADR 0006 (Scientific Validation Dataset, Schema, and Evaluation Provenance), Nexus formalizes a strict decoupling between authentic observed facts, externalized matching policies, immutable evaluation datasets, and the deterministic matching engine.

However, an evaluation protocol cannot be scientifically defensible if its statistical framing, metric definitions, and boundary conditions are ambiguous. Specifically:
1. **Unbounded Recall Denominators:** If Recall is defined without declaring whether evaluation is *pooled* or *open-universe*, the metric vacillates between measuring recovery over a curated subset vs. population recall across millions of patents.
2. **Epistemic Distortion in Precision & Uncertainty:** Coercing `RelevanceGrade.UNCERTAIN = -1` to negative ($0$) or penalizing a ranker for encountering unjudged items conflates absence of expert knowledge with verified irrelevance (`UNKNOWN != NEGATIVE`).
3. **Multilevel Ranking Ambiguity under Incomplete Judgements:** Standard nDCG formulations break down when encountering unjudged items, or when a demand possesses zero relevant items ($IDCG = 0$).
4. **Rank-cutoff Confusion in Reciprocal Rank:** Conflating global Mean Reciprocal Rank (MRR) with rank-truncated MRR@K creates irreproducible baselines.
5. **Implicit Runtime Discovery of Engine Commit:** Requiring the evaluation runner to discover Git commits via shell commands (`git rev-parse`) or inspect filesystem metadata violates ADR 0005's zero-implicit-resolution invariant.

This ADR establishes the rigorous mathematical and architectural contract for scientific matching evaluation in Nexus.

---

## Decision

### 1. Fundamental Evaluation Framing: Pooled Evaluation over Sealed Candidate Universe

Nexus adopts the **Pooled Benchmark Evaluation Methodology** (Cranfield / TREC paradigm):

1. For each demand $d \in \mathcal{D}$ in an evaluation dataset, the set of candidates $\mathcal{P}_d$ present in `EvaluationDataset.patents` defines the **sealed, exhaustive candidate universe** for that benchmark.
2. The engine's ranker is evaluated strictly on its ability to order candidates within this pooled universe $\mathcal{P}_d$.
3. **Recall Denominator Definition:**  
   $$\text{TotalRelevant}(d, \tau) = \left| \{ p \in \mathcal{P}_d : \text{grade}(d, p) \text{ is judegable and } \text{IsRelevant}(d, p, \tau) \} \right|$$
   Recall measures the fraction of all known relevant items within the pooled candidate universe that are recovered in top-$K$. It is explicitly bounded and closed under the dataset.

---

### 2. Relevance Grade Semantics & Dual Operational Projections

Under ADR 0006, `RelevanceGrade` defines a 4-point discrete ordinal scale plus epistemic uncertainty:
* **Grade 0 (`IRRELEVANT`):** Out of domain, or unrelated technology.
* **Grade 1 (`DOMAIN_RELATED`):** Same technological sector, but does not solve the specific technical problem posed in the demand.
* **Grade 2 (`TECHNOLOGICALLY_RELEVANT`):** Substantively addresses core problem components, analogous mechanisms, or direct technical dependencies.
* **Grade 3 (`DIRECTLY_ADDRESSING`):** Directly targets the specific technical solution sought by the demand.
* **Grade -1 (`UNCERTAIN`):** Ambiguous prior art or insufficient expert consensus requiring deeper investigation.

To prevent opportunistic goalpost-shifting, two canonical binary projections are established:

1. **Strict Target Alignment ($\tau_{\text{strict}}$):**
   $$\text{IsRelevant}_{\text{strict}}(g) = \begin{cases} \text{True} & \text{if } g = 3 \\ \text{False} & \text{if } g \in \{0, 1, 2\} \end{cases}$$
2. **Broad Technological Alignment ($\tau_{\text{broad}}$):**
   $$\text{IsRelevant}_{\text{broad}}(g) = \begin{cases} \text{True} & \text{if } g \in \{2, 3\} \\ \text{False} & \text{if } g \in \{0, 1\} \end{cases}$$

---

### 3. Epistemological Invariant: Explicit Handling of `UNCERTAIN` (-1)

Under the core invariant **`UNKNOWN != NEGATIVE`** (AGENTS.md §3):

1. **No Coercion:** `RelevanceGrade.UNCERTAIN` (-1) MUST NEVER be coerced to $0$ or treated as negative.
2. **Judged-Item Precision@K ($P@K$):**  
   Precision is computed strictly over **judged/known candidates** in the top-$K$:
   $$P@K = \begin{cases} \frac{\text{TP}_K}{\text{TP}_K + \text{FP}_K} & \text{if } (\text{TP}_K + \text{FP}_K) > 0 \\ 0.0 & \text{if } (\text{TP}_K + \text{FP}_K) = 0 \end{cases}$$
   where:
   * $\text{TP}_K = |\{ p \in \text{TopK}(d) : \text{grade}(p) \neq \text{UNCERTAIN} \land \text{IsRelevant}(p, \tau) \}|$
   * $\text{FP}_K = |\{ p \in \text{TopK}(d) : \text{grade}(p) \neq \text{UNCERTAIN} \land \neg \text{IsRelevant}(p, \tau) \}|$
3. **Judged Coverage at K ($Judged@K$):**  
   To prevent gaming precision by retrieving unjudged candidates, every evaluation MUST concurrently report:
   $$\text{Judged}@K = \frac{|\{ p \in \text{TopK}(d) : \text{grade}(p) \neq \text{UNCERTAIN} \}|}{K}$$
4. **Dataset Uncertainty Rate:**  
   $$\text{UncertaintyRate} = \frac{|\{ a \in \mathcal{A} : a.\text{grade} = \text{UNCERTAIN} \}|}{|\mathcal{A}|}$$

---

### 4. Ranking Metrics: nDCG and Reciprocal Rank

#### Graded Relevance Ranking: nDCG@K
1. **Filtering:** Candidates with grade `UNCERTAIN` are excluded from the evaluated sequence before computing DCG.
2. **DCG Formulation:** For the remaining judged sequence in top-$K$ with grades $g_i \in \{0, 1, 2, 3\}$:
   $$\text{DCG}@K = \sum_{i=1}^{\min(K, N_{\text{judged}})} \frac{2^{g_i} - 1}{\log_2(i + 1)}$$
3. **Ideal DCG (IDCG):** Computed by sorting all judged candidates for demand $d$ in descending order of grade:
   $$\text{IDCG}@K = \sum_{i=1}^{\min(K, N_{\text{judged}})} \frac{2^{g_i^*} - 1}{\log_2(i + 1)}$$
4. **Boundary Condition ($\text{IDCG}@K = 0$):**  
   If all judged candidates for demand $d$ have grade $0$ (meaning no relevant items exist in the candidate pool for this demand), $\text{IDCG}@K = 0.0$.  
   In this case, the ranking task is non-informative for graded relevance. By definition:
   $$\text{nDCG}@K = 1.0 \quad \text{if } \text{IDCG}@K = 0 \land \text{DCG}@K = 0$$
   $$\text{nDCG}@K = 0.0 \quad \text{if } \text{IDCG}@K = 0 \land \text{DCG}@K > 0 \quad (\text{mathematically impossible})$$

#### Reciprocal Rank: Global MRR vs. MRR@K
1. **Global MRR (Primary Metric):**  
   Evaluates the reciprocal rank of the first relevant candidate according to its **true position in the system's original ranked candidate list**:
   $$\text{RR}(d, \tau) = \begin{cases} \frac{1}{\text{rank}_{\text{orig}}(p^*)} & \text{where } p^* \text{ is the first relevant item in the system's ranked list} \\ 0.0 & \text{if no relevant item is retrieved} \end{cases}$$
   where $\text{rank}_{\text{orig}}(p^*) \in \{1, 2, \dots, N\}$ represents the original 1-indexed retrieval position produced by the engine. Items flagged as `UNCERTAIN` preceding $p^*$ are NOT skipped or collapsed for position indexing: if an engine places an uncertain item at rank 1 and a relevant item at rank 2, the relevant item is at system rank 2 ($\text{RR} = 1/2 = 0.5$).
2. **Rank-Truncated MRR@K (Secondary Metric):**  
   $$\text{RR}@K(d, \tau) = \begin{cases} \frac{1}{\text{rank}_{\text{orig}}(p^*)} & \text{if } \text{rank}_{\text{orig}}(p^*) \le K \\ 0.0 & \text{otherwise} \end{cases}$$
   When the metric is named `MRR`, it refers exclusively to Global MRR across the full original ranking.

---

### 5. Architectural Contract: Explicit Execution Context & Zero Implicit Discovery

Under ADR 0005:

1. **`EvaluationExecutionContext` Model:**  
   The runner does NOT execute Git commands, inspect `.git`, or read filesystem timestamps. All execution environment coordinates MUST be injected explicitly:
   ```python
   class EvaluationExecutionContext(BaseModel):
       engine_name: str
       engine_version: str
       engine_commit_hash: str = Field(min_length=7, max_length=40)
       execution_timestamp: datetime
       environment: str  # e.g., "ci", "local", "benchmarking"
   ```
2. **Runner Protocol Signature:**
   ```python
   class EvaluationRunner(Protocol):
       def run_evaluation(
           self,
           dataset: ValidatedDataset,
           engine: MatchingEngine,
           policy: MatchingPolicyConfig,
           context: EvaluationExecutionContext,
       ) -> EvaluationRunReport:
           ...
   ```
3. **Pure Audit Decoupling:**  
   The runner depends strictly on the `MatchingEngine` protocol, never on concrete implementation classes (`DefaultMatchingEngine`). It performs **zero** filesystem I/O.

---

## Consequences

### Positive
* **Mathematical Precision:** No ambiguous denominators; exact formulas for $P@K$ under uncertainty, $Judged@K$, $IDCG = 0$, and global $MRR$.
* **Honest Scientific Reporting:** High precision achieved by avoiding unjudged items is immediately revealed by low $Judged@K$.
* **CWD & Tooling Independence:** Execution is 100% reproducible without Git repository presence or disk access.

### Negative
* Higher metric verbosity: reports must present $P@K$, $R@K$, $Judged@K$, $nDCG@K$, and $UncertaintyRate$ across both $\tau_{\text{strict}}$ and $\tau_{\text{broad}}$.

---

## Enforcement

A Pull Request is **non-compliant** and MUST NOT be merged if:

1. `RelevanceGrade.UNCERTAIN` is coerced to $0$ or included in true-negative / false-positive counts.
2. $P@K$ is computed with unjudged items treated as negatives without reporting $Judged@K$.
3. The evaluation runner touches disk, executes Git commands, or resolves file paths.
4. The runner accepts optional `dataset=None`, `engine=None`, `policy=None`, or `context=None`.
5. $\text{IDCG} = 0$ results in a divide-by-zero exception rather than handling the boundary condition deterministically.

### Automated Test Requirements
The test suite MUST verify:
1. **Uncertainty Isolation Test:** Adding `UNCERTAIN` annotations modifies $Judged@K$ and $UncertaintyRate$, but does NOT alter $P@K$ over the remaining judged items.
2. **Zero IDCG Boundary Test:** Evaluation of a demand with 0 relevant items produces $\text{nDCG} = 1.0$ deterministically without division errors.
3. **CWD & Pure Memory Test:** `EvaluationRunner` completes cleanly in a sandbox where filesystem read/write is completely disabled.
4. **Provenance Integrity Test:** Injected `EvaluationExecutionContext`, `ValidatedDataset.manifest.content_sha256`, and `policy.policy_sha256` are strictly stamped into `EvaluationRunReport`.
