# Post-Hackathon Roadmap — Shipping as a Product

Written 2026-08-31, once the hackathon submission was functionally complete. This
is not a hackathon deliverable — it's the plan for turning the demo into
something Lydia and Valentín can actually ship. Nothing here blocks the
Devpost submission.

## Why this list exists

The hackathon build made deliberate shortcuts to hit a deadline (in-memory job
store, one hand-built BigQuery domain index, no auth, a mock demand signal).
Every one of those was the right call for a 15-day hackathon and the wrong
call for a product with real users. This doc separates "shortcuts that must
be paid down before onboarding a real customer" from "things that make it
better once it's real."

## Blocking — won't survive contact with a real user

- **Persistence.** `backend/patent_agent/shared/job_store.py`'s
  `InMemoryJobStore` lives in one process's RAM, and Cloud Run is pinned to
  `--max-instances=1` specifically so that's safe for the demo. A crash,
  redeploy, or any attempt to scale past one instance wipes every stored
  analysis. Needs Firestore (or Cloud SQL) before job history means anything
  to a real customer.
- **Auth & multi-tenancy.** There is no login. Anyone with the URL can see
  every past analysis via `GET /api/analyze`. This is IP research — leaking
  one customer's candidate inventions to another is the one failure mode
  that actually kills trust in this product. Needs real accounts and
  workspace/org scoping before a second real customer exists.
- **Domain coverage.** The BigQuery layer that makes this cheap
  (`patent_agent_index.domain_index`, ~15.7MB/query vs. ~245GB against the
  raw public dataset) was built once, by hand, for one locked domain. A
  product needs on-demand index creation for whatever domain a customer asks
  about — not a manual `CREATE TABLE` per topic.
- **Real demand signal.** `InnogetDemandDataSource`'s 19-record fixture
  doesn't cover most domains, including the demo's own. Either be explicit
  that the demand term is illustrative until real coverage exists, or wire a
  market-signal source with actual breadth before charging for it.

## Important — not blocking, but where the value is

- **Export.** A PDF/DOCX brief per candidate (executive summary, opportunity
  and technical layers, prior art, agent review, evidence, technical
  appendix) that a patent attorney can act on without touching the UI.
  Probably the single highest-value feature for anyone paying for this. The
  2026-08-31 `ResultsView` rework (executive summary first, technical detail
  collapsed behind "Details") is the on-screen version of this same
  structure — the PDF should mirror it, not invent a new layout.
- **"Continue analysis" as a real action, not just a reset.** Today
  `ResultsView`'s only next step is "Analyze another opportunity" (start
  over). A product should let the user continue *this* opportunity:
  explore more prior art, ask the agent to refine the candidate, compare it
  against alternative candidates in the same cluster, or generate the
  technical brief above. None of these exist as backend capabilities yet —
  don't add the buttons until the capability behind them is real.
- **Workflow states.** Candidate → under review → filed/abandoned. Turns
  this from a one-shot report into something a team tracks over time.
- **Audit trail.** Immutable log of what was searched, when, and what
  evidence was shown. Matters if a real legal or filing decision ever traces
  back to this tool.
- **Real billing/usage tiers.** Replace the flat per-IP rate limit
  (`_ANALYZE_RATE_LIMIT` in `backend/main.py`) with Stripe-backed plans once
  there are paying customers to meter.
- **Notifications.** Email/Slack on job completion — the async job model
  (`POST /api/analyze` → `202` → poll) already supports this without
  architecture changes.

## Later — quality-of-life and differentiation

- Split the adversarial agent's reasoning into anticipation (§102) vs.
  obviousness (§103) explicitly, and offer freedom-to-operate as a distinct
  mode from patentability.
- Collaboration: comments and sharing on a candidate within a team.
- Real error monitoring (Sentry-style), beyond the existing
  `PipelineProfiler` latency telemetry.

## Explicitly not carried over from the hackathon build

- The per-IP in-memory rate limiter and the `--max-instances=1` pin are
  demo-window safety nets, not the intended long-term shape — see the
  Blocking section above for what replaces each of them.

