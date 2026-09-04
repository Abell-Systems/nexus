# ADR 0011: Frozen Evaluation Boundary, Execution Context Sealing, and Comparative Statistical Harness

**Status:** Accepted  
**Date:** 2026-09-04  
**Scope:** `domain/models/evaluation`, `application/evaluation`, `scripts/run_scientific_evaluation.py`, `config/evaluations`  

---

## Context

Under ADR 0006 (Validation Dataset, Schema, and Provenance), ADR 0007 (Evaluation Protocol and Metrics), and ADR 0010 (Inferential Statistical Testing Framework), Nexus establishes:
1. Byte-exact cryptographic integrity of benchmark datasets via `.sha256` files.
2. Standard information retrieval metrics (MRR, nDCG@5, Precision@K, Judged@K, UncertaintyRate) evaluated over a closed candidate pool.
3. Pure inferential statistical testing primitives (`paired_wilcoxon_test`, `paired_bootstrap_ci`, `adjust_benjamini_hochberg`).

However, without a formal boundary governing how comparative evaluations are conducted:
1. **Hypothesis Fishing / Post-Hoc Comparison Selection:** If comparative evaluations across model variants (M0–M6) are not pre-registered, an experimenter could run arbitrary pairwise tests and report only those achieving statistical significance or select FDR correction families opportunistically.
2. **Aggregation Fallacy in Paired Testing:** Non-parametric tests (such as the Wilcoxon signed-rank test and paired bootstrap) require **paired demand-level observations** ($y_i, x_i$), where each pair corresponds to the exact same demand $d_i \in \mathcal{D}$. Applying statistical tests to macro-averaged summary numbers or unpaired random vectors is mathematically invalid and yields spurious confidence.
3. **Product Contamination:** Introducing experiment runner commands or evaluation logic into the product CLI (`infrastructure/cli.py`) blurs the boundary between product capabilities and scientific audit harnesses. The product exists to solve matching problems; the evaluation harness exists to independently audit whether the product succeeds.
4. **Execution Provenance Gaps:** Storing evaluation reports without linking the exact study protocol hash (`study_protocol_sha256`) permits protocol drift between runs.
5. **Pilot vs Frozen Conflation:** Preliminary pilot executions designed to smoke-test the pipeline must not be masqueraded as final frozen inferential evidence.

---

## Decision

### 1. Separation of Product Core and Scientific Evaluation Harness

> **The laboratory lives outside the product.**
> The product does not exist to produce the paper; the evaluation harness exists to determine if the product merits confidence.

1. The production CLI (`infrastructure/cli.py`) and product domain models (`matching`, `synthesis`, `landscape`) MUST NOT import or expose scientific evaluation runners.
2. The scientific evaluation entrypoint remains strictly external in `scripts/run_scientific_evaluation.py`.
3. The evaluation subsystem operates strictly as an **independent auditor** via `EvaluationRankingPort`.

---

### 2. Pre-Registered Study Protocol & Fixed Comparison Family

To prevent post-hoc hypothesis selection, all model comparisons and statistical parameters MUST be pre-registered in versioned configuration (`config/evaluations/comparisons_m0_m6.json`) prior to inferential testing:

1. **Model Variant Hierarchy (M0–M6):**
   * **M0:** Baseline (Lexical BM25 retrieval and keyword matching).
   * **M1:** Dense semantic retrieval.
   * **M2:** CPC concordance & structural taxonomy.
   * **M3:** Tripartite evidence assessment (asymmetrical verification; `UNKNOWN != NEGATIVE`).
   * **M4:** Origin policy resolution.
   * **M5:** Multi-agent synthesis (inventor and adversarial verification).
   * **M6:** Nexus Complete Pipeline.
2. **Fixed Hypothesis Family:** Each hypothesis has a stable identifier (e.g. `H01_M1_vs_M0_MRR`, ..., `H06_M6_vs_M0_MRR`), fixed primary metric (`mrr` strict), target alternative (`greater`), pre-set significance level ($\alpha = 0.05$), and fixed random seed ($42$) for non-parametric bootstrap resampling ($B = 10,000$).
3. **Monotonic FDR Correction:** Benjamini–Hochberg step-up adjustment is applied strictly across the closed family of pre-registered hypotheses. Hypotheses cannot be selectively added or omitted after observing $p$-values.

