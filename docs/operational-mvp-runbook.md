# Operational MVP runbook: demand to Spanish assets

Status: prototype MVP on real data; ranking quality is an internal, LLM-judged estimate without human validation. Specs: `docs/superpowers/specs/2026-09-30-demand-to-assets-mvp-design.md` and `2026-09-30-operational-dense-retrieval-design.md` (amendments A1 to A3).

## What it does

A user picks one of the example demands ingested from Innoget. The service returns the five Spanish patents or utility models among the 44,195 eligible ones (the operational corpus holds 54,997 assets of Spanish applicants, one per family; its 10,793 EP records are excluded) that a frozen multilingual embedding model ranks closest, with holder, abstract, the asset's own CPC codes and links to Google Patents and Espacenet. No score or quality band is shown; the rank is the only ordering signal.

## Rebuild the artifacts

All outputs go to `data/snapshots/operational_corpus_v1/` and are git-ignored (third-party text and 169 MB of vectors).

```bash
python scripts/build_operational_corpus.py            # BigQuery -> publications.parquet + manifest.json
python scripts/extract_operational_texts.py            # texts for the isolated generation environment
.venv-embedding-generation/bin/python scripts/generate_operational_embeddings.py   # about 2.2 h on CPU, batch_size 1
python scripts/build_demands_snapshot.py               # demands_v1.json with its texts hash
```

The generation environment is isolated on purpose (ADR 0014): the runtime never imports torch, transformers or sentence-transformers.

## Run it locally

```bash
cd frontend && npm install && npm run build && cd ..
cd backend/src/main && python -m infrastructure.mvp_entrypoint --artifacts ../../../data/snapshots/operational_corpus_v1 --static ../../../frontend/dist   # open http://127.0.0.1:8080/
```
The MVP runs as its own process (`infrastructure.mvp_entrypoint`) and reads no environment variables: the artifacts directory is `--artifacts` (required), the built frontend is `--static` (API only when omitted), and `--host`/`--port` default to `127.0.0.1:8080`. It never imports the hackathon agent (`api.py`, ADK), so none of that app's provider or credential variables apply. The demo selection is the versioned file `backend/src/main/infrastructure/operational/demo_selection_v1.json`.

Startup verifies every hash: corpus against its manifest, both embedding indexes against theirs, index ids against corpus order, the indexes against the corpus and demand file they were built from, same model and dimension in both indexes, and demand texts against the snapshot's texts hash. Any mismatch aborts startup; the service never falls back to BM25 or to a live model.

## What the product serves

The product is this one screen, served at `/` (`/matches` shows the same page). `?demanda=<id>` opens a chosen demand, so a result can be shared or reloaded. The hackathon agent (the former landing, its `/api/analyze` job runner and the ADK scaffold routes `/run`, `/run_sse`, sessions, `/docs`, `/openapi.json`) is not reachable: its UI is no longer part of the bundle and the MVP process simply does not contain them: its only routes are `/health` (`{"ready": true}`, answered only after every artifact hash verified), the two MVP routes and the static files. `api.py` remains as the legacy app and is not part of the product. The legacy components still exist in `frontend/src/main/components/UserZero`, unused.

## Before a demo

Kill any server already on the port first: a server left running from an older build answers happily with old notices and all 39 demands (this happened while preparing the demo). Then start the backend and run:

```bash
python scripts/demo_preflight.py [http://127.0.0.1:8080 [artifacts-dir]]
```

It exits non-zero if an agent route such as `POST /run` or `POST /api/analyze` answers, or unless the listed demands equal `demo_selection_v1.json`, the four notices equal the current build, each demo journey returns five assets with no score field in the response, and `meta.corpus_id`, `corpus_parquet_sha256` and `embedding_index_sha256` equal what the artifacts on disk declare (the artifacts directory, second argument of the script), so a stale server with the same shape but another build is caught. Startup already warms the first query (a cold first query took about 2 s), and answers are memoised per demand and limit, because the artifacts are frozen and verified.

