# Abell Nexus

<!-- PROJECT_STATUS:START -->
[![Project Status](https://img.shields.io/badge/Project_Status-PASS-brightgreen)](PROJECT_STATUS.md)
[![CI Gates](https://img.shields.io/badge/CI_Gates-PASS-brightgreen)](https://github.com/Abell-Systems/nexus/actions/workflows/ci.yml)
[![Architecture](https://img.shields.io/badge/Architecture-PASS-brightgreen)](PROJECT_STATUS.md#architecture-pass)
[![Tests](https://img.shields.io/badge/Tests-995_passed-brightgreen)](PROJECT_STATUS.md#backend_testing-pass)
[![Coverage](https://img.shields.io/badge/Coverage-95.53%25-brightgreen)](PROJECT_STATUS.md#backend_coverage-pass)
[![Docs](https://img.shields.io/badge/Docs-PASS-brightgreen)](PROJECT_STATUS.md#documentation-pass)
[![Scientific Integrity](https://img.shields.io/badge/Scientific_Integrity-PASS-brightgreen)](PROJECT_STATUS.md#scientific_integrity-pass)
[![SonarCloud](https://img.shields.io/badge/SonarCloud-UNVERIFIED-yellow)](PROJECT_STATUS.md#sonar_cloud-unverified)
[![Scientific Dashboard](https://img.shields.io/badge/Scientific_Dashboard-Live-blue)](https://abell-systems.github.io/nexus/)

> **Verified against:** `a427ca5419` · `2026-09-30T14:05:27.461362+00:00` · [Scientific Dashboard](https://abell-systems.github.io/nexus/) · [Full Project Status](PROJECT_STATUS.md) · [Raw Contract](project_status.json)
<!-- PROJECT_STATUS:END -->

> **From a real technology demand to Spanish patents and utility models.**

**Abell Nexus** takes a real technology demand and retrieves the Spanish industrial-property assets most similar to it, showing for each one its holder, abstract, its own CPC codes and links to the public source. It is a **prototype MVP on real data**, built by **Abell Systems**.

---

## 1. What it does today

- You pick one of 21 example demands ingested from Innoget (the demand text and a link to the original are shown).
- Nexus ranks **54,997 Spanish patents and utility models** (Spanish applicant, one per family, from Google Patents Public Data) against it and shows the top five of the 44,195 eligible assets.
- Matching is **cross-lingual**: a frozen multilingual embedding model (`paraphrase-multilingual-mpnet-base-v2`, pinned revision) compares English demands with Spanish patent text. About 0.2 s per query.
- The only ordering signal shown is the rank. There is no score and no quality band.
- Every result links to its public source (Google Patents, Espacenet). A chosen demand has its own URL (`/?demanda=INNOGET-1935`).

## 2. What it does not claim

- **Ranking quality is not validated by humans.** An internal estimate exists, judged by a language model, and the screen says so. The pre-registered human evaluation is parked.
- Only the example demands: there is no free-text search, and no question from the audience can be answered live.
- Only patents and utility models filed in Spain by Spanish applicants; EP records with a Spanish applicant are not included yet.
- No "unexploited asset" detection, no price, demand or market-size figures.
- Data licence: Google Patents Public Data is CC BY 4.0 and the attribution is on screen. Counsel has not yet confirmed the chain of underlying patent-office data, which is required before charging for anything.

Details and reproducible evidence: [operational runbook](docs/operational-mvp-runbook.md), [quality evidence](docs/operational-mvp-quality-evidence.md), [design spec](docs/superpowers/specs/2026-09-30-demand-to-assets-mvp-design.md).

## 3. Run it

The frozen data (`data/snapshots/operational_corpus_v1/`, about 230 MB of third-party text and vectors) is **not in git**; the runbook explains how to rebuild it.

```bash
cd frontend && npm install && npm run build && cd ..
cd backend/src/main && python -m infrastructure.mvp_entrypoint --artifacts ../../../data/snapshots/operational_corpus_v1 --static ../../../frontend/dist   # open http://127.0.0.1:8080/
python scripts/demo_preflight.py     # before any demo: checks the server is the current build
```
Tests: `python -m pytest backend/test`, `cd frontend && npm test`, and the pre-release gate in the runbook (real-artifact integration test and a Playwright browser journey).

## 4. Architecture

```text
frozen, hash-verified artifacts ──> infrastructure (load and verify at startup, NumPy retrieval)
                                        │ implements ports
                                        ▼
                               application (find assets for a demand)
                                        │
                                        ▼
                                  domain (Asset, demand, eligibility)
                                        ▲
                     delivery: two HTTP routes + one React screen
```

- Clean Architecture: dependencies point inward, enforced by Import Linter. The runtime never imports torch or transformers ([ADR 0014](docs/adr/0014-m1-semantic-ranking-protocol.md)); embeddings are generated offline and verified by hash at startup, and any mismatch aborts startup.
- The backend exposes only `/health`, `/api/demand-examples`, `/api/matches` and the static files, with a stable `{code, message}` error contract.
- The repository also contains the research code behind the evaluation protocols (`experiments/`) and an earlier agent prototype that is neither served nor reachable.

---

## 5. Engineering Governance

Nexus enforces decoupled Clean Architecture and rigorous empirical standards backed by automated CI quality gates. Architectural decisions, scientific contracts, and non-regression policies are recorded as binding contracts in [docs/adr/](docs/adr/) and enforced via:
- **Binding Architecture Decision Records**: [ADR 0001](docs/adr/0001-nexus-testing-strategy.md) through [ADR 0024](docs/adr/0024-scientific-verification-workspace.md).
- **Automated Verification**: Ruff, Mypy, Import Linter, Vitest, Pytest, and docs correctness gates run on every pull request.
- **Scientific Reproducibility**: Sealed datasets, manifests, SHA-256 sidecars, and pre-registered hypotheses.

---

## 6. Scientific Verification Dashboard

Nexus publishes its live empirical status as an autonomous presentation consumer of the canonical [`project_status.json`](project_status.json) contract (governed by [ADR 0022](docs/adr/0022-project-status-contract.md), [ADR 0023](docs/adr/0023-scientific-verification-as-external-consumer.md), and [ADR 0024](docs/adr/0024-scientific-verification-workspace.md)):

* **Live Dashboard:** [https://abell-systems.github.io/nexus/](https://abell-systems.github.io/nexus/)
* **Canonical Machine Contract (Tier 3):** [`project_status.json`](project_status.json)
* **Audited Telemetry Report (Tier 2):** [`PROJECT_STATUS.md`](PROJECT_STATUS.md)

The dashboard is decoupled from the Nexus core engine, executes as a static SPA deployed to GitHub Pages from the bounded monorepo workspace `nexus-status/frontend/`, and strictly renders repository verdicts without synthesizing or recalculating evidence.

