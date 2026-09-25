# WIPO IPC8 Technology Concordance — Freeze

```text
QUESTION:  Can Nexus enrich the OEPM/INVENES production-scale patent
           corpus (docs/adr/0035-oepm-production-scale-patent-corpus-contract.md,
           pending merge via PR #112) with a
           patent-side technology_sector field, using an established,
           citable classification rather than an ad hoc taxonomy?
INPUT:     Ulrich Schmoch (2008), "Concept of a Technology Classification
           for Country Comparisons", final report to WIPO -- Table 2
           (p.9), the same table cited in Lydia Bares's PhD thesis
           (`experiments/thesis/TESIS COMPLETA 220622.docx`, Anexo III)
           as the source for her own patent-sector classification of the
           Andalusian OPI corpus.
METHOD:    Located the primary PDF, read all 15 pages directly, and
           transcribed Table 2 verbatim -- every IPC code, wildcard, and
           include/exclude split, exactly as printed. Not a re-derivation,
           not a paraphrase, not a third-party summary.
OUTPUT:    config/policies/data/wipo_ipc8_technology_concordance_v1.json
           (+ .sha256) -- 35 technology fields, 5 aggregate sectors.
VALIDITY:  Source PDF frozen alongside the register
           (data/external/wipo_schmoch_2008_ipc_technology_concordance.pdf,
           sha256 pinned in the register's own provenance block).
STATUS:    FROZEN. Not yet applied to the corpus (SS3).
```

## 1. Why this register, and why now

Nexus already flags this exact gap in two places:

- `docs/phase2-cpv-cpc-concordance-feasibility-closure.md`: closed
  `SCOPE-FAILED/DEFERRED` on the demand-side CPV→NACE→IPC→CPC path,
  noting explicitly *"Neither Schmoch (2003) nor Dorner & Harhoff (2018)
  [table] has been acquired."*
- `docs/scientific-model.md` (line 119): repeats the same open item.

Lydia's own PhD thesis (Anexo III, "Metodología para la clasificación de
las patentes por sectores tecnológicos y complejidad") already
operationalized this concordance against the same source database
(INVENES/OEPM) Nexus's PR #112 corpus (`docs/adr/0035-oepm-production-scale-patent-corpus-contract.md`,
pending merge) is drawn from. This is not a new
register invented for Nexus — it recovers an external, reproducible
classification already used in Lydia's research, applied to the same
corpus authority.

**This is a patent-side register, not a demand-side one.** It does not
touch, reopen, or depend on the CPV→NACE bottleneck (30% ceiling,
Construction-only official concordance) that closed the demand-matching
path. It classifies patents by their own IPC codes — no CPV, no NACE, no
demand text involved.

## 2. Two distinct, separately-tracked artifacts — do not merge

| Register | Categories | Source | Status |
|---|---|---|---|
| `technology_sector` | 35 fields / 5 sectors | Schmoch (2008), WIPO IPC8-Technology Concordance, Table 2 | **FROZEN** (this document) |
| `technological_complexity` | 4 levels (alta/media-alta/media-baja/baja) | Schmoch et al. (2003), NACE 1.1↔IPC concordance, operationalized in the thesis's Anexo III | **PENDING** — table not yet acquired |

These are two different Schmoch-lineage artifacts, from two different
reports, answering two different questions (*what technology* vs. *how
complex*). The 2008 WIPO report used here explicitly does not attempt
technological complexity — its own SS1 states establishing a
technology↔sector-economic-performance concordance is "not yet realised
in this report." Lydia's Anexo III cites a separate 2003 concordance
(NACE 1.1 ↔ IPC) for complexity specifically, and separately documents
having to work around a NACE 1.1 vs NACE 2 concordance gap Eurostat never
closed cleanly. That table has not been located or acquired; the most
direct path is asking Lydia whether she retained the exact table/version
she used, rather than re-deriving or substituting a different one.

**No commit may add a `technological_complexity` field derived from any
source other than the exact table Lydia used**, once acquired. Until
then, `technological_complexity` does not exist anywhere in this
register or in any downstream config.

## 3. What this freeze does NOT do (deliberately, not yet)

- Does not apply `technology_sector` to any patent in the OEPM/INVENES
  corpus (`docs/adr/0035-oepm-production-scale-patent-corpus-contract.md`,
  pending merge via PR #112). This document and its register are pure data
  provenance; corpus enrichment is a separate, later step.
- Does not touch retrieval, scoring, matching, or the demand-side
  6-category `phase2_sector_taxonomy_v1` (`docs/phase2-sector-taxonomy-amendment.md`)
  — that taxonomy classifies TED *demands*, this one classifies *patents*
  by IPC code; they are not interchangeable and this freeze does not
  attempt to reconcile them.
- Does not acquire `technological_complexity` (SS2).
- Does not compare Nexus's corpus composition against the thesis's
  historical Andalusian distribution (Tabla 3.3.1.1) — a legitimate later
  use for the paper's discussion section, once the register is applied.

## 4. Source note: Table 1 vs Table 2

The PDF contains two tables: **Table 1** (p.5, "ISI-OST-INPI, update:
February 2005", 30 classes, the report's own starting point) and
**Table 2** (p.9, "New concept of technology classification, update: May
2008", 35 fields, IPC8-based). **Table 2 is what this register
transcribes** — it is the version the report's own text designates as
the deliverable ("the following chapter documents the new version"), the
version WIPO's IPC-statistics site cites as "WIPO IPC-Technology
Concordance Table", and the version with page-level exclusion rules
(e.g. field 14 excludes `A61K`, `A61K-008`, `A61Q`; field 6 excludes
`G06Q`) that a 30-class predecessor table does not carry.

## 5. Legacy download link is dead

The table's own footnote directs readers to
`www.wipo.int/ipstats/en/statistics/patents` for an Excel download; the
literal legacy path
(`wipo.int/export/sites/www/ipstats/en/statistics/patents/xls/ipc_technology.xls`)
returns HTTP 404 as of 2026-09-25 (verified directly, not assumed). The
PDF, read and transcribed directly, is treated as the primary source —
not a substitute for a missing file, but the report's own original
deliverable.

## 6. Next steps (not part of this freeze)

1. Ask Lydia whether she retained the exact Schmoch et al. (2003)
   NACE↔IPC complexity table used in the thesis's Anexo III.
2. Only once that table is frozen the same way (source + sha256 +
   provenance), design how `technological_complexity` gets applied to
   the corpus — as its own register, own freeze, own commit.
3. Separately: apply `technology_sector` (this register) to the ADR-0035
   OEPM/INVENES corpus — a new, explicit task, not implied by this
   freeze.
