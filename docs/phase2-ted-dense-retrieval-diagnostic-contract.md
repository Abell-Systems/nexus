# #104 Dense Retrieval Diagnostic — Contract

```text
QUESTION:  Following the closed sequence (BM25 pool-coverage -> CPC
           channel diagnostic -> CPV->NACE scope-gate), does dense/semantic
           retrieval -- the one retrieval dimension not yet exercised --
           surface eligible candidates for the same 30 frozen Dev demands
           against the same 63-patent frozen corpus, and how does its
           activation/coverage compare to BM25's?
INPUT:     The 30 frozen Dev demands, the 63-patent frozen corpus, the
           existing 108-pair gold set -- none modified. ADR 0014's already-
           pinned embedding model/revision/config (science freeze, ADR
           0014 SS13) and its already-isolated dependency stack
           (requirements/evaluation-generation.txt).
METHOD:    Generate a frozen embedding artifact offline (ADR 0014 SS3, SS6-7)
           for the 30 demands + 63 patents; run DuckDbDenseSemanticRetriever
           (existing code, unmodified) with limit_per_method=20 (matching
           BM25/CPC's own setting, SS3 below) over the same demand set;
           compare against BM25's frozen 108-pair pool the same way the
           CPC diagnostic did (shared / dense-exclusive-already-scored /
           dense-exclusive-new-unscored).
OUTPUT:    Dense activation report (does every demand get a non-trivial
           pool, since with the retriever's own default there is no hard
           threshold -- see SS3) + incremental-candidate report, split into
           gold-scorable vs. new/unscored, same discipline as the CPC
           diagnostic.
VALIDITY:  ADR 0014's own explicit split already applies here: model choice
           is exogenous/a-priori (language coverage, license, offline-
           runnability), NOT validated against this specific 30-demand
           Dev set or 63-patent corpus -- whether it performs well is what
           this diagnostic (and any later evaluation) exists to find out,
           not something assumed by picking the model.
STATUS:    ENVIRONMENT VERIFIED, EMBEDDINGS NOT YET GENERATED. See SS7.
```

## 1. Representation, and why it's a priori appropriate for Dev's languages

Sentence embeddings via `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
(XLM-RoBERTa base, 768-dim, mean pooling) — already selected and frozen by
ADR 0014, not re-decided here. XLM-RoBERTa's pretraining covers 100
languages including every language observed in the frozen 30-demand Dev
set: **de (11), fr (7), nl (3), en (2), es (2), da, fi, pl, sv, cs (1
each)** — verified against the real distribution in
`docs/phase2-ted-dev-cpv-extraction-audit.md`, not assumed. This is the
exact structural weakness the CPC channel diagnostic exposed (26/30
demands not EN/ES, defeating exact-phrase lexical matching): dense
retrieval's semantic-representation approach doesn't require phrase-level
lexical overlap, which is precisely why it's the next dimension worth
testing, not a guess.

**What this is not:** a claim that this model performs well on
Spanish-patent / multilingual-procurement semantic matching. ADR 0014 §1
is explicit that the choice is exogenous (license, coverage, offline-
runnability, architecture maturity), not benchmark-validated — the same
distinction this diagnostic preserves. Whether it activates meaningfully
on Dev/corpus is what execution will show, not what this contract assumes.

## 2. Exact stack (reused verbatim from ADR 0014, not re-decided)

```text
model:              sentence-transformers/paraphrase-multilingual-mpnet-base-v2
revision:            4328cf26390c98c5e3c738b4460a05b95f4911f5
dependency stack:    requirements/evaluation-generation.txt (isolated;
                     torch==2.5.1+cpu, transformers==4.47.1,
                     sentence-transformers==3.4.1, pydantic==2.13.4)
generation device:   CPU
input text:          patent `title + ' ' + abstract`; demand
                     `title + ' ' + description` -- same fields already
                     used by BM25/CPC, no new text sources
