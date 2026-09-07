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

## 2. Where things stand (2026-09-05)

**Deterministic core:** `domain/` + `application/matching/` + `infrastructure/matching/` shareable but not consolidated. M0 (BM25) wired via frozen manifest; M1 artifact frozen and wired as raw cosine (#42). Fusion transform (ADR 0016) implemented (#41) — `evaluator.py` applies `f_lex`/`f_sem` at fusion time, no raw weighted sum.

**Lab:** sealed pilot (3 demands × 15 patents, 23/45 pairs, `PILOT / PROOF_OF_HARNESS`). `IDCG=0` handling (undefined → `None`, excluded from macro, never imputed; #44, see §4 item 4) and the canonical dataset hash chain (dataset/manifest/embeddings triple verified against one SHA-256, #43, see `docs/dataset-identity-audit.md`) are resolved. Primary confirmatory endpoint is `nDCG@10` (see §4 item 3).

A first empirical M0-vs-M1 comparison ran under this protocol (#45): all three pre-registered hypotheses (`nDCG@10`, `Recall@5`, `MRR`) show no detectable difference on the 3-demand pilot. **`study_status: PILOT`, not `FINAL`.** This result does **not** demonstrate that the M1 semantic signal is useless — it demonstrates that, on this specific benchmark and policy, wiring it did not alter the ranking. Both readings remain open questions for the corrected/scaled dataset below.

The temporal pool eligibility contract (ADR 0018, proposed #48 / implemented #49) now exists — `temporal_pool_mode: "strict" | "unconstrained"`, mandatory, with a fail-fast on the contaminated combination — but it has **not yet been used to correct the sealed dataset**: the 3 flagged temporal violations (#43) remain uncorrected in the pilot, and #45's frozen artifact predates this contract (it is not reproducible bit-for-bit by any contract-compliant run; see ADR 0018 Consequences). Still open before any efficacy claim: producing a new, separately-versioned corrected dataset (never overwriting #45's sealed benchmark), re-running M0-vs-M1 on it under the identical protocol, dual blinded annotation + IAA, powered Phase-2 dataset.

**Product:** landscape/analyze APIs on in-memory jobs (demo-only), no Matching Store, no persistent jobs, no lifecycle, no audit export, no disclaimers in UI/API. Nothing billable yet by design.

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

**PR-D execution note:** the canonical-dataset and metric-alignment parts of PR-D's scope were executed as #43 (hash chain, read-only audit) and #44 (`IDCG=0`/primary-endpoint alignment; see §4 items 3–4) rather than as a single PR under this exact label — recorded here rather than rewritten into the table above. PR-D's temporal-eligibility part ("pool pre/post-`Φ_temporal` decided") is **partially** executed: ADR 0018 (#48/#49) delivers the mechanism (an explicit, tested `strict`/`unconstrained` contract), but the sealed dataset itself has not yet been corrected — that remains open, sequenced before the PR-F track below.

**Naming note:** the table's lettered **PR-E** ("Blinded re-annotation + IAA dry-run + CPC-auto card") has **not** been executed — that work is fully open. A differently-scoped comparative experiment, the first empirical M0-vs-M1 comparison (#45), was informally called "PR-E" in project discussion around the same time; it is not a substitute for annotation/IAA work and does not close this table row. To avoid compounding the ambiguity, later ad hoc work is referenced here by its actual PR number (e.g. "#48/#49"), not by a reused letter.

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

## 6. Future Research Extensions

The Demand → Patent experiment is Nexus's first empirical case, not the scientific definition of Nexus.

Not before completion of the current Phase-2 evaluation and PR-F, the deterministic evidence engine may be evaluated on additional heterogeneous technology-matching problems, including:

* **L2 — Research → Patent:** linkage between scientific research outputs and patent-based technological outputs, including replication/extension of prior research corpora where appropriate.
* **L3 — Generalized Technology Matching:** evaluation of whether the same provenance-aware, deterministic and versioned evidence infrastructure can support multiple matching problems without introducing application-specific ranking logic.

These extensions are **future research directions, not current implementation commitments**. They do not introduce additional experimental branches into the current Phase-2 work and must not alter the frozen protocol, benchmark, or evaluation sequence defined for the Demand → Patent study.

No implementation is planned under this section before completion of the current Phase-2/PR-F work.
