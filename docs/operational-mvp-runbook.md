# Operational MVP runbook: demand to Spanish assets

Status: prototype MVP on real data, ranking quality under internal evaluation. Specs: `docs/superpowers/specs/2026-09-30-demand-to-assets-mvp-design.md` and `2026-09-30-operational-dense-retrieval-design.md` (amendments A1 to A3).

## What it does

A user picks one of the example demands ingested from Innoget. The service returns the five Spanish patents or utility models of the operational corpus (54,997 assets, one per family, Spanish applicant) that a frozen multilingual embedding model ranks closest, with holder, abstract, the asset's own CPC codes and links to Google Patents and Espacenet. No score or quality band is shown; the rank is the only ordering signal.

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
NEXUS_MVP_ENABLED=1 uvicorn main:app --app-dir backend/src/main --port 8080
cd frontend && VITE_API_BASE_URL=http://127.0.0.1:8080 npm run dev     # then open http://127.0.0.1:5173/matches
```

`uvicorn` does not serve `frontend/dist` from the repo in development (the static path in `api.py` resolves under `backend/src/main`), so use Vite as above. With `NEXUS_MVP_ENABLED` unset the two routes do not exist and the legacy app is unchanged.

| Variable | Meaning | Default |
|---|---|---|
| `NEXUS_MVP_ENABLED` | `1` mounts `/api/demand-examples` and `/api/matches` | unset (off) |
| `NEXUS_OPERATIONAL_DIR` | directory with the artifacts above | `data/snapshots/operational_corpus_v1` |
| `NEXUS_DEMO_SELECTION` | which demands the screen lists | `backend/src/main/infrastructure/operational/demo_selection_v1.json` |

When enabled, startup verifies every hash: corpus against its manifest, both embedding indexes against theirs, index ids against corpus order, the indexes against the corpus and demand file they were built from, same model and dimension in both indexes, and demand texts against the snapshot's texts hash. Any mismatch aborts startup; the service never falls back to BM25 or to a live model.

## Measured (2026-09-30, this machine)

| | |
|---|---|
| Startup with all hashes verified | 2.0 to 2.4 s |
| One `/api/matches` request | about 0.2 s |
| Eligible assets per demand | 44,195 |
| Patent texts truncated at 128 tokens | 76.4 % |

## Demo selection

The 39 demands stay intact. The screen lists 21, chosen by a written rule applied to the demand text before any result was looked at (`demo_selection_v1.json`: each demand has a one-line reason; 5 borderline ones are excluded by default). The owners review the file. Choosing which demands to present in a given demo is a presentation decision and is not a reclassification.

## What may and may not be claimed

May say: it works on real ingested demands over a corpus of 54,997 Spanish industrial-property assets; every result links to its public source; ranking comes from a frozen, versioned multilingual embedding model; the data is "Google Patents Public Data" by IFI CLAIMS Patent Services and Google under CC BY 4.0 (attribution is shown on screen).

An internal estimate exists: judged by a language model, without human validation, dense retrieval reached P@5 of about 0.24 against 0.06 for lexical BM25 over 31 demands. It was used for product decisions only. It is not a probe outcome and must not be cited as scientific validation (spec amendment A3).

May not say, until the gates close: anything presenting the ranking quality as validated; "unexploited" assets; any price, demand or market-size figure; "customer-ready". The accurate framing for financing conversations is "working prototype MVP on real data, quality evaluation in progress".

## Known limits

Only the 39 example demands can be searched (free text would need live embedding, forbidden by ADR 0014). EP records with a Spanish applicant (about 10,793) are not included. There is no OTRI or transfer contact; the screen shows the holder and the public source. The CC BY 4.0 reading is not legal advice; confirm with counsel, including the chain of the underlying patent-office data, before charging for the service.
