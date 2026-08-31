# Close Days 10-13 + Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reach and confirm `governor_agent` in a real live run (closing Days 10-11), then expose the full agent-graph output to the frontend so the Invention Opportunity Map can show candidates/verdicts/scores (Days 12-13 DoD), then execute the actual Cloud Run + static-frontend deploy (`docs/deploy.md`).

**Architecture:** No new agents or schemas — everything downstream reuses `root_agent`, `state_keys.py`, and the Pydantic contracts in `tools/schemas.py` exactly as they are. The only structural addition is a thin FastAPI endpoint that runs `root_agent` through ADK's `Runner` (reusing the `RateLimiter` plugin already written in `backend/run_pipeline.py`) and returns the four state-keyed payloads as JSON, plus a frontend view that calls it per selected cluster.

**Tech Stack:** Python/FastAPI/google-adk (backend), React/Vite/TypeScript (frontend), `gcloud` CLI (deploy).

**Spec:** `docs/roadmap.md` (Days 7-15), `docs/architecture.md` (shared-state contract), `backend/patent_agent/tools/schemas.py` (data contracts — do not change).

## Global Constraints

- Never change `PatentRecord`/`PatentCluster`/`InventionCandidate`/`AdversarialVerdict`/`ScoreCard` field names — frontend types in `frontend/src/types/patent.ts` mirror them by hand.
- Never set `GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` alongside a Vertex express-mode `GEMINI_API_KEY` — breaks auth (see roadmap decisions log, Aug 24).
- Free tier: 5 req/min, 20 req/day per model. Any code path that calls the LLM must go through a rate limiter — do not add a second, uncoordinated one.
- Backend endpoint contracts are frozen once Task 4 starts (Days 12-13 rule in roadmap) — no schema changes to the new endpoint's response shape after that point.
- Commit trailers: every commit needs `Co-Authored-By: Lydia Bares <lydiabares@gmail.com>` (CLAUDE.md) in addition to the Claude co-author line.

---

### Task 1: Reach and confirm `governor_agent` in a live run

**Files:**
- None modified — this is a run/verification task using existing `backend/run_pipeline.py`.

**Interfaces:**
- Consumes: `backend/run_pipeline.py` as-is, `INVENTION_LOOP_MAX_ITERATIONS` env var (already read in `backend/patent_agent/config.py:11`).

- [ ] **Step 1: Budget the run under the daily quota**

The first run hit ~20+ calls and never reached `governor_agent`. Cut the loop to one iteration so research (1) + inventor (1) + adversarial (1) + governor (1) ≈ 4-6 calls, safely under 20/day even with retries:

```bash
cd backend
export INVENTION_LOOP_MAX_ITERATIONS=1
export GEMINI_MODEL=gemini-3.5-flash-lite   # separate per-model quota bucket, keep flash for the recorded demo
.venv/bin/python run_pipeline.py
```

- [ ] **Step 2: Verify `governor_agent` output**

