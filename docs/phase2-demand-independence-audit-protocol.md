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

## Tripartite Grouping Rule

For each of the N=24 eligible demands, using only `requesting_organization` from acquisition-time metadata (`dataset_phase2_demand_corpus_n39.origin_audit.json`):
1. **Exact string match only:** Demands with an identical, non-empty, non-placeholder `requesting_organization` string form an organization group.
2. **Representative selection:** Within a group, the lexicographically smallest `demand_id` is marked `INDEPENDENT`; all remaining members are marked `PSEUDOREPLICATE`.
3. **Non-identifying placeholder handling:** Demands with `requesting_organization == "Anonymous Organization"` or `None` receive `independence_group_id = None` and `status = UNKNOWN`. Because their organization is unknown, their independence cannot be verified (`UNKNOWN != INDEPENDENT`). They are never grouped with each other.

## Closure & Real Data Findings

Applied to `dataset_phase2_eligible_corpus_n24_v1.json` (24 demands) via `generate_independence_audit.py`, frozen as `phase2_demand_independence_audit_n24_v1.json`:
* **12 INDEPENDENT** (verified independent observations):
  - 10 singleton organizations: `Bax & Company`, `ALLIANCE project`, `Celsa Group`, `Familia Torres`, `Fundingbox`, `Blue Room Innovation`, `Alberto from Pharmactive Biotech Products`, `Indira from Bax&Co`, `Repsol`, `INDUSAC`.
  - 2 group representatives: `INNOGET-2401` (SMAR3TS), `INNOGET-2491` (Lacer, S.A).
* **6 UNKNOWN** (indeterminate organization independence):
  - 4 demands carrying `"Anonymous Organization"` placeholder (`INNOGET-1625`, `INNOGET-1932`, `INNOGET-1935`, `INNOGET-1972`).
  - 2 demands with `requesting_organization is None` (`LOMBARDIA-860`, `LOMBARDIA-947`).
* **6 PSEUDOREPLICATE** (excluded duplicate observations):
  - 4 from `SMAR3TS` (`INNOGET-2403`, `INNOGET-2404`, `INNOGET-2405`, `INNOGET-2417`).
  - 2 from `Lacer, S.A` (`INNOGET-2492`, `INNOGET-2493`).
* **Operational organization-audited corpus:** `dataset_phase2_organization_audited_corpus_v1.json` ($N=18$), retaining the 12 verified independent demands plus 6 demands with unknown organization independence. For confirmatory inference, only the 12 verified independent observations provide demonstrated degrees of freedom.

## Critical Dev/Test Leakage Audit

An audit of the frozen split `devtest_split_n13_v1.json` against organization groups showed:
* **SMAR3TS:** `INNOGET-2404` (Dev) vs `INNOGET-2403` (Test).
* **Lacer, S.A:** `INNOGET-2491` (Dev) vs `INNOGET-2492`, `INNOGET-2493` (Test).
* **Contamination:** 2 of 2 multi-member groups straddle the Dev/Test boundary, affecting 5 of 13 split demands (38.5%).
* **Binding architectural invariant:**
  > **No puede haber dos demandas con una identidad organizativa observada común en lados distintos de Dev/Test.**  
  > *(No two demands with a shared observed organization identity may appear on opposite sides of the Dev/Test boundary.)*
* **Resolution:** `devtest_split_n13_v1.json` is contaminated at the organization level and cannot be used for confirmatory powered testing; clean re-partitioning is required.

## Sample Size Status

* **Neither N=18 nor N=12 is the new powered-study sample.** They are audit findings from the current N=24 eligible set.
* The pre-registered minimum sample size for 80% power at $\theta = 0.2$ remains **$|\mathcal{D}| = 60$** (`docs/empirical-study-protocol.md` §3.2).
