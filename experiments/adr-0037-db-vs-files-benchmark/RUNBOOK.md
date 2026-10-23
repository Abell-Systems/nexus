# Runbook: authorising and running the benchmark (for the person who does it)

This file prepares a human decision; it does not take it. The harness never creates `AUTHORISATION.json`, and neither did the author of this runbook. Technical review of the harness (#156) and authorisation to run are separate steps.

## 0. Preconditions to check before authorising

1. The protocol in force is the merged `PREREGISTRATION.md` (R1 #155 + R2 #157). Its hash:
   `sha256sum experiments/adr-0037-db-vs-files-benchmark/PREREGISTRATION.md` must print `e443232df87fab16e5485dd230f215bd287295ca34bc029d770a5180a5d4c23b` (if the protocol was amended since, use the hash of the version in force and say why).
2. The Python environment is the one in `requirements.lock.txt` (every package at an exact version, hashes not required): `python3 -m venv <venv> && <venv>/bin/pip install -r experiments/adr-0037-db-vs-files-benchmark/requirements.lock.txt`. `requirements.txt` lists the direct dependencies and why; it does not pin the transitive ones. `environment.json` records the versions really installed, not these. The harness PR (#156) has been reviewed and merged, or you run from its reviewed commit, and `python -m pytest experiments/adr-0037-db-vs-files-benchmark/tests` passes on the machine that will run it (with `NEXUS_BENCH_PG_DSN` set, so the PostgreSQL variants are not skipped: a run that says "skipped" for them is not a pass of those tests).
3. The data are the pinned ones: the 26 files verify against `config/whitespace/oepm_biblio_2000_2025.json` (the adapter checks this itself) and `data/snapshots/operational_corpus_v1` loads (its loader verifies its own hashes).
4. Nothing from a previous attempt is left behind. The harness refuses, and names, any pre-existing object instead of deleting it. List before running; remove explicitly and only what you know is a leftover of an interrupted run: `FilesStore.remove_leftover_staging`, `PostgresStore.remove_leftover_database`, `PgRetriever.remove_leftover_schema`. The work directory passed to `--work-dir` must be new or empty.
5. The machine is otherwise idle (the harness also waits for a 1-minute load average <= 1.0 before every warm run, up to 5 minutes, and records it).

## 1. Authorisation

A person creates `experiments/adr-0037-db-vs-files-benchmark/AUTHORISATION.json`:

```json
{
  "protocol_sha256": "<sha256 of PREREGISTRATION.md in force>",
  "protocol_pr_merged_commit": "<merge commit of the protocol, 3298274678d88d20db4eec0bf21f825b54f5d59b for R2>",
  "authorised_by": "<name of the person>",
  "date": "<ISO date>",
  "harness_commit": "<commit of the harness that was reviewed>"
}
```

The harness reads `protocol_sha256`, `protocol_pr_merged_commit` and `authorised_by`; the other fields are for the record. If `PREREGISTRATION.md` changes afterwards the barrier refuses again. Commit this file (it is part of the evidence) before running.

## 2. Running

Start the PostgreSQL container used by alternative A, then (all arguments are required, and `--work-dir` must not exist or must be empty):

```
# full session: A and B in one process, warm runs alternating
python experiments/adr-0037-db-vs-files-benchmark/run_benchmark.py \
  --work-dir <new dir>/session --pg-dsn "<dsn>" --container <container>

# initial performance, protocol section 2: separate fresh sessions, same procedure
python experiments/adr-0037-db-vs-files-benchmark/run_benchmark.py --only A --work-dir <new dir>/only_A ...
python experiments/adr-0037-db-vs-files-benchmark/run_benchmark.py --only B --work-dir <new dir>/only_B ...
```

Exit codes: 0 every graded check passed, 1 a check failed, 2 refused, 3 an incident (see `incident.json` or the `incident` fields of `raw.jsonl`). An exit code 1 is a result, not a reason to run again.

## 3. If something goes wrong

* **Incident** (environment, crash outside the store's contract, load gate not met): write the cause down, fix the environment, and repeat that run in a new work directory. Never delete or edit the earlier results.
* **`check_failed`:** it counts against the alternative. It is never repeated to obtain a pass. A slow valid warm run is a result.
* **Do not** change the harness, a contract, a criterion or the protocol after the first measurement without a dated amendment that states what was already known.

## 4. After the run

Write `RESULTS.md` from `raw.jsonl`, `summary.json`, `timings.json` and `environment.json`: environment table; the section 3 table with min/median/max; the section 5 verdict per alternative (C1 to C5; a timing difference is "material" only by the rule of the protocol); the operational section 6 (written factually, no scores); every incident and deviation; and the known asymmetries of `HARNESS_DESIGN.md`. State what the run does not show (concurrency, growth, cost of operating a server over time). Commit the raw outputs. The benchmark is evidence for gate 1 of ADR 0037 section 5.1 and does not accept the ADR.
