# Single Container Cloud Run Deployment (100% Google Cloud)

Target: User Zero validation and judge demonstration via a single unified Google Cloud Run URL (`https://patent-agent-....run.app`). The Cloud Run URL doubles as the required "visible Google Cloud" evidence for the demo video.

## 0. Prerequisites (one-time, needs the GCP account owner)

1. Log into Google Cloud Console → create project `ip-matchmaker`.
2. Install `gcloud` CLI:
   ```bash
   gcloud auth login
   gcloud config set project ip-matchmaker
   ```

## 1. Single Command Cloud Run Deploy

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

gcloud run deploy patent-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=<PASTE_KEY>,GEMINI_MODEL=gemini-3.5-flash,USE_MOCK_BIGQUERY=true"
```

`USE_MOCK_BIGQUERY=true` here is deliberate, not a placeholder — see §2 below before changing it.

Notes:
- `--source .` uses the multi-stage `Dockerfile` at root to compile React (`npm run build`) and bundle it directly into FastAPI.
- Serves both SPA UI and REST endpoints on a single HTTPS URL.
- Zero external dependencies (no Vercel, Netlify, or third-party proxy).
- Grab the URL: `gcloud run services describe patent-agent --region us-central1 --format 'value(status.url)'`

Smoke test:
- Open `<cloud-run-url>` in browser to see User Zero UI.
- Curl API: `curl "<cloud-run-url>/health"`

## 2. BigQuery rollout status

`USE_MOCK_BIGQUERY=false` is a deliberately staged rollout, not a single flag flip, because
the risk here isn't BigQuery failing (the code already falls back to mock on any error) --
it's BigQuery working too well and running up cost against a public, unauthenticated
endpoint, or reporting as "real" data on a method that's still mocked underneath. The agreed
sequence is:

| Step | Status |
|---|---|
| Cost cap (`maximum_bytes_billed`, env-tunable) + in-process TTL cache on every real query | ✅ Done |
| `get_patents_datasource()` memoized so the cache/client survive across requests | ✅ Done |
| Observability: `/health` reports actual `patents_datasource` status (bigquery / bigquery_cached / mock_fallback), not just the config flag; `get_status()` lists which methods are genuinely real | ✅ Done |
| `get_citations` wired to a real query | ✅ Done |
| `get_similar_patents` real query (needs `google_patents_research.publications`'s precomputed similarity fields — separate table, separate cost profile) | Not started, not blocking |
| IAM: grant the Cloud Run runtime service account `roles/bigquery.jobUser` | ✅ Done (2026-08-30) |
| Dry-run against the live public dataset to measure actual bytes scanned | ✅ Done — see §2b, this is what drove the domain-index redesign |
| Real-credentials integration test | Still only exercises the mocked-client fallback path (`test_bigquery_real.py`); a live-credentials test against `DOMAIN_INDEX_TABLE` is a documented follow-up, not blocking given the manual verification in §2b |
| Flip `USE_MOCK_BIGQUERY=false` in `.github/workflows/deploy.yml` | ✅ Done (2026-08-30), after §2b landed |

## 2b. Domain index — why querying the public dataset directly was a dead end

The public dataset is `patents-public-data.patents.publications` (170M rows, 3 TB, no
partitioning or clustering) plus `google_patents_research.publications` (170M rows, 505 GB,
also unpartitioned). Because neither table is partitioned or clustered, **a `WHERE
publication_number = ...` filter doesn't reduce bytes scanned at all** -- BigQuery still has
to read the full referenced columns for all 170M rows. Measured with `bq --dry_run`:

| Query | Bytes scanned |
|---|---|
| `search_patents` against `patents.publications` directly | 245.6 GB |
| `search_patents` against `google_patents_research.publications` + a join back for dates/assignee | 158.3 GB |
| `get_patent_by_number` (single patent!) against either table | ~158-168 GB -- **same order as a full search**, because filtering by publication_number doesn't prune anything |
| `get_citations` (single patent!) | ~168 GB |

The conclusion: no SQL rewrite fixes this for point lookups against the raw public tables.
An agent loop calling `get_patent_by_number`/`get_citations` a handful of times per run would
scan multiple TB per pipeline execution against a public, unauthenticated endpoint -- a real
cost risk, not a hypothetical one.

**Fix: a materialized domain index**, built once from the public dataset, scoped to the
locked demo domain and clustered by `publication_number`:

```sql
CREATE TABLE `ip-matchmaker-506820.patent_agent_index.domain_index`
CLUSTER BY publication_number
AS
SELECT
  p.publication_number,
  m.title,
  m.abstract,
  m.cpc_low AS cpc_codes,
  m.top_terms,
  p.country_code,
  ARRAY(SELECT name FROM UNNEST(p.assignee_harmonized)) AS assignee,
  CAST(p.filing_date AS STRING) AS filing_date,
  CAST(p.publication_date AS STRING) AS publication_date,
  ARRAY(SELECT cite.publication_number FROM UNNEST(p.citation) AS cite) AS citations
