# User Zero Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the UI and backend telemetry into a zero-friction, decision-oriented platform for "User Zero" that demonstrates an autonomous agent finding, attacking, revising, scoring, and proving patent white-space opportunities.

**Architecture:** Extend backend job tracking in `backend/main.py` to publish explicit real-time execution stages (`stage`) and telemetry counters (`progress`), unifying research and analysis into a single `POST /api/analyze` job. Redesign frontend into a 3-state User Zero view (Landing → Execution Pipeline → Decision & Causal Chain Results).

**Tech Stack:** Python 3.11, FastAPI, Pydantic, ADK, React 18, TypeScript, Vite, CSS Modules, pytest.

## Global Constraints

- Backend as single source of truth: No client-side fake progress or stage interpolation.
- No technical jargon in UI: Use problem-domain terms (*Prior-art challenge*, *Final assessment*).
- All commits must credit Lydia Bares (`lydiabares@gmail.com`) and Claude Sonnet 5 as co-authors.

---

### Task 1: Backend Job Telemetry & Pipeline Stage Engine

**Files:**
- Modify: `backend/main.py`
- Create: `backend/tests/test_user_zero_api.py`

**Interfaces:**
- Consumes: Existing `get_patents_datasource()`, `get_demand_datasource()`, `cluster_patents()`, `root_agent`, `_session_service`, `_runner`
- Produces: `POST /api/analyze` accepting `{ domain: string, query?: string }`, returning `{ job_id: string, status: "running", stage: "researching" }`
- Produces: `GET /api/analyze/{job_id}` returning `{ job_id, status, stage, progress, clusters, candidates, verdicts, scorecards, error }`

- [ ] **Step 1: Write failing test for backend telemetry and job status endpoint**

```python
# backend/tests/test_user_zero_api.py
import pytest
from fastapi.testclient import TestClient
from main import app, _jobs

client = TestClient(app)

def test_analyze_job_telemetry():
    response = client.post("/api/analyze", json={
        "domain": "solid-state battery electrolytes",
        "query": "solid electrolyte interphase"
    })
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "running"
    assert data["stage"] in ("queued", "researching")

    job_id = data["job_id"]
    status_resp = client.get(f"/api/analyze/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "stage" in status_data
    assert "progress" in status_data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_user_zero_api.py -v`
Expected: FAIL (missing fields `stage`/`progress` or payload structure mismatch).

- [ ] **Step 3: Implement backend telemetry & job tracking in `backend/main.py`**

Update `AnalyzeRequest` in `backend/main.py`:
```python
class AnalyzeRequest(BaseModel):
    domain: str = Field(min_length=1)
    query: str = Field(default="solid electrolyte interphase")
    cluster_id: str | None = None
```

Update `_run_job` and `_execute_analysis` in `backend/main.py` to record stage and telemetry updates directly:
- `stage="researching"`: Query patents datasource and demand signals. Record `progress={"patentsAnalyzed": len(records)}`.
- `stage="clustering"`: Run `cluster_patents`. Record `progress={"patentsAnalyzed": ..., "clustersFound": len(clusters)}` and store `clusters` in job object.
- `stage="inventing"`: Run ADK agent loop. Inspect ADK session state to count generated candidate inventions (`progress={"candidatesGenerated": len(candidates)}`).
- `stage="adversarial"`: Count verdicts (`candidatesRejected`, `candidatesRevised`, `candidatesSurvived`).
- `stage="governor"`: Generate final scorecards and evidence citations.
- `stage="done"`: Set status to `done`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && pytest tests/test_user_zero_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_user_zero_api.py
git commit -m "feat(backend): add stage telemetry and progress tracking to analyze jobs

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Frontend Data Contracts & Client API Update

**Files:**
- Modify: `frontend/src/types/patent.ts`
- Modify: `frontend/src/api/client.ts`

**Interfaces:**
- Consumes: `GET /api/analyze/{job_id}` response payload
- Produces: TypeScript interfaces `PipelineStage`, `JobProgress`, `JobStatusResponse`
- Produces: Updated `startAnalyze(domain: string, query?: string)` and `getAnalyzeStatus(jobId: string)` in `client.ts`

- [ ] **Step 1: Update `frontend/src/types/patent.ts` with telemetry schemas**

Add to `frontend/src/types/patent.ts`:
```typescript
export type PipelineStage =
  | "queued"
  | "researching"
  | "clustering"
  | "inventing"
  | "adversarial"
  | "governor"
  | "done"
  | "error";

export interface JobProgress {
  patentsAnalyzed?: number;
  clustersFound?: number;
  candidatesGenerated?: number;
  candidatesRejected?: number;
  candidatesRevised?: number;
  candidatesSurvived?: number;
}

export interface JobStatusResponse {
  job_id: string;
  status: "running" | "done" | "error";
  stage: PipelineStage;
  progress?: JobProgress;
  clusters?: PatentCluster[];
  candidates?: InventionCandidate[];
  verdicts?: AdversarialVerdict[];
  scorecards?: ScoreCard[];
  error?: string;
}
```

