# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Patent Innovation Agent — finds patentable white-space opportunities by mining patent
landscapes (Google Patents Public Datasets on BigQuery, mocked by default), proposing
candidate inventions, stress-testing them against prior art, and scoring survivors with
traceable evidence. Built for a hackathon (see `docs/roadmap.md` for the day-by-day plan
and current status; `docs/architecture.md` for the system design/data-flow contract).

## Commit attribution

Every commit in this repo must credit **Lydia Bares** (`lydiabares@gmail.com`) as
co-author, in addition to the Claude co-author trailer, on every commit:

```
Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

## Commands

### Backend (`backend/`)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env        # defaults to USE_MOCK_BIGQUERY=true, no GCP creds needed
adk web patent_agent           # interactive ADK dev UI, exercises the full agent graph
# or:
uvicorn main:app --reload --port 8080   # FastAPI wrapper (Cloud Run entrypoint)
pytest                         # run all tests
pytest tests/test_clustering.py::test_cluster_patents_empty_input   # single test
```

### Frontend (`frontend/`)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev        # vite dev server
npm run build       # tsc -b && vite build
npm run lint        # oxlint
```

## Architecture

Backend is a Python **Google ADK** agent graph, wrapped by a thin FastAPI app
(`backend/main.py`) that serves as the Cloud Run entrypoint. Frontend is a React + Vite
SPA that renders the pipeline via two plain REST endpoints — it does not talk to the
ADK web protocol directly.

### Agent graph (`backend/patent_agent/agent.py`)

`root_agent` = `SequentialAgent([research_agent, invention_loop, governor_agent])`, where
`invention_loop` = `LoopAgent([inventor_agent, adversarial_agent])` (propose → critique,
repeats until `adversarial_agent` calls `exit_loop` or `INVENTION_LOOP_MAX_ITERATIONS`
is hit). Each sub-agent lives under `backend/patent_agent/sub_agents/<name>/` with its
own `agent.py` + `prompt.py`. Data contracts shared between agents (via ADK session
state) are defined once in `backend/patent_agent/tools/schemas.py` — `PatentRecord`,
`PatentCluster`, `InventionCandidate`, `AdversarialVerdict`, `ScoreCard` — and the state
keys they're stored under are centralized in `backend/patent_agent/shared/state_keys.py`.
Treat both files as the source of truth before touching agent I/O; `docs/architecture.md`'s
shared-state table must stay in sync with `state_keys.py`.

Note: `LoopAgent`/`SequentialAgent` are deprecated in favor of a newer ADK `Workflow`
API, but are deliberately still used here because `Workflow` can't yet nest as an
`LlmAgent` sub-agent (see comment in `agent.py` and the roadmap's decisions log).

### Deterministic vs. LLM-backed steps

Not everything in the pipeline is an LLM call. The clustering step
(`backend/patent_agent/tools/clustering.py`) is a plain `FunctionTool` — a CPC-prefix
heuristic (`white_space_score = 0.4·(1-density) + 0.2·recency + 0.15·citation_velocity
+ 0.25·demand`), deliberately credential-free. `GET /api/landscape` in `backend/main.py`
calls the patents/demand data sources + `cluster_patents` directly, bypassing the ADK
Runner/Gemini — it works with zero external credentials. `POST /api/analyze` runs the
full agent graph for one cluster (requires GEMINI_API_KEY); both endpoints are used by
the frontend's OpportunityMap component. Demand data source selection is controlled by
`DEMAND_SOURCE` (`mock` | `innoget`).

### Mock/real data swap

`backend/patent_agent/tools/bigquery_patents.py` has both a real BigQuery-backed data
source and `MockPatentsDataSource` (fixtures in `tools/fixtures.py`). Which one is used
is controlled entirely by `USE_MOCK_BIGQUERY` (`backend/patent_agent/config.py`) — no
call-site code changes needed to swap. Tests set `USE_MOCK_BIGQUERY=true` and run
against the mock source; the locked demo domain across mocks/tests is "solid-state
electrolytes for EV batteries" (see roadmap §2 for why).

### Frontend

`frontend/src/api/client.ts` calls the backend's `/api/landscape` REST endpoint (not
ADK's own web protocol). `frontend/src/types/patent.ts` should mirror the Pydantic
schemas in `backend/patent_agent/tools/schemas.py` — check both when changing the
landscape/cluster response shape.

### CORS

ADK's `get_fast_api_app` has its own origin-check middleware that a plain
`CORSMiddleware` added after the fact does not override — allowed origins are passed in
directly via `FRONTEND_ORIGINS` (comma-separated) in `backend/main.py`.
