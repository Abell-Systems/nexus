# Vertical 3: acceptance status against the contract and ADR 0038

**Status:** Working record, not an approval. It traces each requirement to what exists today. It does not declare the view conforming to ADR 0038 E5 and it authorises no merge, deployment or exposure.
**Date:** 2026-10-27
**Checks:** [vertical 3 contract](product-vertical-3-contract.md) §2–§9 · [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) E1–E8
**State of the pull requests when written:** #182 (data copy and nginx barrier), #186 (verified loader) and #187 (screen, stacked on #182 and carrying #186's commit) are **open drafts, not merged**. #184 (texts) is a draft. Everything marked below as «in #18x» is therefore not on `main`.

## 1. Vocabulary

| Word | Meaning here |
|---|---|
| Merged | On `main`. |
| Implemented | Code exists on an open branch; not on `main`. |
| Tested | An automated test fails if the behaviour breaks. A test is not claimed to cover more than it asserts. |
| Run | Executed by hand by the assistant on a local build. **Not independent**: the contract asks scenarios to be run by a named person and recorded. |
| Inspected | Read in a diff or file, with the reader named. An inspection is not a test. |
| Pending | None of the above. |

## 2. Data and gates (merged)

| Requirement | Source | Status | Evidence |
|---|---|---|---|
| Expected count E3, years without documents skipped, never zero | ADR E3; contract §3, §6 | Merged, tested | #179 |
| Versioned result of unobserved pairs, invariants against the pair and density results | contract §6; ADR E8 | Merged, tested | #180 |
| Completeness gate of 2025 (≤ 1 % absent per kind group, fail-closed) | contract §9.2 | Merged, tested; **run on 2026-10-27 against the committed exposure result**: `allowed: true`, no reasons, each group within threshold (EP translations, kind `Y`, other) | #181; the run is a command output, not yet recorded in a signed exposure record |
| Contract and ADR 0038 accepted | — | Merged | #177, #178 |
| Amendment §6.1 (integrity at load) and M8 | contract §6.1, §8 | Merged | #185 |

## 3. Loader and integrity (contract §6.1 and its tests)