- [ ] **Step 2: Update `frontend/src/api/client.ts` API functions**

Update `startAnalyze` and `getAnalyzeStatus` in `frontend/src/api/client.ts`:
```typescript
export async function startAnalyze(
  domain: string,
  query?: string,
): Promise<{ job_id: string; status: string; stage: PipelineStage }> {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain, query: query || "solid electrolyte interphase" }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to start analysis");
  }
  return res.json();
}

export async function getAnalyzeStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/api/analyze/${jobId}`);
  if (!res.ok) {
    throw new Error(`Failed to check analysis status: ${res.statusText}`);
  }
  return res.json();
}
```

- [ ] **Step 3: Run frontend type checking & linter**

Run: `cd frontend && npm run lint`
Expected: Clean pass with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/patent.ts frontend/src/api/client.ts
git commit -m "feat(frontend): update API client and patent types for pipeline telemetry

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: User Zero Landing View Component

**Files:**
- Create: `frontend/src/components/UserZero/LandingView.tsx`
- Create: `frontend/src/components/UserZero/LandingView.module.css`

**Interfaces:**
- Consumes: User inputs for `domain` and `query`
- Produces: `onStartAnalysis(domain: string, query: string)` callback trigger

- [ ] **Step 1: Build `LandingView.tsx` and `LandingView.module.css`**

`LandingView.tsx`:
```tsx
import { useState } from "react";
import styles from "./LandingView.module.css";

interface LandingViewProps {
  onStartAnalysis: (domain: string, query: string) => void;
  isLoading?: boolean;
}

