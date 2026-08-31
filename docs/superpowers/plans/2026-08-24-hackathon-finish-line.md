# Hackathon Finish-Line Plan — Deploy, Async, Real Data, Demo

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the working pipeline into a winning submission: async analyze endpoint, Cloud Run deploy with visible-Google-Cloud proof, one real BigQuery run, verified README + diagram, 4-min demo video, Devpost copy.

**Architecture:** `/api/analyze` becomes a 202 + job-id poll pattern (`asyncio.create_task` + in-memory job dict; Cloud Run pinned to `--max-instances=1 --no-cpu-throttling` so background tasks survive the HTTP response). Frontend polls job status every 5 s. Everything else is ops/submission work on top of the existing graph.

**Tech Stack:** FastAPI/ADK backend, React/Vite frontend, Cloud Run, BigQuery (patents-public-data), Gemini API.

**Global Constraints**
- Deadline: **Sept 1, 2026, 2:00am GMT+2**. Days Aug 30–31 are submission/buffer only — no new features.
- Gemini free tier: 5 req/min, **20 req/day per model**. Rehearse on `gemini-3.5-flash-lite` + `INVENTION_LOOP_MAX_ITERATIONS=1`; record the final take on `gemini-3.5-flash`.
- Never set `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` alongside the AI Studio key.
- Commit attribution (CLAUDE.md): every commit credits Lydia Bares + Claude trailers.
- Every commit message ends with:
  ```
  Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  ```

**Calendar (7 days left)**
| Day | Work |
|---|---|
| Aug 24–25 | Tasks 1–3 (async analyze, backend+frontend+tests) |
| Aug 25–26 | Task 4 (Cloud Run deploy) — start GCP account signup TODAY, it gates everything |
| Aug 27 | Task 5 (real BigQuery run), Task 6 (README verify + diagram embed) |
| Aug 28–29 | Task 7 (rehearse + record video), Task 8 (Devpost copy) |
| Aug 30 | Task 9 (bonus content) if slack; otherwise buffer |
| Aug 31 | Submit. Do not debug on deadline day. |

---

### Task 1: Backend — async analyze (job store + status endpoint)

**Files:**
- Modify: `backend/main.py`
- Test: `backend/tests/test_main.py`

**Interfaces:**
- Produces: `POST /api/analyze` → `202 {"job_id": "<hex>", "status": "running"}`; `GET /api/analyze/{job_id}` → `{"status": "running"}` | `{"status": "done", "candidates": [...], "verdicts": [...], "scorecards": [...]}` | `{"status": "error", "detail": "..."}`; coroutine `_execute_analysis(req: AnalyzeRequest) -> dict` (extracted from current handler body).
- Consumes: existing `_runner`, `_session_service`, `_validated`, state keys, `_ANALYZE_TIMEOUT_S`.

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_main.py`:

```python
def test_analyze_returns_202_with_job_id_and_completes(monkeypatch):
    import asyncio

    import main

    async def fake_execute(req):
        await asyncio.sleep(0)
        return {"candidates": [], "verdicts": [], "scorecards": []}

    monkeypatch.setattr(main, "_execute_analysis", fake_execute)
    resp = client.post("/api/analyze", json={"query": "q", "domain": "d", "cluster_id": "c"})
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    import time

    for _ in range(100):
        body = client.get(f"/api/analyze/{job_id}").json()
        if body["status"] != "running":
            break
        time.sleep(0.05)
    assert body["status"] == "done"


def test_analyze_status_unknown_job_is_404():
    assert client.get("/api/analyze/nope").status_code == 404


def test_analyze_rejects_concurrent_runs(monkeypatch):
    import asyncio

    import main

    gate = asyncio.Event()

    class FakeReq:
        query = "q"
        domain = "d"
        cluster_id = "c"

    async def slow_execute(req):
        await gate.wait()
        return {"candidates": [], "verdicts": [], "scorecards": []}

    monkeypatch.setattr(main, "_execute_analysis", slow_execute)
    first = client.post("/api/analyze", json={"query": "q", "domain": "d", "cluster_id": "c"})
    assert first.status_code == 202
    second = client.post("/api/analyze", json={"query": "q", "domain": "d", "cluster_id": "c2"})
    assert second.status_code == 503
    gate.set()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `cd backend && python -m pytest tests/test_main.py -k "job or concurrent or returns_202" -v`
