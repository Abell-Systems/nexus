# ADR 0035: OEPM Production-Scale Patent Corpus — Acquisition & Normalization Contract

**Status:** Proposed
**Date:** 2026-09-14
**Scope:** Defines the contract for acquiring and normalizing a production-scale
domestic Spanish patent corpus from OEPM, to replace the 16-patent pilot benchmark
(`data/snapshots/patents_es_snapshot.duckdb`) as the retrieval universe for
`CandidatePoolBuilder` (BM25/CPC/Dense) and, eventually, for the confirmatory
efficacy evaluation itself. **Documentary only — no scraper, harvester, ingestion
code, or DuckDB write happens in this document**, following the same
contract-before-code discipline as ADR 0031/ADR 0032/ADR 0034.

---

## 1. Context

#104's dry-run (`docs/phase2-ted-independence-audit-and-freeze-closure.md`'s
successor work) attempted to build candidate pools for 8 deliberately diverse TED
Dev demands against the only patent corpus materialized in this repo. Result: 5 of 8
pools were empty; the 3 non-empty pools totaled 11 candidates. This is not a pipeline
defect — a bug in `CandidatePoolBuilder._fetch_patents` was found and fixed along the
way, and the 3 non-empty pools confirm the blind-export mechanics work correctly. The
finding is that the **16-patent pilot corpus's domain coverage (detergents, medical
devices, energy storage, IoT — six narrow target sectors chosen for an early pilot)
does not overlap enough with TED's broader public-sector demand topics** (forestry
monitoring, hospital data systems, wastewater treatment, electricity metering, etc.)
to support a meaningful annotation dry-run, let alone the eventual confirmatory
efficacy evaluation.

This is the same class of finding as #101c (InnoGet), #102 (EEN/POD), and ADR 0033
(source qualification): the pipeline works; what it operates on doesn't yet exist at
adequate scale. The fix is the same discipline applied to the *patent* side of the
evaluation for the first time in this study — a contract before acquisition.

## 2. What already exists (reuse, do not rebuild)

- **Canonical target schema:** `domain/models/patent.py::PatentDocument` — already
  defines every field a production corpus must populate: `publication_id`,
  `country_code`, `doc_number`, `kind_code`, `application_number`, `title`,
  `abstract`, `assignees`, `inventors`, `filing_date`, `publication_date`,
  `priority_date`, `classifications_cpc`, `classifications_ipc`,
  `forward_citation_count`, `backward_citation_count`, `family_id`. This ADR does not
  add or change fields — it defines how OEPM data populates them.
- **Family model:** `PatentFamily` / `FamilyMembership` already exist for ADR 0027's
  family-aware evaluation — this corpus must populate them if OEPM family data is
  available (§7), not invent a new mechanism.
- **Retrieval-time schema adaptivity:**
  `infrastructure/matching/duckdb_helpers.py::resolve_patent_columns` already handles
  both a canonical (`publication_id`) and a snapshot (`publication_number`) table
  shape. §5's canonical schema should use `publication_id` directly to avoid needing
  that fallback at all going forward.
- **Eligibility jurisdiction gate:**
  `infrastructure/matching/eligibility.py::DefaultPatentEligibilityPolicy` already
  filters on `patent.country_code == target_jurisdiction` (`"ES"` by default) — §3
  below defines what populates `country_code`, not a new filter.
