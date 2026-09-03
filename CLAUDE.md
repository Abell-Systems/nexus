# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Canonical Clean Architecture

Each application (backend and frontend) strictly follows the 3-tier Clean Architecture:

```text
backend/
├── src/
│   └── main/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
└── test/
    ├── unit/
    ├── integration/
    └── e2e/

frontend/
├── src/
│   └── main/
│       ├── domain/
│       ├── application/
│       └── infrastructure/
└── test/
    ├── unit/
    ├── integration/
    └── e2e/
```

- `src/main` contains exclusively production code.
- `test` contains exclusively tests (`unit/`, `integration/`, `e2e/`).
- Layers:
  - `domain`: Pure business entities, models, validation, and contracts.
  - `application`: Use cases, pipelines, metrics, and orchestration.
  - `infrastructure`: Storage (Parquet, DuckDB, RawStore), external sources, LLM providers, and FastAPI/CLI entrypoints.

## Commit attribution

Every commit in this repo must credit **Lydia Bares** (`lydiabares@gmail.com`) as co-author:

```text
Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
```

## Commands

### Backend (`backend/`)

```bash
pip install -r backend/requirements.txt
pytest                         # runs backend/test/
python -m infrastructure.cli ingest --source-type oepm_bopi --source-file data/raw/oepm_open_data_es.json --dataset-id patents_es_v1
uvicorn main:app --app-dir backend/src/main --reload --port 8080
```

### Frontend (`frontend/`)

```bash
cd frontend
npm install
npm run dev        # vite dev server
npm run build      # tsc -b && vite build
```
