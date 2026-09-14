# ADR 0034: TED Source Admission Contract

**Status:** Accepted
**Date:** 2026-09-14
**Scope:** Admits TED (Tenders Electronic Daily, the EU public procurement notice
supplement) as a third authorized primary source under ADR 0031 §2.2, restricted to
`Innovation partnership` procedure-type, `Competition` notice-type records. Defines
the structural fields, the notice-version/amendment resolution rule, and the
provenance contract this source must satisfy. Supersedes nothing in ADR 0031 §2.2 —
adds to it.

---

## 1. Context

ADR 0033 (source qualification gate) and its §6 spike found TED's `Innovation
partnership` `Competition` notices provisionally admissible: identity (buyer name) and
date (`OJ S` publication line) are both structurally mandatory fields, unlike InnoGet
(identity yes, date no) and EEN/POD (date yes, identity no) — the two failure modes
that respectively blocked #101c/#101d's InnoGet exclusion and #102's `N_power = 0`
closure. This ADR formalizes admission and the acquisition contract; it does not
itself acquire any data (ADR 0031 §1.2's "golden rule" pattern, repeated here).

## 2. What was additionally discovered while scoping acquisition

The spike (ADR 0033 §6) inspected TED's Angular-rendered SPA pages
(`ted.europa.eu/en/notice/-/detail/{id}`), which do **not** contain buyer name,
publication date, or description in their initial server response (verified: a plain
HTTP fetch of that URL returns the page shell only, confirmed by `curl` returning no
match for either the buyer name or `OJ S` on that route). Two things make this
tractable without a headless browser (avoiding a fundamentally heavier and less
reproducible harvester architecture than every other source in this study):

1. **A public, unauthenticated JSON search API**
   (`POST https://api.ted.europa.eu/v3/notices/search`), documented by response
   inspection, accepting an expert query (`procedure-type=innovation AND
   notice-type=cn-standard`) and returning `publication-number`,
   `totalNoticeCount` (confirmed `671`, matching the UI count exactly), and — per
   notice — a `links.htmlDirect.<LANG>` URL.
2. **A server-rendered, plain-HTML detail page per notice**
   (`https://ted.europa.eu/en/notice/{id}/html`, `links.htmlDirect.ENG` in the API
   response) that *does* carry buyer name, publication date, and description in
   static markup, each labeled with a stable eForms Business Term (BT) code:
   - `BT-500-Organization-Company` → buyer official name.
   - `BT-24-Procedure` → description (the technical-need narrative).
   - `BT-21-Procedure` → title.
   - `BT-105-Procedure` → type of procedure (confirms `Innovation partnership`).
   - The notice-type summary line additionally carries the literal substring
     `"Change notice"` (or `"Corrigendum"`) when the notice amends an earlier one —
     a plain, deterministic string fact, not a semantic judgment.

This makes the harvester architecture identical in shape to the other three sources:
one HTTP call for listing (paginated), one HTTP call per detail record, plain
`urllib`, no browser automation, no JS execution — consistent with ADR 0032 §3's
provider-agnostic, network-dependency-free core.

## 3. Decisions

### 3.1 Authorized source and construct
* **Source:** `source_id = "ted"`, TED (Tenders Electronic Daily).
* **Permitted construct:** `Innovation partnership` — the `procedure-type=innovation`
  facet, `notice-type=cn-standard` (`Competition`) only. `Result`, `Planning`,
  `Direct award preannouncement`, and `Contract modification` notice types are never
  harvested: they report on, precede, or amend a solicitation, they are not
  themselves one. General (non-Innovation-Partnership) procurement is not authorized —
  ADR 0033 §3.1 found it construct-mismatched (a specification for a known
  deliverable, not an open technical-problem solicitation).
* **Public access mode:** `unauthenticated_public_http` (both the search API and the
  `htmlDirect` detail pages require no authentication).