| Requirement | Status | Evidence / gap |
|---|---|---|
| One loader; hashes in a manifest inside the bundle | Implemented in #186 (loader) and #187 (manifest import of `provenance.json`) | The manifest for the identifier lists does not exist (no lists). |
| GET with `cache: 'no-store'`, status exactly 200, `arrayBuffer()`, `JSON.parse` only after equality, `response.json()` never used | Implemented, tested (#186) | 18 tests including a spy on `JSON.parse`. |
| Body-read failure is a load error (T18); mismatch, missing entry, missing hash, missing or undefined manifest, hash failure are integrity errors (T19) | Implemented, tested | #186. |
| Pure-JS SHA-256 without a new dependency, not relying on `crypto.subtle` | Implemented, tested | Written from FIPS 180-4, origin stated in the file header. Dependency absence: **inspected by the assistant** (no change in `package.json`); the contract asks the review to check it. |
| SHA-256 vectors required by §8: empty, «abc», 55/56/64/119 bytes of «a», the NIST 56-byte message, one million «a», and an input of at least 2.5 MB against an independent implementation | **Partly tested** | #186 covers empty, «abc», the NIST message and lengths 55, 56, 63, 64, 65, 119, 120, 1000, 100000 against Node `crypto`. **Missing:** one million «a» and the ≥ 2.5 MB comparison. |
| Test with `crypto.subtle` stubbed as undefined: correct file accepted, one changed byte rejected | **Pending as a unit test** | The loader never calls `crypto.subtle`, but no test stubs it. Covered only by the manual run below. |
| Negative tests detect removal of the check (delete or skip the comparison and see the tests fail) | **Pending** | Must be recorded in the PR that implements the loader. |
| Screen: on rejection no pair, count or list in the DOM; integrity text and load-error text are different and never shown together | Implemented, tested (#187) | |
| «Each of the states T15 to T19 and the empty result renders a different text» | **Partly** | T14, T18, T19, T12, T13, T08 exist (T13 and T14 untested). T15, T16, T17 do not (no signal for not published or blocked). |
| No service worker or application cache | Inspected (assistant): no `serviceWorker` in `frontend/src`; **not tested** | Review must repeat the inspection. |
| M8 on a local `static` build, non-loopback address, no `crypto.subtle` | **Run by the assistant on 2026-10-27**, not independent | Address `172.17.0.1:8089` (Docker bridge, outside LAN and tailnet); `isSecureContext === false`, `crypto.subtle === undefined`; nginx block lifted inside the container; original file works; one byte changed inside a string value (`independence` → `independenEe`, 1 byte per `cmp`, still valid JSON) shows the integrity text, no table; original restored works again. `nginx -t` run as root in the container failed (cause not investigated), the reload worked. A named person has not run or recorded it. |

## 4. Screen (contract §2–§4)

| Requirement | Status | Evidence / gap |
|---|---|---|
| Open from an anchor of the front page; no router, no dependency | Implemented in #187 | Nav anchor `#pares-no-observados`. |
| No list of pairs before a subclass or section is chosen | Implemented, tested, run in a browser | The 2.8 MB file **is fetched at the first touch of a control** (search needs the list of active subclasses), but no pair is drawn. Whether §2.3 also forbids the fetch is a reading of the contract still to be decided. |
| Search by symbol; section; type A and type A with expected ≥ 1; sort | Implemented, tested | |
| Default order alphabetical by first then second subclass | Implemented, tested | Checked against the full real file in a test and in a browser. |
| Expected-count sort only on the user's choice, with the notice | Implemented, tested, run in a browser | |
| The link keeps the default order (no shareable sort) | Implemented trivially: the view has no URL state | Not tested. |
| One decimal for the expected count; the browser computes no metric | Implemented | |
| Mandatory texts: notice with ADR 0036 link, parameters, absence sentence, limits | Implemented, tested | Texts of #184 as approved (T19 approved 2026-10-27; T22 not approved; T23 excluded). #184 is not merged. |
| Study status line stays on the page | Existing in the page | Not specific to this section. |
| Forbidden formulations over page text, accessible names and data labels | Implemented, tested for the states the test renders | The check is the one described in the contract; **missing:** a test that the allowlist equals the mandatory constants; the check covers the section, not the whole page. |
| No rank column, position badge, colour scale on the expected count, or «top N» headline | Implemented, tested for the column set | Pagination of 200 rows follows the user's chosen order and does not headline the first rows. Inspection only for the rest. |
| States T08, T12, T18, T19 | Implemented, tested |
| States T13 (subclass without unobserved pairs) and T14 (loading) | Implemented, **no test** | |
| States T15, T16, T17 | **Pending** | No signal exists for «not published» or «blocked by the completeness gate». A `404` is a load error (T18) and is not relabelled. |
| Open a pair (§2.6) and the evidence (§5): per-year terms, corpus identity, hashes, configuration identifier, limits | **Pending** | Not implemented in #187. |
| Full list of publication identifiers and dates per subclass, on demand (E5) | **Pending** | Not generated, not stored, not served. Storage options in #183; owner's decision provisional and conditional on a person reading the OEPM legal notice. |
| T20, T21, T22 | **Pending** | Depend on the evidence panel and E5. |

## 5. Contract §8 automated list

| Item | Status |
|---|---|
| typecheck, lint, build, unit tests | Run on #187: full frontend suite 94 passed, 1 skipped (pre-existing); `tsc -b`, `oxlint`, `npm run build` clean. CI of the three PRs is separate and not summarised here. |
| Keyboard operation | **Pending** (no test) |
| Phone width without horizontal scroll | **Pending** (no test) |
| Playwright journey (open, notice, search, filter, sort, open a pair) | **Pending** (not in the repository; a manual browser run was done on 2026-10-27 for everything except opening a pair) |
| The diff adds no endpoint and no dependency and changes no figure of the study | Inspected by the assistant; to be repeated by the reviewer |
| Test that no file of this vertical imports study code (§7) | **Pending** |
| No script computes quality of the ordering on study origins (§7) | No such script exists; no test asserts it |
| Documentation gate | Passes on this branch (local run); not checked here for #182, #186, #187 |

## 6. Manual scenarios and gates for exposure

| Id / gate | Status |
|---|---|
| M1 reading of the order by a person who has not read the ADR | Pending |
| M2 sort by expected count and notice; link keeps default | Pending (behaviour observed by the assistant, not recorded as the scenario) |
| M3 every text read against the forbidden list by a person | Pending |
| M4 follow the evidence to the corpus identity and recompute one pair by hand | **Pending and blocked** until the evidence panel exists |
| M5 initial and empty states | Pending |
| M6 desktop, phone, keyboard only | Pending |
| M7 access-list record before the first outside viewer, with the panel decision for each person (ADR E7) | Pending |
| M8 | See §3: run by the assistant, not recorded by a named person |
| Visual review | Pending |
| Completeness gate | Passes in a local run; to be recorded with the exposure |
| OEPM legal notice read by a person (gate 5 §8.3, E8) | Pending |
| Authorisation to lift the nginx block | Not given. #182 keeps the data answering `404` in the static image; T18 in that case was **run by the assistant** on 2026-10-27 (page 200, data 404, T18 with a working retry button, no table). |
| Deployment to staging | Not authorised. |

## 7. What this record concludes

* **Implemented, tested and run locally:** search, filters, default order, optional expected-count sort with its notice, the integrity check in an insecure context, T18 and T19 behaviour.
* **Not conforming to E5:** the evidence panel, the identifier lists and T22 do not exist. #187 can be accepted only as an intermediate increment documented as such, or after those requirements are met. Nothing here relaxes E5.
* **Independent validation is reserved** for the gates that require a named person (M1–M7, visual review, access record, legal notice). The assistant's runs of T18 and M8 are recorded as such and are not repeated only for that reason.
* **Separate from this record:** a defence against an invalid sort value in the section (a crash, seen only when an invalid value was injected by hand). It is an improvement to be defined with its expected behaviour and a regression test.
