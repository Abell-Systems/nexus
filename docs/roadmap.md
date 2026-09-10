# Roadmap — Abell Nexus (canonical, dual-track)

**Status:** canonical as of ADR 0017. This file is the single official roadmap.
**Superseded plan:** the 15-day hackathon plan is archived unmodified at [archive/hackathon/roadmap-15d.md](archive/hackathon/roadmap-15d.md) and is no longer operative.
**Normative architecture:** [ADR 0017: Nexus Dual-Track Architecture](adr/0017-dual-track-architecture.md).
**Scientific method:** [empirical-study-protocol.md](empirical-study-protocol.md) (Lab only).

---

## 1. Strategy in one page

> Nexus maintains one deterministic evidence engine with two controlled execution contexts: scientific evaluation and customer intelligence. Same evidence → different usage contract.

```text
                         NEXUS
                           │
              ┌────────────┴────────────┐
              │                         │
             LAB                     PRODUCT
              │                         │
       scientific validity        customer workflow
              │                         │
       benchmark / gold set       Matching Store
       Phase-2 evaluation         Demand lifecycle
       ablations                  Evidence / audit
       robustness                 Export
       WPI                        Monitoring
              │                         │
              └────────────┬────────────┘
                           │
                   deterministic core
```

Rules that are non-negotiable (see ADR 0017 §5–§7 for the binding text):

* The benchmark is not the product; the product does not wait for Phase 2.
* The ADK generative path (inventor / adversarial / governor) is synthesis/UX/product-demo, never ranking evidence.
* Pilot numbers are never commercial claims; no score is ever presented as patentability, FTO, or legal opinion.
* Licensing/data-rights is a commercial gate with veto power over monitoring promises.
* Pilotable (store + persistent jobs + reduced lifecycle + export + disclaimers) is explicitly not production-ready (no SSO, tenancy, SLA, billing, scale).

---

## 2. Where things stand (2026-09-10)