export function LandingView({ onStartAnalysis, isLoading }: LandingViewProps) {
  const [domain, setDomain] = useState("Solid-state electrolytes for EV batteries");
  const [query, setQuery] = useState("solid electrolyte interphase");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (domain.trim()) {
      onStartAnalysis(domain.trim(), query.trim());
    }
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          Find invention opportunities hidden in the patent landscape.
        </h1>
        <p className={styles.subtitle}>
          Give the agent a technology area. It researches prior art, finds white-space, invents candidates and attacks them before scoring the survivors.
        </p>
      </header>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.fieldGroup}>
          <label htmlFor="domainInput">Domain</label>
          <input
            id="domainInput"
            type="text"
            className={styles.input}
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="e.g. Solid-state electrolytes for EV batteries"
            required
          />
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="queryInput">
            Research query <span className={styles.optional}>(optional)</span>
          </label>
          <input
            id="queryInput"
            type="text"
            className={styles.input}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. solid electrolyte interphase"
          />
        </div>

        <button type="submit" className={styles.submitBtn} disabled={isLoading}>
          {isLoading ? "Starting analysis…" : "Analyze opportunity"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Add styles in `LandingView.module.css`**

Create clean, modern styles for inputs, header typography, and action button.

- [ ] **Step 3: Test component compilation**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/UserZero/LandingView.tsx frontend/src/components/UserZero/LandingView.module.css
git commit -m "feat(frontend): add User Zero LandingView component

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: User Zero Execution View Component (Live Pipeline Tracker)

**Files:**
- Create: `frontend/src/components/UserZero/ExecutionView.tsx`
- Create: `frontend/src/components/UserZero/ExecutionView.module.css`

**Interfaces:**
- Consumes: `domain: string`, `stage: PipelineStage`, `progress?: JobProgress`
- Produces: Live visual pipeline tracker reflecting exact backend execution status

- [ ] **Step 1: Build `ExecutionView.tsx`**

`ExecutionView.tsx`:
```tsx
import type { JobProgress, PipelineStage } from "../../types/patent";
import styles from "./ExecutionView.module.css";

interface ExecutionViewProps {
  domain: string;
  stage: PipelineStage;
  progress?: JobProgress;
}

export function ExecutionView({ domain, stage, progress }: ExecutionViewProps) {
  const stagesList = [
    {
      id: "researching",
      label: "Research patent landscape",
      metric: progress?.patentsAnalyzed ? `${progress.patentsAnalyzed.toLocaleString()} patents` : null,
    },
    {
      id: "clustering",
      label: "Find white-space",
      metric: progress?.clustersFound ? `${progress.clustersFound} opportunities` : null,
    },
    {
      id: "inventing",
      label: "Generate inventions",
      metric: progress?.candidatesGenerated ? `${progress.candidatesGenerated} candidates` : null,
    },
    {
      id: "adversarial",
      label: "Prior-art challenge",
      metric:
        progress?.candidatesRejected !== undefined || progress?.candidatesSurvived !== undefined
          ? `${progress?.candidatesRejected ?? 0} rejected / ${progress?.candidatesRevised ?? 0} revised / ${progress?.candidatesSurvived ?? 0} survived`
          : null,
    },
    {
      id: "governor",
      label: "Final assessment",
      metric: stage === "governor" || stage === "done" ? "Scores & evidence" : null,
    },
  ];

  const stageOrder: PipelineStage[] = [
    "queued",
    "researching",
    "clustering",
    "inventing",
    "adversarial",
    "governor",
    "done",
  ];

  const currentIdx = stageOrder.indexOf(stage);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h2 className={styles.domainTitle}>{domain}</h2>
      </header>

      <div className={styles.pipeline}>
        {stagesList.map((st, idx) => {
          const stIdx = stageOrder.indexOf(st.id as PipelineStage);
          let stateClass = styles.pending;
          let icon = "○";

          if (stIdx < currentIdx || stage === "done") {
            stateClass = styles.completed;
            icon = "✓";
          } else if (stIdx === currentIdx) {
            stateClass = styles.active;
            icon = "●";
          }

          return (
            <div key={st.id} className={`${styles.stepRow} ${stateClass}`}>
              <span className={styles.icon}>{icon}</span>
              <span className={styles.label}>{st.label}</span>
              <span className={styles.metric}>{st.metric || ""}</span>
            </div>
          );
        })}
      </div>

      <footer className={styles.notice}>
        <p>The agent is working autonomously.</p>
      </footer>
    </div>
  );
}
```

- [ ] **Step 2: Add styles in `ExecutionView.module.css`**

Define styling for steps, completed checkmarks, active indicators, and progress counts.

- [ ] **Step 3: Test compilation**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/UserZero/ExecutionView.tsx frontend/src/components/UserZero/ExecutionView.module.css
git commit -m "feat(frontend): add User Zero ExecutionView component

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: User Zero Decision & Results View Component + Causal Chain

**Files:**
- Create: `frontend/src/components/UserZero/ResultsView.tsx`
- Create: `frontend/src/components/UserZero/CausalChain.tsx`
- Create: `frontend/src/components/UserZero/ResultsView.module.css`

**Interfaces:**
- Consumes: `JobStatusResponse` containing `clusters`, `candidates`, `verdicts`, `scorecards`
- Produces: Decision card (*What is proposed? Why? What challenged it? Why survived? Evidence? Scores*) and drill-down Causal Chain

- [ ] **Step 1: Build `CausalChain.tsx`**

Create `CausalChain.tsx` rendering nodes: `OPPORTUNITY` → `PRIOR ART` → `PRIOR-ART CHALLENGE` → `REVISION` → `SURVIVAL` → `EVIDENCE`. Each node expands when clicked to show authentic patent titles, white-space rationale, adversarial objections, and citations.

- [ ] **Step 2: Build `ResultsView.tsx`**

`ResultsView.tsx`:
- Render summary of top surviving candidate invention.
- Render direct answers for human domain questions:
  - *Why this opportunity?* (Cluster label & white-space score)
  - *What challenged it?* (Adversarial cited patents)
  - *Why did it survive?* (Differentiation rationale)
  - *Evidence* (Patent citations)
  - *Final assessment scores* (Novelty, Prior-art risk, Differentiation, Evidence)
- Embed `<CausalChain />` section under button `"Why this candidate?"`.

- [ ] **Step 3: Add styles in `ResultsView.module.css`**

- [ ] **Step 4: Test build**

Run: `cd frontend && npm run build`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/UserZero/ResultsView.tsx frontend/src/components/UserZero/CausalChain.tsx frontend/src/components/UserZero/ResultsView.module.css
git commit -m "feat(frontend): add decision-oriented ResultsView and CausalChain drill-down

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Integrate Main App State Machine & Error Handling

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Controls view transitions: `Landing` → `Execution` → `Results` / `Error`

- [ ] **Step 1: Wire up state machine in `frontend/src/App.tsx`**

`App.tsx` handles:
- Polling `getAnalyzeStatus(jobId)` every 2 seconds during `executing` state.
- Transitioning to `results` on `status === "done"`.
- Handling errors cleanly with user-friendly notices (*"We couldn't complete the analysis. Your opportunity wasn't lost. Try again."*).

- [ ] **Step 2: Run frontend build & linter**

Run: `cd frontend && npm run lint && npm run build`
Expected: PASS with 0 linting or build errors.

- [ ] **Step 3: Run backend test suite**

Run: `cd backend && pytest`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/index.css
git commit -m "feat(frontend): connect User Zero views in main App container

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: End-to-End Verification & User Zero Test

- [ ] **Step 1: Launch backend and frontend dev servers**
- [ ] **Step 2: Verify zero-friction flow end-to-end**
  - Open `http://localhost:5173`.
  - Verify immediate understanding from landing text.
  - Click `Analyze opportunity`.
  - Verify live execution pipeline transitions (`researching` → `clustering` → `inventing` → `adversarial` → `governor`).
  - Verify decision-oriented candidate result card and causal chain.
- [ ] **Step 3: Final commit & freeze**
