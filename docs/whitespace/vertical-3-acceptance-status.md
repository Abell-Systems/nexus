# Vertical 3: acceptance status against the contract and ADR 0038

**Status:** Working record, not an approval. It traces each requirement to what exists today. It does not declare the view conforming to ADR 0038 E5 and it authorises no deployment or exposure. Merging code into `main` is not acceptance of the exposure criteria.
**Date:** 2026-10-27 (updated after the merge of #187, and again after #188, #194, #183, #184, #189 and #192)
**Checks:** [vertical 3 contract](product-vertical-3-contract.md) §2–§9 · [ADR 0038](../adr/0038-exploratory-white-space-product-track.md) E1–E8
**State of the pull requests when updated:** merged into `main`: #177, #178, #179, #180, #181, #185, #190, #191, #182, #186, #187 (merge commits in §9). #188 (this record, first version), #194 (its first update), #184 (Spanish texts), #189 (E5 evidence specification), #192 (experience proposal for the evidence sheet) and #183 (E5 storage options and the OEPM notice reading checklist) are merged as well. **Merging a document records its content; it decides nothing it leaves open.** Still open, a draft: #193 (partial evidence sheet, local prototype, blocked by S4/T22). What is marked «merged» below is on `main`; what is marked pending is not.

## 1. Vocabulary

| Word | Meaning here |
|---|---|
| Merged | On `main`. |
| Implemented | Code exists; where it matters the entry says whether it is merged. |
| Tested | An automated test fails if the behaviour breaks. A test is not claimed to cover more than it asserts. |
| Run | Executed by hand by the assistant on a local build. **Not independent**: the contract asks scenarios to be run by a named person and recorded. |
| Inspected | Read in a diff or file, with the reader named. An inspection is not a test. |
| Pending | None of the above. |

## 2. Data and gates

| Requirement | Source | Status | Evidence |
|---|---|---|---|
| Expected count E3, years without documents skipped, never zero | ADR E3; contract §3, §6 | Merged, tested | #179 |
| Versioned result of unobserved pairs, invariants against the pair and density results | contract §6; ADR E8 | Merged, tested | #180 |
| Completeness gate of 2025 (≤ 1 % absent per kind group, fail-closed) | contract §9.2 | Merged, tested; **run on 2026-10-27 against the committed exposure result**: `allowed: true`, no reasons, each group within threshold (EP translations, kind `Y`, other) | #181; the run is a command output, not yet recorded in a signed exposure record |
| Contract and ADR 0038 accepted | — | Merged | #177, #178 |
| Amendment §6.1 (integrity at load) and M8 | contract §6.1, §8 | Merged | #185 |
| Amendment of the evidence sheet: presentation arithmetic (D1), Authority File provenance (D2), configuration identifier (D3) | contract §3, §5, §6 | Merged (requirements only; says nothing about D4) | #190 |
| Result with `documents_by_year` and `configuration`; every earlier field unchanged | contract §6 | Merged, tested: 621 active subclasses, 149,048 unobserved pairs, 2,992,694 bytes, SHA-256 `6a269125d4d92725d74a875f1264553bacb798dac0b1ef7061508027fb3482f7`; configuration id equals the contract's test vector `456858bd…83bd8` | #191 |
| The reconstructed sum of the per-year terms equals the stored expected count for every pair, with `Number(sum.toFixed(9))` and `===`, no tolerance | contract §5 rules 4 and 6 | Merged, tested: 149,048 of 149,048 concordant, in Node (V8); a stored value changed by 1e-9 made the test fail (run once, file restored) | #191; not run in a browser |
| Copy of the result in the frontend with its hash test | contract §6 | Merged, tested; copy byte-identical to the original, `provenance.json` records the SHA-256 above | #182 |
| Static image answers `404` for the data file until the exposure authorisation | contract §8 (exposure gates) | Merged, tested in the staging-compose script test and CI; also **run by the assistant** against a local build | #182 |

## 3. Loader and integrity (contract §6.1 and its tests)

| Requirement | Status | Evidence / gap |
|---|---|---|
| One loader; hashes in a manifest inside the bundle | Merged | Loader #186; manifest import of `provenance.json` in #187. The manifest for the identifier lists does not exist (no lists). |
| GET with `cache: 'no-store'`, status exactly 200, `arrayBuffer()`, `JSON.parse` only after equality, `response.json()` never used | Merged, tested (#186) | 25 loader tests including a spy on `JSON.parse`. |
| Body-read failure is a load error (T18); mismatch, missing entry, missing hash, missing or undefined manifest, hash failure are integrity errors (T19) | Merged, tested | #186. |
| Pure-JS SHA-256 without a new dependency, not relying on `crypto.subtle` | Merged, tested | Written from FIPS 180-4, origin stated in the file header. Dependency absence: **inspected by the assistant** (no change in `package.json`); the contract asks the review to check it. |
| SHA-256 vectors required by §8: empty, «abc», 55/56/64/119 bytes of «a», the NIST 56-byte message, one million «a», and an input of at least 2.5 MB against an independent implementation | Merged, tested (#186) | All of them; the independent implementation is Node `crypto`, on a 2,600,001-byte input. |
| Test with `crypto.subtle` stubbed as undefined: correct file accepted, one changed byte rejected | Merged, tested (#186) | Plus the manual M8 run below. |
| Negative tests detect removal of the check (delete or skip the comparison and see the tests fail) | Run once and recorded in a comment of #186 (not independent) | Skipping the comparison makes 4 tests fail; moving `JSON.parse` before the comparison makes 3 fail. The loader was restored afterwards. |
| Screen: on rejection no pair, count or list in the DOM; integrity text and load-error text are different and never shown together | Merged, tested (#187) | |
| «Each of the states T15 to T19 and the empty result renders a different text» | **Partly** | T08, T12, T13, T14, T18, T19 exist (T13 and T14 untested). T15, T16, T17 do not exist: no signal for not published or blocked. |
| No service worker or application cache | Inspected (assistant): no `serviceWorker` in `frontend/src`; **not tested** | Review must repeat the inspection. |
| M8 on a local `static` build, non-loopback address, no `crypto.subtle` | **Run by the assistant on 2026-10-27**, not independent | Address `172.17.0.1:8089` (Docker bridge, outside LAN and tailnet); `isSecureContext === false`, `crypto.subtle === undefined`; nginx block lifted inside the container; original file works; one byte changed inside a string value (`independence` → `independenEe`, 1 byte per `cmp`, still valid JSON) shows the integrity text, no table; original restored works again. `nginx -t` run as root in the container failed (cause not investigated), the reload worked. Run against the build of #187 before the result of #191 was copied in; **not repeated** on the current `main`. A named person has not run or recorded it. |

## 4. Screen (contract §2–§4)

| Requirement | Status | Evidence / gap |
|---|---|---|
| Open from an anchor of the front page; no router, no dependency | Merged (#187) | Nav anchor `#pares-no-observados`. |
| No list of pairs before a subclass or section is chosen | Merged, tested, run in a browser | The ~3 MB file **is fetched at the first touch of a control** (search needs the list of active subclasses) and nothing is drawn until a choice. **Owner's reading, 2026-10-27: §2.3 prohibits presenting a list of pairs before the choice, not downloading the file.** The behaviour stands. |
| Search by symbol; section; type A and type A with expected ≥ 1; sort | Merged, tested | |
| Default order alphabetical by first then second subclass | Merged, tested | Checked against the full real file in a test and in a browser. |
| Expected-count sort only on the user's choice, with the notice | Merged, tested, run in a browser | |
| The link keeps the default order (no shareable sort) | Implemented trivially: the view has no URL state | Not tested. |
| One decimal for the expected count; the browser computes no metric | Merged | The only arithmetic in the client is the presentation function of #191, which nothing imports yet. |
| Mandatory texts: notice with ADR 0036 link, parameters, absence sentence, limits | Merged, tested | Texts of #184 as approved (T19 approved 2026-10-27; T22 not approved; T23 excluded). #184 is merged (`36cb87c`); T22 and S4 are still not approved. |
| Study status line stays on the page | Existing in the page | Not specific to this section. |
| Forbidden formulations over page text, accessible names and data labels | Merged, tested for the states the test renders | **Missing:** a test that the allowlist equals the mandatory constants; the check covers the section, not the whole page. |
| No rank column, position badge, colour scale on the expected count, or «top N» headline | Merged, tested for the column set | Pagination of 200 rows follows the user's chosen order and does not headline the first rows. Inspection only for the rest. |
| States T08, T12, T18, T19 | Merged, tested | |
| States T13 (subclass without unobserved pairs) and T14 (loading) | Merged, **no test** | |
| States T15, T16, T17 | **Pending, not covered** (owner, 2026-10-27) | No code and no tests. No signal exists for «not published» or «blocked by the completeness gate». A `404` is a load error (T18) and is not relabelled. They belong to the exposure work. |
| Open a pair (§2.6) and the evidence (§5): per-year terms, corpus identity, hashes, configuration identifier, limits | **Pending on `main`**; a partial sheet exists as a **local draft** (#193, not merged, not E5) | The data (`documents_by_year`, `configuration`) and the arithmetic function are merged (#191). The draft shows the symbols, the activity by year on a common scale with 2010 as a gap, the per-year terms with the sum next to the stored value, the traceability and the limits; 125 frontend tests passed in the assistant's own local run at its last HEAD (not an independent check and not acceptance of E5), and it was looked at only locally, by the assistant. Specification in #189 and experience in #192 (both merged as documents; they leave D4, S4 and the panel decision open). |
| Full list of publication identifiers and dates per subclass, on demand (E5) | **Pending** | Not generated, not stored, not served. Requirements recommended in #189 §8; storage options in #183 (merged as options, not as a decision); the owner's choice is provisional, is not a legal conclusion, and is conditional on a person reading the OEPM legal notice. |
| T20, T21, T22 | T20 titles and T21 are used by the draft sheet (#193); **T22 pending** | T22 depends on D4. The draft uses S4, which stands in for T22 and is **not approved**, so #193 cannot be merged until T22 and S4 are decided in #184. |
| S1, S2, S3, S5 (texts of the evidence sheet) | Approved by the owner on 2026-10-27 (review of #192), subject to the forbidden-words check and M3 | S4 not approved. Approval of a text is not acceptance of an implementation. |

## 5. Contract §8 automated list

| Item | Status |
|---|---|
| typecheck, lint, build, unit tests | On the HEAD of #187 before merging (`1bef615`): frontend suite 106 passed, 1 skipped (pre-existing); `tsc -b` exit 0; `oxlint` prints nothing; `npm run build` ok; all 10 CI checks SUCCESS. Not re-run on the merge commit. |
| Keyboard operation | **Pending** (no test) |
| Phone width without horizontal scroll | **Pending** (no test) |
| Playwright journey (open, notice, search, filter, sort, open a pair) | **Pending** (not in the repository; a manual browser run was done on 2026-10-27 for everything except opening a pair) |
| The diff adds no endpoint and no dependency and changes no figure of the study | Inspected by the assistant for #186 and #187; to be repeated by the reviewer. #191 regenerated a result: its earlier fields are unchanged (compared), and the two added keys are new data. |
| Test that no file of this vertical imports study code (§7) | **Pending** |
| No script computes quality of the ordering on study origins (§7) | No such script exists; no test asserts it |
| Documentation gate | Passes on this branch (local run) |

## 6. Manual scenarios and gates for exposure

| Id / gate | Status |
|---|---|
| M1 reading of the order by a person who has not read the ADR | Pending |
| M2 sort by expected count and notice; link keeps default | Pending (behaviour observed by the assistant, not recorded as the scenario) |
| M3 every text read against the forbidden list by a person | Pending |
| M4 follow the evidence to the corpus identity and recompute one pair by hand | **Pending**; the terms can be followed in the draft sheet (#193), but a person has not run it, and E5's identifier lists do not exist |
| M5 initial and empty states | Pending |
| M6 desktop, phone, keyboard only | Pending |
| M7 access-list record before the first outside viewer, with the panel decision for each person (ADR E7) | Pending; the decision on whether Lydia, or anyone, may take part in the human review of the study is **not taken**, and until it is, no candidate is shown to anyone |
| M8 | See §3: run by the assistant, not recorded by a named person |
| Visual review | Pending |
| Completeness gate | Passes in a local run; to be recorded with the exposure |
| OEPM legal notice read by a person (gate 5 §8.3, E8) | Pending |
| Authorisation to lift the nginx block | Not given. `main` keeps the data answering `404` in the static image, where the section shows T18. |
| Deployment to staging | Not authorised. Nothing merged changes a deployment. |

## 7. UX evolution: product proposals, not obligations

The view above is the first instrument of a longer path. The path is a **product proposal**; it does not change the contract or ADR 0038, and the identifiers below do not replace theirs.

| Phase | What the user does | Status |
|---|---|---|
| A. Discover and explore | Reads the notice, searches or filters, understands the default order and the optional expected-count order, and tells apart absent pairs, empty filters, a failed load and an integrity failure | A1–A3 merged in #187 as an intermediate increment; human validation pending (see §4, §6) |
| B. Understand a combination | Opens a pair and sees what it is, which data support it, which corpus and configuration were used, and what cannot be concluded | **Required by E5 and contract §5**; pending |
| C. Link the combination to a technical problem | Describes a problem, what each subclass could contribute, and contrasts the idea with existing documents | Proposal; not specified; needs search capability and sources not defined |
| D. Document and prioritise research | Saves a research sheet (combination, problem, hypothesis, searches, uncertainties); any prioritisation uses explicit criteria agreed with users | Proposal; not specified |

Constraints that hold in every phase: an observed absence does not show that the technology does not exist, that there is an opportunity, or that a patent would be novel or inventive. No score of «potential» and no ranking of opportunities (ADR 0038 E4). If a later phase needs a score, new labels, another way of ordering or an inference the contract does not allow, it is a product and scientific-governance decision taken explicitly, not a change made to fit a design. Success of a first version would be measured by whether a person can explain a pair, find its evidence, state a technical hypothesis and say what to check before proposing a patent, observed in usability sessions; no predictive performance is measured on the study's reserved origins (ADR 0038 E7).

Phases C and D need their own specification (user needs, data sources, scientific risks, acceptance criteria).

## 8. What this record concludes

* **Merged, tested and run locally:** search, filters, default order, optional expected-count sort with its notice, the verified loader with its negative tests, T18 and T19 behaviour, the data for the evidence sheet and the exhaustive concordance of the per-year terms.
* **Not conforming to E5:** the evidence sheet, the identifier lists (D4) and T22 do not exist. #187 is merged as an **intermediate increment** and must not be exposed. Nothing here relaxes E5.
* **Open decisions that are the owner's:** the store of the identifier lists and how they reach the read-only image (#183, provisional); the reader of the OEPM legal notice, **not named** (a checklist is ready in #183); the approval of T22 and S4 (#184); the panel decision of ADR E7 (including whether Lydia may score); whether the partial sheet of #193 is kept, revised or discarded after an evaluation by people; and the full E5 sheet (specification in #189, D4 open).
* **Independent validation is reserved** for the gates that require a named person (M1–M7, visual review, access record, legal notice). The assistant's runs of T18 and M8 are recorded as such and are not repeated only for that reason.
* **Separate from this record:** a defence against an invalid sort value in the section (a crash, seen only when an invalid value was injected by hand); the 22 failures of the full backend suite in a local run, identical on `main` and on the branch of #191 and absent in CI, whose local cause has not been investigated; two Sonar S5778 findings reported earlier in `test_unobserved_pairs.py` (a cleanup item; not rechecked after #191).

## 9. Pull requests referred to

| PR | Subject | State | Merge commit |
|---|---|---|---|
| #177 | Contract (approved) | Merged | `dac1660` |
| #178 | ADR 0038 accepted | Merged | `bd843d5` |
| #179 | Expected count (E3) | Merged | `ea916ba` |
| #180 | Unobserved pairs result | Merged | `c6301db` |
| #181 | Completeness gate | Merged | `92fbd2a` |
| #185 | Contract §6.1 (integrity at load) | Merged | `4c88ecf` |
| #190 | Contract amendment D1–D3 | Merged | `5c80245` |
| #191 | Result with documents by year and configuration; presentation function | Merged | `2ac641f` |
| #182 | Frontend copy of the result and nginx barrier | Merged | `da62a76` |
| #186 | Verified loader | Merged | `4f82f37` |
| #187 | Screen (intermediate increment, not E5) | Merged | `7e9de4d` |
| #183 | E5 storage options for the identifier lists | Merged | `5124408` |
| #184 | Spanish texts by state | Merged | `36cb87c` |
| #189 | E5 evidence sheet specification | Merged | `f7d2124` |
| #188 | This record, first version | Merged | `9f7ca6d` |
| #192 | Experience proposal for the evidence sheet | Merged | `5046574` |
| #193 | Partial evidence sheet, local prototype (not E5, not for exposure; blocked by S4/T22) | Open, draft | — |
| #194 | First update of this record | Merged | `5c9feb7` |
| (this pull request) | Second update of this record | Its state is in the pull request, not in this table | — |
