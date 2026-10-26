# ADR 0037 gate 5: licences and retention

**Purpose:** evidence for gate 5 of [ADR 0037](../adr/0037-operational-corpus-in-database.md) §5 and §5.1 (licensing and retention). It inventories the data and software the pilot touches, what each source's terms say with a pointer to where, what the project does with it, and what is not established. **It is not legal advice, it does not close the gate and it does not accept the ADR.** Where a right is not evidenced it says *pending*; no legal conclusion is drawn.
**Date:** 2026-10-22. **Companion:** the gate 3 evidence (network and credential custody), PR #158.

## 1. Method and limits of the evidence

* Terms were read from the publisher's own pages on 2026-10-22 with a fetch tool that **summarises and limits quotations to about 125 characters**. Quotes below are therefore fragments; a person must read the full text of every clause that matters before relying on this document. Pages that show no version or date are recorded as such.
* Software licences were read from the metadata of the packages installed in the benchmark environment, or from the upstream `LICENSE` file, not from memory.
* The repository was inspected for what it tracks (`git ls-files`) and for its visibility (`gh repo view`). The git **history** was not scanned.
* Not examined: the Kopia retention settings of the Lenovo, the contents of the git-ignored data beyond their manifests, and any contract with Minesoft.

## 2. The repository is public and tracks third-party material (finding G1)

`Abell-Systems/nexus` is **public**, licensed MIT (`LICENSE`: "Copyright (c) 2026 Abell Systems"; GitHub reports the same). It tracks, among other files:

| Tracked path | What it is | Size |
|---|---|---|
| `backend/test/fixtures/innoget_sample_*.html` (2 files) | Pages of Innoget technology calls | e.g. 152,870 bytes |
| `backend/test/fixtures/lombardia_sample_*.html` (3 files) | Pages of the Lombardia open-innovation portal | not measured |
| `backend/test/fixtures/epo_ops_*.xml`, `oepm_bopi_sample.xml` | Samples of EPO OPS and OEPM BOPI responses | not measured |
| `data/snapshots/patents_es_corpus.parquet`, `.jsonl`, `patents_es_manifest.json` | Spanish patent corpus with title and abstract (OEPM BOPI per `docs/data_provenance.md`) | not measured |
| `data/annotations/pilot_strict_annotation_*.csv` | Annotation sheets with patent title, abstract and CPC, by demand id | small |
| `docs/validation/validation_sheet_v1.csv` | Demand titles (Innoget) against asset titles | 23,707 bytes |
| `data/external/wipo_schmoch_2008_ipc_technology_concordance.pdf` | WIPO IPC-technology concordance (Schmoch 2008) | 113,367 bytes |
| `experiments/article/minesoft_*` (31 files) and `exports/*.xlsx` | CSVs with `family_id, leader_id, compound, title, family_countries, has_ES`, apparently from the Minesoft service (inferred from the folder names, not from a source statement) | up to 542,026 bytes |

The MIT licence is the project's licence for its own work. Whether it can cover third-party data files kept in the same public repository is exactly what §3 leaves open for each source. **None of this has been assessed as lawful or unlawful here.**

### 2.1 State after #160, #161, #162 and #163 (2026-10-23)

The table above is the inventory as found on 2026-10-22. D1 has since been applied in part (merge commits `033283d`, `d91b55d`, `8a7febf`, `62d44ee`); the per-file record is `docs/data-acquisition/third-party-files-d1-inventory.md`.