max_seq_length:      128 tokens (pinned model's own config)
pooling:             mean pooling over token embeddings (pinned model's
                     own config)
encode() call:       normalize_embeddings=True, batch_size=1
dimensionality:      768
normalization:       L2 (via normalize_embeddings=True)
similarity metric:   cosine, via the existing, unmodified
                     infrastructure/matching/vector_math.cosine_similarity
```

This is ADR 0014's own science freeze (§13), not a new decision — copied
here so this contract is self-contained, not because any value is being
reconsidered. **Not yet verified in this session**: that the pinned
Hugging Face revision is actually resolvable/downloadable from this
environment (network reachability to huggingface.co) — a real
precondition for execution, checked at execution time, not assumed now.

## 3. Candidate definition, fixed before any result is seen

`DuckDbDenseSemanticRetriever` (existing, unmodified code) has
**`min_threshold: float = 0.0`** as its own default — since the cosine
score is rescaled to `[0, 1]` via `(cos + 1) / 2`, a `0.0` threshold
accepts every eligible patent with a computed vector, meaning the pool is
bounded *only* by `limit`, not by any similarity cutoff. Fixed here, in
advance:

- **`limit_per_method=20`** — identical to BM25's and CPC's own setting
  throughout #104 (`generate_ted_annotation_at_scale.py`,
  `run_cpc_channel_diagnostic.py`), so results are comparable on the same
  basis, not because 20 is independently optimal for dense retrieval.
- **`min_threshold=0.0`** — the retriever's own existing default, left
  unchanged. Not tuned, not raised to "clean up" a noisy-looking result
  after execution.
- Eligibility policy: `DefaultPatentEligibilityPolicy(target_jurisdiction="ES")`
  — identical to BM25/CPC, unchanged.

Both values are stated here, before generation or retrieval runs, exactly
so neither can be adjusted post-hoc to produce a more favorable pool.

## 4. Estimand — explicitly not "recall," same discipline as #104

Per `docs/phase2-ted-pool-coverage-estimand-contract.md`'s own reasoning,
restated for dense: the 108-pair gold set covers only the pairs BM25's
pool actually retrieved. Dense retrieval, run independently, will likely
surface some patents for a given demand that were never in BM25's pool —
those pairs have **no gold judgment** and none will be invented here.

What gets measured, mirroring the CPC diagnostic's own report structure:

- **Dense activation**: for each of the 30 demands, pool size (bounded by
  `limit=20`) and whether it is non-empty — with `min_threshold=0.0` this
  is expected to differ qualitatively from CPC's activation gate (dense
  has no equivalent "zero symbols" failure mode; the open question is
  whether a non-empty pool is *informative*, not whether it exists).
- **Overlap with BM25's 108 pairs**: shared candidates (already
  gold-scored — coverage/yield computable immediately), dense-exclusive
  candidates that happen to already be gold-scored (coincidence,
  computable), and dense-exclusive **new** candidates (unscored — reported
  by count and identity only).
- **No coverage or yield number is computed over the new/unscored set.**
  If that set is large enough to be worth judging, extending the gold set
  with a small incremental blind-annotation round is a separate, later
  decision (same discipline as the CPC contract §3), not performed here.
- **No recall claim**, for the same structural reason as BM25: no
  independent judgment exists over patents outside any retriever's pool.

## 5. What stays frozen and unmodified

The 30 Dev demands, the 63-patent corpus, the 108-pair gold set, BM25's
9/30 pool-coverage result, the CPC channel diagnostic's 0/30 result, and
the CPV→NACE scope-gate (`SCOPE-FAILED/DEFERRED`) are all read-only inputs
to this diagnostic. None are re-opened, re-scored, or re-interpreted by
running dense retrieval — this is a new, independent measurement of a
different retrieval capability, not an attempt to improve or explain any
prior #104 result.

## 7. Execution checkpoints (appended as they happen, contract body above unchanged)

**Checkpoint 1 — model accessibility (2026-09-15):** Verified directly
against the Hugging Face API (`GET /api/models/sentence-transformers/paraphrase-multilingual-mpnet-base-v2/revision/4328cf26390c98c5e3c738b4460a05b95f4911f5`,
HTTP 200) — exact pinned revision resolves, `sha` in the response matches
ADR 0014 §2 byte-for-byte. Model's own language tags include all 10
languages observed in Dev (cs, da, de, en, es, fi, fr, nl, pl, sv). PyTorch
CPU wheel index (`download.pytorch.org/whl/cpu`) reachable. No BLOCKED
condition, no discrepancy with ADR 0014's freeze.

**Checkpoint 2 — isolated environment (2026-09-15):** Created
`.venv-embedding-generation/` (repo root, gitignored, separate from
`backend/.venv` — the `embedding-generation-stack-isolation` Import Linter
contract forbids `domain`/`application`/`infrastructure` from importing
`torch`/`transformers`/`sentence_transformers`, so this stays a fully
separate interpreter, not merely a separate import path). Installed
`requirements/evaluation-generation.txt` **exactly as pinned, no
substitutions**. Verified installed versions match declared pins
byte-for-byte:

```text
torch                2.5.1+cpu   (pinned: 2.5.1+cpu)    MATCH
transformers          4.47.1      (pinned: 4.47.1)        MATCH
sentence-transformers 3.4.1       (pinned: 3.4.1)         MATCH
pydantic              2.13.4      (pinned: 2.13.4)        MATCH
```

No BLOCKED condition — installation succeeded cleanly on the first
attempt, no dependency conflict requiring a version substitution.
**Embeddings not yet generated** — this checkpoint is explicitly scoped to
environment creation + installation + verification only, per instruction.

## 6. Non-goals

- Does not invent gold judgments for dense-exclusive new candidates.
- Does not tune `limit_per_method` or `min_threshold` after seeing results.
- Does not re-select the embedding model — ADR 0014's choice is reused
  as-is; a different model would require its own ADR-level decision, not
  a substitution inside this contract.
- Does not touch BM25, CPC, the CPV→NACE track, the corpus, the demand
  corpus, or the gold set.
- Does not compute a merged "BM25+dense" pool or score — this diagnostic
  characterizes dense on its own terms first, exactly as CPC was
  characterized on its own terms before any merge was considered.
- Does not touch ADR 0036.
