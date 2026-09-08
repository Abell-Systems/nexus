# Abell Nexus

<!-- PROJECT_STATUS:START -->
[![Project Status](https://img.shields.io/badge/Project_Status-PASS-brightgreen)](PROJECT_STATUS.md)
[![CI Gates](https://img.shields.io/badge/CI_Gates-PASS-brightgreen)](https://github.com/Abell-Systems/nexus/actions/workflows/ci.yml)
[![Architecture](https://img.shields.io/badge/Architecture-PASS-brightgreen)](PROJECT_STATUS.md#architecture-pass)
[![Tests](https://img.shields.io/badge/Tests-566_passed-brightgreen)](PROJECT_STATUS.md#backend_testing-pass)
[![Coverage](https://img.shields.io/badge/Coverage-80.24%25-brightgreen)](PROJECT_STATUS.md#backend_coverage-pass)
[![Docs](https://img.shields.io/badge/Docs-PASS-brightgreen)](PROJECT_STATUS.md#documentation-pass)
[![Scientific Integrity](https://img.shields.io/badge/Scientific_Integrity-PASS-brightgreen)](PROJECT_STATUS.md#scientific_integrity-pass)
[![SonarCloud](https://img.shields.io/badge/SonarCloud-UNVERIFIED-yellow)](PROJECT_STATUS.md#sonar_cloud-unverified)

> **Verified against:** `edb0c732e6` · `2026-09-08T16:36:36.933417+00:00` · [Full Project Status](PROJECT_STATUS.md)
<!-- PROJECT_STATUS:END -->

> **Autonomous Technology Discovery, White-Space Synthesis & Prior-Art Defense.**

**Abell Nexus** is an autonomous deep-tech intelligence system built by **Abell Systems**. It continuously mines global technology demand and patent landscapes to discover uncrowded white space, autonomously synthesize candidate inventions, stress-test them in adversarial prior-art loops, and emit verifiable, citation-backed innovation scorecards.

---

## 1. Lineage & Sovereignty

> **`Abell Nexus` emerged from the research prototype developed in `ip-matchmaker`. Nexus is the sovereign production system.**

---

## 2. Core Architecture

```text
[Industrial Tech Calls] ──> [Demand Ingestion] ──┐
                                                 ├──> [Landscape Clustering] ──> [Nexus UI]
[Google Patents / BQ]   ──> [Patent Data Lake] ──┘           │
                                                             ▼
                                             [Autonomous Innovation Pipeline]
                                                             │
                                         ┌───────────────────┴───────────────────┐
                                         ▼                                       ▼
                                [Research Agent]                        [Governor Agent]
                                         │                                       ▲
                                         ▼                                       │
                              [Adversarial Loop (LoopAgent)] ────────────────────┘
                              ├── Inventor Agent (Synthesizes candidate)
                              └── Adversarial Agent (Critiques & cites prior art)
```

- **LLM Engine**: Gemini 3.5 via Google ADK (`gemini-3.5-flash` / `gemini-3.5-flash-lite`).
- **Data Engine**: Google Patents Public Datasets on BigQuery + Industrial Technology Calls.
- **Verification Engine**: Multi-agent propose-critique loop enforcing strict prior-art traceability (`supporting_evidence` and `cited_patents`).
- **Frontend**: React + Vite (TypeScript) with live execution feed, causal chain inspection, and analysis history.
- **Architecture & Invariants**: Governed by binding Architecture Decision Records ([docs/adr/](docs/adr/)), automated CI quality gates, and invariant tests.

---

## 3. Quickstart (Local Development)

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # USE_MOCK_BIGQUERY=true by default
uvicorn main:app --reload --port 8080
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 4. Architecture & Engineering Governance

Nexus enforces decoupled Clean Architecture and rigorous empirical standards backed by automated CI quality gates. Architectural decisions, scientific contracts, and non-regression policies are recorded as binding contracts in [docs/adr/](docs/adr/) and enforced via:
- **Binding Architecture Decision Records**: [ADR 0001](docs/adr/0001-nexus-testing-strategy.md) through [ADR 0021](docs/adr/0021-engineering-quality-and-non-regression.md).
- **Automated Verification**: Ruff, Mypy, Import Linter, Vitest, Pytest, and docs correctness gates run on every pull request.
- **Scientific Reproducibility**: Sealed datasets, manifests, SHA-256 sidecars, and pre-registered hypotheses.
