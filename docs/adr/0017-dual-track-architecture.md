# ADR 0017: Nexus Dual-Track Architecture — Deterministic Core with Two Controlled Execution Contexts

**Status:** Proposed
**Date:** 2026-09-05
**Scope:** Conceptual architecture boundary for all future Lab and Product work: terminology, separation of execution contexts, provenance bridge, prohibitions, and documentation single-source rule. Doc only — no code, no test changes, no modifications to existing ADRs.

---

## Context

Until now the Nexus roadmap has been effectively linear: scientific engine → benchmark → evaluation → product → *World Patent Information* publication. A repository audit against `main` showed that this linear framing no longer matches reality, for one structural reason:

> **Nexus does not have a single engine today; it has two heads with different natures.**
>
> * **Head A (generative):** landscape white-space heuristic (`W_i`) + ADK multi-agent synthesis loop (inventor / adversarial / governor `ScoreCard`), exposed via `GET /api/landscape` and `POST /api/analyze`. Stochastic, quota-bound, UX-oriented.
> * **Head B (deterministic):** UC1 matching pipeline (`DefaultMatchingEngine` + deterministic retrievers + `DefaultEvidenceEvaluator`), exercised only via `scripts/` and the sealed evaluation harness. Reproducible, policy-driven, auditable.

Treating Head A as scientific evidence for ranking efficacy, or treating Head B as a finished product, are both category errors. At the same time, both heads share a real common substrate (`domain/` models, `MatchingPolicyConfig`, eligibility rules, provenance conventions under ADR 0006 and ADR 0007) that must not be forked.

This ADR fixes the strategy:

> **Nexus maintains one deterministic evidence engine with two controlled execution contexts: scientific evaluation and customer intelligence.**
> **Same evidence → different usage contract.**

The product also needs science (to be trustworthy), and the science also needs the product (to demonstrate utility). The difference is not "science engine vs product" but the contract under which the same evidence is used.

---

## Decision

### 1. Terminology: deterministic core (not "Shared Engine")

The shared substrate is hereby named the **deterministic core**:

* `domain/` (patent, demand, matching, evaluation, origin-policy models)
* `application/matching/` (`DefaultMatchingEngine`, feature extractor, evidence evaluator)
* `infrastructure/matching/` (deterministic retrievers: BM25, CPC, dense; eligibility policy)

It is explicitly **not** presented as a consolidated architecture. It is the *shareable deterministic nucleus* around which the product concept is still to be built. No claim is made that the core is complete, stable, or sufficient for either track on its own.

### 2. Two controlled execution contexts

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

1. **Lab (scientific evaluation):** `application/evaluation/` + `scripts/` + `config/evaluations/` + `data/evaluation/`. Operates strictly as an independent auditor. Its **only** permitted contact point with matching internals is `application/evaluation/matching_adapter.py` (existing ADR 0007/ADR 0011 boundary, unchanged).
2. **Product (customer intelligence):** demand lifecycle, `MatchRun` persistence, evidence/audit export, monitoring. Reuses the deterministic core through the same `DefaultMatchingEngine.evaluate()` entrypoint with a versioned `MatchingPolicyConfig`, but **never** reads from or writes to `data/evaluation/` or `config/evaluations/`.
3. **Head A (ADK inventor/adversarial/governor) is classified as synthesis/UX/product-demo.** Its `ScoreCard.supporting_evidence` fields are mandatory UX citations, not relevance grades. It does not feed metrics, ablations, or efficacy claims. This classification is architectural, not provisional.

### 3. Boundary is conceptual; physical layout stays open

The Lab/Product separation approved here is **conceptual and architectural**. A location such as `application/product/` is an implementation proposal subject to review during the Matching Store PR (PR-H), not dogma imposed by this ADR. No directory is created or mandated by this decision. The enforcement mechanism is dependency direction (see §7), not folder names.

### 4. Provenance bridge: same traceability, two purposes

```text
                  deterministic core
                         │
       ┌─────────────────┴─────────────────┐
       │                                   │
  EvaluationRun                        MatchRun
       │                                   │
   scientific                           customer
       │                                   │
  benchmark dataset                  DemandVersion
  study protocol                     PatentDatasetVersion
  model configuration                EngineVersion
  engine commit                      ConfigurationVersion
                                     PolicySHA + TransformID
                                     Timestamp
```

* Every scientific run records dataset bytes (`.sha256`), policy digest, study-protocol digest, engine commit, and environment (ADR 0006, ADR 0011 — unchanged).
* Every customer run records `DemandVersion + PatentDatasetVersion + EngineVersion + ConfigurationVersion + PolicySHA + TransformID + Timestamp → Ranked Matches → Evidence + Audit Trail`.
* `PolicySHA` and `TransformID` (the ADR 0016 fusion transform identity) are mandatory members of the customer contract: without them reproducibility claims are false.
* Neither context mutates the other's sealed artifacts. The product freezes `EngineVersion + ConfigVersion` per `MatchRun`; the lab freezes benchmark + protocol per `EvaluationRunReport`.

### 5. Binding principles