Expected: FAIL — POST currently blocks and returns 200 with results, no job_id.

Note: the old sync behavior is covered by no test that asserts 200-from-POST, so nothing to delete; keep `test_analyze_rejects_empty_input_before_llm_call` as-is (still valid).

- [ ] **Step 3: Implement**

In `backend/main.py`, replace the current `@app.post("/api/analyze")` handler block (everything from `# One full-graph run at a time` through the end of `analyze`) with:

```python
# One full-graph run at a time: it burns minutes of free-tier Gemini quota and
# concurrent runs would serialize unpredictably on the RateLimiter plugin.
_analyze_lock = asyncio.Lock()
_ANALYZE_TIMEOUT_S = int(os.getenv("ANALYZE_TIMEOUT_SECONDS", "900"))

# ponytail: in-memory job store — valid because deploys pin --max-instances=1
# (see docs/deploy.md). Swap to Firestore only if multi-instance ever matters.
_jobs: dict[str, dict] = {}


# AnalyzeRequest (main.py:96) stays where it is — not redefined here.


async def _execute_analysis(req: AnalyzeRequest) -> dict:
    """Runs the agent graph for one cluster; returns candidates/verdicts/scorecards."""
    session = await _session_service.create_session(app_name="ip_matchmaker", user_id="web")
    prompt = (
        f"Mine the patent landscape for domain '{req.domain}' (query: '{req.query}'), "
        f"then propose, adversarially test, and score candidate inventions for cluster "
        f"'{req.cluster_id}'."
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    async def run() -> None:
        async for _ in _runner.run_async(user_id="web", session_id=session.id, new_message=msg):
            pass

    try:
        # timeout is applied by _run_job's outer wait_for — one layer, not two
        await run()
        final = await _session_service.get_session(
            app_name="ip_matchmaker", user_id="web", session_id=session.id
        )
        final_state = final.state or {}
        return {
            "candidates": _validated(InventionCandidate, final_state.get(CANDIDATE_INVENTIONS)),
            "verdicts": _validated(AdversarialVerdict, final_state.get(ADVERSARIAL_VERDICTS)),
            "scorecards": _validated(ScoreCard, final_state.get(SCORED_CANDIDATES)),
        }
    finally:
        await _session_service.delete_session(
            app_name="ip_matchmaker", user_id="web", session_id=session.id
        )


async def _run_job(job_id: str, req: AnalyzeRequest) -> None:
    async with _analyze_lock:
        try:
            result = await asyncio.wait_for(_execute_analysis(req), timeout=_ANALYZE_TIMEOUT_S)
            _jobs[job_id] = {"status": "done", **result}
        except TimeoutError:
            _jobs[job_id] = {
                "status": "error",
                "detail": f"Agent run exceeded {_ANALYZE_TIMEOUT_S}s.",
            }
        except Exception as exc:
            logger.exception("analyze job %s failed", job_id)
            _jobs[job_id] = {"status": "error", "detail": str(exc)[:300]}
    # ponytail: no job pruning — single-user demo, ~20 runs/day max, store stays tiny


@app.post("/api/analyze", status_code=202)
async def analyze(req: AnalyzeRequest) -> dict:
    """Kicks off the full agent graph (research -> inventor/adversarial loop ->
    governor) in the background and returns a job id immediately. Poll
    GET /api/analyze/{job_id}; only one run may be in flight at a time."""
    if _analyze_lock.locked():
        raise HTTPException(status_code=503, detail="An analyze run is already in progress.")
    job_id = uuid.uuid4().hex
    _jobs[job_id] = {"status": "running"}
    asyncio.create_task(_run_job(job_id, req))
    return {"job_id": job_id, "status": "running"}


@app.get("/api/analyze/{job_id}")
async def analyze_status(job_id: str) -> dict:
    """Poll endpoint for a background analyze run."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job id.")
    return job
```

