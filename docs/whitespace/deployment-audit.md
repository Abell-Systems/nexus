# Audit of where the white-space page is published (read-only)

**Date:** 2026-10-23 · **Scope:** three questions. Where is the page published? Who can see it? Which version of the product is being served? **Read-only**: no workflow, secret, variable, DNS, configuration or server was changed; no deployment was run; no credential was read or printed. Each statement is marked **Verified** (observed today, with the command or file), **Inferred** or **Pending**.

## 0. Update, 2026-10-23 13:22 CEST: a staging now runs on the Lenovo

The audit below was written before any deployment and is kept as the record of that moment. At 13:19:49 CEST the static staging of the page was deployed to the Lenovo (Nexus `main` at `e8f19c9`, infrastructure `main` at `3b7fac5`). **Current answers:**

| Question | Answer now |
|---|---|
| Where is the page published? | **Verified.** On the Lenovo, container `nexus-staging-web-1`, image `nexus-static:staging` (nginx 1.30.6, 97 MB), `http://100.119.147.8:8081/` |
| Who can see it? | **Verified.** Only machines on the tailnet: the port is published on `100.119.147.8:8081` and nowhere else (`docker inspect` `HostConfig.PortBindings` and `ss`: `LISTEN 100.119.147.8:8081`), plain HTTP, no authentication. The public GitHub Pages site is still the other application |
| Which version is served? | **Verified.** Nexus `main` at `e8f19c9` (the merge of #169 and #171): the served bundle holds the page, the attribution and the download date (20 October 2026). The checkout itself was done by the playbook; reading the commit on the host needs root and was not done separately |

What was deployed and what was not: only the static page. No matcher API, operational corpus, database or secret; `/matches` and `/api/...` answer 404. The bundle still contains the matcher's front-end code, including one interface sentence that mentions Innoget ("Demandas de ejemplo ingeridas desde Innoget"), but no data; excluding it would be a separate change.

Evidence of the deployment (outputs kept by the owner and reviewed):
* First real run (limited to `nexus` by extra vars): directories, deploy key and a 0600 env created; stopped at the checkout with `Permission denied (publickey)`, as planned; `/srv/{code,config,secrets}/nexus` modes checked (755, 755, 700), `env` and `deploy_key` 600 root, `.pub` 644.
* The deploy key was added to `Abell-Systems/nexus` as a read-only deploy key after the organisation setting that disables deploy keys was changed by the owner (the first attempt returned 422).
* Second real run: `ok=33 changed=2 failed=0` (checkout and `compose up`), readiness passed.
* `security-verify.yml`: `ok=18 changed=0 failed=0`, `SECURITY GATE: COMPLIANT`, the container "fully compliant with containment constraints". `workload-verify.yml` (nexus and career-os): `ok=37 changed=0 failed=0`; contract rules 1 to 6 `ok` for nexus (rule 7 skipped: no volumes or mounts); secret paths `600 root`; "no age key files and no private-key-format string under /root, /home, /srv".
* `career-os` untouched: same creation times and states before and after.

Still **not** established: a human visual review of the page; the OEPM reuse conditions for a served page (gate 5); any host other than the Lenovo, GitHub Pages and the container registry (the token cannot list packages). The original `--check` note: on a first run `--check` reaches the checkout and fails there with the same authentication error, so it proves nothing about the build or the start; the role's documentation says otherwise and has not yet been corrected.

## 1. Answer at the time of the first audit (before the deployment)

| Question | Answer |
|---|---|
| Where is the white-space page (`frontend/`, `WhiteSpacePage`) published? | **Nowhere that was found.** Verified: no workflow publishes it; it is built only inside the container image; no host is recorded as running that image |
| Who can see it? | **Nobody outside whoever runs the image locally**, as far as the repository and the checked hosts show. Pending: any host this audit could not see |
| Which version is served? | Not applicable to the white-space page. What *is* public is a **different** application (see 2.1), built from `main` at `eba724c` |

## 2. Evidence

### 2.1 What is published: the "Nexus Scientific Verification" dashboard (not the white-space page)

* **Verified.** `.github/workflows/deploy-nexus-status.yml` builds `nexus-status/frontend`, checks that `dist/project_status.json` equals the root `project_status.json`, and publishes `nexus-status/frontend/dist` to GitHub Pages, only when a `ci` run on `main` succeeded (`workflow_run`); a manual run builds and validates but cannot publish.
* **Verified.** `gh api repos/Abell-Systems/nexus/pages`: `html_url` `https://abell-systems.github.io/nexus/`, `build_type` `workflow`, `public: true`, `https_enforced: true`.
* **Verified.** Latest deployment: id 7274222146, environment `github-pages`, ref `main`, sha `eba724c3851fa455336d80633ae48edf2e8c9d57` (the merge of #166), created 2026-10-23T08:55:52Z, status `success`.
* **Verified.** A public GET of the site returns HTTP 200 with the title "Nexus Scientific Verification". Its JavaScript bundle (`assets/index-CT_FX9J5.js`, 225,921 bytes) contains that title once and **none** of the page strings searched ("Cobertura y ausencias", "Origen de los datos: Oficina", "Explorador de subclases", "White spaces predictivos"). So the public site is not the white-space page.
* **Who can see it: Verified**: anyone with the URL (public repository, public Pages). The README links to it as the "Scientific Dashboard".

### 2.2 The white-space page: built into an image, not deployed

* **Verified.** The `Dockerfile` builds `frontend/` (stage `frontend`, `npm run build`) and copies `dist` into the image as `/app/static`; the entrypoint serves it with the matcher API. `docker-compose.yml` puts it behind Caddy with basic auth (`auth.caddy` is a git-ignored secret, not read here); `docs/deploy.md` describes the procedure and states that the choice of host, DNS, monitoring, CI/CD and secret management are **out of scope**.
* **Verified.** `ci.yml` job "5c. Container Image" builds the image and checks that it refuses an empty volume and that the compose file is valid. It does not push the image to a registry or deploy it.
* **Verified.** `.github/workflows/deploy.yml` deploys to Cloud Run, is headed "TEMPORARILY DISABLED… until VPS / production target is provisioned" and runs only on `workflow_dispatch`. **Verified** (`gh run list --workflow deploy.yml`): its only two runs are from 2026-08-31, triggered by `workflow_run` (the earlier trigger, since replaced), one failed and one cancelled; there is no later run.
* **Verified.** The Lenovo (read-only `docker ps -a`, 2026-10-23) runs four career-os staging containers and no Nexus container. The infrastructure repository's inventory lists only the localhost and the Lenovo; its `workloads.md` lists Hetzner only as a possible placement and Nexus is not a workload there.
* **Inferred.** The deployment path recorded in my session notes (2026-10-01) was a Hetzner VPS with an `<IP>.sslip.io` name and Caddy basic auth, with the VPS not yet created at the time. Nothing in the repository shows it was created. Not a fact about today.
* **Pending.** Whether a VPS, a local machine or another host runs `nexus-mvp` today, with which build and with which artefacts. It cannot be settled from the repository; it needs the owner's statement, or a read of the hosting provider's console, which this audit did not do and has no permission for.

### 2.3 Correspondence with the code

* **Verified.** The white-space components were last changed in #151 (`4e8e67d`); `main` is at `eba724c`. What `main` builds today is the page the contract describes; its tests and Playwright journeys pass (see `mvp-gap-review.md`).
* **Not applicable / pending.** A running instance of the page could not be compared with the code because none was found.

## 3. Consequences for the MVP

1. The "descriptive MVP" is a **built and tested artefact**, not yet a **served product**: nobody outside the repository can open it.
2. The public Pages site shows a different thing (project verification status). Calling it the product, or linking it as the white-space page, would be wrong.
3. Publishing the page needs decisions that are not technical findings: host, access control, domain, who may see it, and the data-reuse conditions of the OEPM for a served page (gate 5). None is made here.

## 4. What would settle the pending items

* The owner states whether `nexus-mvp` runs anywhere, where, with which build and for whom.
* If it runs on a hosting provider: read access to its console or the host, to compare the image digest and the artefact hashes with the repository. The check in `docs/deploy.md` (`/health`, the preflight, the validation-sheet diff) is the procedure already designed for it.
* If it does not run anywhere: a decision on the host and the access model, in its own change, with no secret in the repository.

## 5. Not checked

* Any host other than GitHub Pages and the Lenovo; the registry for container images (the token has no `read:packages` scope: the listing returned HTTP 403); DNS; the content of `auth.caddy`; the Cloud Run project, if one exists.