**Deterministic core:** `domain/` + `application/matching/` + `infrastructure/matching/` shareable but not consolidated. M0 (BM25) wired via frozen manifest; M1 artifact frozen and wired as raw cosine (#42). Fusion transform (ADR 0016) implemented (#41) — `evaluator.py` applies `f_lex`/`f_sem` at fusion time, no raw weighted sum. ADR 0016's normalization was re-audited against protocol §5.2.1 / ADR 0012 (#78); that audit left an open decision, not yet resolved.

**Lab — corpus:** ADR 0020 (D×P experimental corpus architecture) landed the multi-jurisdiction OPS-backed `PatentCorpus` (#57) with partitioned enumeration (#58). ADR 0019 resolved annotation-pool eligibility under unknown posting dates via `TEMPORAL_UNKNOWN` (superseding the earlier PR-E0.2 OAuth/volume blocker). The Phase-2 demand sample size is frozen at `|D|=60` for a pre-registered minimum effect θ=0.2 (#52). A 39-demand corpus passed a per-record construct-eligibility audit (Auditor A #85, confirmed by Auditor B with no disagreements #86); a 24-demand eligible subset is frozen (#88). A 6-sector taxonomy is frozen with an explicit `no_sector_coverage` escape hatch (#89–#92), and sector assignments over the frozen corpus are frozen (#92). A stratified Dev/Test split mechanism (stratified by sector, per protocol §5.3) plus a frozen WPI split landed as #79/#93 — **this is the change under review on the current branch.**

**Lab — annotation & IAA:** the IAA machinery (linear/quadratic-weighted Cohen's κ, confusion matrix, degenerate-case handling) is implemented and tested (#56, hardened for annotator-distinctness and NaN-vs-1.0 degenerate cases). PR-E.1 produced a blind re-annotation candidate pool under strict temporal eligibility (#72). PR-E.2 kicked off the pilot annotation template/instructions (#77); Annotator A (Valentín)'s pilot blind judgments are recorded (#82). Dual annotation + κ over the full Phase-2 pool has not yet run.

**Lab — prior pilot result (superseded status, not re-run):** the sealed 3-demand pilot (#45, `PILOT`) and its `strict`-mode re-run (ADR 0018, #48/#49) still stand as the only executed M0-vs-M1 comparison and remain non-significant at `n=3`; nothing above supersedes that result, it is simply not yet repeated at Phase-2 scale.

**Boundary:** ADR 0026 formally establishes the experiment/domain boundary and merged as #87. **This branch independently carries a spec+plan (`5c21528`, `396b548`) to design the same boundary reset — written against a base that predates #87 and does not know about it. Reconcile against the merged ADR before doing anything else with those two commits**, likely by discarding or rebasing them, to avoid a competing design landing on top of an already-accepted one.

**Observatory (new, undocumented track):** a public GitHub Pages "scientific verification" dashboard (`nexus-status`) was built end-to-end and is live — ADR 0022 (project status contract), ADR 0023 (verification as external consumer), ADR 0024 (workspace), ADR 0025 (scientific-results publication contract, deterministic atomic publisher, real Landscape execution wired in) (#61, #63–#67, #69–#76). This is a third initiative not represented anywhere in the §1 Lab/Product diagram — it publishes Lab results externally but is neither Lab nor Product machinery in the ADR 0017 sense. The diagram and rules in §1 should be amended to place it, rather than leaving it undocumented.

**Product:** landscape/analyze APIs on in-memory jobs (demo-only), no Matching Store, no persistent jobs, no lifecycle, no audit export, no disclaimers in UI/API. Nothing billable yet by design. No visible progress on PR-G onward since the last roadmap update.

---

## 3. PR sequence

```text
PR-A  ADR-0017 + this canonical roadmap (doc-only)          ← THIS PR, no code
        ↓
PR-B  #40 — ADR 0016 implementation (fusion + bounds)        [shared/lab]
        ↓
  ┌─────┴─────┐
  │           │
 LAB        PRODUCT (parallel after PR-B; product never waits for efficacy)
  │           │
 M1+audit   Guardrails → Matching Store+jobs → lifecycle+export → monitoring
  │           │
 canonical   licensed-data gate (parallel veto)
 data+metrics
  │           │
 annotation
  │           │
 Phase-2 → efficacy → WPI
```

| PR | Objective | Must NOT include | Acceptance | Track |
|---|---|---|---|---|
| **PR-A** | ADR-0017 + canonical roadmap + archive 15-day plan | Code changes; edits to existing ADRs; #40 | ADR-0017 merged, this file canonical, archive byte-identical, docs gate green | Both (decision) |
| **PR-B (#40)** | Implement ADR 0016: `f_lex`/`f_sem` at fusion, `semantic ∈ [-1,1]`, provenance entry | M1 wiring; pilot numbers in same PR | `overall ∈ [0,1]` structural + tests, no benchmark-derived parameters | Shared/Lab |
| **PR-C** | M1 wiring + end-to-end PILOT audit run | Re-tuning; efficacy claims | M0+M1+M2+M6 green over 45 pairs, `study_status: PILOT` | Lab |
| **PR-D** | Canonical dataset + temporal + metric alignment | New annotations | Single hash chain, pool pre/post-`Φ_temporal` decided, one primary endpoint | Lab |
| **PR-E** | Blinded re-annotation + IAA dry-run + CPC-auto card | Phase-2 collection | κ reported, classifier precision/recall reported | Lab |
| **PR-F** | Phase-2 dataset + DEV/TEST freeze + powered efficacy + WPI | Product code | Wilcoxon + paired bootstrap + BH on untouched test | Lab |
| **PR-G** | Guardrails: disclaimers + coverage disclosure + archive narrative fix | Scoring changes | Disclaimer on UI/API/exports | Product |
| **PR-H** | Matching Store + persistent jobs (`tenant_id` field, no auth system) | Monitoring; auth | Restart-safe `MatchRun` with 5-version contract | Product |
| **PR-I** | Reduced lifecycle + audit export | Alerting | CSV+JSON exports with hashes | Product |
| **PR-J** | Monitoring events (no alerting yet) | SLA/scale | Versioned diffs as new runs | Product |

Licensing gate runs parallel to all Product PRs with veto power; it is not sequenced as a feature.

**PR-D execution note:** the canonical-dataset and metric-alignment parts of PR-D's scope were executed as #43 (hash chain, read-only audit) and #44 (`IDCG=0`/primary-endpoint alignment; see §4 items 3–4) rather than as a single PR under this exact label — recorded here rather than rewritten into the table above. PR-D's temporal-eligibility part ("pool pre/post-`Φ_temporal` decided") is **fully executed as a mechanism, not as a one-off dataset edit**: ADR 0018 (#48/#49) is a contractual eligibility contract (`temporal_pool_mode: "strict" | "unconstrained"`, mandatory, fail-fast on the contaminated combination), not a dataset correction — the sealed dataset stays byte-identical and is never rewritten; `strict` mode excludes the flagged violations from the pool **at runtime**, over the same sealed data, with `temporal_pool_mode` stamped on every report for provenance. There is no pending "correct the dataset" task. What remains open before PR-F is running annotation/IAA and the M0-vs-M1 comparison at Phase-2 scale under this same `strict` contract — not any further dataset mutation.

**Naming note:** the table's lettered **PR-E** ("Blinded re-annotation + IAA dry-run + CPC-auto card") has now been substantially, though not completely, executed under real PR numbers rather than the reused letter: independent candidate pool + blind dual annotation + IAA dry-run (#56), blind re-annotation pool under strict temporal eligibility (#72), pilot annotation template/instructions (#77), and Annotator A's recorded pilot judgments (#82). Dual annotation + κ over the full Phase-2 pool (not just the pilot) is still open. The differently-scoped first empirical M0-vs-M1 comparison (#45) remains informally "PR-E" in older discussion and is still not a substitute for this row. Later work continues to be referenced by actual PR number, not by a reused letter.

---

## 4. Recorded contradictions (open, owned, not silently fixed)

1. `architecture.md` still describes the pre-UC1 ip-matchmaker topology (BigQuery-global white-space method). Owner: PR-G or a Lab docs PR — rewrite or archive, not both.
2. Archived hackathon narrative promises ScoreCards "for patent filings" / "patentable white space". Owner: PR-G — editorial correction + disclaimer; archive itself stays byte-identical.
3. Primary endpoint mismatch: M0–M6 hypothesis family (strict MRR) vs study protocol (primary `nDCG@10`). **Resolved (docs-only, no code/hash change):**

   > **Confirmatory endpoint:** `nDCG@10`, as specified by the empirical study protocol and used by the current evaluation implementation.
   >
   > The sealed M0–M6 hypothesis configuration (`config/evaluations/comparisons_m0_m6.json`) retains `MRR` as its historical primary metric. This configuration is preserved unchanged for provenance and reproducibility and is treated as **legacy/secondary analysis**, not as the confirmatory endpoint of the Phase-2 study.
   >
   > No re-sealing, re-hashing, or mutation of `comparisons_m0_m6.json` is permitted. `MRR` remains a valid secondary metric — it simply is not the pre-specified confirmatory endpoint.

4. `IDCG=0` handling: protocol (exclude + report) vs `metrics.py` (impute 1.0). **Resolved (#44):** `metrics.py` now returns `None` when `IDCG == 0` (never imputed) and excludes the observation from macro averages, with explicit per-metric denominators (`EvaluationRunReport.macro_denominators`). Protocol and code now agree.

---

## 5. What "done" means

* **Lab done:** powered efficacy on a frozen DEV/TEST split with pre-registered transform, dual annotation + IAA, and a WPI manuscript that reports a protocol + harness + limitations — efficacy claims only after PR-F.
* **Product done (pilotable):** a customer pilot runs on persistent `MatchRun`s with full version provenance, reduced lifecycle, auditable exports, and visible recall-aid disclaimers — without waiting for PR-F and without enterprise machinery.

---

## 6. Reconciliation with external scientific-rigor review (2026-09-10)

An external review of the empirical study (P0–P6 gap analysis) was checked against `docs/empirical-study-protocol.md` and the merged ADRs. Most of its P1–P3 asks are **already specified**, not new work:

* Relevance-construct validation (0–3 rubric with worked boundary examples) — protocol §6.2.
* Inter-rater agreement (weighted Cohen's κ, threshold κw ≥ 0.70) — protocol §6.3/7.3, implemented and tested (#56).
* Ablation matrix over {BM25, Dense, CPC} and their unions — protocol §8.
* Sector/domain heterogeneity analysis — protocol §7, frozen taxonomy (#89–#92).
* Effect size (standardized θ), paired bootstrap CIs, Wilcoxon — protocol §7, power analysis frozen (#52).
* External validation (cross-jurisdiction) — already correctly deferred, protocol §10.2 and this file's §7 (L2/L3).

Two items are genuine gaps, not covered by the protocol or any merged ADR, and should be scheduled into the Lab track **before PR-F efficacy claims**, per the review's own P1 priority (avoid overclaiming on a flawed benchmark):

* **Patent-family-aware evaluation:** no family/duplicate-detection policy exists anywhere in the codebase or protocol (`family_policy: allow|collapse|exclude_related` and a family-aware sensitivity re-run). Needed to rule out one invention contributing multiple ranked hits.
* **Demand independence audit:** the existing Phase-2 audits (#84–#86) check whether each demand *is* a valid technology solicitation (construct eligibility), not whether the 39/24/60 demands are independent observations (same company, sector, tech family, or duplicate industrial problem). These are different questions; only the first has been done.

One item (public benchmark packaging, review's P4) is a natural post-PR-F deliverable and fits the "done" criteria in §5 rather than needing its own PR row yet.

---

## 7. Future Research Extensions

The Demand → Patent experiment is Nexus's first empirical case, not the scientific definition of Nexus.

Not before completion of the current Phase-2 evaluation and PR-F, the deterministic evidence engine may be evaluated on additional heterogeneous technology-matching problems, including:

* **L2 — Research → Patent:** linkage between scientific research outputs and patent-based technological outputs, including replication/extension of prior research corpora where appropriate.
* **L3 — Generalized Technology Matching:** evaluation of whether the same provenance-aware, deterministic and versioned evidence infrastructure can support multiple matching problems without introducing application-specific ranking logic.

These extensions are **future research directions, not current implementation commitments**. They do not introduce additional experimental branches into the current Phase-2 work and must not alter the frozen protocol, benchmark, or evaluation sequence defined for the Demand → Patent study.

No implementation is planned under this section before completion of the current Phase-2/PR-F work.