| Item | State now |
|---|---|
| Innoget fixtures | Replaced by synthetic ones (#160). The real page is still in git history |
| Corpus of 39 demands (37 Innoget, 2 Open Innovation Lombardia): full title and description in 6 JSON files and 63 quotes in 2 scripts | Retired from the tree, identity recorded in `RETIRED_FILES.json`, scripts read an external restricted copy and stop if it is absent, synthetic set added (#161). A CI guard checks the versioned tree |
| Validation sheet | Titles removed from the versioned copy; the full sheet is generated privately (#162) |
| Employer-tagged personal given names in the independence example and test | Replaced by synthetic strings (#163). They remain in ADR 0029, the independence protocol, plans and `experiments/` data (kept provisionally as historical record) |
| Demand ids | Kept (provisional) |
| Requesting-organisation names | Pending a specific review |
| 2 Lombardia fixtures and their test | Replaced by synthetic ones (after this section was written, see the D1 inventory); the 2 demands still need their own authorisation |
| EPO OPS and OEPM BOPI samples, patent corpus snapshots, annotation sheets, WIPO PDF, Minesoft CSVs | Unchanged, pending review (annotation sheets checked: no Innoget text) |
| Git history, forks, clones, backups | Not touched. Nothing here is a deletion; rewriting history is a separate open decision |

Limits of the guard: exact fingerprints of selected text in the versioned tree; no paraphrase, no history.

## 3. Data: rights by source

| Source | What Nexus holds, where | What the source's terms say (pointer) | State |
|---|---|---|---|
| **OEPM OpenData** (BIBLIO 2000-2025, the white-space corpus) | 26 files, 793 MB, git-ignored, hash-pinned in `config/whitespace/oepm_biblio_2000_2025.json`; the spike database is a derived copy | The legal notice (`https://sede.oepm.gob.es/eSede/datos/es/aviso-legal/`) allows reuse "para fines comerciales y no comerciales" under Ley 37/2007 and RD 1495/2011, on conditions: cite "Origen de los datos: Oficina Española de Patentes y Marcas"; "Está prohibido desnaturalizar el sentido de la información"; state the date of the last update when the document gives it; do not suggest the OEPM sponsors or supports the reuse; keep the update-date and reuse-condition metadata. Read 2026-10-22 (no version or date shown on the page) and recorded earlier from a logged-in session on 2026-10-21 in `docs/whitespace/oepm-bulk-datasets-audit.md` §2 | **Documented.** Repository's own reading: derived products are not forbidden if the conditions are met. Counsel has not reviewed the notice (`docs/whitespace/oepm-biblio-corpus-characterization.md`, row "Licence"). The SOAP service's terms are separate and unread |
| **OEPM BOPI corpus** (`patents_es_corpus`, tracked in git) | Title, abstract, assignee, CPC, filing and publication dates | Provenance recorded in `docs/data_provenance.md` (datos.gob.es / OEPM Datos Abiertos). Its own licence statement was not separately verified | **Pending** as a separate source. Whether the attribution and update date accompany the tracked files was not checked |
| **Google Patents Public Data** (operational corpus: title, abstract, assignees, CPC of 54,997 assets; embeddings derived from the text) | `data/snapshots/operational_corpus_v1`, git-ignored, 229 MB | The publisher's blog (`https://cloud.google.com/blog/products/gcp/google-patents-public-datasets-connecting-public-paid-and-private-patent-data`) prints the attribution line "Source: “Google Patents Public Data” by IFI CLAIMS Patent Services and Google, CC BY 4.0" and, for CPC, "by the EPO and USPTO, for public use". The dataset's own listing or terms page was **not** retrieved; the `google/patents-public-data` repository states Apache-2.0 for the repository only | **Documentary support for CC BY 4.0, formal terms not retrieved.** The repository's docs say counsel has not confirmed the chain of the underlying patent-office data and that this is needed before charging for anything |
| **Innoget demands** (37 of the 39 demands, with title, description, date, country, `source_url`) | Inside the operational snapshot (git-ignored). *As found on 2026-10-22:* titles also in the public `validation_sheet_v1.csv` and two Innoget pages tracked as fixtures, both since removed from the tree (2.1) | Innoget Terms of Service, "last updated March 2026" (`https://www.innoget.com/terms-and-conditions`), Section 6: use, exploitation, copying and reproduction of site content "without written permission" prohibited; contributors' content belongs to its authors; Section 2.4: "You may not engage in any commercial activities" (user conduct). The page was searched for scraping, extraction and robots terms and **none was found**. Extraction was done on 2026-08-25 by "structured web extraction" (`docs/data_provenance.md`); the version of the terms in force then is not established | **Pending, and the highest-risk item.** No written authorisation from Innoget or the authors was found in the repository |
| **Lombardia open-innovation portal** | One demand in the 39; three pages tracked as fixtures | Terms not examined | **Pending** |
| **Minesoft** (commercial patent service; extracts for the article) | CSVs and exports tracked in the public repository | No terms or contract in the repository | **Pending** |
| **EPO Open Patent Services** | Samples as fixtures; ingestion code | OPS terms of use not read | **Pending** |
| **WIPO concordance** (Schmoch 2008) | PDF with a `.sha256` file, tracked | WIPO terms for this publication not read | **Pending** |

Derived artifacts (embeddings, pair counts, section maps, the normalised database): their status depends on the source rows above. The OEPM terms speak of derived use; for the other sources **no statement about derived data was found**.

## 4. Software and components

| Component | Licence (as read) | Source |
|---|---|---|
| PostgreSQL | The PostgreSQL License; "Portions Copyright © 1996-2026, The PostgreSQL Global Development Group" | `https://www.postgresql.org/about/licence/` (2026-10-22) |
| pgvector | PostgreSQL License | upstream `LICENSE`, `master` (2026-10-22). The Python client `pgvector 0.5.1` declares MIT in its package metadata |
| DuckDB 1.5.5 | MIT ("Copyright 2018-2026 Stichting DuckDB Foundation") | upstream `LICENSE` (2026-10-22); package classifier "MIT License" |
| pyarrow 26.0.0 | Apache-2.0 | package metadata |
| numpy 2.5.4 | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | package metadata |
| pydantic 2.14.1, pytest 9.1.1 | MIT | package metadata |
| httpx 0.28.1 | BSD-3-Clause | package metadata |
| tenacity 9.2.1, requests 2.34.2 | Apache-2.0 | package metadata |
| **psycopg 3.3.6 and psycopg-binary 3.3.6** | **LGPL-3.0-only** | package metadata |
| SOPS | Mozilla Public License 2.0 | upstream `LICENSE` (2026-10-22) |
| age | BSD 3-Clause (copyright The age Authors, Google LLC, Filippo Valsorda) | upstream `LICENSE` (2026-10-22) |
| Docker image `pgvector/pgvector:pg17` | Contents (a Debian base plus PostgreSQL and pgvector) **not audited** | n/a |
| Ansible, Kopia, Tailscale, Docker | **Not checked** | n/a |

Observations:

* The versions read are those of the benchmark environment, which **differ from the pins** in `backend/requirements.txt` (`pyarrow` 26.0.0 against 25.0.1, `numpy` 2.5.4 against 2.4.6, `pydantic` 2.14.1 against 2.13.4). The licence of the pinned versions was not checked. The same difference matters for the benchmark's reproducibility, not only for licences.
* `psycopg` is LGPL and is used by the benchmark harness and would be used by the loader. It is not in `backend/requirements.txt`. If the loader or the database adapter becomes part of a distributed image, the LGPL obligations (and those of the libraries bundled in `psycopg-binary`) need a review that has not been done.

## 5. Findings

| # | Finding | Evidence |
|---|---|---|
| G1 | The public repository tracks third-party content (§2) whose terms are pending or restrictive | `git ls-files`, `gh repo view` |
| G2 | The Innoget terms prohibit copying and reproducing site content without written permission; the demands were extracted programmatically and no authorisation is recorded | Innoget ToS Section 6, `docs/data_provenance.md` |
| G3 | The operational manifest says `license_status: "UNVERIFIED - internal use only; do not redistribute until verified"`, while the documentation says "CC BY 4.0, attribution shown on screen". The database manifest of ADR 0037 §3.2 would carry whichever text is chosen | `manifest.json`, `operational-mvp-quality-evidence.md` |
| G4 | OEPM's conditions (attribution, last-update date, "do not distort") apply to every derived table and to the product; compliance in the explorer page, the tracked files and the database manifest was not verified | OEPM legal notice; `product-vertical-2-contract.md` says "source attribution as in vertical 1" but the code was not checked |
| G5 | No source states the status of embeddings or other derived data of its text, except the OEPM notice for its own data | §3 |
| G6 | The benchmark's outputs (digests, counts, timings, ids) contain no corpus text, except demand identifiers in W7's per-demand diagnostics; the run's tracebacks (`incident.json`) can contain local paths | harness code |
| G7 | The spike database (1.29 GB of derived OEPM data) sits on the developer machine and in a stopped container | `docker ps -a` |

## 6. Retention: what exists and a proposal for the owner

The right-hand column is a **proposal**, not a decision.

| Artifact | Where | Third-party text? | Proposed retention and deletion trigger |
|---|---|---|---|
| OEPM source zips | `data/raw/oepm_open`, git-ignored, hash-pinned | Yes (public, OEPM terms) | Keep while the study needs reproducing; re-downloadable, so deletion is recoverable |
| Operational snapshot (parquet, embeddings, demands) | `data/snapshots/operational_corpus_v1`, git-ignored | Yes (Google Patents text; **Innoget text**) | Keep while the MVP runs; the Innoget part waits for G2; delete on a rights-holder's request |
| Spike database and container | OMEN, Docker volume | Derived OEPM | Delete after the benchmark results are committed and gate 1 is decided; the scripts rebuild it |
| Staging database (when it exists) | Lenovo | As the corpora it holds | One immutable schema per version (ADR 0037 §3.1); keep the current and the previous; drop older ones on the owner's order |
| Backups of the database volume | **Declared** (§6.1): Kopia snapshots only `/mnt/data/valentin/backup-data`; a Docker volume is not in that path | As above | **Pending:** observe the real Kopia configuration (§6.1); until then, no deletion promise and no assumption that the database is backed up |
| Benchmark aggregate results (`summary.json`, `timings.json`, `environment.json`, `RESULTS.md`) | Repository | No (G6) | Keep as evidence, **conditional on reviewing the artefacts** for identifiers and local paths before committing |
| Benchmark per-demand records (`raw.jsonl` and per-demand diagnostics) | Repository or work directory | No text, but **demand identifiers** | Do not assume harmless: review the identifiers against the Innoget decision (D2) before publishing; retention to be decided after that review |
| Execution logs, tracebacks and `incident.json` | Work directory | No text, but local paths | Review and redact before publishing; keep only with the results they explain |
| Tracked third-party files of §2 | Public repository | Yes | Owner decision (D1); removing from the working tree does not remove them from history, forks or clones |

### 6.1 Kopia as declared in the infrastructure repository (not observed on the host)

Source: `valentinlineiro/infrastructure`, `roles/node/tasks/backup.yml`, `docs/backup-operations.md`, `docs/ADR-001-backup-tool.md`, `docs/recovery.md`, read locally on 2026-10-22. This is the **declared** state; the Lenovo was not inspected.

* Source of the snapshot: `/mnt/data/valentin/backup-data` only. `/srv` (workload code, config, secrets) and `/var/lib/docker` sit on the SSD and are **not** declared as sources; `docs/recovery.md` lists `/srv/*` as "SSD + Kopia snapshot of backup-data where applicable". A PostgreSQL volume would live under `/var/lib/docker` or `/srv`, so by declaration it has no Kopia backup.
* Repository: filesystem repo `/mnt/backup-external/kopia-lenovo` on an external NTFS disk selected by UUID. The wrapper skips with a warning when the disk is absent ("expected state"), so snapshots can be missing for long periods.
* Schedule: daily timer with a randomised delay and `Persistent=true`.
* Retention: `--keep-daily 7 --keep-weekly 4 --keep-monthly 6`, no yearly, applied by policy on the source path. The Drive repository was discarded (2026-09-10).
* A pre-purge snapshot set (242 GB) is documented as surviving "until 7/4/6 retention prunes", which is the declared precedent that deleted data persists in snapshots until retention expires.
* A file-level snapshot of a live PostgreSQL data directory is not a consistent backup; the dump-based path of ADR 0037 would be needed. Not designed.

Three separate questions, which the inspection answers only in part: **coverage** (is `/srv` or `/var/lib/docker` a source), **consistency** (a file copy of a running PostgreSQL is not a recoverable backup whatever the coverage), and **retention** (seven/four/six is the declared policy for data in the snapshots, not a guarantee of how long a deleted item stays). Even a clean inspection would not make the policy adequate for staging; that is a decision for D6.

**Consequence if the declaration is accurate:** the database would not be backed up, so deleting a source from it would not leave copies in Kopia, but a disk failure would lose it; and anything placed under `backup-data` would persist up to about six months after deletion. Both statements depend on the observation below.

**Read-only inspection for the host owner (run as root; prints no secrets).** Do not share `repository.config`, the password file or any output containing keys.

```bash
kopia --version
systemctl list-timers 'kopia*' --no-pager
systemctl cat kopia-lenovo-hdd.service kopia-lenovo-hdd.timer | grep -v -i -E 'password|token|key'
sed -E '/KOPIA_PASSWORD|PASSFILE/d' /usr/local/bin/kopia-lenovo-hdd.sh
findmnt /mnt/backup-external; ls -ld /mnt/backup-external/kopia-lenovo
kopia repository status 2>&1 | grep -v -i -E 'password|key'
kopia policy list; kopia policy show --global; kopia policy show /mnt/data/valentin/backup-data
kopia snapshot list --all | tail -n 40
journalctl -t kopia-lenovo-hdd --since '60 days ago' --no-pager | tail -n 40
df -h /srv /var/lib/docker /mnt/data /mnt/backup-external
docker volume ls
```

What the output must settle: which paths have snapshots; the effective retention; the date of the last snapshot; whether the disk was present; whether `/srv`, `/var/lib/docker` or any volume is a source.

#### 6.1.1 Observed on the Lenovo without root (2026-10-23)

Read-only commands run over SSH as the unprivileged user (`valentin`, in the `sudo` and `docker` groups; no password prompt answered, no `sudo` used). Output kept in the session scratchpad, not in the repository.

| Observation | Result | Reading |
|---|---|---|
| Kopia version | `0.23.1` | As declared |
| Timer | `kopia-lenovo-hdd.timer` active; last run Fri 2026-10-23 08:23 CEST, next 2026-10-24 00:23 | The job fires daily |
| Deployed wrapper | Same as the Ansible role: repository `/mnt/backup-external/kopia-lenovo`, single source `/mnt/data/valentin/backup-data`, skips quietly when the disk or the repository directory is missing | Matches the declaration |
| `/mnt/backup-external` | `findmnt` printed nothing and `/mnt/backup-external/kopia-lenovo` does not exist | **The external backup disk is not mounted at the time of the check.** With this wrapper, a run in that state ends in "skipping" without a snapshot. Whether snapshots exist from earlier runs was not observed |
| Disks | `/` and therefore `/srv` and `/var/lib/docker` are on `/dev/sda2`; `/mnt/data` is `/dev/sdb1` (280 GB used) | `/srv` and `/var/lib/docker` are not under the snapshot source, as declared |
| Docker volumes | `career-os-staging_pgdata` exists | A PostgreSQL volume of another workload lives in `/var/lib/docker`, **outside the declared Kopia source** |
| Journal of the job | Not readable by this user (not in `adm`/`systemd-journal`) | Whether recent runs said "snapshot ok" or "HDD absent, skipping" is **not observed** |

Still not observed (needs root): `kopia snapshot list`, the effective policy, the repository status, the date of the last real snapshot, and the journal. Until then: **the declared coverage is confirmed for the source path; the declared retention is unconfirmed; and the external disk being absent means the existence of any recoverable snapshot is unconfirmed.** No deletion promise and no assumption that a database volume is backed up.

#### 6.1.2 Observed on the Lenovo with `sudo` (2026-10-23)

Run by the owner over `ssh -t` (two earlier attempts ran on the developer workstation, not on the Lenovo, and are not evidence). The external disk had been connected that day (`/dev/sdc1`, NTFS, 1.8 TB, UUID as expected, plugged at 09:20) but was not mounted and has no `fstab` entry. It was mounted **read-only** for the commands and unmounted afterwards (`unmounted-ok`). The only change on the host: an empty directory `/mnt/backup-external` created as mount point. While it is not mounted, the wrapper finds the UUID, sees the parent filesystem type and skips with "mount unexpected".

Before the disk was connected, the journal of `kopia-lenovo-hdd` showed four runs, all `HDD absent, skipping` (2026-10-22 07:57 and 08:23, 2026-10-23 07:52 and 08:23); it returned nothing older although 60 days were requested (journal retention not checked).

**Snapshots in the repository (all there is):**

| Source | When | Size | Files | Retention tags shown |
|---|---|---|---|---|
| `root@valentin:/mnt/data/valentin/backup-data` | 2026-09-09 15:15 (+1 identical until 17:09) | 242.3 GB | 8027 | latest-4..5, hourly-4..5, daily-3 |
| same | 2026-09-10 10:52 (+2 identical until **2026-09-11 10:37**) | 48.7 GB | 7897 | latest-1..3, hourly-1..3, daily-1..2, weekly-1, monthly-1, annual-1 |

* **Last snapshot: 2026-09-11 10:37.** Nothing in the six weeks since. No other source is in the repository.
* The 242.3 GB / 8027-file snapshot is the **pre-purge** state; it is still in the repository, as `docs/backup-operations.md` anticipated "until retention prunes". Nothing has pruned it because no snapshot has been taken since.

**Effective retention policy for the source** (differs from the declared 7/4/6):

| Rule | Value | Origin |
|---|---|---|
| Daily / weekly / monthly | 7 / 4 / 6 | defined for the target |
| **Annual** | **3** | inherited from global |
| **Hourly** | **48** | inherited from global |
| **Latest** | **10** | inherited from global |
| Scheduled snapshots | none in Kopia (the systemd timer is the scheduler) | |
| Compression | zstd, with the never-compress list as declared | |

Reading (an inference from the policy, not tested): with `latest 10` and `annual 3`, a snapshot would not simply expire after about six months; one per year is kept for up to three years. Retention is applied when snapshots are made or maintenance runs; I did not check Kopia maintenance. Deleting something that is in a snapshot would need an explicit snapshot deletion and repository maintenance, not just waiting.

**Scope:** the only source is `backup-data` on `/mnt/data` (personal data by its path name; its contents were not examined). The Nexus corpus is not in that path, and `/srv`, `/var/lib/docker` and the staging volume are outside the source. So by this evidence **the Lenovo's Kopia repository holds no Nexus data, and Nexus staging data on the Lenovo would have no backup.**

**Conclusion for D5 at this point:** declared coverage confirmed for the source path; **actual protection lapsed** (last snapshot 2026-09-11; the scheduled job has been skipping because the disk was not available to the system); effective retention is more generous than declared (annual 3, hourly 48, latest 10) and does not run while no snapshots are taken; recovery of `backup-data` is plausible from the two surviving states but was not tested (no restore was attempted). A complete-deletion promise cannot be made for anything in `backup-data`; for Nexus data there is no Kopia copy to delete, and also none to restore.

**Owner's answer, 2026-10-23 (statement in the session, not verified on the host):** the owner disconnected the external disk from their own PC; "nothing serious". This explains why the disk was not available to the Lenovo in October; it implies the disk is a portable drive that moves between machines, so the backup depends on someone reconnecting and mounting it on the Lenovo. It does **not** say when it was first taken away, so the absence of snapshots since 2026-09-11 is still not explained, and it does not change the findings above: the last snapshot is 2026-09-11 and nothing protects Nexus staging data.

**Operational question (not decided here):** whether the external disk is meant to be disconnected. If intended, document when it is connected, how copies are made meanwhile and what protects the data in the interval. If not, treat it as a possible interruption of the backup protection and find since when. In both cases the quiet "skipping" deserves attention. Nothing about the mount, the timer or the script is changed under D5 without operational authorisation.

**What is still open for D5:** (a) why there is no snapshot since 2026-09-11 and whether the disk was meant to be absent (operational answer needed); (b) whether anything else protects `backup-data`; (c) whether a restore works (never tested here); (d) the intended backup of Nexus staging, which does not exist today; (e) the intended procedure when the disk is absent, and whether the quiet skipping should alert. Items 1-4 of the earlier list (repository, snapshots, policy, last snapshot, scope) now have evidence.

**Deletion and recovery.** The owner authorises any deletion. Removing a source from a database corpus means building a new version without it (versions are immutable), dropping the old schema, and then purging the backups that still hold it, which depends on the unread Kopia retention. A restore is checked by the manifest digest of ADR 0037 §3.3 and, for the benchmark, by W6; neither tells whether a restored copy brings back material that was meant to be deleted. That interaction is not designed yet.

#### 6.1.3 Observed and changed on 2026-10-26 (D5: automount; the gap is not yet explained)

Sources: read-only SSH from the developer workstation, and output pasted by the owner from sessions on the Lenovo. Facts first, then inference.

**Facts**
* The Lenovo is **switched off on purpose** (owner's statement). `last -x` shows a clean shutdown and boot every working day (2026-10-20 to 2026-10-23: boot about 07:50-08:40, shutdown about 17:30-18:45) and one weekend off (shutdown 2026-10-23 17:30:29, boot 2026-10-26 08:41:09). The shutdowns are orderly (the journal ends at `shutdown.target`). Who or what shuts it down was not found.
* At about 08:55 on 2026-10-26 the disk was attached (`sdc1`, NTFS, UUID `9420E7F320E7DA6E`) and **not mounted**; `/etc/fstab` had three lines and no entry for it. The journal shows, for the 09:00:49 run of `kopia-lenovo-hdd`: `mount unexpected, skipping`. The unit ended `status=0/SUCCESS` in 27 ms. So that run took no snapshot and nothing flagged it.
* Owner's decision: the disk should mount by itself when connected.
* Infrastructure PR #18 (merge `534594c`) adds an fstab entry by UUID (`ntfs-3g`, `nofail,x-systemd.automount,x-systemd.device-timeout=10s`, root-only) and changes the wrapper so that a disk that is present but not mounted **fails** (unit failed, journal `err`) instead of skipping; an absent disk still skips. `node.yml --check` showed 5 changes (these two, a drift in `node-housekeeping.sh` that predates this work, and two GPG-key downloads that `get_url` always reports in check mode; both keys were identical to the upstream ones); the real run gave `ok=71 changed=5 failed=0`.
* After the run the automount unit was generated but `inactive` (systemd starts it at boot). The owner started it by hand: `/dev/sdc1` appeared as `fuseblk rw` under the automount. Reading it as a non-root user gave `Permission denied`, by design (`umask=077`, root-only).
* The owner then started `kopia-lenovo-hdd.service`: the journal shows `snapshot ok` at **2026-10-26 10:35:56**.

**Repository after the snapshot** (`sudo kopia snapshot list --all`, pasted by the owner; one source, `root@valentin:/mnt/data/valentin/backup-data`):

| First snapshot of the group | Object | Size | Files / dirs | Identical ones after it | Retention tags shown |
|---|---|---|---|---|---|
| 2026-09-09 15:15:46 | `k79e2a36f…` | 242.3 GB | 8027 / 378 | 1, until 2026-09-09 17:09:37 | latest-5..6 |
| 2026-09-10 10:52:27 | `k6d5e6098…` | 48.7 GB | 7897 / 378 | 3, until **2026-10-26 10:35:54** | latest-1..4, hourly-1, daily-1, weekly-1, monthly-1..2, annual-1 |

* The snapshot of 2026-10-26 (journal `snapshot ok` 10:35:56; listed at 10:35:54) was grouped by Kopia as **identical to the one of 2026-09-10**: same root object, same size (48.7 GB) and counts (7897 files, 378 dirs). Before it that group ended on 2026-09-11 10:37 (§6.1.2), so it grew from 3 to 4 snapshots. Reading, an inference from how Kopia groups identical snapshots: nothing under `backup-data` changed between 2026-09-10 and 2026-10-26 as far as Kopia can see. It does not say anything about the content being the intended one.
* The tag `monthly-1..2` now covers two months (September and October), which fits one snapshot having been added in October.

**Not verified**: what the data contains (only Kopia's metadata was read); that the automount starts by itself at the next boot; any restore; that the identical-snapshot reading above holds, since it was not checked against the source.

**Inference, not tested**: the missing fstab entry explains the skip of 2026-10-26 (disk attached, not mounted). It does **not** explain the whole gap since 2026-09-11: on 2026-10-22 and 2026-10-23 morning the runs said `HDD absent` (disk not attached, §6.1.2), and the journal before 2026-10-22 was not readable. Whether the disk was attached and unmounted between 2026-09-11 and 2026-10-22 is unknown.

**D5 status after this**: mounting and silent skipping of an attached disk: addressed in infrastructure (applied on the host, one real snapshot). Still open: the cause of the gap before 2026-10-22; a restore test; any backup of Nexus staging (the source is still only `backup-data`); an alert on the age of the last snapshot that does not depend on the disk being present (the observability script looks at the last 48 hours of `snapshot ok` in the journal, and a machine that is off at night makes a daily job easy to miss).

## 7. Scientific publication: what can accompany an article (proposal)

* **Likely compatible with the evidence above:** the project's own code (MIT); the benchmark results and manifests (hashes, counts, timings); aggregate results derived from OEPM data, with "Origen de los datos: Oficina Española de Patentes y Marcas", the date of the last update, no suggestion of OEPM endorsement, and a statement of any record dropped or corrected.
* **Needs a decision before inclusion:** the normalised BIBLIO tables or the embeddings of third-party text.
* **Not without the rights-holder's authorisation (per §3):** Innoget demand text, Minesoft data and any other source marked pending.
* The runbook's existing rule stays: no claim that ranking quality is validated, no price, demand or market-size figure, and the CC BY 4.0 reading is not legal advice.

## 8. Pending evidence, owner decisions and closing conditions

The three are different things. A decision recorded is not evidence obtained, and neither closes the gate.

### 8.1 Containment measures (provisional, reversible; applied status in 2.1)

* No new copy of the Innoget demands is added to the shared staging database or to any new operational snapshot until D2 is resolved.
* The operational corpus stays out of staging (D4) until the scope of the rights review and the provenance of its components are clear. That a source is publicly accessible does not by itself show that all its data may be redistributed.
* `license_status` keeps an explicitly unverified state (D3); it is not replaced by an affirmative licence without evidence. The Google blog attribution is not a verification of the whole chain of rights.
* The retention table of §6 is not presented as approved, and no complete-deletion promise is made until the Kopia policy is read (D5).
* The benchmark of gate 1 stays awaiting a person's authorisation; this document does not authorise it.
* Nothing is removed from git history; that is a separate, outward-facing decision.

### 8.2 Order in which to decide (by exposure, reversibility and dependency)

1. D1-D2: third-party files and Innoget.
2. D4: operational corpus in staging.
3. D3: `license_status`.
4. D5-D6: Kopia retention read first, then the retention table.
5. D7-D8: assign owners to the pending checks and set the scope of legal review. They do not delay 1-4.

### 8.3 Pending evidence (to obtain, not to decide)

* Full text of Innoget §2.4 and §6 and of the OEPM legal notice, read by a person.
* Kopia: the host inspection of §6.1 (declared state is recorded, observed state is not).
* Terms still marked *pending* in §3: Minesoft, EPO OPS, WIPO, OEPM BOPI dataset licence; Google Patents formal dataset terms.
* LGPL review of `psycopg` if the loader is distributed in an image.
* Reproducibility: the benchmark environment versions differ from `backend/requirements.txt`; a separate task, outside this PR.

### 8.4 Provisional decisions on D1 and D2

Status: **adopted by the owner on 2026-10-22** (recorded in the session as "adoptadas"). They are provisional operational measures, not legal conclusions about past extraction, and **the D1 part is applied in part (see 2.1); no request to Innoget has been sent.**

* D1. Replace the Innoget fixtures with synthetic or minimal examples that keep the test cases. Review the Lombardia, EPO OPS, OEPM, WIPO and Minesoft files one by one; they do not necessarily get the same treatment. History is not rewritten.
* D2. Request written authorisation for the 37 Innoget demands (the 2 Lombardia demands need a separate request), stating the uses, storage and publication it would cover. Until it exists, the demands do not enter the shared staging database.
* Replacing files in the working tree does not remove them from existing commits, forks or clones. The fixture review and the history decision are recorded independently, and the second is still open.

### 8.5 Owner decisions

* D1. What to do about the third-party files tracked in the public repository (§2): ask each rights-holder, replace them with synthetic or minimal fixtures, or keep them with a recorded basis.
* D2. Whether to ask Innoget for written permission for the 37 demands (a draft exists, not sent; Lombardia separate), and whether staging may hold them meanwhile (8.1 proposes no).
* D3. Which text `license_status` carries in the manifest (G3).
* D4. Whether staging may include the operational corpus before counsel confirms the Google Patents chain, or only the OEPM corpus.
* D5. Who reads and records the Kopia retention and the volume's coverage.
* D6. Approve or change the retention table of §6.
* D7. Who performs each pending check of 8.3.
* D8. Whether counsel reviews the OEPM notice and the Google Patents chain (both recorded as unreviewed).

## 9. What would close the gate (none done)

1. The decisions D1-D8 recorded **and** the containment measures of 8.1 either applied or explicitly declined.
2. Every *pending* row of §3 evidenced from the publisher's own terms (page, date, full clause read by a person) or removed from the pilot.
3. The manifest text and the product's attribution checked against the OEPM and Google conditions.
4. The Kopia retention read and the retention table approved.
5. The benchmark artefacts reviewed for identifiers and paths before any is published.

Decisions documented alone do not close the gate.

## 10. How the evidence was gathered

`gh repo view Abell-Systems/nexus --json visibility,licenseInfo`; `git ls-files` on `backend/test/fixtures`, `data`, `docs/validation` and `experiments/article`; the pages named in §3 and §4 on 2026-10-22; `importlib.metadata` on the benchmark environment; the repository documents cited by path.
