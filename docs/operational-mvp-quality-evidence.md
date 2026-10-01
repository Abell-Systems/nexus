# Operational MVP: quality evidence

Status of the demand-to-assets MVP (Product B, phase 1) as of 2026-10-01, measured on commit `451bea5` (tip of `main` at 10:59 UTC). Every line says what was checked, with which command, and what that does not prove. Numbers were measured locally from a clean checkout of that commit; the CI artifacts of each run are the authoritative record.

**Two different things are separated here.** The table below is engineering quality and reproducibility of the system. None of it says the ranking is scientifically valid; that is covered in "What is not validated".

## What is verified

| Claim | How to reproduce | Result |
|---|---|---|
| Backend tests pass (unit, integration, e2e, providers) | `python -m pytest backend/test -q` | 1012 passed. By suite: unit 899, integration 56, e2e 11, providers 46. CI skips the 6 real-artifact tests, so its count is 6 lower |
| Frontend unit tests pass | `cd frontend && npm test` | 58 passed, 1 skipped (the live-backend journey, see below) |
| Line coverage | backend: the CI commands (`pytest backend/test/unit`, `.../integration`, `.../e2e` with `--cov=backend/src/main --cov-append`, providers separately, then `coverage combine` and `coverage xml`); frontend: `cd frontend && npm test` (lcov) | backend 95.50 % lines and 86.39 % branches combined (core alone 88.73 % lines; the e2e gate requires at least 80 %); frontend 91.02 % lines (304 of 334). Whole backend and frontend, not only the MVP |
| Static quality | `ruff check backend/src/main backend/test scripts`, `mypy backend/src/main --ignore-missing-imports`, `python scripts/check_architecture.py`, `python scripts/check_docs_correctness.py`, `cd frontend && npm run lint && npm run typecheck && npm run build` | ruff: all checks passed; mypy: no issues in 150 source files; architecture: pass; docs: pass (105 markdown files, 31 ADRs); lint, typecheck and build: exit 0 |
| Clean Architecture dependency rules hold (domain ← application ← infrastructure; runtime never imports torch or transformers) | `python scripts/check_architecture.py` (Import Linter contracts) | pass |
| The MVP process needs no environment and does not import the legacy agent | `test_app.py::test_should_start_without_environment_and_without_importing_the_legacy_agent` | pass: an empty environment, and `infrastructure.api`, `google.adk`, `agents` absent from `sys.modules` |
| HTTP to use case to the real frozen artifacts works | `python -m pytest backend/test/integration/operational -q` | 6 passed |
| The user journey works in a real browser, against the single process that serves SPA and API | `cd frontend && npm run test:e2e` (Playwright builds the frontend and starts `infrastructure.mvp_entrypoint --static`) | 1 passed |
| The server being demoed is the current build | `python scripts/demo_preflight.py [url [artifacts-dir]]` | READY (0.9 s for all journeys): listed demands, notices and build identity (corpus and index hashes) match the artifacts on disk; each demo journey returns five assets and no score field; closed routes answer 404/405 |
| The container image runs the same retrieval | `docker compose up -d --build`, then the commands of `docs/deploy.md` | nexus healthy; `/` answers 401 without credentials and 200 with them; `/health` returns `{"ready":true}`; the image has `numpy` 2.4.6, `pyarrow` 25.0.1, `duckdb` 1.5.5 (pinned) |
| A rebuild cannot change results | "Same results after a rebuild" in `docs/deploy.md` | when the pins were introduced (#127), an unpinned and a pinned image gave identical demands, ranks and publication ids for the 21 listed demands |
| Artifacts are the ones the embeddings were built from | automatic at startup | any hash, model, dimension or text mismatch aborts startup |
| Errors on the MVP routes have one stable shape | `backend/test/unit/infrastructure/operational/test_errors.py` | `{code, message}`; legacy routes keep `detail` |
| No score or qualitative band is exposed | `test_router.py` (structural key check) and the preflight | none in any response |

## Where the evidence lives

- Tests named by behaviour, at three levels: application unit tests (real use case and domain, fakes only at ports), integration over the real artifacts, one browser journey.
- Design decisions and amendments: `docs/superpowers/specs/2026-09-30-demand-to-assets-mvp-design.md` and `2026-09-30-operational-dense-retrieval-design.md`.
- Operation: `docs/operational-mvp-runbook.md`.
- Data: Google Patents Public Data, CC BY 4.0, attribution shown on screen. Counsel has not yet confirmed the chain of underlying patent-office data; this is required before charging for anything, not before demonstrating.

## What depends on this machine

The frozen artifacts (`data/snapshots/operational_corpus_v1/`: the 54,997-asset snapshot and its embeddings) are not in git. CI therefore cannot run the real-artifact integration test or the browser journey; both are skipped there (the frontend's live-backend journey is the one skipped Vitest test). CI does build the image, check that it reaches artifact verification and refuses an empty volume, and validate the Compose file. The real-artifact tests, the browser journey and the container run above are a manual pre-release gate (runbook, section "Pre-release gate"), and the preflight is the demo-day guard.

## What is not validated

- **Ranking quality.** The ranking comes from a frozen multilingual embedding model. An internal estimate exists, judged by a language model, with no human validation; the on-screen notice says exactly that. The pre-registered human probe is parked (Amendment A3 of the retrieval spec) and nothing here validates it.
- 39 example demands only (21 listed), so a live demo cannot take a question from the audience.
- Searchable universe: 44,195 Spanish patents (19,921) and utility models (24,274) with a title and an abstract. The frozen snapshot holds 54,997 assets; the rest are 10,793 EP records with a Spanish applicant (excluded) and 9 Spanish patents without an abstract.
- Exposure: the app itself has no authentication and no rate limiting. The deployment architecture puts Caddy with Basic Auth in front of it (`docs/deploy.md`), verified locally only; it is not deployed anywhere yet, and there is still no rate limiting or CSP.
- Dependency and image vulnerability scanning is not part of CI.
- Sonar Quality Gate on `main`: see the repository's SonarCloud dashboard; this document states no Sonar figure.
