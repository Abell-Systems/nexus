# Phase 2 Sector Taxonomy Amendment: closing the `sector` attribute

**Status:** Proposed. This is a **methodological amendment record**, kept separate from
`docs/empirical-study-protocol.md` §4.1 by design: the protocol's `sector` attribute
definition is not rewritten here as if it had always named six closed categories. This
document records a decision made *after* pre-registration to close an open-ended
attribute the protocol specified but never finished specifying — the same pattern
`docs/phase2-sample-size-amendment.md` uses for the N=60→39 gap.

## What was pre-registered

`docs/empirical-study-protocol.md` §4.1 lists `sector` as a required per-demand
attribute:

> `sector`: Industrial domain classification (Consumer Chemistry, Sanitary/Materials,
> Industrial IoT/Energy, Metallurgy, Biotechnology, **etc.**).

RQ4 independently names overlapping example domains:

> ... distinct technological domains (e.g., consumer chemistry, industrial
> machinery/IoT, metallurgy, renewable energy storage) ...

Both are open-ended ("etc.", "e.g."). Neither closes a finite category set. No other
protocol section, ADR, or repository artifact defines one either — confirmed directly
against the frozen N=39 corpus (`data/evaluation/dataset_phase2_demand_corpus_n39.json`
carries no `sector` field, and `target_cpc_prefixes` is empty for all 39 records, so
there is no fallback CPC-derived signal). The only concrete application of these
category names anywhere in the repository is `docs/data_provenance.md` §2, describing
three unrelated, hand-picked INDUSAC demo calls (#2292/#2293/#2297) from an earlier,
separate curated dataset — not a canonical taxonomy, and not applicable to the real
N=39 corpus.

This is a gap in the pre-registered design: `sector` is a required stratification
variable for the Dev/Test split (§3, "stratified by industrial sector"), but was never
operationalized as a finite, assignable category set.

## What this amendment closes

**This amendment closes the category set only, based exclusively on the domains
already named in §4.1 and RQ4.** It does not observe, and was not written by consulting,
the actual distribution of the 39 Phase 2 demands. No category below was added,
removed, split, or merged on the basis of the observed Phase 2 demand corpus.

> **Adequacy rule:** the taxonomy's adequacy is judged solely by its correspondence to
> the pre-registered domain (protocol §4.1 / RQ4), never by the distribution observed in
> the Phase 2 N=39 corpus. If applying it (in #80) later reveals a stratum too small for
> a sensible Dev/Test partition, that is a real, expected consequence handled downstream
> in the partition-rule design (#79) — it is not, by itself, grounds to reopen or amend
> this taxonomy. A future phase finding it inadequate is a new amendment/version, never
> a silent edit to `v1`.

### D1 — Closed category set: `phase2_sector_taxonomy_v1`

| Code                       | Sector                              | Traceable to |
|-----------------------------|--------------------------------------|--------------|
| `CONSUMER_CHEMISTRY`        | Consumer Chemistry                   | §4.1 |
| `SANITARY_MATERIALS`        | Sanitary / Materials                 | §4.1 |
| `INDUSTRIAL_MACHINERY_IOT`  | Industrial Machinery / IoT            | §4.1 ("Industrial IoT") / RQ4 ("industrial machinery/IoT") |
| `ENERGY_STORAGE`            | Energy / Renewable Energy Storage    | §4.1 ("Energy") / RQ4 ("renewable energy storage") |
| `METALLURGY`                | Metallurgy                           | §4.1 / RQ4 |
| `BIOTECHNOLOGY`              | Biotechnology                        | §4.1 |

Six categories, closed. No thirteenth "Other"/"Miscellaneous" bucket is defined —
ambiguous cases are resolved by D5 below, into one of these six, not into a residual
category that would itself need justification.

`§4.1`'s single combined example "Industrial IoT/Energy" is resolved into two separate
categories (`INDUSTRIAL_MACHINERY_IOT`, `ENERGY_STORAGE`), because RQ4 independently
names "renewable energy storage" as its own technologically distinct example alongside
"industrial machinery/IoT" — the two are not the same technical domain (mechanical/
control systems vs. energy storage chemistry/hardware), and RQ4's separate mention is
itself part of the pre-registered design being materialized here, not an invention.
They are not split further (e.g. separating "machinery" from "IoT", or "storage" from
"generation") because §4.1/RQ4 give no basis to draw those finer lines, and doing so
with only 39 demands would risk single-digit strata with no pre-registered support for
the split.

### D2 — Classification unit: exactly one sector per demand

Each demand is assigned **exactly one primary sector**. Not multi-label.

`sector` means **the primary technological domain of the need expressed in the
demand** — not every industry the resulting technology could conceivably be applied
in. A chemistry-based technology later usable in IoT sensors is still classified by
the demand's primary technical object, not by a downstream application.

Multi-label was rejected because #79 needs one stratification key per demand; assigning
more than one would require inventing an unregistered tie-break rule for how a
multi-sector demand counts toward the Dev/Test split, itself a new experimental
construct this amendment is explicitly meant to avoid introducing.

### D3 — Permitted / forbidden information

**Permitted (available before any classification decision):**
- `title`
- `description`
- demand provenance metadata already present in the frozen corpus (source, origin
  country, posted date)

**Forbidden:**
- retrieved candidate patents
- retrieval/similarity scores of any kind
- patent CPC/IPC classifications
- demand–patent concordance of any kind
- any output produced by Nexus's matching pipeline

Rule: **sector classification is a property of the demand, determined independently of
the experiment being evaluated.** This prevents leakage into #79's partition and, later,
into ADR 0016's normalization decision.

### D4 — Assignment rule

Applied in strict order, stopping at the first level that resolves a single sector:

1. **Primary technical object** of the demand (what is being sought/described).
2. **Primary technical problem** the demand seeks to solve, if (1) alone does not
   disambiguate.
3. **Industrial domain of application**, used only when (1) and (2) do not
   disambiguate — never as the first-pass criterion.

Example: a demand describing a solution usable across chemistry, automotive, and
energy contexts is not counted in all three. The rule asks: *what technical object/
problem constitutes the core of the expressed need?* — and assigns exactly the one
sector that answers that.

`CPC/IPC is explicitly not used` (D5): sector assignment is demand-side and
text-based only.

### D5 — CPC/IPC is not used

Sector assignment does **not** use CPC/IPC codes, demand-side or patent-side.

Reasons:
- `target_cpc_prefixes` is empty for all 39 frozen demand records — there is no
  existing demand-side CPC to reuse.
- Deriving one now (via `map_concept_to_cpc`/`extract_demand_cpc_auto` or any other
  method) would introduce a classification layer the protocol never specified for this
  purpose, and would conflate two distinct constructs: `sector` (§4.1, a demand
  attribute) and `classified_cpc_prefixes`/CPC concordance (§4.2, the matching
  engine's own signal, deliberately structured as a separate, pre-registered
  automated/expert-assisted modality to avoid circularity — see §4.2).
- It is not needed: sector is fully determinable from demand text under D4.

### D6 — Ambiguity handling

If, after applying D4's full ordered rule, more than one sector remains equally
supported by the demand text:

1. Re-read the demand's `title` and `description` jointly (not in isolation) and
   re-apply D4 once.
2. If still tied, the assignment is resolved by the primary technical object named
   *first* in the `title` (titles are the demand's own stated framing of its
   primary need).
3. Every ambiguous case resolved by step 2 must be recorded with an explicit
   rationale in the assignment artifact (#80) — which candidate sectors were tied,
   and why the title-order tie-break selected the one it did. This is auditability,
   not silent disambiguation.

No sector is assigned by guessing or by convenience toward a better-balanced
stratum — this rule is fixed now, before any of the 39 demands are read against it.

### D7 — Versioning and freezing

The taxonomy is named `phase2_sector_taxonomy_v1` and is normative for all of Phase 2
once this amendment merges. Its frozen specification (this document) constitutes the
category definitions; a subsequent, content-addressed artifact (#80) will record the
actual per-demand assignments made against it — this amendment does not itself contain
any assignment.

Each category, once applied in #80, is fixed for `v1`. A future phase that finds it
inadequate documents that as a new version (`phase2_sector_taxonomy_v2` or similar) in
a new amendment — never a silent edit to this one.

## Relation to the protocol

This amendment **materializes** a variable the protocol already required (`sector`,
§4.1) by closing its open-ended example list into a finite, assignable set. It does
not introduce a new experimental construct, and it does not alter the study's
scientific questions (RQ1–RQ4) or endpoints. The six categories are each traceable to
an explicit protocol mention (table in D1); none is derived from, or tuned to, the
Phase 2 N=39 corpus's observed content.

## What this amendment does not do

- Does not assign any of the 39 demands to a sector (that is #80, after this merges).
- Does not touch the Dev/Test partition rule (#79) or ADR 0016's normalization
  decision.
- Does not modify `docs/empirical-study-protocol.md` §4.1 itself — the protocol's
  original open-ended text is left unchanged, exactly as `docs/
  phase2-sample-size-amendment.md` leaves §3.2's `N=60` unchanged.
