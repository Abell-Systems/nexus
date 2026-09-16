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

**Update (2026-09-16) — Lab work past Milestone #101a:** commit messages since #101a use task labels #101b–#101d, #102–#104, etc.; **these are not real GitHub issue/PR numbers** (they diverged — real PR #102 was "Nexus Scientific Model", not the TED audit described below, and this very roadmap-reconciliation PR later took the real GitHub number #104) — treat them as internal milestone labels only. Under those labels: acquisition against the frozen ADR 0031 contract closed (#101b), a historical-source feasibility check returned negative (#101c), a construct-expansion amendment and re-acquisition ran (#101d), and an independence audit + global Dev/Test freeze closed at `N_power=65 ≥ 60 PASS` — clearing the `|D|=60` target set in §2's corpus paragraph above. On a separate corpus track, ADR 0035 acquired and qualified an OEPM Spanish-patent corpus (63/60 records, sealed + hash-verified) as the source of annotation-pool candidates.

Dual blinded annotation + IAA then closed on a 108-pair at-scale batch (30 Dev demands × BM25-only candidate pools): 108/108 agree within one point, κ=0.597 unweighted / 0.916 quadratic-weighted, 12 disagreements adjudicated, gold set frozen — this is the "dual annotation + κ over the full Phase-2 pool" flagged as not-yet-run in the annotation paragraph above; it has now run, at-scale rather than at pilot scale. Pool-coverage was measured under a pre-registered, explicitly non-"recall" estimand (demand-level coverage 9/30, pool yield 14/108) — initially mislabeled BM25+CPC, corrected same session (`docs/phase2-ted-pool-coverage-results.md`). CPC-auto retrieval — the PR-E "CPC-auto card" — was diagnosed as structurally inactive (0/30 demands activate any CPC concept: a vocabulary-register gap between procurement prose and patent-title phrasing, not a taxonomy defect), closing that card as an inconclusive/negative diagnostic rather than a precision/recall report. A CPV→CPC concordance path (a candidate route to a working CPC channel) was then closed `SCOPE-FAILED/DEFERRED`: the only official CPV↔NACE correspondence (EC Reg. 2195/2002 Annex III) covers Construction only, matching 9/30 demands. A dense-retrieval diagnostic (ADR 0014's pinned multilingual model, isolated venv) ran last: 30/30 demands get a structurally non-empty pool at `min_threshold=0.0`, but only 47/600 dense pairs overlap the existing gold set — 553 pairs, including all 220 across the 11 BM25-zero-pool demands, are dense-exclusive and unscored, with no relevance inferred for any of them.

None of the above is a powered efficacy result or a WPI manuscript — PR-F (§3) remains open on both fronts. Undecided next step: whether to annotate a sample of the 553 dense-exclusive pairs.

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
| **PR-E** | Blinded re-annotation + IAA dry-run + CPC-auto card | **Done (2026-09-16)** — IAA machinery (#56), blind re-annotation pool under strict temporal eligibility (#72), pilot template/instructions (#77), pilot judgments (#82), then dual annotation + κ at scale over a 108-pair pool (κ=0.597 unweighted / 0.916 weighted, gold set frozen — see §2 update). CPC-auto card closed **inconclusive**: the channel produced zero activations (0/30 demands), so no classifier predictions exist to score — this is "the channel never fired," not "the classifier performed poorly." Note: PR-E's own "must NOT include Phase-2 collection" exclusion was knowingly broken, since the annotation had no real pool to run against otherwise. Executed under internal task labels, not a dedicated GitHub PR (see §2 update's numbering note). | Lab |
| **PR-F** | Phase-2 dataset + DEV/TEST freeze + powered efficacy + WPI | **Partial** — Dev/Test split mechanism done (#79/#93); corpus construct-eligibility audit done (#85/#86), 24-demand eligible subset frozen (#88) toward the `|D|=60` target; organization-level demand independence audit completed (ADR 0029) yielding an operational organization-audited corpus of N=18 (`dataset_phase2_organization_audited_corpus_v1.json`: 12 verified independent + 6 unknown organization independence) and identifying historical Dev/Test organization leakage; clean organization-isolated Dev/Test split completed and frozen (ADR 0030, `devtest_split_n18_v2.json`: 10 Dev / 8 Test, zero cross-partition leakage, 100% verified independent in Test); Phase-2 corpus expansion contract frozen (ADR 0031, Milestone #101a, `corpus_expansion_policy_v1.json`). **Update (2026-09-16):** the forecasted #102–#106 sequence did not execute under those literal GitHub numbers (see §2 update) but its *scope* substantially did: independence audit + global Dev/Test freeze closed at `N_power=65 ≥ 60 PASS` (clears the `|D|=60` target), family-aware evaluation shipped separately as real PR #97 (ADR 0027 — §6 item below is stale, treat as resolved), relevance-denominator alignment shipped as real PR #98, and dual annotation/κ at scale closed (see PR-E row). **Still open:** powered efficacy evaluation on the frozen split; WPI manuscript. | Lab |
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

Two items were genuine gaps as of 2026-09-10; one has since closed:

* **Patent-family-aware evaluation:** **Resolved (real PR #97, ADR 0027)** — a `family_policy: allow|collapse|exclude_related` contract now exists. No longer an open item; left here for the historical record rather than deleted.
* **Demand independence audit:** the existing Phase-2 audits (#84–#86) check whether each demand *is* a valid technology solicitation (construct eligibility), not whether the 39/24/60 demands are independent observations (same company, sector, tech family, or duplicate industrial problem). **Partially closed** (ADR 0029, ADR 0030, ADR 0031): the company/organization axis is resolved with tripartite classification — 6 of the 24 eligible demands are pseudoreplicates of two organizations (SMAR3TS ×5, Lacer S.A. ×3), leaving an operational organization-audited corpus of N=18 (`dataset_phase2_organization_audited_corpus_v1.json`, comprising 12 verified independent + 6 unknown organization independence observations). The historical Dev/Test organization leakage surfaced by ADR 0029 is resolved via ADR 0030: a clean, deterministic, organization-isolated split (`devtest_split_n18_v2.json`: 10 Dev / 8 Test) routes all UNKNOWN demands to Dev, enforces 100% verified independent observations in Test, and guarantees zero cross-partition organization overlap, preserving `devtest_split_n13_v1.json` as an immutable audit record. The sector, tech-family, and duplicate-industrial-problem axes remain open, as does growing the verified independent population toward `|D|=60`. Milestone #101a establishes the pre-registered acquisition contract and declarative policy (ADR 0031, `corpus_expansion_policy_v1.json`) to expand the corpus to $N \ge 60$ independent demands without convenience sampling or outcome-dependent bias. **Update (2026-09-16):** acquisition against that contract closed — see §2 update — reaching `N_power=65 ≥ 60 PASS`. The sector/tech-family/duplicate-problem independence axes remain open.



One item (public benchmark packaging, review's P4) is a natural post-PR-F deliverable and fits the "done" criteria in §5 rather than needing its own PR row yet.

---

## 7. Future Research Extensions

The Demand → Patent experiment is Nexus's first empirical case, not the scientific definition of Nexus.

Not before completion of the current Phase-2 evaluation and PR-F, the deterministic evidence engine may be evaluated on additional heterogeneous technology-matching problems, including:

* **L2 — Research → Patent:** linkage between scientific research outputs and patent-based technological outputs, including replication/extension of prior research corpora where appropriate.
* **L3 — Generalized Technology Matching:** evaluation of whether the same provenance-aware, deterministic and versioned evidence infrastructure can support multiple matching problems without introducing application-specific ranking logic.

These extensions are **future research directions, not current implementation commitments**. They do not introduce additional experimental branches into the current Phase-2 work and must not alter the frozen protocol, benchmark, or evaluation sequence defined for the Demand → Patent study.

No implementation is planned under this section before completion of the current Phase-2/PR-F work.
