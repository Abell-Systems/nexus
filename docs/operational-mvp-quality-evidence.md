# Operational MVP: quality evidence

Status of the demand-to-assets MVP (Product B, phase 1) as of 2026-09-30, commit `634d0b7` on `main`. Every line says what was checked, with which command, and what that does not prove. Numbers were measured locally on 2026-09-30; the CI artifacts of each run are the authoritative record.

## What is verified

| Claim | How to reproduce | Result |
|---|---|---|
| Backend tests pass (unit, integration, e2e, providers) | `python -m pytest backend/test -q` | 995 passed locally; CI skips the 6 real-artifact tests, so it counts 989 |
| Frontend unit tests pass | `cd frontend && npm test` | 55 passed, 1 skipped (see below) |
| Line coverage (whole backend and frontend, not only the MVP) | backend: the four suites of `ci.yml` with `--cov`, core and providers merged with `coverage combine`; frontend: `cd frontend && npm test` | backend 95.53 %, frontend 91.19 % (local run; `PROJECT_STATUS.md` records it with its commit) |
| Static quality: lint, types, architecture, docs | `ruff check backend/src/main backend/test scripts`, `mypy backend/src/main --ignore-missing-imports`, `python scripts/check_architecture.py`, `python scripts/check_docs_correctness.py`, `cd frontend && npm run lint && npm run typecheck && npm run build` | all green |
| Clean Architecture dependency rules hold (domain ← application ← infrastructure; runtime never imports torch or transformers) | `python scripts/check_architecture.py` (Import Linter contracts) | pass |
| HTTP to use case to the real frozen artifacts works | `python -m pytest backend/test/integration/operational -q` | 6 passed |
| The user journey works in a real browser | `cd frontend && npm run test:e2e` (Playwright starts its own backend and Vite) | 1 passed |
| The server being demoed is the current build | `python scripts/demo_preflight.py [url]` | READY: listed demands, notices and build identity (corpus and index hashes) match the artifacts on disk; each demo journey returns five assets and no score field |
| Artifacts are the ones the embeddings were built from | automatic at startup | any hash, model, dimension or text mismatch aborts startup |
| Errors on the MVP routes have one stable shape | `backend/test/unit/infrastructure/operational/test_errors.py` | `{code, message}`; legacy routes keep `detail` |
| No score or qualitative band is exposed | `test_router.py` (structural key check) and the preflight | none in any response |

## Where the evidence lives

- Tests named by behaviour, at three levels: application unit tests (real use case and domain, fakes only at ports), integration over the real artifacts, one browser journey.
- Design decisions and amendments: `docs/superpowers/specs/2026-09-30-demand-to-assets-mvp-design.md` and `2026-09-30-operational-dense-retrieval-design.md`.
- Operation: `docs/operational-mvp-runbook.md`.
- Data: Google Patents Public Data, CC BY 4.0, attribution shown on screen. Counsel has not yet confirmed the chain of underlying patent-office data; this is required before charging for anything, not before demonstrating.

## What depends on this machine

The frozen artifacts (`data/snapshots/operational_corpus_v1/`, 54,997 assets and their embeddings) are not in git. CI therefore cannot run the real-artifact integration test or the browser journey; both are skipped there. They are a local pre-release gate (runbook, section "Pre-release gate"), and the preflight is the demo-day guard.

## What is not validated

- **Ranking quality.** The ranking comes from a frozen multilingual embedding model. An internal estimate exists, judged by a language model, with no human validation; the on-screen notice says exactly that. The pre-registered human probe is parked (Amendment A3 of the retrieval spec) and nothing here validates it.
- 39 example demands only (21 listed), so a live demo cannot take a question from the audience.
- Spanish patents and utility models of Spanish applicants only. EP records with a Spanish applicant are excluded.
- No authentication or rate limiting: suitable for a local demonstration, not for public exposure.
- Sonar Quality Gate on `main`: see the repository's SonarCloud dashboard; this document states no Sonar figure.