1. The scientific benchmark is not the product.
2. The product does not wait for Phase 2. Product work proceeds in parallel from PR-A onward.
3. The deterministic core feeds both scientific experiments and customer workflows through the same typed entrypoint.
4. Provenance, determinism, versioning, and auditability are simultaneously scientific requirements and product properties.
5. The product never presents Nexus as a substitute for patent counsel, patentability analysis, freedom-to-operate, or legal opinion — in UI, API responses, exports, or commercial material.
6. Initial commercial positioning is **technology/IP intelligence and recall aid**, never a substitute for a legal prior-art search.
7. Current limitations (abstract-only corpus, 128-token embedding truncation, unvalidated CPC-auto classifier, no family deduplication, ES 2016–2024 coverage, pilot sample unrepresentative of T3 rights) are disclosed, not hidden.
8. Pilot results (`PILOT / PROOF_OF_HARNESS`) are never used as commercial efficacy claims.
9. `PILOT / PROOF_OF_HARNESS` stays strictly separated from any future `PHASE_2 / EFFICACY_EVALUATION`.
10. Product infrastructure is designed so it cannot contaminate the scientific protocol or leak into benchmarks (no shared mutable state, no unversioned configuration, no silent re-ranking).

### 6. Licensing and data rights is a commercial gate, not a feature

P8 (licensed data sources) is a **parallel commercial gate**, not an ordinary product PR. Rule: **without sufficiently clear commercial usage rights for a source, Nexus neither promises nor commercialises monitoring over that source.** This does not block scientific work over legitimately available snapshots. The gate has veto power over monitoring promises and over any revenue-bearing pilot that depends on the gated source.

### 7. Pilotable vs production-ready

**Pilotable** (commercial Definition of Done for this phase):

* Matching Store (Demand, DemandVersion, MatchRun with the §4 contract, Match, Evidence)
* Persistent jobs / MatchRuns (container restart is not data loss)
* Reduced lifecycle (`INGESTED → MATCHED → REVIEWED → MONITORED → ARCHIVED`)
* Auditable export (CSV + JSON with version hashes)
* Disclaimers + coverage disclosure in UI, API, and exports

**Explicitly out of scope** (neither required for a paid pilot nor to be built prematurely):

* SSO, full multi-tenancy, SLA, billing, enterprise infrastructure, production-scale operation

Tenant isolation is carried as a `tenant_id` field from the Matching Store PR onward; building the system around it is deferred until a second customer or confidential data requires it.

---

## What this ADR does not do

* Creates no directories, models, tables, or migrations. The Product Core entity sketch (`Organization → Demand → DemandVersion / MatchRun / Match / Evidence / Review / Export / MonitoringEvent`) remains a proposal for the Matching Store PR, with `Organization` reduced to a field and the lifecycle reduced per §7 until real pilot needs say otherwise.
* Implements nothing from ADR 0016 (fusion transform) or M1 wiring. The next code change remains the ADR 0016 implementation, in a separate PR.
* Edits no existing ADR. Known documentary contradictions are recorded in the canonical roadmap (`../roadmap.md`), not repaired here: `docs/architecture.md` still describes the pre-UC1 ip-matchmaker topology, archived hackathon material still promises ScoreCards "for patent filings", and the M0–M6 hypothesis family (strict MRR) and the empirical study protocol (primary `nDCG@10`) still name different primary endpoints. Those reconciliations belong to their respective Lab/Product PRs.
* Introduces no tuning, no re-weighting, and no benchmark contact of any kind.

## Consequences

### Positive

* Lab and Product stop blocking each other: the product freezes engine/config versions per run while the lab freezes benchmark/protocol per report, with no shared mutable state between them.
* The ADK generative path keeps its demo and UX value without contaminating scientific validity — the two-heads ambiguity that motivated this ADR is resolved by classification, not by deletion.
* Commercial pilots become possible on provenance and auditability alone, without waiting for powered efficacy results.
* Licensing risk is fenced by a gate with veto power instead of being discovered during a customer pilot.

### Negative

* Two heads must still be maintained until the product demonstrably subsumes the demo narrative; Head A is quarantined, not removed, which carries ongoing maintenance cost.
* The reduced lifecycle and deferred tenancy will need revisiting at the second customer — this ADR buys focus now at the price of a known future migration.
* The recorded (not repaired) documentary contradictions mean `docs/architecture.md` and the MRR-vs-`nDCG@10` endpoint question remain open items with explicit owners (roadmap), not silent drift.

## Enforcement

A Pull Request is **non-compliant** with this ADR if it:

1. Lets Lab code import product workflow types (jobs, tenants, exports, monitoring), or lets product code import `domain/models/evaluation` or anything under `config/evaluations/` or `data/evaluation/`, except through the existing `matching_adapter.py` Lab boundary.
2. Writes product runtime state into `data/evaluation/`, mutates `config/evaluations/*` outside a Lab PR, or re-ranks a sealed `MatchRun`/`EvaluationRunReport` in place instead of producing a new versioned run.
3. Uses pilot (`PILOT / PROOF_OF_HARNESS`) numbers in commercial material, UI copy, or export templates.
4. Presents any score, rank, or `ScoreCard` as patentability, freedom-to-operate, or legal opinion, or omits the recall-aid disclaimer and coverage disclosure from a customer-facing surface.
5. Promises or bills monitoring over a source that has not passed the §6 commercial gate.
6. Introduces SSO, full multi-tenancy, SLA, or billing machinery before a documented pilot need requires it.
7. Tunes, re-weights, or re-derives any model, transform, or threshold against the frozen benchmark under the guise of either track (governed jointly with ADR 0012).
