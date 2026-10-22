# ADR 0037 gate 3: network and credential custody

**Purpose:** evidence for gate 3 of [ADR 0037](../adr/0037-operational-corpus-in-database.md) §5 and §5.1 (network and credential custody). It inventories what the pilot really connects to and which secrets it handles, records what is verified and what is not, and specifies, and for the database grants tests, the custody model the ADR leaves open. **It does not close the gate and does not accept the ADR.** Nothing was deployed, no host was reached, no secret was read.
**Date:** 2026-10-22 · **Evidence sources:** `infrastructure` at `c4c40a0`; `career-os` `docker-compose.staging.yml`; `secrets` repository (file names and README only, no value opened); the spike container `nexus-spike-pg`; `experiments/adr-0037-db-vs-files-benchmark` (harness); `experiments/adr-0037-gate3-custody` (grants and their tests).

## 1. Scope

Two situations, kept apart:

* **A. The benchmark and the spike** (gate 1): a throwaway PostgreSQL in Docker on the developer machine (OMEN, WSL). Nothing leaves that machine.
* **B. The proposed staging deployment on the Lenovo** (ADR 0037 §3.9): a Nexus workload with its own PostgreSQL, loaded from the controller over the tailnet. It does not exist yet: there is no `nexus` entry in the workload list and no `staging/nexus.env` in the secrets repository (only `career-os.env`).

Out of scope: production, licences and retention (gate 5), the choice database versus files (gate 1).

## 2. Inventory

### A. Benchmark and spike (verified on the machine)

| Item | Finding | How it was verified |
|---|---|---|
| Container `nexus-spike-pg`, image `pgvector/pgvector:pg17` | Publishes `5432` only on `127.0.0.1:55432`; default bridge network; stopped when not in use | `docker inspect` (`HostConfig.PortBindings`) |
| Credential | Superuser `postgres` with a throwaway password set at `docker run`; the harness connects as that superuser | container env (value not printed here), harness code |
| Authentication seen from the host port | Password is enforced: a wrong and an empty password are refused (`password authentication failed`) | connection attempts |
| Authentication inside the container | `pg_hba.conf` of the image trusts the local socket and `127.0.0.1`/`::1` (`trust`), and requires `scram-sha-256` for every other address; `password_encryption = scram-sha-256`, `listen_addresses = *`, `ssl = off` | `docker exec ... pg_hba.conf`, `SHOW` |
| Outbound network from the harness | None: no HTTP or socket code in `harness/` or `run_benchmark.py`; it talks to PostgreSQL by DSN and to Docker by `docker exec` | `grep` |
| How the DSN reaches the harness | `run_benchmark.py --pg-dsn <dsn>`: **the password travels in the command line** (visible in the process list and shell history). The tests read it from the environment variable `NEXUS_BENCH_PG_DSN` | code |
| Docker access | Alternative A's backup and restore use `docker exec` into the container, which requires the invoking user to be able to use the Docker daemon (root-equivalent on that machine) | code |
| What the outputs contain | `environment.json` has the authorisation record and the store configuration (versions and settings), no DSN or password | code |
| Data in the container | BIBLIO records derived from public OEPM files (1.29 GB in the spike); the container is stopped, not removed | `docker ps -a` |

### B. The Lenovo as it is configured today (read from the infrastructure repository, not from the host)

| Item | Finding | Source |
|---|---|---|
| Inbound firewall | UFW default deny incoming; allowed: `22/tcp` and `41641/udp` (Tailscale) | `roles/node/tasks/hardening.yml` |
| Published container ports | The workload contract (rule 6) allows a published port only for services declared in `published_services` and only on `127.0.0.1` or `100.119.147.8`; `workload-verify` inspects the containers Docker really applied and fails otherwise | `verify_contract.yml`, `playbooks/workload-verify.yml` |
| Other contract rules | Non-root user, read-only root filesystem, no-new-privileges, `cap_drop ALL`, memory/CPU/PID limits, named non-host network, bind mounts only under the workload's config and secrets (secrets read-only), local volume driver only | `verify_contract.yml` |
| Existing pattern for a database | `career-os`: `db` (postgres:16) on a named compose network, **not published**; only `app` is published, on the tailnet address; one password (`POSTGRES_PASSWORD`) from the environment file | `career-os/docker-compose.staging.yml` |
| Secrets flow | SOPS + age: encrypted `staging/<w>.env` in a separate repository; decrypted **on the controller only**; installed on the host as `/srv/secrets/<w>/env`, root, `0600`; variables validated by pattern and `required_env` before anything is changed; no age private key on any host | `docs/workloads-deploy.md`, `secrets/README.md` |
| Custody of the admin age key | Password-manager copy done; **offline passphrase-encrypted copy deliberately deferred**; required before the first production secret; staging and prod use different values and recipients | `secrets/README.md` (status 2026-10-21) |
| Workload placement note | `docs/workloads.md` lists a generic PostgreSQL as "No: no workload asks for it". A database owned by the Nexus workload is not that generic service, but the placement is a decision the owner should record | `docs/workloads.md` |

