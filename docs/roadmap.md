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

**Lab — corpus:** ADR 0020 (D×P experimental corpus architecture) landed the multi-jurisdiction OPS-backed `PatentCorpus` (#57) with partitioned enumeration (#58). ADR 0019 resolved annotation-pool eligibility under unknown posting dates via `TEMPORAL_UNKNOWN` (superseding the earlier PR-E0.2 OAuth/volume blocker). The Phase-2 **target** demand sample size is frozen at `|D|=60` for a pre-registered minimum effect θ=0.2 (#52) — this is the eventual Phase-2 N, not yet reached. Against that target: a 39-demand corpus passed a per-record construct-eligibility audit (Auditor A #85, confirmed by Auditor B with no disagreements #86), and a 24-demand **eligible subset of those 39** is frozen (#88) — 24 is an intermediate eligibility count, not the Phase-2 dataset itself; growing it toward 60 is still open. A 6-sector taxonomy is frozen with an explicit `no_sector_coverage` escape hatch (#89–#92), and sector assignments over the frozen corpus are frozen (#92). The stratified Dev/Test split mechanism (stratified by sector, per protocol §5.3) and a frozen WPI split are implemented and merged (#79/#93).

**Lab — annotation & IAA:** the IAA machinery (linear/quadratic-weighted Cohen's κ, confusion matrix, degenerate-case handling) is implemented and tested (#56, hardened for annotator-distinctness and NaN-vs-1.0 degenerate cases). PR-E.1 produced a blind re-annotation candidate pool under strict temporal eligibility (#72). PR-E.2 kicked off the pilot annotation template/instructions (#77); Annotator A (Valentín)'s pilot blind judgments are recorded (#82). Dual annotation + κ over the full Phase-2 pool has not yet run.

**Lab — prior pilot result (superseded status, not re-run):** the sealed 3-demand pilot (#45, `PILOT`) and its `strict`-mode re-run (ADR 0018, #48/#49) still stand as the only executed M0-vs-M1 comparison and remain non-significant at `n=3`; nothing above supersedes that result, it is simply not yet repeated at Phase-2 scale.

**Boundary:** ADR 0026 (Accepted, #87) establishes the experiment/domain boundary: Nexus (`backend/`) implements generic, taxonomy-agnostic evaluation mechanisms; experiment-specific configuration, frozen data, and observed results live under `experiments/<paper-slug>/` (e.g. `experiments/wpi-demand-patent-matching/`), never referenced from `backend/src` or `backend/test`, enforced by an automated boundary guard. #86's scientific conclusion stands unchanged under this move; future scientific work (sector taxonomy, Dev/Test split, and beyond) follows this same allocation from the start.

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

The lettered rows below are the original conceptual sequence; **Status** is the current ground truth, since much of Lab work executed under its own PR numbers rather than these letters — treat Status, not the letter, as authoritative.

| PR | Objective | Status | Track |
|---|---|---|---|
| **PR-A** | ADR-0017 + canonical roadmap + archive 15-day plan | **Done** — ADR-0017 merged, this file canonical | Both (decision) |
| **PR-B (#40)** | Implement ADR 0016: `f_lex`/`f_sem` at fusion, `semantic ∈ [-1,1]`, provenance entry | **Done** (#40/#41). Normalization re-audited against protocol §5.2.1/ADR 0012 (#78) — that audit left the `k` constant an open decision, unresolved | Shared/Lab |
| **PR-C** | M1 wiring + end-to-end PILOT audit run | **Done** — M1 wired (#42), first PILOT-status M0-vs-M1 comparison run (#45) | Lab |
| **PR-D** | Canonical dataset + temporal + metric alignment | **Done, as a mechanism, not a one-off dataset edit** — hash chain (#43), `IDCG=0` alignment (#44), temporal eligibility contract `temporal_pool_mode: strict\|unconstrained` (ADR 0018, #48/#49). The sealed dataset stays byte-identical; `strict` excludes flagged violations **at runtime**, with provenance stamped on every report. There is no pending "correct the dataset" task. | Lab |
| **PR-E** | Blinded re-annotation + IAA dry-run + CPC-auto card | **Partial** — IAA machinery (#56), blind re-annotation pool under strict temporal eligibility (#72), pilot annotation template/instructions (#77), Annotator A's pilot judgments recorded (#82). **Open:** dual annotation + κ over the full Phase-2 pool (not just the pilot); CPC-auto card | Lab |
| **PR-F** | Phase-2 dataset + DEV/TEST freeze + powered efficacy + WPI | **Partial** — Dev/Test split mechanism done (#79/#93); corpus construct-eligibility audit done (#85/#86), 24-demand eligible subset frozen (#88) toward the `|D|=60` target; organization-level demand independence audit completed (ADR 0029) yielding an operational organization-audited corpus of N=18 (`dataset_phase2_organization_audited_corpus_v1.json`: 12 verified independent + 6 unknown organization independence) and identifying historical Dev/Test organization leakage; clean organization-isolated Dev/Test split completed and frozen (ADR 0030, `devtest_split_n18_v2.json`: 10 Dev / 8 Test, zero cross-partition leakage, 100% verified independent in Test); Phase-2 corpus expansion contract frozen (ADR 0031, Milestone #101a, `corpus_expansion_policy_v1.json`). **Next active step:** Milestone #101b (data acquisition against frozen contract toward `|D|=60` independent demands), followed by multidimensional independence audit (#102), global Dev/Test split v3 (#103), dual annotation/κ at scale (#104), family-aware evaluation (#105), and powered efficacy evaluation (#106). | Lab |
| **PR-G** | Guardrails: disclaimers + coverage disclosure + archive narrative fix | **Open** — no visible progress | Product |
| **PR-H** | Matching Store + persistent jobs (`tenant_id` field, no auth system) | **Open** | Product |
| **PR-I** | Reduced lifecycle + audit export | **Open** | Product |
| **PR-J** | Monitoring events (no alerting yet) | **Open** | Product |

Licensing gate runs parallel to all Product PRs with veto power; it is not sequenced as a feature.

**Naming note:** the differently-scoped first empirical M0-vs-M1 comparison (#45) was informally called "PR-E" in older discussion around the same time as the letter above; it is not the same work and does not close the PR-E row. Work since #45 is referenced by actual PR number, not by a reused letter.

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
* **Demand independence audit:** the existing Phase-2 audits (#84–#86) check whether each demand *is* a valid technology solicitation (construct eligibility), not whether the 39/24/60 demands are independent observations (same company, sector, tech family, or duplicate industrial problem). **Partially closed** (ADR 0029, ADR 0030, ADR 0031): the company/organization axis is resolved with tripartite classification — 6 of the 24 eligible demands are pseudoreplicates of two organizations (SMAR3TS ×5, Lacer S.A. ×3), leaving an operational organization-audited corpus of N=18 (`dataset_phase2_organization_audited_corpus_v1.json`, comprising 12 verified independent + 6 unknown organization independence observations). The historical Dev/Test organization leakage surfaced by ADR 0029 is resolved via ADR 0030: a clean, deterministic, organization-isolated split (`devtest_split_n18_v2.json`: 10 Dev / 8 Test) routes all UNKNOWN demands to Dev, enforces 100% verified independent observations in Test, and guarantees zero cross-partition organization overlap, preserving `devtest_split_n13_v1.json` as an immutable audit record. The sector, tech-family, and duplicate-industrial-problem axes remain open, as does growing the verified independent population toward `|D|=60`. Milestone #101a establishes the pre-registered acquisition contract and declarative policy (ADR 0031, `corpus_expansion_policy_v1.json`) to expand the corpus to $N \ge 60$ independent demands without convenience sampling or outcome-dependent bias; Milestone #101b (active) executes acquisition against this frozen contract.



One item (public benchmark packaging, review's P4) is a natural post-PR-F deliverable and fits the "done" criteria in §5 rather than needing its own PR row yet.

---

## 7. Future Research Extensions

The Demand → Patent experiment is Nexus's first empirical case, not the scientific definition of Nexus.

Not before completion of the current Phase-2 evaluation and PR-F, the deterministic evidence engine may be evaluated on additional heterogeneous technology-matching problems, including:

* **L2 — Research → Patent:** linkage between scientific research outputs and patent-based technological outputs, including replication/extension of prior research corpora where appropriate.
* **L3 — Generalized Technology Matching:** evaluation of whether the same provenance-aware, deterministic and versioned evidence infrastructure can support multiple matching problems without introducing application-specific ranking logic.

These extensions are **future research directions, not current implementation commitments**. They do not introduce additional experimental branches into the current Phase-2 work and must not alter the frozen protocol, benchmark, or evaluation sequence defined for the Demand → Patent study.

No implementation is planned under this section before completion of the current Phase-2/PR-F work.
