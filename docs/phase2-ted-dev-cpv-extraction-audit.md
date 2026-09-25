# CPV Extraction & Audit — 30 Dev Demands

```text
QUESTION:  Step 1 of docs/phase2-cpv-cpc-concordance-feasibility-contract.md:
           what CPV codes do the 30 frozen Dev demands actually carry, at
           what granularity, and is the resulting structure even a
           reasonable candidate for a later CPV->NACE->IPC->CPC chain?
INPUT:     data/raw/phase2_candidates_ted/ted/<demand_id>.html (raw TED
           postings, already harvested) for the 30 Dev demand_ids.
METHOD:    experiments/phase2/extract_dev_cpv_codes.py: the same
           code|name|cpv.(\d{8}) regex already exercised by the #104
           dry-run's extract_cpv_code(), re-verified directly against the
           raw markup before trusting it at 30-demand scale, deduplicated
           per demand. NO concordance mapping performed.
OUTPUT:    data/experiments/phase2_v4/ted_dev_cpv_codes_v1.json (+.sha256)
           -- frozen extraction artifact + audit statistics.
VALIDITY:  Regex verified against real markup context (not assumed from
           the dry-run's own untested-at-scale precedent) before running
           at the full 30-demand set.
STATUS:    CLOSED -- extraction + audit only, no mapping decision made.
```

## 1. Coverage

**30/30 Dev demands carry at least one CPV code** — full coverage, no
missing HTML, no zero-CPV demand.

## 2. Count per demand — highly skewed

| CPV count | # demands |
|---:|---:|
| 1 | 14 |
| 2 | 7 |
| 3 | 2 |
| 4 | 1 |
| 5 | 2 |
| 7 | 1 |
| 13 | 1 |
| 16 | 1 |
| 32 | 1 |

Nearly half the demands (14/30) carry exactly one CPV code; three demands
(`42938-2024`: 32, `200095-2024`: 16, `158024-2024`: 13) carry a large,
heterogeneous set spanning construction, software, telecoms, and financial
services categories in the same notice — consistent with large multi-lot
framework tenders rather than narrow technical requests.

## 3. Granularity — mixed, with a coarse tail

CPV codes are hierarchical by trailing-zero count. Across the 89 distinct
codes observed:

| Level | # distinct codes |
|---|---:|
| division (coarsest, e.g. `72000000` = "IT services") | 11 |
| group | 21 |
| class | 24 |
| category | 11 |
| subcategory or finer (most specific) | 22 |

**`72000000` ("IT services: consulting, software development, Internet and
support") alone appears in 9/30 demands** — the single most common code,
and also the coarsest kind. A code this generic would, under any
CPV→NACE→IPC concordance, map to an extremely broad swath of NACE/IPC
space, plausibly touching a large fraction of the corpus's own CPC codes
indiscriminately.

## 4. Implication for the concordance decision (not decided here)

This audit doesn't settle Schmoch (2003) vs. Dorner & Harhoff (2018), but
it does surface a concrete risk the user anticipated: **a meaningful
fraction of the CPV signal (11/89 distinct codes, and the single most
frequent one) is division-level and structurally too coarse to be
discriminative**, regardless of which NACE→IPC table is used downstream.
The 22/89 subcategory-or-finer codes are where any chained concordance has
a real chance of being informative; the coarse tail is a plausible
candidate for `FEASIBLE_WITH_LOW_DISCRIMINATION` rather than `FEASIBLE`,
once the actual mapping is run — but that is a conclusion for the next
step, not this one.

## 5. Limitation disclosed

The raw markup did not carry a recoverable "Main CPV" vs. "Additional CPV"
field distinction under the extraction pattern used — all codes per demand
are reported as one undifferentiated set. If the eventual concordance
experiment needs to weight a demand's primary CPV more heavily than
secondary ones, that distinction would need a different extraction
approach, not assumed here.

## 6. Non-goals

- Does not map any CPV code to NACE, IPC, or CPC.
- Does not decide between Schmoch (2003) and Dorner & Harhoff (2018).
- Does not acquire any external concordance table.
- Does not touch BM25, the corpus, the gold set, or #104's results.
