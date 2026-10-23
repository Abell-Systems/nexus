# Deploying the MVP

The MVP is one container (`nexus`, the `Dockerfile` at the repo root) behind Caddy, which adds TLS and basic auth. The container needs **no environment variables and no secrets**: the frozen artifacts are a read-only volume and everything else is on its command line (`--artifacts`, `--static`, `--host`, `--port`; see the [runbook](operational-mvp-runbook.md)).

```text
browser --HTTPS--> caddy (TLS + basic auth) --> nexus:8080 --reads--> /srv/nexus/data (read-only)
```

## What you need on the host

- Docker with Compose.
- The frozen artifacts in `data/snapshots/operational_corpus_v1/` (not in git; the runbook explains how to rebuild them). The container refuses to start if any hash does not verify.
- `auth.caddy` next to `docker-compose.yml` (git-ignored; start from `auth.caddy.example`; it is mounted as a Compose secret, so `docker compose up` says "secret file ... does not exist" until it is there):

  ```bash
  docker run --rm caddy:2 caddy hash-password        # prompts for the password, prints the bcrypt hash
  ```

## Run

```bash
docker compose up -d --build
docker compose ps        # nexus turns healthy after the artifacts verify (about 25 s)
```

`docker-compose.yml` publishes only Caddy (80/443); the app port is not exposed to the host. Without a domain Caddy serves plain HTTP on `:80`. To get HTTPS, replace `:80` in `Caddyfile` with the domain, point its DNS at the host, and restart; Caddy obtains the certificate itself.

## Check it before handing out the URL

```bash
curl -i  http://<host>/                      # 401: auth is in front
curl -su <user>:<password> http://<host>/health   # {"ready":true}
docker run -d --rm -p 8099:8080 -v "$PWD/data/snapshots/operational_corpus_v1:/srv/nexus/data:ro" --read-only nexus-mvp
python scripts/demo_preflight.py http://127.0.0.1:8099    # READY: current build, closed legacy routes, five assets per journey
```

The preflight does not speak basic auth, so run it against the bare container as above, not through Caddy.

## Same results after a rebuild

`numpy`, `pyarrow` and `duckdb` are pinned in `backend/requirements.txt` because they decide the numbers of the frozen retrieval. After changing a pin or the base image, the five results of every listed demand must not move:

```bash
python scripts/build_validation_sheet.py data/snapshots/operational_corpus_v1 /tmp/sheet.csv --without-titles
diff /tmp/sheet.csv docs/validation/validation_sheet_v1.csv && echo identical
```

Run it with the interpreter that the image uses (for example through `docker run --entrypoint python`, with `scripts/` and `backend/` mounted) to check the container itself. When the pins were introduced, the unpinned image (`numpy` 2.5.3, `duckdb` 1.5.6) and the pinned one (2.4.6, 1.5.5) gave identical demands, ranks and publication ids.

CI only builds the image, checks that it reaches artifact verification and refuses an empty volume, and validates the compose file (the corpus is not in git). The run above, with the real artifacts, is the manual pre-release check.

## Staging of the white-space page only (Lenovo)

`docker-compose.staging.yml` builds the Dockerfile target `static` (the built SPA behind an unprivileged nginx, `deploy/nginx-static.conf`) and nothing else: **no matcher (neither its route nor its code: the bundle is built with `VITE_STATIC_ONLY=1`), no API, no operational corpus, no database, no secret, no environment.** It shows only the versioned OEPM results the page bundles, with their attribution. The matcher route (`/matches`) answers 404 there. It is the staging of the page, not of the MVP above; the default target of the Dockerfile is still the MVP.

* Published only on the host's Tailscale address (`TAILSCALE_BIND_IP`, exactly one port, 8081 to 8080/tcp), never on `0.0.0.0`; the image is nginx 1.30 (supported branch), pinned by exact version and digest. Access is from the tailnet, over plain HTTP, as for the other workloads of the Lenovo.
* The Workload Security Contract of the infrastructure repository is checked on the rendered configuration by `scripts/check_staging_compose.py` (unit-tested), and on the running container by CI (job "5c. Container Image": the page, `/health`, a data file and the 404 of `/matches`).
* Merging this file deploys nothing. The deployment is the `workloads` playbook of the infrastructure repository, run with the owner's authorisation after the diffs are reviewed.
* Why not the matcher: it needs the operational corpus, which holds Innoget demands that must not enter a shared staging until Innoget answers (ADR 0037, gate 5, D2 and D4).

Local check: `TAILSCALE_BIND_IP=127.0.0.1 docker compose -f docker-compose.staging.yml up -d --build`, then `http://127.0.0.1:8081/`.

## Out of scope here

Choice of host, DNS, rate limiting, backups, monitoring, CI/CD and secret management. Basic auth is enough for a single reviewer; add rate limiting before opening access to more people.