Add `import uuid` to the top imports of `main.py`.

Note on the lock race: between `if _analyze_lock.locked()` and the task acquiring the lock there is a benign window where two requests both get 202 but the second serializes behind the first inside `_run_job`. Acceptable for a single-user demo; do not add extra machinery.

- [ ] **Step 4: Run full backend suite**

Run: `cd backend && python -m pytest`
Expected: all PASS (old analyze test included).

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_main.py
git commit -m "feat: async analyze via job id + poll endpoint

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Frontend — poll instead of blocking fetch

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/OpportunityMap/OpportunityMap.tsx`

**Interfaces:**
- Consumes: Task 1's `202 {"job_id"}` and GET `/api/analyze/{job_id}` contract.
- Produces: `startAnalysis(query, domain, clusterId): Promise<string>` (returns job id); `getAnalysisStatus(jobId): Promise<AnalysisJob>` where `type AnalysisJob = { status: "running" } | { status: "error"; detail: string } | ({ status: "done" } & AnalyzeResponse)`.

- [ ] **Step 1: Update the API client**

Replace `analyzeCluster` in `frontend/src/api/client.ts` with:

```ts
export type AnalysisJob =
  | { status: "running" }
  | { status: "error"; detail: string }
  | ({ status: "done" } & AnalyzeResponse);

export async function startAnalysis(
  query: string,
  domain: string,
  clusterId: string,
): Promise<string> {
  const res = (await requestJson(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, domain, cluster_id: clusterId }),
  })) as { job_id: string };
  return res.job_id;
}

export async function getAnalysisStatus(jobId: string): Promise<AnalysisJob> {
  return (await requestJson(`${API_BASE_URL}/api/analyze/${jobId}`)) as AnalysisJob;
}
```

Update the file's header comment: analyzeCluster now runs via POST /api/analyze (202 + job id) and polling GET /api/analyze/{job_id}.

- [ ] **Step 2: Update OpportunityMap**

In `frontend/src/components/OpportunityMap/OpportunityMap.tsx`:

Change the import:

```tsx
import { getAnalysisStatus, getLandscape, startAnalysis } from "../../api/client";
import type { AnalysisJob } from "../../api/client";
```

Replace `handleAnalyze` and add `pollJob`:

```tsx
function handleAnalyze(clusterId: string) {
  if (analysis[clusterId] === "loading") return;
  setAnalysis((prev) => ({ ...prev, [clusterId]: "loading" }));
  startAnalysis(search.query, search.domain, clusterId)
    .then((jobId) => pollJob(clusterId, jobId))
    .catch(() => setAnalysis((prev) => ({ ...prev, [clusterId]: "error" })));
}

function pollJob(clusterId: string, jobId: string) {
  const tick = () =>
    getAnalysisStatus(jobId)
      .then((job: AnalysisJob) => {
        if (job.status === "running") {
          setTimeout(tick, 5000);
          return;
        }
        if (job.status === "error") {
          setAnalysis((prev) => ({ ...prev, [clusterId]: "error" }));
          return;
        }
        const { status: _status, ...data } = job;
        setAnalysis((prev) => ({ ...prev, [clusterId]: data }));
      })
      .catch(() => setAnalysis((prev) => ({ ...prev, [clusterId]: "error" })));
  tick();
}
```

No JSX changes needed — the existing loading/error/result rendering already keys off `analysis[clusterId]`.

- [ ] **Step 3: Verify build + lint**

Run: `cd frontend && npm run lint && npm run build`
Expected: clean.

- [ ] **Step 4: Manual smoke (mock mode, no Gemini needed)**

Run backend (`uvicorn main:app --reload --port 8080` in `backend/`) and frontend (`npm run dev`). Note: without a live key the job will end in `"error"` after the runner fails — that still proves the 202→poll→terminal-state UI path works. Confirm: button click shows "Running…" then error card, no browser hang, no request timeout.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/components/OpportunityMap/OpportunityMap.tsx
git commit -m "feat: frontend polls async analyze jobs

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: GCP account + Cloud Run deploy (ops)

**Files:**
- Modify: `docs/deploy.md` (add CPU-throttling flags)

This task needs the GCP account owner (blocked item in roadmap §1). Start signup today even if Tasks 1–2 aren't merged yet.

- [ ] **Step 1: Create GCP project** — follow `docs/deploy.md` §0 verbatim (fresh account, project `ip-matchmaker`, gcloud auth).

- [ ] **Step 2: Update deploy command** — add these flags so background jobs survive response-return (in-memory store requires single instance):

```bash
gcloud run deploy patent-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --max-instances=1 \
  --timeout=3600 \
  --set-env-vars "GEMINI_API_KEY=<PASTE_KEY>,GEMINI_MODEL=gemini-3.5-flash-lite,USE_MOCK_BIGQUERY=true"
