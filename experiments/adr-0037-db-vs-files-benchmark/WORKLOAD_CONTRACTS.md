# Contracts of the seven workloads

Subordinate to `PREREGISTRATION.md`: R1 merged in #155 (merge commit `d622c8e8e314edcd1568428d4da2f4c6187d454c`, sha256 `591ff8cf7c157b846dee9a20f652d98c80c51b094443d0eeb3bf7e52f1e557d5`) **plus amendment R2** (#157), which this file follows. R2 is merged (#157, merge commit `3298274678d88d20db4eec0bf21f825b54f5d59b`); the hash of the protocol in force is `e443232df87fab16e5485dd230f215bd287295ca34bc029d770a5180a5d4c23b` and the authorisation must name it. Where this file and the protocol differ, the protocol wins and this file is wrong. It adds no criterion, threshold or rule. It fixed, before the orchestration code was written, what each workload takes, produces and how it may fail; the orchestration now exists (`harness/workloads.py`, `harness/operational.py`) and has been run only on synthetic data. Nothing has been measured.

## Common rules

* **Result record.** Every workload run produces one JSON object appended to `results/raw.jsonl`: `{workload, alternative, repetition, run_kind, order_in_repetition, status, timings[], outputs{}, checks{}, incident?}`. `status` is `ok`, `check_failed` or `incident`. `timings` are `recorder.Entry` objects with their `prepare`/`execute` phase.
* **Status meaning.** `ok`: ran to the end and every check of that workload that is graded passed. `check_failed`: ran to the end and a graded check failed; counts against the alternative (exit code 1). `incident`: the run could not complete for a reason outside the alternative's behaviour (environment, harness bug, interrupted process); nothing is graded, it is recorded, the cause is written down and the run is repeated (protocol §7). Whether a failure is an incident or a check failure is decided by the rules below, never after seeing which alternative it affects.
* **Isolation.** Each alternative runs in its own directory / schema namespace; versions are immutable; shared rows are never modified. A worker of one alternative never reads the other's data.
* **Input.** The shared rows come from one parse of the 26 files through `OepmBiblioSource` (hashes verified); the parse is recorded as `shared_input` and belongs to neither alternative. If the adapter reports a different count of read or rejected records than 711,547 and 341, the run is an incident.
* **Order and repetition.** Warm runs alternate A/B across repetitions (A first in odd repetitions, B first in even ones); which alternative runs first is recorded. `first_run_after_start` is a separate record and is never compared between A and B (protocol §2).
* **Valid warm runs (R2).** A warm run is invalid and repeated only if (a) it ended in an exception or crash outside the store's contract, (b) the container or the disk was unavailable, or (c) the 1-minute load average before it started was above 1.0 and did not fall within 5 minutes (recorded before every run; the harness waits up to 5 minutes). A valid run is a result: it is not discarded as atypical and not repeated to obtain a pass.
* **Environment capture.** Once per session: machine, OS, kernel, Python and package versions, image digest, each store's `configuration()`. A session missing it is invalid.

## W1 – Prepare BIBLIO

* **Input:** shared rows, version name `w1_<alternative>_<n>`.
* **Does:** `store.prepare(version, rows)`; A in one transaction, B by staging and rename. Recorded as phase `prepare`, label `prepare`. Afterwards `store.size_bytes(version)` and `store.verify(version)`.
* **Outputs:** manifest digest, size in bytes, `logical_digest(version)`, `load_checks(version)`.
* **Graded (C1):** `logical_digest` equals `canonical_rows_digest(shared rows)`; the five load checks equal 711,547 / 341 / 660 / 2,749 / 707,985; and `verify(version)` returns the digest `prepare` returned (`verify_returns_prepared_digest`: a discrepancy is a check failure, not a silent pass).
* **Incident:** out of disk, container not running, any exception that is not `ReferentialError` or `IntegrityError`. **Check failure:** `ReferentialError` on the shared rows (they are known valid), or a mismatch in the graded items.
* **Repetitions:** the version is dropped after each run; every repetition prepares a fresh version. A and B timings are reported with the referential-checking caveat of `HARNESS_DESIGN.md`.

## W2 – Report

