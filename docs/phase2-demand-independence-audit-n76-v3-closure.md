# Phase 2 Demand Independence Audit — N=76 (v3) Closure

**Status:** Closed. Organization axis (ADR 0029) applied to the 76 candidates accepted
under `corpus_expansion_policy_v3` (`data/experiments/phase2_v3/candidates_accepted.json`,
#101d). Result is decisive and stops the gate before the sector, technology-family, or
duplicate-industrial-problem axes were run.

## What was checked

Per ADR 0029 §3.1 (**Observed Metadata Only — Accept-Only, Never Inferred**):

> Production algorithms must never compute organization identity from demand title,
> description, CPC codes, or external databases.

`derive_independence_groups` (unchanged, no new code) was run against all 76 accepted
records, using each record's `organization_raw` exactly as acquired:

```
accepted total: 76
records with non-null organization_raw: 0
status counts: {UNKNOWN: 76}
N_power (INDEPENDENT count): 0
```

## Why every record is `UNKNOWN`, not a mapper gap

Verified exhaustively across all 315 raw payloads (100%, not a sample): every official
`een.ec.europa.eu` detail page exposes a `Company's Country` field but **never** a
company/organization *name* field, for either `Technology request` or `R&D request`.
Confirmed dt-label taxonomy across sampled pages contains no `Company Name` /
`Organisation name` variant anywhere. This is consistent with EEN's brokered-matching
model: the requesting organization's identity is disclosed only to a partner who
"expresses interest" through the network, never on the public listing.

Several records' free-text `Full Description` *do* name the organization explicitly
(e.g. "Green Tribology Solutions (GTS) develops..."). **This evidence cannot be used.**
ADR 0029 §3.1 forbids inferring organization identity from title/description text
specifically because it is not independently observed metadata — using it here would
be exactly the kind of ad-hoc, unverified-inference shortcut ADR 0029 was written to
prevent, for the same reason ADR 0029/ADR 0027 reject text-similarity heuristics
elsewhere: a signal strong enough to reliably extract a name from free text is not a
verified fact, and applying it selectively (some records legible, most not) would
introduce an undocumented, non-uniform judgment call into a supposedly deterministic
audit.

## Gate result

Per the pre-agreed gate: **N_power = 0 < 60 → STOP.** No criteria were relaxed, no
observation was rescued by a post-hoc decision. Sector, technology-family, and
duplicate-industrial-problem checks were not run — they cannot turn an `UNKNOWN` into
an `INDEPENDENT` (ADR 0029 §2.2, symmetric: `UNKNOWN != INDEPENDENT`), so running them
here would not change this gate's outcome.

## What this actually establishes

This is a source-structure finding, not a corpus-size or temporal-window finding, and
it is broader than #101d: **the entire official EEN/POD portal — both `Technology
request` and `R&D request`, under any temporal window — cannot, on its own, produce an
organization-independent corpus under ADR 0029's current accept-only rule.** No amount
of further acquisition against this source changes this, because the limitation is
that the source never publishes the one field the rule requires.

## Not decided by this document

- Whether to pursue a source or acquisition method that can observe organization
  identity directly (e.g. a source without EEN's brokered-anonymity model, or a
  qualified process for requesting/verifying identity through the network itself,
  per ADR 0031 §2.2's `ADMISSIBLE_SOURCE_CANDIDATE` gate).
- Whether ADR 0029 §3.1's accept-only rule itself should be reconsidered for this
  specific structural case — a distinct, separate methodological decision, not one
  this closure makes.
- Any decision about #104, sector heterogeneity, or the chemistry hypothesis --
  unaffected by and unrelated to this finding.