```

(`flash-lite` for validation runs per quota budget; switch to `flash` for the recorded demo.)

Also add to `docs/deploy.md` §1 notes:
> `--no-cpu-throttling --max-instances=1` are required: `/api/analyze` runs the agent graph as a background task with an in-memory job store, so the instance must keep CPU between requests and must not scale out.

- [ ] **Step 3: Smoke test**

```bash
curl "<url>/health"
curl "<url>/api/landscape?query=solid+electrolyte&domain=batteries" | head -c 300
curl -X POST "<url>/api/analyze" -H 'content-type: application/json' \
  -d '{"query":"solid electrolyte interphase","domain":"solid-state battery electrolytes","cluster_id":"<some-cluster-id>"}'
# expect 202 {"job_id": "..."}; then poll:
curl "<url>/api/analyze/<job_id>"
```

Expected: health ok; landscape clusters JSON; 202 then eventually `done` (or `error` with a clear detail under flash-lite quota).

- [ ] **Step 4: Deploy frontend static host** (deploy.md §2), then redeploy backend with `FRONTEND_ORIGINS=<frontend-url>` and re-run smoke test from the browser.

- [ ] **Step 5: Capture evidence for the video** — screenshot/screen-recording of: Cloud Run service dashboard showing the service healthy, the `.run.app` URL responding, and Cloud Run request logs. Save to `docs/demo-evidence/`.

- [ ] **Step 6: Commit doc change**

```bash
git add docs/deploy.md docs/demo-evidence/
git commit -m "docs: Cloud Run deploy flags for async jobs + demo evidence

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: One real BigQuery run (kills the mock-data smell)

Needs the GCP project from Task 3. One run only — this is for credibility evidence, not the default mode.

- [ ] **Step 1: Enable BigQuery API**, authenticate with user creds (`gcloud auth application-default login`), set `USE_MOCK_BIGQUERY=false` locally with real project id, run `GET /api/landscape` once against `patents-public-data`.
- [ ] **Step 2: Record evidence** — terminal capture of the real query returning real publication numbers, saved to `docs/demo-evidence/`. If result count is poor, tune the query string once (keep domain locked); don't iterate past 3 attempts — the mock remains the demo default either way.
- [ ] **Step 3: Write the finding into the Devpost description** ("mined N patents from Google Patents Public Datasets on BigQuery" — exact N goes here). Revert local `.env` to mock mode afterwards.
- [ ] **Step 4: Commit evidence + any README data-source note**

```bash
git add docs/demo-evidence/ README.md
git commit -m "docs: real BigQuery landscape run evidence

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: README verification + architecture diagram embedded

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Follow README spin-up instructions literally on a clean clone** (`git clone` to `/tmp/opencode/readme-check`, fresh venv, fresh `npm ci`). Fix every step that lies. Judges were promised reproducible setup; this is the cheapest 30%-criterion points available.
- [ ] **Step 2: Render `docs/architecture.md`'s diagram to an image** (export from whatever drew it — mermaid.live, excalidraw, etc.) and embed at the top of `README.md`. Devpost also wants it uploadable — save as `docs/architecture.png`.
- [ ] **Step 3: Commit**

```bash
git add README.md docs/architecture.png
git commit -m "docs: verify spin-up on clean checkout, embed architecture diagram

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Demo script (~4 min) + rehearsal