Expected: the `=== scored_candidates ===` section is no longer `<missing>` — it must contain a JSON list where each entry has all 4 sub-scores (`novelty`, `prior_art_risk`, `differentiation`, `evidence`) and a non-empty `supporting_evidence` list citing real `publication_number`s from the printed `patent_landscape`/`candidate_inventions` sections above it (per `docs/roadmap.md` §4 — a bare score with no citation means the run doesn't count as validated).

- [ ] **Step 3: If quota is still hit before governor, cut further**

Try `INVENTION_LOOP_MAX_ITERATIONS=1` with a shorter/frugal `adversarial_agent`/`inventor_agent` prompt (see `backend/patent_agent/sub_agents/*/prompt.py`) only if Step 2 still fails — do not add retries or backoff logic, the fix is fewer calls, not more resilience.

- [ ] **Step 4: Save the raw run output**

```bash
.venv/bin/python run_pipeline.py > /tmp/governor_run_$(date +%Y%m%d).log 2>&1
```

Keep this log — Task 2 quotes from it, and it's evidence for the mandatory-checklist Gemini item.

---

### Task 2: Update roadmap + architecture docs with confirmed governor findings

**Files:**
- Modify: `docs/roadmap.md` (Days 10-11 section, checklist item 1, decisions log)
- Modify: `docs/architecture.md` (shared-state table, if the governor row is still marked unvalidated)

**Interfaces:**
- Consumes: the run log from Task 1 Step 4.

- [ ] **Step 1: Update `docs/roadmap.md` Days 10-11 section**

Replace the "⏳ built, not yet validated live" heading and body with a "✅ done, validated live" status, quoting one concrete `ScoreCard` example (candidate title + its 4 scores + one cited `publication_number`) the same way Days 7-9 quotes the inventor/adversarial example.

- [ ] **Step 2: Flip checklist item 1 in `docs/roadmap.md` §1**

Change "partially validated" to fully checked (`- [x]`) once all 4 agents have confirmed live-call evidence.

- [ ] **Step 3: Add a resolved-decisions row**

Add a row to the "Resolved decisions" table: which `INVENTION_LOOP_MAX_ITERATIONS`/model combo actually fit under the daily quota, dated with today's date, so the next person doesn't have to rediscover the budget by trial and error.

- [ ] **Step 4: Cross-check `docs/architecture.md`**

If it has a per-agent validation-status column or note, update it to match. If it doesn't track live-validation status at all, skip — don't add a new column speculatively.

- [ ] **Step 5: Commit**

```bash
git add docs/roadmap.md docs/architecture.md
git commit -m "$(cat <<'EOF'
Confirm governor_agent live and close Days 10-11

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Expose a full-graph run endpoint from the backend

**Files:**
- Modify: `backend/main.py`
- Test: `backend/tests/test_main.py` (create if it doesn't exist — check first)

**Interfaces:**
- Produces: `POST /api/analyze` accepting `{"query": str, "domain": str, "cluster_id": str}`, returning `{"candidates": InventionCandidate[], "verdicts": AdversarialVerdict[], "scorecards": ScoreCard[]}` (field names exactly as in `backend/patent_agent/tools/schemas.py`).
- Consumes: `root_agent` from `patent_agent.agent`, `RateLimiter` from `backend/run_pipeline.py` (import it, don't copy-paste it — see Global Constraints on rate limiters), and the four keys from `patent_agent.shared.state_keys`.

- [ ] **Step 1: Check for an existing test file**

```bash
ls backend/tests/test_main.py 2>/dev/null || echo "does not exist"
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_main.py
import os

os.environ.setdefault("USE_MOCK_BIGQUERY", "true")

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_analyze_returns_all_four_keys_shaped_correctly(monkeypatch):
    # The real agent graph needs a live Gemini key; skip calling it in unit
    # tests and instead assert the endpoint exists and validates its input.
    response = client.post("/api/analyze", json={"query": "", "domain": "", "cluster_id": ""})
    assert response.status_code == 422  # empty query/domain rejected before an LLM call is made
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_main.py -v`
Expected: FAIL — `404 Not Found`, no `/api/analyze` route yet.

- [ ] **Step 4: Implement the endpoint**

```python
# backend/main.py — add near the existing /api/landscape route

from pydantic import BaseModel  # add to existing imports

from google.adk.runners import Runner  # add to existing imports
from google.adk.sessions import InMemorySessionService  # add to existing imports
from google.genai import types  # add to existing imports

from patent_agent.agent import root_agent  # add to existing imports
from patent_agent.shared.state_keys import (  # add to existing imports
    ADVERSARIAL_VERDICTS,
    CANDIDATE_INVENTIONS,
    SCORED_CANDIDATES,
)
from run_pipeline import RateLimiter  # reuse, do not duplicate

_session_service = InMemorySessionService()
_runner = Runner(
    agent=root_agent,
    app_name="ip_matchmaker",
    session_service=_session_service,
    plugins=[RateLimiter()],
)


class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    cluster_id: str = Field(min_length=1)


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest) -> dict:
    """Runs the full agent graph (research -> inventor/adversarial loop ->
    governor) for one cluster and returns its candidates, verdicts, and
    scorecards. Rate-limited to the free-tier quota via RateLimiter — do not
    call this endpoint in a tight loop from the frontend or tests."""
    session = await _session_service.create_session(app_name="ip_matchmaker", user_id="web")
    prompt = (
        f"Mine the patent landscape for domain '{req.domain}' (query: '{req.query}'), "
        f"then propose, adversarially test, and score candidate inventions for cluster "
        f"'{req.cluster_id}'."
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    for _ in _runner.run(user_id="web", session_id=session.id, new_message=msg):
        pass
    final = await _session_service.get_session(
        app_name="ip_matchmaker", user_id="web", session_id=session.id
    )
    state = final.state or {}
    return {
        "candidates": state.get(CANDIDATE_INVENTIONS, []),
        "verdicts": state.get(ADVERSARIAL_VERDICTS, []),
        "scorecards": state.get(SCORED_CANDIDATES, []),
    }
```

Note the `Field(min_length=1)` requires `from pydantic import Field` alongside `BaseModel` — add both.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_main.py -v`
Expected: PASS — `422` for the empty-body request (FastAPI's own validation on `min_length=1` fires before the handler body runs).

- [ ] **Step 6: Manual smoke test against the real graph (uses quota — budget it)**

```bash
cd backend
export INVENTION_LOOP_MAX_ITERATIONS=1
uvicorn main:app --port 8080 &
curl -s -X POST localhost:8080/api/analyze \
  -H 'content-type: application/json' \
  -d '{"query":"solid electrolyte interphase","domain":"solid-state battery electrolytes","cluster_id":"<a real cluster_id from /api/landscape>"}' | head -c 500
kill %1
```

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/tests/test_main.py
git commit -m "$(cat <<'EOF'
Add /api/analyze endpoint for full agent-graph runs

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Wire the frontend to show candidates, verdicts, and scores (Days 12-13 DoD)

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/OpportunityMap/OpportunityMap.tsx`
- Modify: `frontend/src/components/OpportunityMap/OpportunityMap.module.css`

**Interfaces:**
- Consumes: `POST /api/analyze` from Task 3, `InventionCandidate`/`AdversarialVerdict`/`ScoreCard` types already declared in `frontend/src/types/patent.ts` (no changes needed there — they already match the backend schemas).
- Produces: an "Analyze this cluster" action on each expanded cluster card in `OpportunityMap`.

- [ ] **Step 1: Add the client function**

```typescript
// frontend/src/api/client.ts — add below getLandscape
import type { AdversarialVerdict, InventionCandidate, ScoreCard } from "../types/patent";

export interface AnalyzeResponse {
  candidates: InventionCandidate[];
  verdicts: AdversarialVerdict[];
  scorecards: ScoreCard[];
}

export async function analyzeCluster(
  query: string,
  domain: string,
  clusterId: string,
): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query, domain, cluster_id: clusterId }),
  });
  if (!response.ok) {
    throw new Error(`Analyze request failed: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 2: Add analyze state and an "explain" toggle per cluster in `OpportunityMap.tsx`**

```tsx
// add alongside the existing expandedClusterId state
const [analysis, setAnalysis] = useState<Record<string, AnalyzeResponse | "loading" | "error">>({});

function handleAnalyze(clusterId: string) {
  setAnalysis((prev) => ({ ...prev, [clusterId]: "loading" }));
  analyzeCluster(search.query, search.domain, clusterId)
    .then((data) => setAnalysis((prev) => ({ ...prev, [clusterId]: data })))
    .catch(() => setAnalysis((prev) => ({ ...prev, [clusterId]: "error" })));
}
```

Render, inside the existing `{expanded && (...)}` block, after the `<ul className={styles.patentList}>`:

```tsx
<button type="button" onClick={() => handleAnalyze(cluster.cluster_id)}>
  Propose &amp; score inventions for this cluster
</button>
{analysis[cluster.cluster_id] === "loading" && <p>Running inventor/adversarial/governor agents…</p>}
{analysis[cluster.cluster_id] === "error" && <p>Analysis failed — check backend logs.</p>}
{analysis[cluster.cluster_id] &&
  analysis[cluster.cluster_id] !== "loading" &&
  analysis[cluster.cluster_id] !== "error" && (
    <ul className={styles.patentList}>
      {(analysis[cluster.cluster_id] as AnalyzeResponse).scorecards.map((card) => {
        const candidate = (analysis[cluster.cluster_id] as AnalyzeResponse).candidates.find(
          (c) => c.candidate_id === card.candidate_id,
        );
        return (
          <li key={card.candidate_id}>
            <strong>{candidate?.title ?? card.candidate_id}</strong>
            <p>{card.summary}</p>
            <p className={styles.patentMeta}>
              novelty {card.novelty} · prior-art risk {card.prior_art_risk} · differentiation{" "}
              {card.differentiation} · evidence {card.evidence}
            </p>
            <p className={styles.patentMeta}>cited: {card.supporting_evidence.join(", ")}</p>
          </li>
        );
      })}
    </ul>
  )}
```

Import `AnalyzeResponse` and `analyzeCluster` from `../../api/client` at the top of the file.

- [ ] **Step 3: Manual browser check (uses quota — one click, budget it)**

```bash
cd backend && export INVENTION_LOOP_MAX_ITERATIONS=1 && uvicorn main:app --port 8080 &
cd frontend && npm run dev &
```

Open the dev URL, expand a white-space cluster, click "Propose & score inventions," confirm the scorecards render with citations. Kill both background processes afterward.

- [ ] **Step 4: Lint**

Run: `cd frontend && npm run lint`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/components/OpportunityMap/OpportunityMap.tsx frontend/src/components/OpportunityMap/OpportunityMap.module.css
git commit -m "$(cat <<'EOF'
Wire candidate/verdict/scorecard drill-down into OpportunityMap

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Execute the actual deploy (`docs/deploy.md`)

**Files:**
- None modified unless deploy surfaces a bug in `docs/deploy.md` itself (fix in place if so).

**Interfaces:**
- Consumes: `docs/deploy.md` steps 0-4 as written — this task is executing that doc, not rewriting it.

- [ ] **Step 1: GCP project prerequisite (needs the account owner, not more engineering)**

Follow `docs/deploy.md` §0: fresh trial account, create project `ip-matchmaker`, `gcloud auth login`, `gcloud config set project ip-matchmaker`.

- [ ] **Step 2: Deploy backend to Cloud Run**

Follow `docs/deploy.md` §1 exactly, using the `GEMINI_API_KEY` already validated in Task 1. Confirm the smoke test (`curl .../api/landscape`) passes.

- [ ] **Step 3: Deploy frontend to static hosting**

Follow `docs/deploy.md` §2, then redeploy the backend with `FRONTEND_ORIGINS` set (§1 note) so CORS passes.

- [ ] **Step 4: Run the post-deploy checklist**

Work through `docs/deploy.md` §4 line by line, including confirming `/api/analyze` (Task 3) works over HTTPS from the deployed frontend, not just `/api/landscape`.

- [ ] **Step 5: Flip the mandatory-checklist items in `docs/roadmap.md` §1**

Check off "Google Cloud infra service" and "Hosted project URL" once the Cloud Run URL is live, and paste the URL into the checklist item.

- [ ] **Step 6: Commit the roadmap update**

```bash
git add docs/roadmap.md
git commit -m "$(cat <<'EOF'
Confirm Cloud Run deploy live, close infra checklist items

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Notes on scope

- **Days 14-15** (demo script, rehearsal, video recording) are intentionally not broken into engineering tasks here — the roadmap already treats them as a non-technical checklist (§5), and turning "rehearse the demo" into pseudo-code steps would be exactly the kind of unrequested scaffolding to avoid.
- If Task 1 shows `INVENTION_LOOP_MAX_ITERATIONS=1` still exceeds quota, do not build retry/backoff machinery — cut further (shorter prompts) or fall back to `flash-lite` per roadmap's own mitigation list. The daily cap resets; do not over-engineer around a quota that a day of waiting also solves.
