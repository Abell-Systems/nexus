# CPV→CPC Concordance — Feasibility Contract

```text
QUESTION:  Does a reproducible, sufficiently informative CPV→CPC
           concordance exist that could activate the CPC retrieval channel
           from the TED demands' own structured classification, instead of
           the free-text exact-phrase matching that #104 showed doesn't
           activate?
INPUT:     The 30 frozen Dev demands' real CPV codes (from TED source data,
           not reinterpreted) + the 63-patent frozen corpus's real CPC
           codes. A concordance source, whose origin is decided BEFORE
           looking at results (SS2).
METHOD:    Extract CPV -> build/acquire concordance -> derive CPC
           candidates deterministically -> apply to the same corpus -> log
           unmatched CPV codes explicitly.
OUTPUT:    CPV activation per demand, derived CPC candidates, patents
           retrieved via this channel, activation rate, demand coverage,
           pool sizes -- kept strictly separate from #104's BM25 result.
VALIDITY:  Extraction tests, concordance-determinism tests, known
           positive/negative cases, concordance audit. No evaluation
           against the gold set unless this contract explicitly says so.
STATUS:    FEASIBILITY, not EFFECTIVENESS -- this asks "can the channel
           activate at all," not "does it improve matching."
```

## 1. Fact-finding before any design decision (verified, not assumed)

No official or normative CPV→CPC (patent) concordance exists. CPV (EU
public procurement classification, maintained by the European Commission)
and CPC (Cooperative Patent Classification, maintained jointly by EPO and
USPTO) are unrelated classification systems with no direct published
mapping between them. What *does* exist, as real published/institutional
sources:

- **CPV→NACE**: the European Commission maintains this correspondence
  natively -- CPV was designed with partial NACE alignment for statistical
  purposes.
- **IPC↔NACE / IPC↔ISIC**: a WIPO-OECD joint project produced an
  IPC-ISIC concordance; independently, **Schmoch et al. (2003)** and
  **Dorner & Harhoff (2018)** published IPC-to-NACE(-industry) concordance
  tables used in patent-economics research.
- **IPC↔CPC**: an official, EPO/USPTO-maintained concordance (CPC is
  structurally an extension of IPC), already the standard bridge between
  the two patent classification systems.

**Consequence:** the only grounded, non-invented path from a demand's CPV
code to a CPC code is **chained**: `CPV -> NACE -> IPC -> CPC`, combining
three externally-sourced, published concordance tables -- none of which
are currently in this repository. This is real external-data acquisition,
not a code change, and needs its own provenance discipline (source,
version, date obtained, license), the same way ADR 0035's OEPM corpus did.

## 2. The three origin options (per the user's own framing), assessed

1. **Pre-existing normative/external source.** Does not exist directly
   (§1). The chained route is the closest available version of this
   option, but it is a composition of three external sources, not one
   authoritative CPV→CPC table -- each hop introduces its own concordance
   error/granularity loss (NACE is industry-coarse; IPC-NACE concordances
   are themselves probabilistic/many-to-many in the literature, not
   1:1 crosswalks).
2. **A concordance derived from a formal relationship between
   classifications.** The IPC↔CPC leg qualifies (structural extension,
   official). The CPV→NACE and NACE→IPC legs do not have a *formal*
   (structural) relationship -- they are empirically/statistically derived
   crosswalks, published as research artifacts, not definitional identities.
3. **A new table built by us.** Explicitly what the user does not want as
   the primary source (risk of corpus-overfit bias) -- not selected.

Given §1's finding, options 1 and 2 collapse into the same real answer:
**the chained external concordance, acquired and disclosed with full
provenance, is the only defensible source** -- but it is a composite of
three research/institutional artifacts, not a single authoritative table,
and that composite nature must be disclosed wherever this experiment's
results are reported (paper included).

## 3. What acquiring this requires (not yet done)

- The 30 Dev demands' **real CPV codes** — not yet extracted from source
  (the dry-run script's `extract_cpv_code` regex on raw TED HTML is the
  only precedent; needs re-verification against the current 30-demand Dev
  set specifically, since it was only exercised on the 8-demand dry-run
  subset).
- A **CPV→NACE table** with a disclosed source (European Commission
  publication) and version/date.
- An **NACE→IPC (or ISIC→IPC) table** with a disclosed source — Schmoch et
  al. (2003) or Dorner & Harhoff (2018) are the two published,
  citable candidates found; picking between them (or using both and
  disclosing divergence) is an explicit decision, not made here.
- The existing official **IPC↔CPC** concordance (EPO/USPTO) — mechanical,
  no decision needed.
- None of these four artifacts exist in this repository yet. Acquiring
  them is external-data work with its own provenance obligations,
  deliberately out of scope for this contract to just "go fetch" without
  the user's explicit sign-off on which NACE↔IPC source to use.

## 4. Non-goals

- Does not build a corpus-derived or hand-tuned CPV→CPC table (rejected in
  §2, option 3).
- Does not touch BM25, the frozen corpus, the frozen gold set, or #104's
  results.
- Does not evaluate against the gold set — this contract is FEASIBILITY
  only; an EFFECTIVENESS follow-up, if this channel activates at all,
  would be its own separate pre-registration.
- Does not touch dense retrieval or ADR 0036.
