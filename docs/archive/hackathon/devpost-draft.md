# Devpost Submission Draft — IP Matchmaker

**Project Name:** IP Matchmaker (Patent Innovation Agent)  
**Tagline:** Autonomous R&D intelligence matching industry tech calls with patent white-space opportunities using Google ADK & Gemini 3.5.  
**Track:** The Taskmaster ("Build a complete workflow, not just a chatbot... make one that takes action.")  

---

## 1. One-Line Pitch
IP Matchmaker mines global patent landscapes and market-pull technology calls, autonomously generating, stress-testing, and scoring patentable inventions with traceable prior-art evidence.

---

## 2. The Problem
R&D teams face a dual challenge: industry technology calls (e.g. Innoget, SBIR) express urgent market demand, but existing patent landscapes are dense, complex, and hard to navigate. Traditional search tools return endless lists of keywords without identifying true white space or verifying whether proposed solutions conflict with prior art.

---

## 3. The Solution
IP Matchmaker provides an end-to-end autonomous R&D workflow:
1. **Market-Pull Ingestion**: Parses open technology calls (Innoget dataset) into structured `DemandSignal` objects.
2. **Patent Landscape Clustering**: Queries Google Patents Public Datasets on BigQuery and scores technology clusters using a quantitative white-space formula ($0.40 \cdot \text{density} + 0.20 \cdot \text{recency} + 0.15 \cdot \text{citation\_velocity} + 0.25 \cdot \text{demand}$).
3. **Autonomous Invention Loop**: An **Inventor Agent** proposes candidate inventions for white-space gaps, while an **Adversarial Agent** stress-tests them against prior art, forcing iterative refinement.
4. **Innovation Governor & Traceability**: An **Innovation Governor Agent** scores surviving candidates across novelty, prior-art risk, differentiation, and evidence, backing every score with exact patent publication numbers.

---

## 4. Technical Architecture

```text
[Innoget Tech Calls] ──> [InnogetDemandDataSource] ──┐
                                                    ├──> [clustering.py] ──> [Frontend landing/results UI]
[Google Patents / BQ] ──> [PatentsDataSource] ──────┘           │
                                                                ▼
                                                [POST /api/analyze (ADK Runner)]
                                                                │
                                            ┌───────────────────┴───────────────────┐
                                            ▼                                       ▼
                                   [research_agent]                         [governor_agent]
                                            │                                       ▲
                                            ▼                                       │
                                 [invention_loop (LoopAgent)] ──────────────────────┘
                                 ├── inventor_agent (proposes)
                                 └── adversarial_agent (critiques + cites prior art)
```

- **Agent Framework**: Built using **Google ADK** (Python), composing `LlmAgent`, `SequentialAgent`, and nested `LoopAgent`.
- **LLM Engine**: Powered by **Gemini 3.5** (`gemini-3.5-flash` / `gemini-3.5-flash-lite`).
- **Data Layer**: Google Patents Public Datasets on BigQuery + Innoget Technology Calls feed.
- **Frontend**: React + Vite (TypeScript) rendering a live execution feed and results view with background-job polling (`POST /api/analyze` $\rightarrow$ `202 Job Accepted` $\rightarrow$ `GET /api/analyze/{job_id}`), plus a history view to reopen past analyses.
- **Infrastructure**: Cloud Run containerized deployment (`backend/Dockerfile`).

---

## 5. Why "The Taskmaster"?
IP Matchmaker is not a conversational chatbot. It takes direct action:
- Executes multi-step search & landscape clustering queries.
- Runs an autonomous propose-critique loop where agents challenge each other using real patent citations.
- Outputs actionable, traceable `ScoreCard` artifacts that R&D directors can use immediately for patent filings or technology licensing decisions.

---

## 6. Example Finding & Validation
In our live validation run on solid-state battery electrolytes:
- **Input Domain**: Solid-state electrolytes for EV batteries.
- **Market Demand**: A simulated demand signal for high-conductivity, stable interface coatings. `InnogetDemandDataSource` parses a real, locally-collected Innoget technology-calls dataset, but its 19 records don't currently cover the battery domain, so the deployed demo runs `DEMAND_SOURCE=mock` for this locked domain -- the `demand` term in the white-space formula is real code, exercised with representative fixture data rather than a live match.
- **White-Space Cluster**: `cluster-C08L` (Polymer compositions / interfacial buffer layers).
- **Candidate Invention**: *"Zwitterionic Polyimide MLD Interfacial Buffer Layer"*.
- **Adversarial Verdict**: Rejected initial draft citing 4 prior-art publication numbers (`US-10448361-B2-17`, `US-10437821-B2-0`), prompting the Inventor agent to refine the chemical composition.
- **Governor ScoreCard**: Novelty 0.92, Prior-Art Risk 0.85, Differentiation 0.88, Evidence 0.95, backed by traceable citations.

---

## 7. Setup & Reproducibility

```bash
# Clone & install backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env

# Run full test suite (89/89 tests passing)
.venv/bin/pytest tests/ -v

# Run interactive ADK Web UI or FastAPI server
adk web patent_agent
# or: uvicorn main:app --reload --port 8080
```

```bash
# Frontend setup
cd frontend
npm install
npm run dev
```

---

## 8. Devpost Submission QA Checklist

- [x] **Hosted project URL**: Verified Cloud Run endpoint (`https://patent-agent-...run.app`).
- [x] **Description & Features**: Fully articulated 4-stage pipeline (Research, Cluster, Loop, Governor).
- [x] **Data sources**: Google Patents Public Datasets on BigQuery (real, via a materialized domain index -- see `docs/deploy.md` §2b) + a simulated market-demand signal (`InnogetDemandDataSource` implements real Innoget dataset parsing, but the deployed demo uses `DEMAND_SOURCE=mock` since the current 19-record Innoget fixture doesn't cover the battery domain).
- [x] **Findings/learnings**: Solid-state electrolyte case study documented with before/after agent iteration.
- [x] **Repository URL**: GitHub public repo with complete setup instructions.
- [x] **README spin-up**: Reproducible instructions for both mock and real GCP modes.
- [x] **Architecture diagram**: Embedded 1-page Mermaid & ASCII topology in `docs/architecture.md`.
- [ ] **Demo Video (≤ 4 min)**: Script is ready and timed (`docs/demo-script.md`), but no video has been recorded/uploaded yet. A script is not a video — do not check this until a YouTube/Vimeo link exists and has been watched end-to-end.
- [x] **Google Cloud proof**: Cloud Run dashboard & URL visible in live demo.
- [x] **Hackathon Track**: **Taskmaster**.
- [x] **Gemini requirement**: Configured with `gemini-3.5-flash`.
- [x] **Google Agent Framework requirement**: Built natively with Google ADK (`SequentialAgent`, `LoopAgent`, `LlmAgent`).
- [x] **Google Cloud Infrastructure requirement**: Deployed on Cloud Run. Live deploy runs `USE_MOCK_BIGQUERY=false`, serving real BigQuery data via a materialized domain index (`patent_agent_index.domain_index`, ~15.7MB/query vs. ~245GB against the raw public dataset — see `docs/deploy.md` §2b).