* **Input:** a verified version from W1 (the same version across the repetitions of one session).
* **Does:** `read_records(version)` (timed, `execute`, label `read`), then `subclass_pairs` for origins 2006 and 2022 over the returned records (timed, `execute`, label `compute`), unchanged `application/whitespace` code. Total = read + compute.
* **Outputs:** the full pairs result per origin (canonical JSON), the record list, timings.
* **Graded (C1):** pairs equal the versioned `docs/whitespace/oepm-subclass-pairs-results.json` for both origins; `compare_records(adapter path, store records)` equal in every field and in order; **(C3)** every one of the 5 warm totals not greater than 188.6 s, read with the interpretation of the protocol (total of the route from the zips, parsing included). R2 fixes it: acceptance is `max(warm_runs) <= 188.6 s` over the 5 valid warm runs; min, median and max are recorded; a slow valid run is neither discarded nor repeated.
* **Incident:** exception while reading the store that is not an `IntegrityError`; the shared adapter path (needed as reference for records) failing. **Check failure:** any mismatch above; `IntegrityError` on a version that W1 just verified.

## W3 – Verify integrity

* **Input:** a verified, unaltered version.
* **Does:** `store.verify(version)`; timed, `execute`, label `verify`.
* **Outputs:** the manifest digest returned.
* **Graded:** the returned digest equals the one recorded at W1; no exception. **Check failure:** `IntegrityError` or a different digest on an unaltered version. **Incident:** any other exception.

## W4 – Alteration tests

* **Input:** a throwaway copy per test (a new version prepared from the shared rows; never the version of W1–W3).
* **Tests:** (i) `change_subclass`, (ii) `flip_byte`, (iii) `delete_object`, (iv) `swap_rows`. For each: `alter`, then `store.verify`, with **no report generated first**. Recorded: whether `verify` raised `IntegrityError` (detected), whether a report could be produced before detection (must be false), seconds to detection.
* **Graded (C2):** (i), (ii), (iii) detected, raised explicitly, before any report. A warning, a non-zero digest that is only logged, or a verify that returns normally is `not detected` and a **check failure**. (iv) is reported with what each store did and is not graded.
* **Incident:** `alter` itself raising, or the throwaway version failing to prepare. A store that cannot be verified because `verify` crashed with an exception other than `IntegrityError` counts as **not detected with the exception recorded** (a crash is not a controlled detection) and is a check failure, not an incident, unless the crash is traced to the harness.

## W5 – Rebuild after a source change, previous version preserved

* **Input:** version `v_prev` from W1, its manifest digest recorded **before** starting.
* **Does:** build `v_next` from shared rows with one record changed (the first `ipc_entry` subclass replaced by another existing symbol; the shared rows are copied first, never mutated), in a separate namespace/directory. Timed: `prepare`, label `rebuild`. Then `verify(v_prev)`.
* **Outputs:** `v_next` manifest digest, `logical_digest(v_next)`, re-verified digest of `v_prev`.
* **Graded (C5):** `v_prev` verifies and its digest equals the recorded one; `logical_digest(v_next)` differs from `logical_digest(v_prev)` and equals the digest of the changed rows; `v_next` verifies. **Incident:** failure to build for environment reasons. **Check failure:** `v_prev` altered or unverifiable after the rebuild.

## W6 – Backup and restore (R2: W6a and W6b, both required)

