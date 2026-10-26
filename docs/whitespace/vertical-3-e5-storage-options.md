# Vertical 3, rule E5: where the identifier lists live (options, draft for decision)

**Status:** Draft for review. **No option is chosen and nothing is implemented.** It compares the alternatives against the criteria the review asked for, with the measurements that exist.
**Date:** 2026-10-26
**Checks:** [vertical 3 contract](product-vertical-3-contract.md) §5, §6, §9.1 · [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) E5, E7, E8 · [gate 5](../operations/adr-0037-gate5-licences-and-retention.md) §3, G4
**Scope:** E5 requires, for each active subclass, the publication identifiers and dates of the documents that make it active, loaded on demand when the evidence of a pair is opened. This document decides nothing about the screen, the Spanish terms, or exposure.

## 1. What has to be stored (measured 2026-10-26, definition O4)

One list per active subclass: the publication identifier and the earliest publication date of each document that carries the subclass (union of the subclasses of its earliest date), sorted by date and identifier, as compact JSON. Measured from the local corpus (`BIBLIO_2000…2025`, hashes verified):

| Quantity | Value |
|---|---|
| Active subclasses at 2025 (≥ 20 identifiers) | 621 |
| Subclass-document incidences | 1,281,995 |
| Total size, uncompressed | 37.1 MB |
| Total size, zlib level 6 | **6.3 MB** (what Git would store; the working tree holds the 37.1 MB) |
| Largest list | 2.44 MB (`A61K`) |
| Today's `.git` | 93 MB |

An earlier estimate by source record gave 37.2 MB and 1,287,829 incidences; the O4 figures above replace it. These are measurements of a script run, not yet of a committed artifact.

## 2. Facts that bound the options

* The corpus (793 MB, account-protected download, git-ignored) is **not on the Lenovo and not in CI**. Nothing at deployment can regenerate the lists from the corpus.
* The static staging image is built from a checkout of this repository on the host (`compose up --build`) and serves a read-only filesystem. Files reach the container by being in the build context, or by a mount.
* The workload contract (infrastructure repository, rule 7) confines workload data to `/srv/apps`, `/srv/config` and `/srv/secrets` and forbids mounting `/mnt/data`, the Docker socket and system paths. A bind mount of a new data directory is a change to the contract, not a free choice.
* The repository already versions derived OEPM results with attribution: the subclass pairs (6.2 MB) and the unobserved pairs (2.8 MB). Identifiers and dates are OEPM facts, not derived scores.
* Gate 5 (§3) records that the OEPM legal notice allows reuse, including commercial, **on conditions** (cite "Origen de los datos: Oficina Española de Patentes y Marcas", do not distort the information, state the last update), and that its full text has to be read by a person (pending, §8.3 there). So no option here is cleared by gate 5 yet; the conditions apply to every one of them equally, in or out of Git.
* The history of the public repository is not rewritten (decision on record). A file committed stays in history.

## 3. Options

**A. In Git**, as static files under `frontend/public/data/` (one per subclass, loaded on demand), with the manifest and hash test of `sync_whitespace_frontend_data.py`.
**B. Outside Git**, as a versioned archive plus a manifest committed in Git (file names, sizes, SHA-256, a hash of the set, the corpus identity and the generating commit). A deploy step fetches or copies the archive into the build context and verifies the manifest; if it is missing or any hash differs, the deployment fails.
**C. Generated at deployment from the corpus.** Requires the 793 MB corpus on the host. Listed to be excluded.
**D. A shorter list (for example the 20 earliest identifiers).** Not an option for E5: it is a change to the ADR's rule (§9.1 of the contract), listed to be excluded.

## 4. Comparison

| Criterion | A. In Git | B. Outside Git, manifest in Git | C | D |
|---|---|---|---|---|
| Immutable identity and version | The commit; the manifest hash test already exists | The manifest hash; the archive's identity is only as strong as the store (a release asset can be replaced unless its hash is checked, which the manifest does) | Corpus identity only | — |
| Hashes and reproducible provenance | Yes, same mechanism as today; regenerating from the corpus gives identical bytes (shown for #180) | Yes, if the manifest is verified at every use; reproducible from the corpus the same way | Yes | — |
| Available at deployment | Always: it is in the checkout the host already makes | Depends on a new step and on the store being reachable | Not available (no corpus) | — |
| Missing or corrupt file | The build fails (test and CI), or the file is simply absent from the image | Must be built: a deployment that fails closed on any mismatch; a design to write and test | — | — |
| Update and rollback | A commit; rollback by ref, as today | Two things to roll back together (ref and archive); a mismatch must fail | — | — |
| Repository weight | +6.3 MB in history (37.1 MB working tree), permanent | 0 | 0 | — |
| New moving parts | None | A store, a fetch step in the infrastructure role or a pre-build script, and possibly a rule-7 change if it needs a mount | A corpus on the host (retention, Kopia, gate 5) | — |
| Path to partial or wrong exposure | The files ship with the image; blocking them is an nginx rule like the one for the unobserved pairs | The same, plus a window where the archive and the code differ | — | — |
| Compatibility with gate 5 | Not yet cleared: the OEPM notice's conditions still have to be read by a person | The same; being outside Git does not change the conditions, only who can fetch the files | — | — |

## 5. Reading, kept separate from the facts

* The measurement changes the cost of A: what enters the history is about 6 MB, not 37 MB.
* B's advantage is a smaller repository and a separable data lifecycle; its cost is a deployment path that does not exist yet and must fail closed. Its gate-5 position is the same as A's.
* The deciding questions are therefore not size: (1) is a permanent 6 MB in a public history acceptable for OEPM identifiers and dates under the notice's conditions (to be read by a person); (2) is the owner willing to build and test a fail-closed fetch step for a 37 MB artifact.
* If the answer to (1) is yes, A is the smaller design: nothing new to deploy, to verify or to roll back. If the answer is no, B is the way, and its manifest and deploy check are the work to specify next.

## 6. Decision needed

The owner and the reviewer choose between A and B, after the OEPM notice has been read by a person. Until then: no lists in Git, no deployment path for them, no screen that needs them, and no exposure. This document does not authorise any of those.
