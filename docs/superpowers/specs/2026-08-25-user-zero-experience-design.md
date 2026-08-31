# User Zero Experience Design Spec

## Executive Summary

The User Zero Experience transforms the Patent Innovation Agent from a technical developer tool into an intuitive, zero-friction, decision-oriented platform. A first-time visitor ("User Zero") can immediately understand the platform, launch an autonomous research and invention pipeline with one click, observe live agent progress with real backend telemetry, evaluate surviving inventions, and inspect evidence through a transparent causal chain.

---

## 1. Core Principles & User Mental Model

1. **Zero Technical Prerequisites**: No instructions, no configuration, no setup, no knowledge of Gemini, ADK, BigQuery, or multi-agent architectures required.
2. **Unified Action ("Analyze opportunity")**: The user inputs a technology area and clicks a single primary CTA. The user sees one seamless process: Research → White-space → Invention → Challenge → Assessment.
3. **Backend-Driven Truth**: Progress indicators reflect actual backend agent execution stages and counts (`stage` and `progress`), never simulated mock timelines or client-side fake timers.
4. **Decision-Oriented Results**: Results answer human domain questions (*What is proposed? Why this opportunity? What challenged it? Why did it survive? Where is the evidence?*).
5. **Problem-Domain Terminology**: Internal agent names are rendered in problem-domain terms:
   - "Adversarial Agent" → **Prior-art challenge**
   - "Governor Agent" → **Final assessment**
6. **Transparent Causal Chain ("Why this candidate?")**: Step-by-step evidence tracing (`OPPORTUNITY` → `PRIOR ART` → `PRIOR-ART CHALLENGE` → `REVISION` → `SURVIVAL` → `EVIDENCE`) backed strictly by real data without private chain-of-thought output.

---

## 2. Architecture & Data Contracts

### 2.1 Backend Telemetry (`backend/main.py` & Agent Callbacks)

#### Pipeline Stages
```typescript
type PipelineStage =
  | "queued"
  | "researching"
  | "clustering"
  | "inventing"
  | "adversarial"
  | "governor"
  | "done"
  | "error";
```

*Note: `queued` is brief/transitional when the job starts immediately, switching to `researching` at once so the user perceives immediate activity.*

#### Job Status Schema (`GET /api/analyze/{job_id}`)
```typescript
interface JobProgress {
  patentsAnalyzed?: number;
  clustersFound?: number;
  candidatesGenerated?: number;
  candidatesRejected?: number;
  candidatesRevised?: number;
  candidatesSurvived?: number;
}

interface JobStatus {
  job_id: string;
  status: "running" | "done" | "error";
  stage: PipelineStage;
  progress: JobProgress;
  clusters?: PatentCluster[];
  candidates?: InventionCandidate[];
  verdicts?: AdversarialVerdict[];
  scorecards?: ScoreCard[];
  error?: string;
}
```

#### Unified Execution Flow (`POST /api/analyze`)
`POST /api/analyze` receives `{ domain: string, query?: string }`.
The background task executes:
1. `stage = "researching"`: Fetch patent records & market demand signals. Record `patentsAnalyzed`.
2. `stage = "clustering"`: Run deterministic CPC clustering. Record `clustersFound` and save clusters to job.
3. `stage = "inventing"`: Run Inventor agent for top white-space clusters. Record `candidatesGenerated`.
4. `stage = "adversarial"`: Run Prior-art challenge agent. Record `candidatesRejected`, `candidatesRevised`, `candidatesSurvived`.
5. `stage = "governor"`: Run Final assessment agent. Record scores and citations.
6. `stage = "done"`: Complete job payload with results.

### 2.2 Error and Concurrent Job Handling
- If `_analyze_lock` is held: Return friendly status (HTTP 409/503 wrapped) with existing `active_job_id` so the frontend can display: *"An analysis is already running. You can follow its progress here."*
- If pipeline fails: Job status set to `error` with user-friendly detail: *"We couldn't complete the analysis. Your opportunity wasn't lost. Try again."*

---

## 3. Frontend UX & View Flow

### View State Machine
The UI operates in 3 distinct views:
1. **Landing View** (Paso 1 & 2)
2. **Execution View** (Paso 3 & 4)
3. **Decision & Results View** (Paso 5, 6 & 7)

---

### View 1: Landing View
- **Header**: `Find invention opportunities hidden in the patent landscape.`
- **Subtitle**: `Give the agent a technology area. It researches prior art, finds white-space, invents candidates and attacks them before scoring the survivors.`
- **Form Inputs**:
  - **Domain** (`domain`): Input field with placeholder/default `Solid-state electrolytes for EV batteries`.
  - **Research query** (`query`, optional): Input field with placeholder/default `solid electrolyte interphase`.
- **Primary CTA**: `Analyze opportunity` button.

---

### View 2: Execution View (Live Agent Work)
- **Top Context**: Title + Active Domain (`Solid-state electrolytes for EV batteries`).
- **Central Stage Progress Diagram**:
  - `✓ Research patent landscape` — `1,247 patents`
  - `✓ Find white-space` — `3 opportunities`
  - `● Generate inventions` — `4 candidates`
  - `○ Prior-art challenge` — `2 rejected / 1 revised / 1 survived`
  - `○ Final assessment` — `Scores & evidence`
- **Notice Bar**: `The agent is working autonomously.`

---

### View 3: Decision & Results View
- **Header**: Top Surviving Opportunities for `[Domain]`

#### 1. Candidate Summary Card
- **Candidate Title & Description**: Resumen de 2-3 líneas.
- **Why this opportunity?**: White-space cluster name + demand signal.
- **What challenged it?**: Prior-art patents identified in attack phase.
- **Why did it survive?**: Specific differentiation rationale.
- **Evidence**: Supporting patent numbers with titles & assignees.
- **Final Assessment Scores**:
  - Novelty: `[82]`
  - Prior-art risk: `[21]`
  - Differentiation: `[87]`
  - Evidence rating: `[Strong]` (backed by citations)

#### 2. "Why this candidate?" Causal Chain Drill-down (Real Data Driven)
Horizontal/vertical causal pipeline:
```
[OPPORTUNITY] ➔ [PRIOR ART] ➔ [PRIOR-ART CHALLENGE] ➔ [REVISION] ➔ [SURVIVAL] ➔ [EVIDENCE]
```
Each node links strictly to verified execution data:
- `OPPORTUNITY`: Cluster label, white-space score, demand signal source.
- `PRIOR ART`: Concrete patent numbers, titles, and abstracts analyzed.
- `PRIOR-ART CHALLENGE`: Exact objections and prior-art attacks raised by the adversarial agent.
- `REVISION`: Specific adjustments made to candidate claims.
- `SURVIVAL`: Exact differentiation condition permitting survival.
- `EVIDENCE`: Direct patent citations and claim references.

---

## 4. Definition of Done & Verification

User Zero test scenario:
1. Open application URL.
2. Immediately understand purpose.
3. Enter or leave default technology domain.
4. Click `Analyze opportunity`.
5. Observe live, authentic backend execution progress with real metrics.
6. Review decision-oriented candidate card.
7. Understand why candidate survived and inspect evidence via causal chain.
8. No developer intervention required.
