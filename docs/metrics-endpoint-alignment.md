# Metrics / Endpoint Alignment — PR #44

**Status:** alignment record (implementation + protocol audit, no engine/data change).
**Date:** 2026-09-05
**Normative reference:** `empirical-study-protocol.md` §7 (endpoints, exclusion rules).
**Scope:** how Nexus measures, never what Nexus measures.

---

## 1. Decisions

### 1.1 Primary endpoint: nDCG@10, MRR secondary
The protocol (§7, H1) establishes **nDCG@10, hybrid vs best single-signal baseline
(selected on the dev split)** as the single confirmatory endpoint. Strict MRR is a
secondary endpoint. Consequence: `MetricSet` now carries `ndcg_at_10`, the CLI reports
it per demand and macro, and the comparative harness supports it as a hypothesis metric
via the existing field-name mechanism. MRR computation is untouched.

The pre-registered `comparisons_m0_m6.json` family (strict-MRR, each-variant-vs-M0) is
**not rewritten in this PR**: no inferential run has been observed under it, and the
confirmatory redesign (hybrid vs best-single on a dev/test split that does not exist
yet) belongs to the Phase-2 freeze, where it will be re-registered explicitly rather
than edited in place. Until then that family is exploratory/secondary. This deferral
is itself part of the alignment: it refuses to silently re-target a sealed protocol.

### 1.2 Undefined is None, never imputed (supersedes ADR 0007 §4)
ADR 0007 §4 mandated `nDCG = 1.0` on `IDCG = 0` (and the code extended the pattern to
`Recall = 1.0` on zero relevant). The protocol mandates exclusion from macro averages
with explicit reporting of excluded queries. The protocol wins:

* `ndcg_at_k` → `None` iff `IDCG == 0` (no judged grade > 0; scope-independent).
* `recall_at_k` → `None` iff `total_relevant == 0` for that projection.
* Precision@K, MRR, Judged@K keep their defined zero behaviors (genuine zeros, not imputations).
* Macro averages skip `None`; `EvaluationRunReport.macro_denominators` records the
  valid-query count per metric per scope (`strict.<field>` / `broad.<field>`).
* `DemandMetricsReport.has_relevant_judged` flags per-demand nDCG validity.
* Paired comparative vectors exclude demands undefined on either side, stamp
  `n_paired` + `excluded_demand_ids` per hypothesis, and fail fast on zero valid pairs.

A formal ADR 0007 amendment is due at the Phase-2 freeze (PR-F track); until then this
record is the binding reconciliation, referenced from the affected docstrings.

## 2. Reconstructibility contract
From one `EvaluationRunReport` JSON a third party recovers, without re-running:
ranked inputs (per-demand ids in `demand_reports` order — the runner never re-sorts),
relevances (hashed dataset + annotations, referenced by `dataset_sha256`),
per-demand metrics (strict/broad sets, `None` where undefined),
aggregation (`macro_*` + `macro_denominators`: excluded = total − denominator),
endpoint inputs (paired vectors re-derivable per demand; `n_paired`/excluded stamped
per hypothesis in `ComparativeRunReport`).

## 3. Explicitly not in this PR
Weights, thresholds, BM25, embeddings, ADR 0016 transform, CandidatePool, labels,
dataset, temporal eligibility, ADK, product, any M0/M1 comparison on real results.
No sealed protocol file was rewritten; no benchmark byte changed.
