# Phase 2 Demand Independence Audit — Protocol

**Status:** Closed. Resolves the roadmap's "demand independence audit" gap for the organization axis only (see "Explicit separation from other independence axes" below).

## Why this exists

`docs/roadmap.md` (§6, external scientific-rigor review):
> *"Demand independence audit: the existing Phase-2 audits (#84–#86) check whether each demand is a valid technology solicitation (construct eligibility), not whether the 39/24/60 demands are independent observations (same company, sector, tech family, or duplicate industrial problem). These are different questions; only the first has been done."*

This document formalizes the closure of the company/organization axis: demands submitted by the same requesting organization share vocabulary, domain assumptions, and problem context, constituting pseudoreplicates rather than independent draws from the industrial innovation demand population.

## Explicit separation from other independence axes

**Sector, technology family, and duplicate-industrial-problem non-independence are not addressed here and are not inferred from organization identity.**
* A demand can share an organization with another demand while addressing distinct technical problems.
* Conversely, two demands from distinct organizations can describe duplicate technical problems.
* Text-similarity heuristics for problem deduplication are explicitly rejected to prevent circularity with the IR relevance judgments under evaluation (ADR 0029).

## Grouping rule

For each of the N=24 eligible demands, using only `requesting_organization` from acquisition-time metadata (`dataset_phase2_demand_corpus_n39.origin_audit.json`):
1. **Exact string match only:** Two demands with identical, non-empty, non-placeholder `requesting_organization` strings are grouped together.
2. **Representative selection:** The lexicographically smallest `demand_id` in each group is marked `INDEPENDENT`; all others are marked `PSEUDOREPLICATE`.
3. **Non-identifying placeholder handling:** Demands with `requesting_organization == "Anonymous Organization"` or `None` receive `independence_group_id = None` and `status = INDEPENDENT`, and are never grouped with each other.

## Closure & Real Data Findings

Applied to `dataset_phase2_eligible_corpus_n24_v1.json` (24 demands) via `generate_independence_audit.py`, frozen as `phase2_demand_independence_audit_n24_v1.json`:
* **18 INDEPENDENT**, **6 PSEUDOREPLICATE**.
* Multi-member groups:
  - **SMAR3TS** (5 members): `INNOGET-2401` retained as independent; `INNOGET-2403`, `INNOGET-2404`, `INNOGET-2405`, `INNOGET-2417` classified as pseudoreplicates.
  - **Lacer, S.A** (3 members): `INNOGET-2491` retained as independent; `INNOGET-2492`, `INNOGET-2493` classified as pseudoreplicates.
* Non-identifying placeholders: 4 `"Anonymous Organization"` demands and 2 `None`-organization demands retained as distinct independent observations.
* Singletons: 10 organizations each appear exactly once.
* Independent corpus projected as `dataset_phase2_independent_corpus_v1.json` (N=18).

## Critical Dev/Test Leakage Audit

An audit of the frozen split `devtest_split_n13_v1.json` against organization groups showed:
* **SMAR3TS:** `INNOGET-2404` (Dev) vs `INNOGET-2403` (Test).
* **Lacer, S.A:** `INNOGET-2491` (Dev) vs `INNOGET-2492`, `INNOGET-2493` (Test).
* **Contamination:** 2 of 2 multi-member groups straddle the Dev/Test boundary, affecting 5 of 13 split demands (38.5%).
* **Scientific invariant:** For the powered efficacy comparison, organization-level independent observations must not cross the Dev/Test boundary.
* **Resolution:** `devtest_split_n13_v1.json` is contaminated and must not be used for confirmatory powered testing; clean re-partitioning is required.

## Sample Size Status

* **N=18 is not automatically the new powered-study sample.** It is an audit finding and a derived independent corpus from the current N=24 eligible set.
* The pre-registered minimum sample size for 80% power at $\theta = 0.2$ remains **$|\mathcal{D}| = 60$** (`docs/empirical-study-protocol.md` §3.2). N=18 does not satisfy this target.
