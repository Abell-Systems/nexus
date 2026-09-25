# #104 Gold Set Freeze

```text
QUESTION:  With 12/108 disagreements adjudicated
           (docs/phase2-ted-annotation-at-scale-iaa-closure.md), what is the
           final frozen gold set of relevance judgments for evaluating the
           BM25+CPC candidate pool?
INPUT:     data/annotations/ted_at_scale_annotation_{valentin,lydia}.csv
           (108/108 each) + data/annotations/ted_at_scale_adjudication.json
           (12 joint decisions, same 0-3 contract, not recalibrated).
METHOD:    experiments/phase2/build_gold_set.py: 96 exact-agreement pairs
           take the agreed score; 12 disagreement pairs take the adjudicated
           score verbatim from the adjudication file (the script makes no
           judgment calls of its own -- it only assembles and validates).
OUTPUT:    data/annotations/ted_at_scale_gold_set_v1.json (+ .sha256) --
           108 sealed relevance judgments (demand_id, publication_id,
           gold_judgment 0-3, provenance, both original annotator scores).
VALIDITY:  Adjudication used the same annotation contract that produced the
           independent judgments (docs/annotation/ted_at_scale_annotation_instructions.md);
           no criterion was changed to accommodate any individual case.
STATUS:    GOLD SET FROZEN.
```

**CORRECTION (`docs/phase2-ted-pool-coverage-diagnostic.md` §1):** every
"BM25+CPC" reference below (including the QUESTION block above and §3)
should be read as **BM25-only** -- `DuckDbCPCRetriever` never received a
populated taxonomy policy and contributed zero candidates across all 30
Dev demands. The gold set itself is unaffected; the retrieval-strategy
label it was framed under is corrected here.

## 1. Composition

- **108 pairs total**: 96 exact agreement (Valentín == Lydia) + 12 adjudicated.
- **Gold judgment distribution**: 0→94, 1→3, 2→5, 3→6.
- 11/12 adjudicated values fall within the range spanned by the two original
  scores. **One case diverges above both** (`315512-2025` / `ES2065820A2`,
  scored 1 and 0 by the two annotators, adjudicated to 2) — confirmed
  explicitly by Valentín after review, not applied silently.

## 2. Contract ambiguity disclosed during adjudication

The word "modular" recurred as a **partial false cognate**: in several
patents it describes building-block/architectural modularity, while one
demand (`814207-2025`, modular deployable machinery for railway
track-sludge removal) uses "modular" for equipment/machine modularity — a
different sense of the same word. This produced systematically lower
adjudicated scores for building-construction patents against that demand
than a naive lexical match would suggest. Recorded here and in the
adjudication file's `contract_ambiguity_noted` field for future annotation
rounds; **not** acted on by changing the guide or re-scoring the 96
non-disputed pairs, per the no-recalibration rule.

## 3. Non-goals (this step)

- Does not evaluate the BM25+CPC pool's recall/coverage against this gold
  set yet — that is the next actual step, not performed here.
- Does not touch the corpus, the demand corpus, or the candidate-pool
  generation code.
- Does not introduce dense/semantic retrieval or ADR 0036 — deferred, per
  explicit instruction, until this gold set's evaluation is done.
