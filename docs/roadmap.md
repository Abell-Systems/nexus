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

**Deterministic core:** `domain/` + `application/matching/` + `infrastructure/matching/` shareable but not consolidated. M0 (BM25) wired via frozen manifest; M1 artifact frozen but unwired; fusion transform (ADR 0016, Proposed) not yet implemented — raw weighted sum still live in `evaluator.py`.

**Lab:** sealed pilot (3 demands × 15 patents, 23/45 pairs, `PILOT / PROOF_OF_HARNESS`). Open items before any efficacy claim: temporal-eligibility correction, metric/protocol alignment (`IDCG=0` handling, primary endpoint MRR-vs-`nDCG@10`), canonical hash chain, dual blinded annotation + IAA, powered Phase-2 dataset.

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

---

## 4. Recorded contradictions (open, owned, not silently fixed)

1. `architecture.md` still describes the pre-UC1 ip-matchmaker topology (BigQuery-global white-space method). Owner: PR-G or a Lab docs PR — rewrite or archive, not both.
2. Archived hackathon narrative promises ScoreCards "for patent filings" / "patentable white space". Owner: PR-G — editorial correction + disclaimer; archive itself stays byte-identical.
3. Primary endpoint mismatch: M0–M6 hypothesis family (strict MRR) vs study protocol (primary `nDCG@10`). Owner: PR-D — unify to one confirmatory endpoint.
4. `IDCG=0` handling: protocol (exclude + report) vs `metrics.py` (impute 1.0). Owner: PR-D — one truth, code or protocol changes accordingly.

---

## 5. What "done" means

* **Lab done:** powered efficacy on a frozen DEV/TEST split with pre-registered transform, dual annotation + IAA, and a WPI manuscript that reports a protocol + harness + limitations — efficacy claims only after PR-F.
* **Product done (pilotable):** a customer pilot runs on persistent `MatchRun`s with full version provenance, reduced lifecycle, auditable exports, and visible recall-aid disclaimers — without waiting for PR-F and without enterprise machinery.
