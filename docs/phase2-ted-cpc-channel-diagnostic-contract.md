# #104 CPC Channel Diagnostic — Construction & Estimand Contract

```text
QUESTION:  With CPC found structurally inert (docs/phase2-ted-pool-coverage-diagnostic.md
           SS1), what does a real, corpus-grounded CPC taxonomy actually
           contribute -- not "does CPC beat BM25", but "what incremental
           contribution does CPC produce where its lexical-match layer can
           activate, and how much of the Dev universe is structurally out
           of its reach given the demand languages"?
INPUT:     The 63-patent frozen corpus's own (title, classifications_cpc)
           pairs -- 56/63 patents carry CPC codes, 240 distinct codes.
           config/policies/matching/default_matching_policy.json's
           non-taxonomy fields (weights, thresholds, concordance levels --
           unrelated to this diagnostic, reused as-is).
METHOD:    Build config/policies/matching/ted_at_scale_cpc_taxonomy_v1.json:
           for each of the 56 CPC-bearing patents, derive short English
           concept phrases (1-3 words) that literally gloss that patent's
           own title, mapped to that same patent's own CPC codes. No
           external dictionary, no codes or concepts not already present in
           the corpus. Re-run CandidatePoolBuilder (BM25 unchanged, CPC now
           configured) over the same 30 Dev demands / same corpus / same
           eligibility policy / same limit_per_method=20.
OUTPUT:    CPC activation report (which demands activate at least one
           concept, which don't, and why) + incremental-candidate report
           (CPC-exclusive candidates vs. BM25∩CPC vs. BM25-only), split into
           gold-scorable (already in the 108-pair gold set) and unscored
           (new, no judgment exists).
VALIDITY:  This is declared, in advance, as a CHANNEL-ACTIVATION DIAGNOSTIC,
           not a merit evaluation of CPC concordance retrieval as a method.
           What is pre-registered is the *limitation to observe*
           (activability, not "no effect") -- the actual activation/overlap
           numbers are not predicted here.
STATUS:    PRE-REGISTERED. Execution is next.
```

## 1. Why "diagnostic," not "evaluation"

`map_concept_to_cpc` does **exact-phrase** regex matching (`\bconcept\b`)
against the lowercased demand text -- not bag-of-words, not fuzzy, not
translated. Even restricting concept phrases to short 1-3 word fragments,
whether any given phrase appears verbatim in a given demand's prose is
partly incidental to phrasing, not solely to topical relevance. Combined
with the language-coverage limitation already disclosed (26/30 Dev demands
are not English or Spanish), a null or weak activation result cannot be
read as "CPC concordance retrieval doesn't help this corpus" -- it can only
ever speak to whether *this specific lexical-matching implementation*,
*under real language and phrasing constraints*, activates. That distinction
is the entire point of running this before touching dense retrieval or
ADR 0036.

## 2. Taxonomy construction method (disclosed, reproducible)

For each of the 56 CPC-bearing patents in the frozen corpus:
1. Take the patent's own title (Spanish, as harvested from INVENES).
2. Produce a literal English gloss of the technical subject -- not a
   marketing paraphrase, the same discipline used throughout this session
   when presenting annotation packs (e.g. "sistema de construcción modular"
   → "modular construction system").
3. Break the gloss into 1-3 word concept fragments where natural (e.g. a
   title yielding both "wearable device" and "vital sign monitoring").
4. Map each fragment to *that patent's own* CPC codes, verbatim from the
   corpus -- never a code the patent doesn't actually carry.

This produces `concept_to_cpc_taxonomy` entries covering exactly the
240-code universe already observed in the corpus, with full provenance
(every entry traces to one specific patent's title and CPC codes) and zero
externally-sourced classification data. The 7 CPC-empty patents contribute
nothing (there is nothing to map them to).

Non-taxonomy policy fields (`weights`, `cpc_concordance_levels`,
`confidence_thresholds`, `sufficiency_rules`, `operational_limits`) are
reused verbatim from the existing production default
(`config/policies/matching/default_matching_policy.json`) — they are not
under test here and changing them would confound the diagnostic.

## 3. What gets reported

**CPC activation:**
- Demands with ≥1 concept phrase matched (activated).
- Demands with zero matches, split by cause where determinable (language
  vs. phrasing).
- Which concept phrases / CPC codes actually fired.

**Incremental retrieval** (BM25 held fixed, exactly the same 108 pairs it
already produced):
- Candidates CPC adds that BM25 already had (shared — no new judgment
  needed, already gold-scored).
- Candidates CPC adds that BM25 did **not** have (CPC-exclusive, new) —
  reported by count and identity only; **no gold judgment is invented for
  these**. If their number is non-trivial, extending the gold set with a
  small incremental blind-annotation round is a separate, later decision,
  not performed here.
- Resulting change (if any) in demand-level coverage and pool relevance
  yield, computed **only over gold-scorable pairs** (the original 108 +
  any CPC-exclusive candidates that happen to already be gold-scored by
  coincidence — none are expected, since the gold set was built exactly
  from BM25's own 108 pairs).

## 4. Non-goals

- Does not change BM25, the corpus, the 30 Dev demands, the gold set, or
  the 0-3 scale.
- Does not touch dense/semantic retrieval or ADR 0036.
- Does not invent judgments for CPC-exclusive new candidates.
- Does not build a multilingual taxonomy variant — that is an explicitly
  separate, later experimental design if this diagnostic motivates it.