### 3.2 Structural field mapping (all observed, none inferred)
| Contract field | TED source |
| :--- | :--- |
| `demand_id` | `publication-number` (e.g. `462609-2026`) |
| `organization_raw` | `BT-500-Organization-Company` ("Official name") — **the field EEN/POD structurally lacks; this is TED's central contribution** |
| `publication_date_evidence` | The `OJ S <issue>/<year> <dd/mm/yyyy>` line (or the API's `publication-date` field, ISO-8601) — `evidence_type = EXPLICIT_METADATA`, never the deadline field |
| `title` | `BT-21-Procedure` |
| `description_text` / `technical_problem_evidence_text` | `BT-24-Procedure` — used for both, mirroring EEN/POD's `Technology request`/`R&D request` Abstract-fallback pattern (ADR 0032): no separate "technical spec" field exists here either, so the one substantive narrative field serves both roles, and the existing generic `min_word_count` / `NO_TECHNICAL_PROBLEM` criteria — unmodified — do the actual eligibility filtering (this is why `452177-2026`'s title-duplicate, sub-25-word description was expected to fail `CONTENT_TOO_SHORT` without any TED-specific rule) |
| `geographic_stratum` | Buyer's country: `spain` if Spain, else `international_european` — same two strata ADR 0031 §2.1 already defines, no new stratum |
| `language_code` | Notice's declared language |
| `has_confidentiality_redaction` | Same `[confidential]`/`[redacted]` bracket-marker check already used for EEN/POD and InnoGet |
| `is_publicly_accessible` | `True` (no login) |

### 3.3 Notice-version resolution: amendments are excluded, not chased
A TED procedure can be republished as a `Change notice`/`Corrigendum` (§2's example:
`452177-2026` amends `435752-2026`). Per ADR 0032's Golden Invariant #3 (`t_demand`
must be the genuine original publication, never a later touch), and to avoid the
complexity and reproducibility risk of walking an amendment chain to its origin (an
extra API round-trip per notice, with no guarantee the chain terminates cleanly):

> **Any notice whose type-summary line contains `"Change notice"` or `"Corrigendum"`
> is excluded from mapping outright** (`MappingError`, landing in
> `mapping_errors.json` like any other malformed/ineligible payload — not a new
> domain concept). Only original, first-publication `Competition` notices become
> candidates.

This is a conservative undercount (some procedures' original notice is dropped if a
later notice in the same chain happens to be sampled instead — not expected, since the
harvester enumerates every `Competition`-type publication number, original and
amendment alike, and applies this exclusion per-notice, so an amended procedure's
*original* notice is still harvested and kept; only the *amendment* notice itself is
dropped), never an overcount, and never requires inferring which notice in a chain is
"truly" first beyond the page's own explicit self-declaration.

### 3.4 Independence
No new independence rule. ADR 0029's `derive_independence_groups` applies unchanged:
`organization_raw` (here, populated) groups notices by exact buyer-name string match.
A public body issuing multiple Innovation Partnership notices across the sampled
decade — plausible per ADR 0033 §6.6 — correctly collapses to one `INDEPENDENT`
representative and the rest `PSEUDOREPLICATE`, exactly as SMAR3TS/Lacer, S.A. did for
InnoGet in #102's predecessor audit (ADR 0029 §4).

### 3.5 What stays unchanged
Temporal window (`corpus_expansion_policy_v4` carries forward `2024-01-01`–
`2025-12-31` from `v3` unmodified — TED's decade of depth does not reopen the window
question ADR 0031's temporal amendment already closed), content-completeness
threshold, technical-problem requirement, confidentiality rule, the two geographic
strata, organization independence/UNKNOWN-quarantine, and the prohibition on
outcome-dependent selection (ADR 0031 §2.7) — TED is admitted on §2's structural
evidence, established before any acquisition ran, not because early records look
favorable.

## 4. Non-goals

* Does not admit general (non-Innovation-Partnership) TED procurement.
* Does not walk amendment chains to recover an amended notice's content under its
  original notice's identity — amendments are dropped, not rescued (§3.3).
* Does not parse attached procurement-document PDFs (ADR 0033 §6.1 noted some
  notices' real technical content may live there) — only the notice's own HTML
  fields. A notice whose `BT-24-Procedure` is too thin to pass eligibility is
  correctly rejected, not supplemented from a PDF.
* Does not change InnoGet's or EEN/POD's status, ADR 0029, or ADR 0031's temporal
  window.

## 5. Consequences

**Positive:** the first source in this study to structurally provide both organization
identity and verifiable publication date simultaneously — directly addresses #102's
`N_power = 0` finding without relaxing ADR 0029.

**Negative:** construct-heterogeneous population (ADR 0033 §6.1) means the realized
eligible fraction is unknown until acquisition runs; a public-sector R&D-demand
population is a genuine representativeness difference from InnoGet/EEN's private-
company demands, to be reported explicitly in any downstream analysis, not smoothed
over.