* **Input:** a verified `v1` with its manifest digest recorded before anything starts.
* **Backup (both):** `backup(v1, artifact)`, timed, label `backup`; artifact size recorded.
* **W6a – new location, original untouched.** A: create a new database, `pg_restore` the dump into it (timed, `restore_new`); B: copy the directory to a new path. Then `verify` on the restored copy (timed, `verify_restored_new`), W2 on it, and `verify(v1)` on the original, whose digest must equal the recorded one.
* **W6b – in place after loss.** `drop(v1)`, then restore under the same name (timed, `restore_in_place`), `verify` (timed, `verify_restored_in_place`), W2 on it. W6b runs after W6a on a freshly prepared version, never on the one W6a's checks depend on.
* **Outputs:** sizes, digests, W2 outputs of each restored copy, timings of every step.
* **Graded (C4):** both procedures complete; each restored copy verifies with the digest recorded before the backup; each restored copy passes every C1 item (pairs, records **and the five load counts**), and the roll-up applies C1 to W6a and W6b as it does to W2 (an absent W6 content check fails C1). W6a additionally requires the original to verify unchanged.
* **Failure classification (phases kept apart):** a failure *before* the original is dropped (preparing, backing up, the drop itself) is not a recovery-procedure failure and is an `incident`. A failure *after* the drop (restore, verification, report on the restored copy) is a **check failure** unless, at that moment, `Store.environment_problems` finds an environment cause (container not running, database unreachable, free disk below twice the backup size); then it is an `incident` carrying that evidence. The output records `original_dropped`, the phase and the problems found (an empty list is evidence that none was found). Nothing is reclassified afterwards. An exception alone proves neither an environment cause nor a procedure failure.
* **Destinations:** `restore_new` refuses an existing destination (A: database `<namespace>_restored_new`; B: the whole directory `<root>_restored_new`, which is never written into nor removed when it already exists) with `FileExistsError`, which ends W6a as an incident naming the leftover. Removing a leftover is explicit and traceable (`remove_leftover_database()`), done before measuring, never by the benchmark itself.
* **Backup directory:** created by W6 if absent.
* **Implementation:** `Store.restore_new` (A: another database; B: another path) and `Store.dispose`, tested for both stores.
* Atomicity and partial states on interruption are described in the operational section of the results, not graded.

## W7 – Operational retrieval

* **Input:** `data/snapshots/operational_corpus_v1`, the 39 demands, A loaded in a separate namespace (`operational_*`), B = the current numpy artifacts. Separate from the BIBLIO workloads; A's schema is built once per session.
* **Gate:** the valid-run gate (load <= 1.0, up to 5 minutes) precedes **every** timed observation and the load obtained is stored with it (`load_before_each_observation`); an unresolved gate ends W7 as an incident.
* **Eligibility:** computed for every demand like the reference path; if the sets differ between demands the harness stops (`eligible_ids`), because a shared eligible table would not reproduce the reference.
* **Does:** for each demand and limit in {5, 100}: ids and scores from A and from `NumpyDenseRetriever` (parity). Then 20 repetitions per demand at limit 5, each alternative timed, `execute`, label `retrieve`, warm. **Aggregation (R2):** the unit of observation is one retrieval call; 20 observations per demand x 39 demands = 780 per alternative, pooled, all demands included; p95 = `statistics.quantiles(observations, n=20)[-1]`, median = `statistics.median`. A and B alternate per demand across repetitions. p95 and median **per demand** are stored as a diagnostic and are not a criterion.
* **Outputs:** pooled p95 and median per alternative, per-demand p95 and median (diagnostic), parity counts reported as in the spike: identical ids and order (n of 78), strict score equality (n), scores within one unit of the last digit (n). The score policy is not re-decided here.
* **Graded:** ids and order identical in 78/78 (equivalence of ranking). **Reported, not graded:** timings (the spike already passed P2), strict and tolerance counts.
* **Incident:** artifacts missing or failing their own hash verification. **Check failure:** a differing id or order.

## Acceptance roll-up (as in the protocol §5)

Per alternative: C1 from W1, W2, W6a, W6b; C2 from W4; C3 from W2; C4 from W6a and W6b; C5 from W5. An alternative is acceptable only if all pass. Exit code 0 if both ran and every graded check of both passed, 1 if any check failed, 3 if any workload ended as an incident that was not repeated successfully. Materiality of timing differences uses `recorder.materially_different` and is only reported.

## What the orchestration must not do

Change a workload's contract after the first measurement without a dated amendment; retry a `check_failed` run to make it pass; discard an incident without writing its cause; run A or B outside its own namespace; compare first runs of A and B as if conditions were equal; create `AUTHORISATION.json`.

## Faults the orchestration records instead of letting them escape

Any exception in W7 (parity or timed queries) ends it as a recorded incident; a failure while building the real context or during the session makes `run_benchmark.py` write `incident.json` with the traceback and exit 3 (never a graded result), and the operational resources it opened are closed.
