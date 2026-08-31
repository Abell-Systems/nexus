# Abell Nexus

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
- **Governance**: Operationally governed by [CIRCLE](.circle/).

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

## 4. Operational Governance

This repository is governed by the **CIRCLE** protocol (`OBSERVE → UNDERSTAND → DECIDE → ACT → VERIFY → LEARN`). Operational evolution, architectural decisions, and post-hackathon milestones are tracked in [.circle/cycle.md](.circle/cycle.md) and archived in [.circle/history/](.circle/history/).
