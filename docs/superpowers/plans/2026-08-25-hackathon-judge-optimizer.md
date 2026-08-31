# Hackathon Judge Optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Elevate `ip-matchmaker` to an **85+ score** by implementing BigQuery patent querying with mock fallback, verifying Cloud Run deployment automation, adding robust edge-case handling, standardizing the 4-minute demo narrative, and updating the definitive architecture diagram and Devpost submission QA.

**Architecture:** 
1. Real BigQuery integration in `backend/patent_agent/tools/bigquery_patents.py` querying `patents-public-data.patents.publications` with fallback to `MockPatentsDataSource`.
2. Deployment automation script `scripts/deploy_cloud_run.sh` and environment validation.
3. Enhanced test coverage for edge cases (timeouts, missing API key, empty results, 503 concurrency locks, 404 job polling).
4. Architecture documentation update in `docs/architecture.md` with complete data flow, ADK agent graph, and state management strategy.
5. 4-minute locked demo script in `docs/demo-script.md` and Devpost QA checklist in `docs/devpost-draft.md`.

**Tech Stack:** Python 3.12, FastAPI, Google ADK, Google BigQuery (`google-cloud-bigquery`), Pytest, React, Vite.

## Global Constraints

- Python 3.12 compatibility
- ADK agents must preserve state keys defined in `patent_agent/shared/state_keys.py`
- All tests must pass with `.venv/bin/pytest`
- Default fallback to `MockPatentsDataSource` when `USE_MOCK_BIGQUERY=true` or when BigQuery credentials are unavailable.

---

### Task 1: Real BigQueryPatentsDataSource Implementation

**Files:**
- Modify: `backend/patent_agent/tools/bigquery_patents.py`
- Test: `backend/tests/test_bigquery_real.py`

**Interfaces:**
- Consumes: `google.cloud.bigquery.Client`
- Produces: `BigQueryPatentsDataSource` implementing `PatentsDataSource` interface (`search_patents`, `get_patent_by_number`, `get_citations`, `get_similar_patents`).

- [ ] **Step 1: Write tests for BigQuery data source (with mock client/fallback)**

Create `backend/tests/test_bigquery_real.py`:
```python
import pytest
from unittest.mock import MagicMock
from patent_agent.tools.bigquery_patents import BigQueryPatentsDataSource

def test_bigquery_search_patents_fallback():
    # Verify fallback logic on exception or empty BigQuery result
    ds = BigQueryPatentsDataSource(project="dummy-project")
    # Mock client query failure
    ds._client = MagicMock()
    ds._client.query.side_effect = Exception("BigQuery connection error")
    
    records = ds.search_patents("solid electrolyte", "batteries", max_results=5)
    assert len(records) > 0
    assert records[0].publication_number is not None
```

- [ ] **Step 2: Run test to verify initial state**

Run: `.venv/bin/pytest tests/test_bigquery_real.py`
Expected: FAIL with `NotImplementedError`

- [ ] **Step 3: Implement BigQueryPatentsDataSource in `bigquery_patents.py`**

Implement real BigQuery queries over `patents-public-data.patents.publications` with try-except fallback to `MockPatentsDataSource`.

- [ ] **Step 4: Run pytest to verify all tests pass**

Run: `.venv/bin/pytest`
Expected: 42+ PASSING

- [ ] **Step 5: Commit changes**

```bash
git add backend/patent_agent/tools/bigquery_patents.py backend/tests/test_bigquery_real.py
git commit -m "feat: implement real BigQueryPatentsDataSource with graceful mock fallback"
```

---

### Task 2: Cloud Run Deployment Automation & Health Verification

**Files:**
- Create: `scripts/deploy_cloud_run.sh`
- Modify: `backend/main.py:60-64`
- Test: `backend/tests/test_robustness.py`

**Interfaces:**
- Consumes: Environment variables `GEMINI_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `FRONTEND_ORIGINS`.
- Produces: Executable deployment script and `/health` payload with GCP & API readiness metadata.

- [ ] **Step 1: Write test for detailed health check and error responses**

Create `backend/tests/test_robustness.py`:
```python
from fastapi.testclient import TestClient
from main import app