## 3. Not verified (no access to the host or to the tailnet administration)

* The live state of UFW and iptables on the Lenovo. Docker inserts its own rules and published ports are known not to pass through UFW's input rules, so on this host the address a port is published on (and the contract check of it) is the only network control that has been read, not one that has been observed working.
* Tailscale ACLs: which tailnet devices can reach which ports.
* Whether the Docker volume of a database is covered by the Kopia backup, and how it would be restored.
* The behaviour of the image used on the Lenovo (version and `pg_hba.conf` may differ from the spike's pgvector image).
* Any rotation or recovery drill.

## 4. Findings

| # | Finding | Severity for the pilot | Action (none taken here) |
|---|---|---|---|
| F1 | The harness takes the DSN, password included, on the command line | Low on the single-user dev machine; unacceptable as a habit for anything with a real credential | Read the DSN from the environment or a `PGPASSFILE`; change in a separate PR to the harness, not before the review/authorisation of #156 |
| F2 | The spike database uses a superuser with a weak throwaway password | Acceptable only because the container is loopback-only, local and disposable | Never reuse it; remove the container and volume after the benchmark; the staging design below does not use a superuser for loading or serving |
| F3 | The image trusts local and loopback connections inside the container | Equivalent to root on the host (needs `docker exec`); not reachable through the published port (verified) | Keep the database unpublished or loopback-published; record that `docker exec` access means database access |
| F4 | A tailnet load needs a published database port, which `career-os` avoids | Widens exposure to every tailnet device, whose reach depends on ACLs not seen here | Prefer loopback publication plus an SSH tunnel (§5.1) |
| F5 | Postgres roles are cluster-wide and PUBLIC may connect to `postgres` and `template1` by default | Found by a test (§6): without a revoke, the loader and app roles could connect to the default databases | `REVOKE CONNECT ... FROM PUBLIC` in the bootstrap (in `roles.sql`) |
| F6 | The workload role installs one environment file per workload on the host | A loader credential in it would sit on the host | §5.3 needs either a controller-only secret in the role or a SCRAM verifier; neither exists |
| F7 | Offline copy of the admin age key is deferred | Fine for staging secrets; blocks production | Owner action before any production secret |

## 5. Proposed custody model for the staging deployment

Specification only. It requires changes to the `infrastructure` repository that are **not made here**, and every item of §7 must hold before the gate can be considered met.

### 5.1 Network

* `db` runs on a named compose network, with the contract's hardening. It is not published on the tailnet address.
* For loading, `db` is published only on `127.0.0.1:<port>` of the host (the contract allows it when the service is listed in `published_services`). The loader on the controller reaches it through an SSH tunnel (`ssh -L`) over the existing key-only SSH. Nothing new is opened on UFW or on the tailnet. Transit is encrypted by SSH; inside the host the loopback hop is local.
* The `app` is published on the tailnet address exactly as `career-os` does and reaches `db` over the compose network.
* Authentication method for every remote address stays `scram-sha-256`; `trust` exists only inside the container for the local socket and loopback (F3).

### 5.2 Roles and grants (specified in `experiments/adr-0037-gate3-custody/roles.sql`, tested in §6)

| Role | Login | Can | Cannot |
|---|---|---|---|
| admin (bootstrap superuser, `POSTGRES_PASSWORD`) | yes | bootstrap, finalize a version, operator tasks | n/a; used by neither the app nor the loader |
| `loader` | only during a load window | create a schema and load it | read or change anything once the version is finalized; create roles; reach other databases |
| `app` | yes | `SELECT` on finalized versions; `TEMPORARY` (alternative A keeps eligible ids in a session-local table) | any write, any DDL, create schemas, see an unfinalized version |
| `frozen` | never | owns finalized schemas and tables, so a finalized version cannot be altered or dropped through any login | n/a |

Finalizing a version (transfer of ownership to `frozen`, then `GRANT SELECT` to `app`) is a separate admin step, so a loader mistake cannot publish a version. The loader is `NOLOGIN` outside a load window.

### 5.3 Secrets

* Three secrets in `secrets/staging/nexus.env` (encrypted, SOPS + age, same rules as `career-os`: URL-safe, minimum length enforced by `env_patterns`, never printed): the admin password, the `app` password and the `loader` password.
* The `app` password reaches the host with the existing environment file. The `loader` password must stay on the controller: either a controller-only environment file supported by the role (new) or a SCRAM verifier set on the host with the cleartext kept only on the controller (to be designed and tested; not done).
* Passwords are given to tools through environment or a password file, never on a command line (F1).

### 5.4 Rotation

Rotate by changing the value in the encrypted file, running the playbook, then `ALTER ROLE ... PASSWORD`. The `app` needs a restart; the `loader` needs nothing between load windows. A credential that has appeared in a chat, a log or a commit is treated as exposed and reissued, as the existing rules already say. A rotation drill has not been run.

### 5.5 Failure behaviour

* The `app` aborts at startup, serving nothing, if it cannot connect, if its role lacks `SELECT`, or if the manifest and content-digest verification of ADR 0037 §3.3 fails.
* A load that fails midway leaves an unfinalized schema that the `app` cannot see (tested). A restore is a single transaction and leaves nothing partial (harness test).
* A secret that fails its pattern stops the playbook before the host is touched (existing behaviour).

## 6. What was tested

`experiments/adr-0037-gate3-custody/test_roles.py` runs against a throwaway database and throwaway roles of the spike container (it needs `NEXUS_BENCH_PG_DSN`, generates its own passwords, prints none, and removes everything, including the `CONNECT` revoke it makes on `postgres` and `template1`). 10 tests, all passing on 2026-10-22:

* the loader creates and loads a version before finalization; the app cannot see it;
* the app reads a finalized version and is refused ten write, DDL and schema-creation statements;
* the app can create a temporary table and use it against finalized data;
* after finalization the loader is refused eleven statements, including reading, `DROP`, `TRUNCATE`, `GRANT` and `ALTER ... OWNER`, and cannot create a schema under the name of a finalized one;
* neither role can connect to other databases nor write to `public` (this found F5);
* neither role is superuser, can create roles or databases, replicate or bypass row security; passwords are SCRAM hashes; `frozen` cannot log in;
* the loader is refused when its login is switched off and works again when it is switched on.

Mutation check: removing the `CONNECT` revoke, the ownership transfer, or granting `ALL` instead of `SELECT` to the app each makes the intended test fail.

## 7. What would close the gate (none done)

1. A change in `infrastructure` adding the Nexus workload with the model of §5, reviewed and applied with `--check` first.
2. `workload-verify` and `security-verify` passing on the Lenovo, and `ss -ltnp` on the host showing the database port only on `127.0.0.1`.
3. The loader credential handling of §5.3 implemented and tested, including that it is not on the host.
4. One rotation drill and one failed-load drill recorded.
5. The owner's recorded decisions below.

## 8. Decisions for the owner

* D1. Load over an SSH tunnel to a loopback-published port (recommended) or publish the database on the tailnet address.
* D2. Loader `NOLOGIN` outside load windows (recommended) or always enabled.
* D3. How the loader credential stays off the host: controller-only secret support in the role, or a SCRAM verifier.
* D4. Keep `TEMPORARY` for the app or change alternative A to pass the eligible ids as a parameter.
* D5. Record that a database owned by the Nexus workload is an accepted exception to the generic "PostgreSQL: No" of `docs/workloads.md`.
* D6. Offline copy of the age key before any production secret (already planned in `secrets/README.md`).