The MVP routes also send `X-Content-Type-Options`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer`, and cap `demand_id` at 64 characters.

## Pre-release gate

Besides CI (which has no frozen artifacts), run these against the real artifacts on this machine:

```bash
python -m pytest backend/test/integration/operational -q     # HTTP -> use case -> real artifacts (skipped without them)
cd frontend && npm run test:e2e                              # real Chromium -> frontend -> HTTP -> backend -> real artifacts
python scripts/demo_preflight.py                             # against the server you are about to demo
NEXUS_E2E_BASE_URL=http://127.0.0.1:8080 npx vitest run test/integration   # optional: the component over real HTTP in jsdom
```

`npm run test:e2e` (Playwright) starts its own backend (port 8090) and Vite (port 5173, the only dev origin the backend CORS list allows) and never reuses running servers, so a stale build cannot answer; stop any Vite on 5173 first. The jsdom test in `frontend/test/integration` is an integration test of the component, not an E2E.

## Measured (2026-09-30, this machine)

| | |
|---|---|
| Startup with all hashes verified | 2.0 to 2.4 s |
| One `/api/matches` request | about 0.2 s |
| Eligible assets per demand | 44,195 |
| Patent texts truncated at 128 tokens | 76.4 % |

## Demo selection

The 39 demands stay intact. The screen lists 21, chosen by a written rule applied to the demand text before any result was looked at (`demo_selection_v1.json`: each demand has a one-line reason; 5 borderline ones are excluded by default). The owners review the file. Choosing which demands to present in a given demo is a presentation decision and is not a reclassification.

## Demo journeys

Main demo, three demands with interpretable results: `INNOGET-1935` (water quality measurement), `INNOGET-2258` (renewable hydrogen), `INNOGET-2417` (sustainable food packaging). Secondary, for domain variety: `INNOGET-2173` (construction materials from mining by-products). The Italian `LOMBARDIA-860` (bridge joints) stays listed but is not a journey: its results are not interpretable enough to persuade a third party, and the demo shows product, not a defence of the model. This is a presentation choice recorded in `demo_selection_v1.json`, not a reclassification.

## What may and may not be claimed

May say: it works on real ingested demands over a corpus of 54,997 assets of Spanish applicants, of which the 44,195 Spanish patents and utility models are searchable; every result links to its public source; ranking comes from a frozen, versioned multilingual embedding model; the data is "Google Patents Public Data" by IFI CLAIMS Patent Services and Google under CC BY 4.0 (attribution is shown on screen).

An internal estimate exists: judged by a language model, without human validation, dense retrieval reached P@5 of about 0.24 against 0.06 for lexical BM25 over 31 demands. It was used for product decisions only. It is not a probe outcome and must not be cited as scientific validation (spec amendment A3).

May not say, until the gates close: anything presenting the ranking quality as validated; "unexploited" assets; any price, demand or market-size figure; "customer-ready". The accurate framing for financing conversations is "working prototype MVP on real data; ranking quality is an internal estimate, not yet validated by humans".

## Known limits

Only the 39 example demands can be searched (free text would need live embedding, forbidden by ADR 0014). EP records with a Spanish applicant (about 10,793) are not included. There is no OTRI or transfer contact; the screen shows the holder and the public source. The CC BY 4.0 reading is not legal advice; confirm with counsel, including the chain of the underlying patent-office data, before charging for the service.

## Deferred minor findings (final review, 2026-09-30)

Not blocking the MVP; none changes behaviour a user sees in the demo path.

- `/matchesfoo` also routes to the matches screen.
- Missing tests: zero-norm query in `NumpyDenseRetriever` (returns `[]`, checked by hand), the loading state of the frontend view, and an API-side assertion that the operational policy factory is the one used (the probe side is covered).
- The `NumpyDenseRetriever` docstring says "without its per-row Python loop"; it still loops over the eligible patents in Python (about 0.2 s per request).
- `experiments/operational-dense-probe/internal_quality_signal.py` parses grades and confidence more loosely than `score_probe.py`.