---

### 3. Paired Demand-Level Observation Extraction

All comparative inferential tests MUST operate on matched vectors aligned by demand identifier:

$$\Delta_i = y(d_i) - x(d_i) \quad \forall d_i \in \mathcal{D}$$

1. The comparative evaluator extracts per-demand metric observations from `EvaluationRunReport.demand_reports`.
2. **Demand Consistency Invariant:** The set of evaluated `demand_id`s in the baseline run MUST match the set in the treatment run exactly:
   $$\{ d.\text{demand\_id} \mid d \in \text{baseline} \} = \{ d.\text{demand\_id} \mid d \in \text{treatment} \}$$
   If any demand is present in one run but missing in the other, the comparator MUST fail fast immediately with `ValueError`.
3. The resulting aligned paired vectors are passed directly to `paired_wilcoxon_test` and `paired_bootstrap_ci`.

---

### 4. Sealed Execution Context & Hash Identity Chain

Every evaluation run report and comparative analysis artifact MUST record the unbroken chain of cryptographic provenance:

```text
Dataset Bytes (.sha256)      ──▶ dataset_sha256
Matching Policy (.json)       ──▶ policy_sha256
Study Protocol (.json)        ──▶ study_protocol_sha256
Engine Source Code (Git)     ──▶ engine_commit_hash
Environment Coordinates       ──▶ environment, timestamp
```

* `study_protocol_id` and `study_protocol_sha256` are stamped directly into comparative reports.
* The evaluation runner NEVER discovers Git or scans paths internally; all execution coordinates are supplied explicitly by the external execution context (`EvaluationExecutionContext`).

> **Note on `protocol_sha256` integrity model:** The hash stored in `comparisons_m0_m6.json` is computed over the payload excluding the `protocol_sha256` field itself (self-referential consistency check). This allows detection of accidental protocol drift but does NOT constitute an external cryptographic seal — a party with write access to the file can recompute the digest. For the PILOT phase this is sufficient. For the final frozen inferential evaluation (PR #26), the expected protocol digest MUST be declared in an external immutable record (e.g. pinned in a companion `.sha256` file or a separate frozen manifest), mirroring the model used for datasets in ADR 0006.

> **Note on `run_scientific_evaluation.py` study metadata decoration:** The script currently injects `study_status` and `study_protocol_id` as post-serialization fields into an `EvaluationRunReport` dict. This is an interim pattern for the PILOT phase — acceptable because the script lives outside the product in `scripts/`. In PR #25/26 the script should instead produce a `ComparativeRunReport` directly via `evaluate_study_protocol()`, making the scientific object the primary output rather than a decorated dict.

---

### 5. Explicit Epistemic Status: Pilot vs Frozen Final

1. Any evaluation execution run prior to benchmark freezing MUST declare `"study_status": "PILOT"`.
2. Pilot runs serve strictly to detect engineering bugs, verify schema validity, check pipeline throughput, and confirm byte-exact reproducibility.
3. Pilot run artifacts MUST NEVER be conflated with or incorporated into final inferential evaluation reports.

---

## Consequences

### Positive
* **Defensible Science:** Statistical significance and confidence intervals reflect authentic demand-level variance, not ecological fallacies on aggregated metrics.
* **Integrity by Design:** Pre-registration prevents cherry-picking comparisons or dredging hypotheses post-hoc.
* **Decoupled Architecture:** Zero evaluation baggage inside the production product CLI or domain models.
* **Unbroken Provenance:** Byte-exact verification of datasets, policies, and study protocols ensures exact reproducibility across machines.

### Negative
* Inflexible comparisons: testing a new hypothesis requires authoring a new versioned protocol rather than running ad-hoc ad-lib comparisons.

---

## Enforcement

A Pull Request is **non-compliant** and MUST NOT be merged if:
1. `infrastructure/cli.py` is modified to expose internal evaluation or benchmarking commands.
2. A comparative evaluator computes Wilcoxon or bootstrap tests over macro-aggregated metrics rather than paired per-demand vectors.
3. Baseline and treatment runs with mismatched demand IDs proceed without raising an immediate `ValueError`.
4. A pilot evaluation report omits `"study_status": "PILOT"`.
5. The comparative evaluation module imports from matching domain types, infrastructure, or external provider SDKs.