def test_health_check_returns_ready():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "use_mock_bigquery" in res.json()
```

- [ ] **Step 2: Run test to verify failure/missing key**

Run: `.venv/bin/pytest tests/test_robustness.py`

- [ ] **Step 3: Update `backend/main.py` health endpoint and deployment script**

Enhance `/health` in `main.py`:
```python
@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "use_mock_bigquery": os.getenv("USE_MOCK_BIGQUERY", "true"),
        "gemini_api_key_configured": bool(os.getenv("GEMINI_API_KEY")),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    }
```

Create executable `scripts/deploy_cloud_run.sh` with full gcloud Cloud Run verification steps.

- [ ] **Step 4: Run test to verify passing status**

Run: `.venv/bin/pytest tests/test_robustness.py`
Expected: PASS

- [ ] **Step 5: Commit deployment script and health improvements**

```bash
git add backend/main.py backend/tests/test_robustness.py scripts/deploy_cloud_run.sh
git commit -m "feat: add deployment script and detailed health status endpoint"
```

---

### Task 3: Robustness & Failure-Mode Handling

**Files:**
- Modify: `backend/main.py`
- Test: `backend/tests/test_robustness.py`

**Interfaces:**
- Handles edge cases: Concurrent `/api/analyze` requests (503 status), missing API key configuration, unknown job ID (404), empty patent search results.

- [ ] **Step 1: Write tests for edge cases in `test_robustness.py`**

Add tests for:
1. Unknown job ID polling (`GET /api/analyze/invalid_id`) -> 404
2. Concurrency lock (`POST /api/analyze` when `_analyze_lock` is locked) -> 503
3. `/api/landscape` empty query validation -> 422 / 400

- [ ] **Step 2: Implement edge case protection in `main.py`**

- [ ] **Step 3: Run pytest to verify all tests pass**

Run: `.venv/bin/pytest`
Expected: ALL PASSING

- [ ] **Step 4: Commit robustness fixes**

```bash
git add backend/main.py backend/tests/test_robustness.py
git commit -m "fix: add robust error handling for concurrent runs, unknown jobs, and empty queries"
```

---

### Task 4: Definitive Architecture Diagram & State Management Rationale

**Files:**
- Modify: `docs/architecture.md`

**Interfaces:**
- Produces: Comprehensive ASCII/Mermaid architecture diagram & in-memory vs Firestore state rationale.

- [ ] **Step 1: Update `docs/architecture.md` with complete 1-page architecture diagram**

Include:
- User -> Frontend -> Cloud Run / FastAPI
- Google ADK Agent Graph (Research Agent -> Invention Loop [Inventor <-> Adversarial] -> Innovation Governor)
- BigQuery Public Datasets / Innoget Demand Integration
- State Key Contracts (`state_keys.py`)
- Explicit In-Memory Rationale (Pinned Cloud Run instance `--max-instances=1` guarantees state consistency for demo without Firestore cost/complexity).

- [ ] **Step 2: Commit documentation update**

```bash
git add docs/architecture.md
git commit -m "docs: update architecture diagram and state persistence strategy"
```

---

### Task 5: 4-Minute Demo Script & Devpost Submission QA Checklist

**Files:**
- Modify: `docs/demo-script.md`
- Modify: `docs/devpost-draft.md`

**Interfaces:**
- Produces: 4-minute timed video script and Devpost judge submission checklist.

- [ ] **Step 1: Update `docs/demo-script.md` with exact minute-by-minute breakdown**

0:00–0:30 Problem statement
0:30–1:00 Input domain (Solid-state electrolytes for EV batteries)
1:00–1:40 Landscape & white-space detection
1:40–2:30 Agent working (Research -> Inventor)
2:30–3:15 Adversarial rejection & Inventor iteration loop
3:15–3:40 Final invention & traceable ScoreCard evidence
3:40–4:00 Cloud Run / Google Cloud live proof dashboard

- [ ] **Step 2: Update `docs/devpost-draft.md` with final QA checklist**

- Hosted URL
- Architecture Diagram
- BigQuery & Gemini verification
- Track details (Taskmaster)

- [ ] **Step 3: Commit demo script and submission QA**

```bash
git add docs/demo-script.md docs/devpost-draft.md
git commit -m "docs: polish 4-minute demo script and Devpost submission checklist"
```

---

### Task 6: Final End-to-End Test & Verification

- [ ] **Step 1: Execute full test suite**

Run: `.venv/bin/pytest`

- [ ] **Step 2: Execute frontend build test**

Run: `cd frontend && npm run build`

- [ ] **Step 3: Final verification report**