- **Embedding pipeline:** `scripts/generate_m1_embeddings.py` already pins the model
  (ADR 0014: `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, revision
  `4328cf26390c98c5e3c738b4460a05b95f4911f5`, CPU, `title + ' ' + abstract` input,
  offline, isolated dependency stack) — §8 reuses this generator against the new
  corpus, not a new pipeline.

## 3. What "domestic Spanish patent corpus" means (resolved explicitly, per request)

**In scope:** patents and utility models **nationally filed with and granted by
OEPM** under Spanish jurisdiction (`country_code = "ES"`, `publication_id` prefix
`ES-`) — exactly what `DefaultPatentEligibilityPolicy(target_jurisdiction="ES")`
already assumes and what the 16-patent pilot corpus already used as its convention.

**Out of scope, explicitly:**
- **European Patents validated in Spain (EP-ES / "European patent (Spain)"
  validations).** These are granted by the EPO under the European Patent Convention,
  not OEPM; Spain is a *validation* jurisdiction, not the granting authority. Their
  `country_code` in most patent databases reads `EP`, not `ES`. Including them would
  silently double the definition of "domestic" to include EPO's examination
  standards and priority practices, which is a different population from what ADR
  0031's "domestic technology base" language and the existing eligibility policy have
  meant throughout this study. **Deferred, not decided here** — a future ADR could
  extend jurisdiction scope, but only as an explicit, separate decision.
- **PCT international applications that have not yet entered Spanish national phase**
  at OEPM.
- **Community/EU-unitary patents** (not applicable to pre-2023 filings; out of scope
  regardless of date given the above).

**Consequence stated plainly:** the patent evaluation universe remains narrower than
the demand corpus's own geography (TED admits international European demands, per
ADR 0031 §2.1's `international_european` stratum) — a non-Spanish public buyer's
demand is still matched only against Spanish-granted patents. This is not new: it is
the pre-existing "Demand Origin ≠ Patent Corpus" principle (ADR 0031 §2.1), restated
here because scaling the corpus is exactly the moment this asymmetry needs to be
explicit, not because this document changes it.

## 4. Primary source and coverage

- **Source:** OEPM's OpenData portal (`sede.oepm.gob.es/eSede/datos/es/`), the same
  official source the existing 16-patent pilot corpus's own `dataset_metadata` cites
  (`OEPM-BOPI-ES-INVENES-SNAPSHOT-2024-V1`, catalog URL
  `datos.gob.es/es/catalogo/e05024401-...`). Confirmed (web research, not assumed):
  - Bulk downloads offered as **daily files by publication date, monthly files for
    the current year, and annual files for prior years** — Bibliographic Data, Full
    Text, Legal Data, CPC, and Citations, each as a separate dataset.
  - **XML format, ST36 standard from 2019-01-01 onward; a proprietary XML format
    before that date.** This is a real schema-versioning boundary, not a detail to
    smooth over (§9).
  - An alternative web-service API (`INVENES`) exists for query-based access, not
    just bulk file download — worth evaluating against bulk download for operational
    simplicity, not decided here.
- **Temporal coverage target:** aligned to the demand corpus's own window discipline
  — not the full 1826–present Authority File. A defensible default is a **multi-year
  window ending at the present** (e.g. 2015–2025, wide enough to catch prior art for
  a 2024–2025 demand corpus under any plausible filing-to-grant lag) rather than the
  full historical archive; the exact bound is an implementation decision for the
  follow-on plan, not fixed here, but it must be **narrower than "everything since
  1826"** by default — unbounded ingestion is a volume and provenance risk this
  contract exists to avoid, not a target to reach for its own sake.

## 5. Canonical schema mapping (OEPM field → `PatentDocument`)

| `PatentDocument` field | OEPM source | Notes |
| :--- | :--- | :--- |
| `publication_id` | Bibliographic Data: publication number | Canonical schema, `publication_id` column name directly (not `publication_number`) — retires the need for `resolve_patent_columns`'s fallback for this corpus going forward. |
| `country_code` | Fixed `"ES"` | Per §3 — not derived per-record; this corpus is Spain-only by construction, not by a per-row filter. |
| `doc_number` / `kind_code` | Parsed from the publication number's structure (kind code suffix, e.g. `A1`/`B2`) | Same parsing convention the pilot corpus and `generate_ted_annotation_dry_run.py`'s fallback already use. |
| `application_number` | Bibliographic Data | Direct field. |
| `title` / `abstract` | Bibliographic Data / Abstracts dataset | Direct fields; Spanish-language by default (OEPM's own working language) — no translation performed here. |
| `assignees` / `inventors` | Bibliographic Data | Direct fields; list-valued. |
| `filing_date` / `publication_date` / `priority_date` | Bibliographic Data | ISO 8601 normalization required — OEPM's own date format needs verifying against a real sample before ingestion (not assumed here). |
| `classifications_cpc` | CPC dataset | Direct field; this is the same taxonomy `DuckDbCPCRetriever` already consumes — no new classification scheme. |
| `classifications_ipc` | Bibliographic/Legal Data (IPC often carried alongside CPC in OEPM exports) | To be confirmed against a real sample; may be absent for older records (§9). |
| `forward_citation_count` / `backward_citation_count` | Citations dataset | Requires a citation-count aggregation step per publication, not a raw field. |
| `family_id` | Not confirmed present in OEPM's own exports | See §7 — do not fabricate; leave `null` if genuinely absent, per the same accept-only principle ADR 0029 §3.1 established for organization identity. |

## 6. Deduplication

Per the same principle ADR 0027 established for patent families (no heuristic
similarity merging): deduplication here means **exact `publication_id` uniqueness
within the ingested set**, nothing more. A publication appearing in both a daily and
a monthly/annual bulk file (overlapping windows) is deduplicated by `publication_id`
identity, not by content similarity. No fuzzy or near-duplicate detection.

## 7. Patent families

OEPM's own bulk exports are not yet confirmed to carry a family identifier
compatible with `PatentFamily`/`FamilyMembership`. This must be verified against a
real downloaded sample before ingestion, not assumed. If absent, `family_id` stays
`null` for all records (matching ADR 0029 §2.2's `UNKNOWN != NEGATIVE` principle
applied here: "no family data" is not "no family exists") and ADR 0027's
family-aware evaluation modes (`allow`/`collapse`/`exclude_related`) degrade to
`allow`-only behavior until family data is separately sourced — an explicit
limitation to disclose, not silently patch with a heuristic (e.g. same-applicant
clustering), which ADR 0027 already rejected for the same circularity reason ADR
0029 rejected it for organizations.

## 8. Embeddings

Reuse `scripts/generate_m1_embeddings.py` unmodified against the new corpus once
ingested — same pinned model/revision, same `title + ' ' + abstract` input
convention, same offline/CPU/isolated-stack constraints (ADR 0014). This is an
explicit, separate, later step in the sequence (§11), not concurrent with ingestion.
The `sentence-transformers` dependency stack (`requirements/evaluation-generation.txt`)
is not installed in the primary working environment (confirmed while investigating
#104's dry-run) — provisioning it is part of this later step, not assumed available.

## 9. Corpus integrity criteria

A record is included only if it has: a resolvable `publication_id`, a non-empty
`title`, a non-empty `abstract`, a valid ISO 8601 `publication_date`, and
`country_code = "ES"` by construction. Records failing any of these are logged to an
exclusion manifest (mirroring `mapping_errors.json`'s pattern from the demand-side
pipeline) — not silently dropped. The **pre-2019 non-ST36 format boundary** (§4) is a
known, disclosed schema-consistency risk: records from that era may need a distinct
parser or may be excluded entirely from the first ingestion pass, a decision for the
follow-on implementation plan, not resolved here.

## 10. Snapshot, versioning, provenance

Same pattern as every acquisition artifact in this study: a frozen dataset file (or
DuckDB table) with a `.sha256` sidecar, an acquisition manifest recording source
URLs/file dates, record counts, and exclusion counts, and a `dataset_id` versioned
independently of `corpus_expansion_policy_v*` (this is the *patent* side, not the
*demand* side — the two must never share a version number, to avoid exactly the kind
of cross-contamination risk ADR 0031 §2.1 already flags between demand origin and
patent corpus).

## 11. Sequence (this ADR authorizes none of it)

1. **This ADR** — contract only.
2. **TDD** — schema mapping/parsing unit tests against a small real downloaded OEPM
   sample (not synthetic fixtures alone), mirroring the demand-side mappers'
   discipline (`TedCandidateMapper`, `EenPodCandidateMapper`).
3. **Ingestion** — bulk download + normalization into `PatentDocument` rows, per §5,
   with the exclusion manifest per §9.
4. **Corpus freeze** — sealed artifact + hashes + manifest (§10).
5. **Retrieval smoke test** — run `CandidatePoolBuilder` (BM25 + CPC; Dense once §8's
   embeddings exist) against a handful of already-known TED demands (the same ones
   #104's dry-run tried) and confirm non-trivial, non-empty pools before declaring
   the corpus usable — the same kind of empirical check that caught this gap in the
   first place, not a re-assertion that ingestion "should" work.
6. **#104 dry-run, resumed** — 6–8 TED demands, this time against a corpus sized to
   actually overlap with their topics.
7. Annotation guide, dual annotation, κ, Dev-30 finalization, Test-35 (sealed until
   final evaluation) — unchanged from the #104 plan already agreed.

## 12. Non-goals

- Does not ingest any patent data (§2–§10 are contract, not execution).
- Does not touch the demand-side corpus, ADR 0029, ADR 0031, ADR 0034, or any
  `corpus_expansion_policy_v*`.
- Does not resolve whether EP-ES validations should eventually be included (§3) —
  explicitly deferred.
- Does not commit to a specific temporal window bound (§4) — a range is proposed as
  a default to avoid unbounded scope, not fixed.
- Does not begin or resume #104 — that is explicitly sequenced after §11 step 5.
