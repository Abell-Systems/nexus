# CEIMAR / Minesoft Origin — global 2000–2025 pull, family-level Spain jurisdiction filter

## Status: jurisdiction-filtering pass complete — NOT relevance-classified yet

This supersedes the earlier `../minesoft_spain_2000_2025_screening/` approach for
determining "which families are Spain-relevant." That pass is **not deleted** —
kept as-is for the record — but its method (filter publications by `cc=ES`) is
now known to badly undercount, and this directory holds the corrected
family-level universe that a future classification pass should use instead.

## Why the earlier `cc=ES` approach was wrong

`cc=ES` filters on the **country code of the one document that matched the
search**, not the country footprint of its **patent family**. A family can have
full Spanish protection (e.g. an EP patent validated in Spain, or a WO
application that entered Spanish national phase) while the specific document
whose title/abstract/claims mention the compound is a US, CN, or JP-published
family member. That earlier pass returned only 26 publications / 23 families
across all 12 compounds — implausibly small next to the ~217/227-family Spain
footprint in the old Espacenet-based master dataset (`../patentes_CEIMAR_master.xlsx`,
1988–2019 priority years). Lydia flagged this directly ("not useful in the
current shape... at least 227") and that correction is what produced this pass.

## Method (this pass)

For each of the 12 compounds:

```
tac=(<compound name>) AND pd>2000 AND pd<2026
```

— the same query as the original global v0.1 pull, but:

- **`group=extendedfamily`**: Minesoft dedupes `numFound` and results to one
  representative publication per extended patent family server-side. This
  cut the per-compound row count by roughly 5x (e.g. Brentuximab vedotin:
  2,613 publications -> 539 families) and made a family-level analysis
  tractable without needing a separate `bulk_publications` enrichment pass.
- **`fl=biblio`**: each result includes `familydata.simple-family-data.publications`,
  the full list of every publication in that family with its `ucid` (whose
  first two letters are the country code). This is the actual family-level
  jurisdiction footprint — the same concept as the `jurisdictions` column in
  the old master dataset, just derived directly from Minesoft rather than
  from Espacenet.
- **`has_ES`**: `True` if `ES` appears among the family's member country codes,
  i.e. the family has (or had) some form of Spanish patent protection,
  regardless of which family member happened to be the text-search hit.
- **Sort**: 11 of the 12 compounds were pulled with Minesoft's default `score`
  sort (fine at their scale — every page was individually verified to yield
  new, non-duplicate families with no gaps). Cytarabine required a stable
  `sort=pd_asc` (publication date ascending) instead — see below for why.
- Pagination: `rows` capped per call by response size (a single family's full
  bibliographic record, including citations/legal-status/chemical-entity
  extraction, can be 200-400 KB — far larger than initially expected — so
  `rows` was reduced from 50 down to as low as 5-15 per call when a full-size
  batch triggered a session error), `start` incremented until each compound's
  `numFound` was reached.

## The `family_id=-1` bug (found and fixed 2026-09-17/18)

Minesoft returns `docdbfamilyid=-1` for publications it can't assign to an
extended family (older documents, some utility models, etc.) — these are
**real, distinct publications**, not one shared "family -1". An early version
of the extraction script deduped naively by `family_id`, which silently
collapsed every `-1` row into a single bucket and dropped all but the first
one found. Confirmed via direct file inspection: this affected all 12
compound files (174 `-1` rows existed pre-fix across the dataset, most of
them in Cytarabine). Fixed by deduping `-1` rows by `leader_id` instead — each
counted as its own distinct entity. All 12 CSVs below reflect the corrected
logic; none contain duplicate `family_id`s or duplicate `-1`/`leader_id`
combinations (independently verified).

## Cytarabine — exhaustive (completed 2026-09-18)

Cytarabine has ~4,030 families globally (vs. tens to low hundreds for every
other compound) for the same generic-chemotherapy-name reason documented in
`../minesoft_origin_2000_2025/README.md`'s original 1,000/19,075
publication-level cap. Per Lydia's explicit decision on 2026-09-17 ("keep
grinding to full 4,031, however long it takes"), this was pulled to full
exhaustive coverage rather than capped — the only compound where exhaustive
coverage took real, documented effort:

1. First attempt used `sort=score` (Minesoft's default) and hit an
   unexplained zero-yield plateau across ~120 consecutive `start` offsets,
   which was explicitly re-scanned (not just skipped) and confirmed empty.
   This is consistent with `score` sort being unstable across tied scores —
   not a safe key to paginate against for a guaranteed-complete pull.
2. Switched to `sort=pd_asc` (publication date ascending, stable/deterministic)
   and re-walked the entire range from `start=0` through `numFound`.
3. Partway through this re-walk, the `family_id=-1` dedup bug above was found
   and fixed, which required a second full `pd_asc` pass (skipping already-known
   real families, recovering previously-dropped `-1` publications).
4. Final verification: `start` beyond `numFound` returns empty; `numFound`
   itself drifted by exactly 1 (4,031 -> 4,030) between the start and end of
   this multi-day pull — normal Minesoft index churn, confirmed via a fresh
   recount rather than assumed stable.

**Final: 4,035 rows (3,765 real unique families + 270 distinct `-1`
publications), has_ES = 690.** This is exhaustive, not a sample — safe to use
and cite directly, unlike the earlier interim 44/200 and 213/1,165 figures
seen during this pull (both superseded).

## Per-compound results (final)

| # | Compound | numFound | Rows in CSV | has_ES=True |
|---|---|---:|---:|---:|
| 01 | Brentuximab vedotin | 539 | 539 | 67 |
| 02 | Cytarabine | 4,030 (drift from 4,031) | 4,035 | 690 |
| 03 | Trabectedin | 422 | 422 | 53 |
| 04 | Vidarabine | 545 | 545 | 81 |
| 05 | Ziconotide | 142 | 142 | 18 |
| 06 | Plitidepsin | 50 | 50 | 4 |
| 07 | Omega-3 acid ethyl esters | 26 | 26 | 4 |
| 08 | Polatuzumab vedotin | 150 | 150 | 9 |
| 09 | Omega-3 carboxylic acid | 4 | 4 | 1 |
| 10 | Enfortumab vedotin | 152 | 152 | 6 |
| 11 | Eribulin mesylate | 158 | 158 | 18 |
| 12 | Lurbinectedin | 79 | 79 | 1 |
| **Total** | | **6,297** | **6,302** | **952** (per-compound, not deduped across compounds) |

Every CSV independently verified: no duplicate `family_id`s among real
families, no duplicate `leader_id`s among `-1` rows, no malformed rows.

**Total unique ES-relevant entities across all 12 compounds, deduped by the
corrected key (a real `family_id`, or `leader_id` for a `-1` publication) so a
family/publication matching more than one compound's search is counted once:
872.**

## Comparison to the two existing reference points

- **Old Espacenet-based master (`../patentes_CEIMAR_master.xlsx`, 227 families,
  1988–2019 priority years)**: ~217/227 families had `ES` in their
  `jurisdictions` column. This pass's 872 unique ES-relevant entities, from a
  *different* time window (2000–2025 publication dates) and a *different*
  source methodology (Minesoft text search + family dedup, vs. Espacenet
  number lookup), is now well above that baseline rather than an order of
  magnitude below it — unlike the superseded `cc=ES` pass's 23 families. Note
  872 includes Cytarabine's disproportionate 690, which the smaller,
  earlier-completed compounds' totals (182 combined) resemble more closely in
  scale to the old baseline; see "What this is NOT yet" below on why the raw
  872 should not be read as "872 marine-drug patents in Spain" without
  relevance classification.
- **Superseded `cc=ES` pass (`../minesoft_spain_2000_2025_screening/`, 23
  families)**: kept untouched. This pass's 872 is the corrected replacement
  for that number specifically — the earlier screening table built on top of
  it (Directly/Indirectly Relevant/Incidental classifications) should be
  considered provisional and re-derived from this larger, more accurate
  universe, not extended as-is.

## What this is NOT yet

- **Not relevance-classified.** This pass answers "does this family have
  Spanish jurisdiction," not "is this family substantively about the target
  compound or just an incidental mention" — the Patent Screening Protocol's
  five-way classification (Directly/Indirectly Relevant, Incidental Mention,
  Not Relevant, Uncertain) from `../minesoft_spain_2000_2025_screening/README.md`
  has not been run against this larger set. **This matters a lot for
  Cytarabine specifically**: on the smaller 23-family `cc=ES` sample, ~78% of
  families turned out to be Incidental Mentions (the compound named only in a
  generic drug list), and Cytarabine is a 60-year-old generic chemotherapy
  name that shows up in exactly that pattern constantly — so a large share of
  its 690 has_ES families are likely to classify as Incidental once evidence
  is checked, not genuinely about Cytarabine as a marine-derived-drug patent
  subject. Do not chart or report the raw 872 (or the 690 Cytarabine figure)
  as "Spain-relevant marine-drug patents" without running this step first.
- **Not deduplicated within has_ES counts shown per-compound in the table
  above** — those are per-compound; the 872 total above is the correctly
  cross-compound-deduped figure.
- **Not merged with any other dataset.** Kept as its own parallel artifact,
  consistent with the project's standing practice of not contaminating the
  Espacenet-based master, the frozen global v0.1 ID snapshot, or the
  superseded `cc=ES` screening pass.

## File format

Each `NN_<Compound>_families.csv` has columns:

- `family_id` — `docdbfamilyid` of the family's representative publication, or
  `-1` if Minesoft could not assign one (see "The `family_id=-1` bug" above —
  each `-1` row is still a distinct real publication, keyed by `leader_id`)
- `leader_id` — the specific publication ID Minesoft returned as that family's
  representative (relevance- or date-ranked depending on the sort used; not
  necessarily the EP/WO/US "leader" convention used in `../query_log.md`'s
  Fase 3 methodology)
- `compound` — which of the 12 searches produced this row
- `title` — the representative publication's title, HTML/entity-tag stripped
- `family_countries` — semicolon-joined sorted 2-letter country codes across
  every publication in the family (from `familydata.simple-family-data.publications[].ucid`)
- `has_ES` — `True`/`False`, whether `ES` appears in `family_countries`

## Next step (not done here)

Run the Patent Screening Protocol's relevance classification against the 872
unique ES-relevant entities found here (pulling full claims + description per
family, the same evidence standard used in
`../minesoft_spain_2000_2025_screening/`), producing a corrected,
right-sized version of that directory's `screening_table.csv`. Given the
scale (872 vs. the earlier 23) and the expected high Incidental-Mention rate
for Cytarabine in particular, this is a substantial follow-up effort, not a
quick one.
