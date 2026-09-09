# UX Audit — Nexus Scientific Verification Dashboard (Phase 0)

## 1. Current state

`nexus-status/frontend` is a small React+Vite SPA with one screen (`ScientificDashboard`),
fed entirely by `project_status.json` at the repo root, deployed to GitHub Pages.

Components: `ScientificDashboard` → `Header` + `DimensionCard[]` (`CheckItem`, `StatusBadge`).
Domain: `frontend/src/domain/status.ts` — a strict parser/validator for the contract
(`ProjectStatus` → `dimensions: Record<string, DimensionStatus>` → `checks: CheckResult[]`).
No routing (single view), no state beyond the fetch hook (`useProjectStatus`).

## 2. Current UX problem

The page renders all 9 dimensions as equal-weight cards:
`backend_testing, backend_coverage, python_quality, frontend_testing, frontend_coverage,
frontend_quality, architecture, documentation, scientific_integrity, sonar_cloud`.

Every one of these is an **engineering** signal (pytest, coverage.xml, ruff, mypy, tsc,
oxlint, architecture linter, docs linter, SonarCloud). There is no scientific narrative:
no demand, no patent landscape, no opportunity, no candidate, no evidence chain. A
non-technical researcher opening this page sees a CI status board, not a scientific
verification workspace — which is exactly the problem the plan calls out.

## 3. Data availability (the actual contract)

`project_status.json` = `{schema_version, commit_sha, evaluated_at, overall_status,
aggregation_rule, summary, dimensions: {...}}`. Every dimension is engineering-only.

The **only** place any scientific quantity appears is inside `scientific_integrity`'s
`checks[].detail`, as unstructured free text meant for audit logging, not display:

- `manifest_counts`: `"manifest=(3,15,23) actual=(3,15,23)"` (demand/patent/? counts)
- `no_duplicate_demand_ids`: `"3 demands"`
- `no_duplicate_patent_ids`: `"15 patents"`
- `embeddings_demand_ids`: `"artifact=['INNOGET-2292', 'INNOGET-2415', 'INNOGET-2501']"`
- `embeddings_patent_ids`: `"artifact=15 dataset=15"`
- `snapshots_count`: `"manifest=16 jsonl=16"`
- `temporal_eligibility`: `"3 temporal violations formally accepted as exceptions under ADR-0018/ADR-0019"`

These are check-level pass/fail evidence for a data-integrity gate, not a KPI/metrics API.
Parsing counts out of prose strings to power a hero KPI would be fragile and arguably
"reinterpreting" data the plan explicitly forbids.

**Nothing else exists in this contract**: no clusters, no opportunity records, no
candidate records, no white-space scores, no prior-art citations, no evidence roles,
no methodology text, no dataset version/hash surfaced as a field (only buried in one
check detail), no timeline/domain data.

## 4. Plan sections vs. data support

| Plan section | Status | Note |
|---|---|---|
| §4 Scientific Overview (hero, "what Nexus does") | **Supportable** | Static/editorial copy, no data dependency |
| §4.1 Scientific KPI cards | **Not supported** | No structured KPI fields; only prose-buried counts in one check |
| §5 Scientific vs Engineering view split | **Supportable today** | Pure IA/reorg of existing `dimensions` |
| §6 Landscape | **Not supported** | No technology/domain/cluster data in contract |
| §7 Opportunities | **Not supported** | No opportunity entities in contract |
| §8 Candidates | **Not supported** | No candidate entities in contract |
| §9 Evidence workspace | **Not supported** | No `supporting_evidence`/`cited_patents` in this contract (plan assumes a different data model than what `project_status.json` actually carries) |
| §10 Methodology | **Supportable** | Static editorial pipeline description, no data dependency |
| §11 Limitations | **Supportable** | Static editorial copy |
| §12 Reproducibility | **Partially supportable** | `commit_sha`, `evaluated_at`, `schema_version` exist; dataset hash/manifest do not (buried in one check's `detail` string only) |
| §13 Evidence export | **Not supported** | Nothing to export beyond the raw JSON already public |
| §14 Engineering view | **Supportable today** | This *is* the current dashboard, verbatim |

## 5. Proposed information architecture (data-honest)

Given the contract, Phase 1 can ship for real:

```
Nexus
├── Scientific Overview   (hero + "what Nexus does" — editorial, static)
├── Reproducibility        (commit_sha, evaluated_at, schema_version — real fields)
├── Methodology             (editorial pipeline description — static)
├── Limitations             (editorial — static)
└── Engineering             (existing 9-dimension grid, moved here verbatim)
```

`Landscape`, `Opportunities`, `Candidates`, `Evidence workspace`, `Evidence export`
cannot be built without fabrication. Building them now would mean either (a) inventing
numbers, which the plan forbids outright, or (b) parsing prose out of
`scientific_integrity.checks[].detail`, which is the same problem in a thin disguise —
it's audit-log text, not a data contract, and it will break the moment the wording of a
check's `detail` string changes.

## 6. Implementation gap to flag upstream

For §6–9 and §13 to ever be real, `project_status.json` (or a sibling artifact) needs a
genuine data contract for scientific entities — e.g. something like:

```
"scientific_results": {
  "demands": [...], "patents": [...], "clusters": [...],
  "opportunities": [{id, domain, demand_signal, patent_density, whitespace_score, ...}],
  "candidates": [{id, opportunity_id, novelty_score, prior_art_conflicts, verification_status, supporting_evidence: [...], cited_patents: [...]}]
}
```

That's a backend/contract decision, out of scope for Phase 0 per the plan ("do not
change backend contracts during this phase"). This audit surfaces it as the actual
blocker rather than silently generating placeholder content for those sections.
