# Post-#109 manuscript audit — full read-through

Audit only, per explicit scope. No manuscript edits made here. Read the
entire current manuscript (182 paragraphs, 3 tables) end to end and checked
every factual claim against what's actually reproducible from the project's
archived datasets, following the checklist: Abstract, Methods, Results,
Discussion, Conclusion, terminology consistency, and prose↔figure/table
cross-checks.

## BLOCKER: the PSR (Patent Search Report X/Y/P/E) claim was only partially removed

#109 removed the PSR claim from the Results paragraph (now [94]) and the
Discussion paragraph (now [113]), each with a note that no dataset supports
it. **But the same claim appears in six locations total, and #109 only
fixed two of them:**

| # | Location | Paragraph | Status |
|---|---|---|---|
| 1 | Abstract | [4]: "...evaluates the quality of inventions through Patent Search Reports." | **Not fixed** — stated as an accomplished part of the methodology/results |
| 2 | Abstract | [4]: "Most patents rely on established prior art, signaling incremental innovation." | **Not fixed** — plain-language restatement of the same removed X/Y-category finding |
| 3 | Introduction | [15]: "By analysing Patent Search Reports and mapping legal classifications, the study provides a detailed understanding of the innovation quality and timing..." | **Not fixed** — a third, previously-unaudited location claiming PSR analysis as a contribution |
| 4 | Results | (was) [93] | **Fixed in #109** |
| 5 | Discussion | (was) [112] | **Fixed in #109** |
| 6 | Conclusion | [123]: "The data further show that most patented inventions are built on well-established prior art (as revealed by the high presence of X and Y category documents in Patent Search Reports)... Additionally, the temporal dynamics of P-category documents stress the importance of timing in the patenting process." | **Not fixed** — explicitly restates the X/Y/P-category finding as a "data show" result |

Also worth noting: the Methodology section (paragraphs [36]–[54]) never
describes *how* PSR data was collected in the first place — there is no
PSR-specific data-collection step documented anywhere, consistent with
`LEGACY_AUDIT.md`'s finding that no PSR source file exists in the archive.
This wasn't a case of losing a once-documented method; the method was never
described, only its outputs were asserted.

**Why this is a blocker, not a warning:** #109 established the principle
that a claim with zero archived support should be removed rather than
restated unverified — and executed that correctly in 2 of 6 places. The
remaining 4 leave the paper internally contradictory: it states in Results
and Discussion that this claim was removed for lack of data, while the
Abstract, Introduction, and Conclusion continue to assert it as fact. This
is precisely the "epistemological audit" failure mode requested for this
read-through — an orphaned claim after a data retirement.

## WARNING: Abstract doesn't reflect the caveats now present in the body

Two Abstract sentences describe findings as accomplished without the
caveats their supporting sections now carry:

- **[4]: "identifies leading organizations"** — the body ([90]) now
  documents that Figure 5 and Table 5 report different, only partially
  reconcilable counts for this exact analysis. The Abstract states it
  without qualification.
- **[4]: "...and a preference for a narrow set of marine organisms"** — the
  body ([75]) now states the per-compound counts underlying Figure 3 "have
  no independently reproducible source in the project archive and should
  be read as illustrative rather than independently audited." The Abstract
  states the organism-preference finding without that caveat.

Not a blocker (the underlying organism-*category* structure does trace to
Table 1, and the applicant-dominance finding has partial archived support),
but an Abstract should not read more confidently than the body it
summarizes.

## PASS — reverified directly against the archived data, not just carried forward

- **Figure 1/2 percentages and counts**: recomputed directly from
  `patentes_CEIMAR_master.xlsx` (year-filtered 2000–2026, matching
  `make_charts.py`). Exact match: Spain 217 (5.82%), USA 208 (5.58%), Japan
  189 (5.07%), Canada 184 (4.94%), China 175 (4.70%); Europe: Denmark 137,
  Poland 115, Portugal 100, Slovenia 81. All reproduce to the reported
  figure.
- **Discussion/Conclusion "internationalization... extensions into the
  United States, China, and Australia" claim** ([111], [121]): verified —
  US (208), China (175), and Australia (170) are indeed among the top
  jurisdictions by mention count in the same reproducible dataset. This
  claim was flagged as "unaudited" earlier in this session's work; it is
  now confirmed accurate, not just plausible.
- **Table 2 and its intro paragraph, Figure 3/4 prose, organism-group
  counts** ([70]–[82]): consistent with `screening_table_consolidated.csv`,
  previously verified during #103/#109.
- **Madrid-thesis revision** (#109): all four locations (Abstract, Results,
  Discussion, Conclusion) now consistently state institutional
  concentration as the finding and regional concentration as an open
  question — no remaining "established fact" framing found anywhere in this
  full read-through.
- **Table 3 retirement**: no dangling reference to the removed table found
  anywhere in the document body.
- **Methodology's Minesoft/Espacenet provenance description** ([53]–[54]):
  consistent with `LEGACY_AUDIT.md`'s findings.

## Minor, out of this audit's primary scope (noted, not a data-reproducibility issue)

- **Duplicate reference**: Ferasso et al. (2021) appears twice in the
  References list (consecutive entries, identical).
- **Citation year mismatch**: in-text citations "Keen; Schwarz; Wini-Simeon,
  2017" / "Keen, Schwarz and Wini-Simion, 2017" (typo: Simion) / "Ken,
  Schwarz, Wini-Simeon, 2017" (typo: Ken) / "Keen et al., 2017" all cite
  2017, but the References list has this work dated 2018 (Keen, Schwarz, &
  Wini-Simeon, 2018). Pre-existing, unrelated to the Minesoft/Espacenet
  data work — flagged for completeness since a full read-through surfaced
  it, not pursued further here.

## Recommendation

The PSR blocker (4 of 6 unaddressed occurrences) should be fixed before this
manuscript is considered settled — it's the same class of problem #109 was
explicitly created to fix, just not caught in all locations at the time.
The two Abstract warnings are lower priority but should be addressed in the
same pass for consistency. Per the agreed process: this is an audit
document; a follow-up editorial PR should apply these fixes, using the same
assertion-based reproducible-script pattern as #103/#109, before any new
data analysis resumes.
