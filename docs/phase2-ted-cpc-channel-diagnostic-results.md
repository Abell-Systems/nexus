# #104 CPC Channel Diagnostic — Results

```text
QUESTION:  Under docs/phase2-ted-cpc-channel-diagnostic-contract.md, what
           actually happens when a real, corpus-grounded CPC taxonomy (85
           concepts, 163/240 corpus CPC codes, zero external/invented
           codes) is run against the same 30 Dev demands?
INPUT:     config/policies/matching/ted_at_scale_cpc_taxonomy_v1.json +
           the same frozen corpus, demand corpus, Dev split, and gold set
           used throughout #104.
METHOD:    experiments/phase2/run_cpc_channel_diagnostic.py -- BM25 held
           exactly as before, CPC now configured with the real policy.
VALIDITY:  Taxonomy correctness verified by positive control before
           interpreting the 0-activation result (SS2) -- ruling out
           implementation failure before reading it as a real finding.
OUTPUT:    data/annotations/ted_at_scale_cpc_channel_diagnostic.json.
STATUS:    CLOSED.
```

## 1. Taxonomy construction

85 concept-phrase entries, derived from the 56 CPC-bearing patents' own
titles, covering 163/240 distinct CPC codes already present in the frozen
corpus. Zero codes outside the corpus, zero externally sourced
classification data (verified programmatically:
`taxonomy_codes - corpus_codes == set()`). Non-taxonomy policy fields
(weights, thresholds, concordance levels) copied verbatim from the existing
production default.

## 2. Positive control (implementation check)

Before interpreting any null result, verified `map_concept_to_cpc` actually
fires on this taxonomy: synthetic text `"we are looking for a wearable
device and air purification solution"` correctly returns 12 CPC codes
spanning two concept phrases. **The matcher and taxonomy are functionally
correct** — the diagnostic result below is not an implementation bug.

## 3. Result: 0/30 demands activate

**Zero of the 30 Dev demands** match even one of the 85 concept phrases —
including the 2 English and 2 Spanish demands, where the language barrier
already disclosed (`docs/phase2-ted-pool-coverage-diagnostic.md` §1) does
not apply. **Zero CPC-exclusive candidates** were added to any pool, scored
or unscored — CPC contributed nothing beyond what BM25 already had, for
every single demand.

This is not attributable to the language-coverage limitation alone (that
would predict activation on 4/30, not 0/30). The deeper cause, per the
contract's own §1 warning: `map_concept_to_cpc` does **exact-phrase**
matching (`\bconcept\b`), not bag-of-words or fuzzy matching. A 30-demand
Dev set of TED procurement postings — written in bureaucratic/administrative
prose describing a desired outcome ("Innovation Challenge for intelligent
digital tenant communication") — essentially never contains the literal
2-3 word technical noun phrases that a patent title would use ("wearable
device", "video identification", "modular construction"), even when the
underlying topic overlaps. Demand text describes *problems and desired
outcomes*; the taxonomy's concept phrases describe *patent-title-level
technical solutions*. The vocabulary gap is real and structural, not a
language-translation problem this taxonomy could have fixed.

## 4. What this does and doesn't say

**Does not say:** "CPC concordance retrieval is a weak method" — a
properly-scoped CPC signal (e.g. derived from a controlled-vocabulary
classifier, or from CPV-to-CPC concordance on the demand's own procurement
classification code, rather than free-text lexical matching) was never
tested here.

**Does say:** the specific implementation exercised by both #104 rounds —
`extract_demand_cpc_auto` + `map_concept_to_cpc`'s exact-phrase matching
against free-text demand descriptions — is not a viable CPC-activation
mechanism for this demand corpus, regardless of taxonomy quality or
language coverage. The bottleneck is the phrase-matching mechanism itself,
not (only) the taxonomy content or the demand languages.

## 5. Consequence for the BM25-only pool-coverage results

`docs/phase2-ted-pool-coverage-results.md`'s numbers (9/30 demand coverage,
14/108 pool relevance yield) stand unchanged and require no further
correction: a real, functioning, corpus-grounded CPC taxonomy genuinely
contributes zero incremental candidates under this implementation, so
"BM25-only" was and remains an accurate description of what was measured,
not merely a placeholder pending a working CPC channel.

## 6. Non-goals

- Does not conclude CPC concordance retrieval should be abandoned as a
  matching signal — only that this specific text-matching implementation,
  under these real demands, doesn't activate.
- Does not attempt a CPV-to-CPC concordance approach (the demand's own
  procurement classification code, rather than free-text concept matching)
  -- that would be a materially different mechanism and a new, separate
  pre-registration if pursued.
- Does not touch dense/semantic retrieval or ADR 0036.
- Does not modify the frozen corpus, demand corpus, gold set, or the
  existing BM25-only results.