FROM `patents-public-data.patents.publications` p
JOIN `patents-public-data.google_patents_research.publications` m
  USING (publication_number)
WHERE p.country_code = 'US'
  AND EXISTS (
    SELECT 1 FROM UNNEST(m.cpc_low) AS c
    WHERE SUBSTR(c, 1, 4) IN ('H01M','C01B','B01J','H01L','C08L','G01N','A61K')
  )
  AND (LOWER(m.title) LIKE '%solid electrolyte%' OR LOWER(m.abstract) LIKE '%solid electrolyte%')
```

Built once (2026-08-30): **166.7 GB scanned, one time**, producing a **10,458-row, 15.7 MB**
table. All three of `search_patents`/`get_patent_by_number`/`get_citations` in
`bigquery_patents.py` now read `DOMAIN_INDEX_TABLE` exclusively -- typical query cost is now
**~12-15 MB**, a ~12,000x reduction. `BIGQUERY_MAX_BYTES_BILLED` was lowered from 200 GB back
to 500 MB (a genuine airbag against a runaway query, not the operating budget it had become).

**Architectural boundary**: the public dataset is an *ingestion source* for this one-time
build, never something the running app queries. `get_citations` only resolves citations that
are themselves inside the domain index -- an out-of-domain citation is dropped rather than
triggering a fresh multi-GB lookup against the public tables. To widen the domain later,
re-run the `CREATE OR REPLACE TABLE` above with a broader CPC/keyword filter; there is no
scheduled refresh yet (not needed for a hackathon demo on a fixed domain).

## 3. Quota & Cost Reality Check

> **Estimated demo infrastructure cost: $0.**
> The prototype is designed to run within the applicable Google Cloud and Gemini free-tier quotas. Cloud Run provides a monthly free tier for low-volume workloads, and the demo's expected usage is substantially below those limits. Gemini usage is likewise intended to remain within the applicable free-tier quota. No paid infrastructure is required for the expected hackathon demonstration workload.
>
> A Google Cloud project and billing-enabled account may be required to deploy Cloud Run. Actual charges depend on current Google Cloud pricing, quotas, region, and account configuration.

Free tier quota: **5 req/min and 20 req/day per model.** One full graph run ≈ 20 calls,
so each User Zero gets roughly one pipeline run per day. Mitigations:

- Set `GEMINI_MODEL=gemini-3.5-flash-lite` in Cloud Run env vars for validation runs
  (separate per-model quota bucket); keep flash for the recorded demo.
- Or attach billing to the project — trial credit absorbs it and paid tier removes
  the daily cap.

## 4. Post-deploy checklist

- [ ] `/health` returns ok over HTTPS
- [ ] `/api/landscape` returns clusters from the frontend origin (CORS passes)
- [ ] Full agent run works via `adk web` locally against the same key before demoing
- [ ] Cloud Run dashboard visible on screen during demo recording (requirement §1)