**Files:**
- Create: `docs/demo-script.md`

- [ ] **Step 1: Write the script** with this beat structure (timings sum to ~3:50):

| Time | Beat |
|---|---|
| 0:00–0:40 | Problem: patent white-space discovery takes specialist weeks; value prop in one sentence. |
| 0:40–1:20 | Live: search landscape on the deployed app (`.run.app` URL visible in browser bar), clusters render with white-space scores. Say "backed by Google Patents Public Datasets on BigQuery". |
| 1:20–2:40 | Live: click "Propose & score inventions" on a white-space cluster → show 202/polling UI ("agents running asynchronously in the background") → scored candidate appears with cited publication numbers. Expand citations. This is the traceability differentiator — dwell here. |
| 2:40–3:20 | Google Cloud proof: Cloud Run dashboard, request logs, BigQuery console — unedited screen recording. Mention ADK graph topology (Sequential → Loop → governor) over an overlay of the architecture diagram. |
| 3:20–3:50 | Recap + what's next. |

- [ ] **Step 2: Rehearse twice on flash-lite before recording.** Quota protocol: rehearse day-of on `GEMINI_MODEL=gemini-3.5-flash-lite`, record the take on `gemini-3.5-flash`, `INVENTION_LOOP_MAX_ITERATIONS=1`. Max 2 recorded takes/day on flash.
- [ ] **Step 3: Record unedited, single take preferred.** Show Cloud Run dashboard on screen (requirement). Commit script + link final video location.

---

### Task 7: Devpost submission copy

**Files:**
- Create: `docs/devpost-submission.md` (paste into Devpost form later)

- [ ] **Step 1: Draft all required fields**: text description, features/functionality, technologies (Gemini 3.5 Flash via Gemini API, Google ADK, Cloud Run, BigQuery, React/Vite), other data sources (Google Patents Public Datasets + SBIR/CORDIS demand signals), findings/learnings (pull 3 bullets straight from roadmap §6 resolved decisions — quota budget, Vertex express-key gotcha, Workflow-nesting limitation; judges reward honest engineering learnings).
- [ ] **Step 2: Track justification paragraph** — Taskmaster fit: the agent completes a multi-step professional workflow autonomously (mine → propose → adversarially attack → score) and delivers a decision-ready artifact with citations, not chat text.
- [ ] **Step 3: Checklist pass against hackathon requirements list** — hosted URL ✓, repo access shared with `testing@devpost.com` + `cloudhackathons@google.com` (if private), README ✓, diagram ✓, video ✓.
- [ ] **Step 4: Commit**

---

### Task 8 (bonus, only with slack): public content

- [ ] dev.to blog post titled around "building a patent white-space agent with ADK" — include the sentence "created for the purposes of entering the All Things Agentic Hackathon". Source material: roadmap §6 decisions log is already written prose.
- [ ] LinkedIn/X post with `#AllThingsAgenticHackathon`.
- Cut entirely if Aug 30 arrives and Tasks 1–7 aren't green.

---

## Self-review notes

- Spec coverage: async analyze (P1 #4) → Tasks 1–2; deploy + hosted URL + GCP proof (P0 #1) → Task 3; real-data credibility (P0 #2) → Task 4; README/diagram (P1 #6) → Task 5; video + quota protocol (P0 #3) → Task 6; Devpost copy → Task 7; bonus → Task 8. Embeddings-clustering upgrade (P1 #5) deliberately excluded — it's post-deadline scope; noted as future work in the Devpost write-up instead.
- Type consistency: `startAnalysis`/`getAnalysisStatus`/`AnalysisJob` defined in Task 2 Step 1 match usage in Step 2; `_execute_analysis` produced in Task 1 matches the test's monkeypatch target.
- Known risk: in-memory job store requires `--max-instances=1` — flagged in code comment and deploy doc.
