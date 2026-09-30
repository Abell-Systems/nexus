# Operational Dense Retrieval — Design & Pre-Registered Probe

**Status:** Approved in chat 2026-09-30 (design, then written spec with one change: bootstrap informative only). Ready for implementation planning.
**Date:** 2026-09-30
**Track:** Product (prototype for South Impact 2026). Not Lab. Produces no scientific efficacy claim.
**Branch:** `feat/operational-corpus-dense-retrieval` (from `main`; independent of the open PRs #112 and #113)

---

## 1. Purpose

The operational corpus v1 (`data/snapshots/operational_corpus_v1/`, 54,997 Spanish-applicant IP assets, see its `manifest.json`) removed the coverage bottleneck: a sanity run of the #104 dry-run demands returned non-empty BM25 pools for 8/8 demands (previously 3/8). But only the two Spanish-language demands returned plausible hits; lexical retrieval is language-blind, and the product's real case is an English demand (Innoget-style open-innovation challenge from a Spanish organization) against a corpus where 80% of abstracts are Spanish.

**Question this iteration answers:**

> Does multilingual dense retrieval remove the cross-language bottleneck that BM25 has on the operational corpus?

This is a product-feasibility probe, pre-registered, with "unresolved" as a valid outcome when the human evaluation itself is unreliable. It is not an efficacy result, is not reported as one, and does not touch the Lab corpus, the Lab Test split, or any sealed Lab artifact.

## 2. Scope

**In scope**
1. Offline generation of dense embeddings for the operational corpus and for the probe demands.
2. A torch-free runtime retriever over the frozen matrix.
3. A pre-registered human-judged probe: BM25 vs dense, blinded.

**Out of scope (explicitly):** BM25+dense fusion, any change to ranking/scoring of the existing engine, UI, alerts, Matching Store, free-text demand input (needs a live embedder, a separate process and an ADR), EPO OPS enrichment, the Lab evaluation.

## 3. Separation rules

- The Lab scientific corpus (OEPM) is untouched. The operational corpus is never an evaluation object for Lab claims.
- No dependency on PR #112/#113 artifacts. The demand population comes from `main` only (§7.1).
- Backend code (`backend/src/main`) never imports from `experiments/` (ADR 0026 boundary guard). Probe harness lives under `experiments/operational-dense-probe/`.
- The runtime never imports torch/transformers/sentence-transformers (Import Linter contract `embedding-generation-stack-isolation`, ADR 0014).

## 4. Embedding generation (offline, once)

Two steps, because the isolated generation environment has no DuckDB/pyarrow (same pattern as the existing `experiments/phase2` generator on the #112 branch):

1. `scripts/extract_operational_texts.py` (main backend venv): reads `publications.parquet` and the probe demand set, writes a plain JSON of ids and texts plus the SHA-256 of each source.
2. `scripts/generate_operational_embeddings.py` (run inside `.venv-embedding-generation`): encodes and writes the artifact.

**Model and settings (identical to ADR 0014 unless stated):**
- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, revision `4328cf26390c98c5e3c738b4460a05b95f4911f5`, CPU, `normalize_embeddings=True`, 768 dimensions.
- Patent text: `title + ' ' + abstract`. Demand text: `title + ' ' + description`. No other text, no normalization beyond the model tokenizer.
- Max sequence length 128 tokens is the model's own configuration. Truncation is accepted and measured (§5).
- `batch_size=1` as in ADR 0014. **Throughput gate:** encode 500 corpus texts first and record texts/second. If the projected full run exceeds 4 hours, a larger batch size may be used, and the deviation, the batch size, and a bit-difference check on a 500-text overlap against `batch_size=1` are recorded in the manifest. The decision is recorded before the full run, not after seeing results.
- Determinism check: re-encode the demand texts and require `np.array_equal`; refuse to write the artifact otherwise.

## 5. Persistence

Stored next to the corpus snapshot, **not committed** (`data/` is already 212 MB); only the manifest is committed.

- `embeddings_patents_v1.npy` — `float32`, shape `(N, 768)`, row order = `ids_patents_v1.json`.
- `embeddings_demands_v1.npy` + `ids_demands_v1.json`.
- `embeddings_manifest_v1.json` — SHA-256 of each file, model name and revision, library versions, device, batch size, SHA-256 of `publications.parquet`, SHA-256 of the demand source file, generation script path and commit, generation date, and **truncation statistics**: the fraction of patent and demand texts exceeding 128 tokens.

Binary is used instead of the ADR 0014 JSON layout: 54,997 × 768 values as JSON is roughly 850 MB.

## 6. Runtime retrieval

- `PrecomputedEmbedder` implements the existing `TextEmbedder` protocol by looking up the frozen demand vector for the exact demand text. An unknown text raises; it never falls back to a live model.
- `NumpyDenseRetriever` implements `PatentCandidateRetriever`: loads the frozen matrix once, applies the same `PatentEligibilityPolicy` as the BM25 retriever, computes cosine similarity as a matrix-vector product (vectors are L2-normalized), scores `(cos + 1) / 2` as in `DuckDbDenseSemanticRetriever`, and breaks ties by `(score DESC, publication_id ASC)`.
- The existing `DuckDbDenseSemanticRetriever` is not modified (it loops per row in Python and is unsuited to 55k rows). The new retriever sits beside it in `infrastructure/matching/`.
- Eligibility (**amended by A1, see the end of this document**): `operational_eligibility_policy()`, the same instance type for both methods: jurisdiction `ES` AND non-empty title AND non-empty abstract. The temporal prior-art rule is not part of the operational eligibility policy; it remains in the Lab's `DefaultPatentEligibilityPolicy`, which this work does not touch.
- **Consequence to accept and report:** the operational policy excludes every record whose `country_code` is not `ES`, so the 10,793 EP-coded Spanish-applicant records of the corpus are not eligible in this probe (44,204 ES-coded records remain). The result document reports, per demand, the eligible-set size. Making the product's jurisdiction rule fit its corpus is a separate product decision, deferred.

## 7. Pre-registered probe

### 7.1 Population

The probe demands are the 39 demands of `experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.json` **minus the 8 Lab Test demands** listed under `test` in `devtest_split_n18_v2.json` (`INNOGET-1605, -1689, -1870, -1965, -2006, -2173, -2258, -2491`), leaving 31. Excluding them keeps the Lab Test split free of any new relevance judgments.

The demand language is recorded per demand (expected: almost all English) and reported as a stratum.

### 7.2 Candidate pairs

For each demand, each method returns its **top-5** eligible candidates (ranking rule per §6 for dense; existing `DuckDbBM25Retriever` ordering for BM25). The judged set for a demand is the **deduplicated union** of both methods' top-5 (at most 10 pairs). A pair appearing in both lists is judged once.

### 7.3 Blinding

Pairs are shuffled across demands with a fixed seed (42) and presented as demand text plus the patent's title and abstract in its original language. Evaluators see no method label, score, rank, or source list. The method provenance table is held in a separate file that evaluators do not open until both have finished.

### 7.4 Relevance scale

The 0–3 scale of `docs/empirical-study-protocol.md` §6.2, unchanged. A pair is **relevant if its final grade is ≥ 2**. `UNCERTAIN` is handled as in §6.3 of that protocol.

### 7.5 Evaluators, common sample, adjudication

- **Evaluator A** (Valentín) judges **all** pairs.
- A **common sample** of 20% of all pairs (`ceil(0.2 · N)`), drawn by simple random sampling **with seed 42** over the full blinded pair list, is judged **independently by Evaluator A and by Lydia**, neither seeing the other's grades.
- For the common sample, report per-evaluator grades, binary Cohen's κ (grade ≥ 2), and quadratic-weighted κ. Protocol §6.4 sets κ_w ≥ 0.70 as the validity threshold; if it is not met, the probe outcome is `UNRESOLVED` regardless of P@5 (§7.7).
- Adjudication of the common sample, fixed before judging: a disagreement of **one grade** is resolved by joint re-review and discussion and the final integer is recorded (never averaged). A disagreement of **two or more grades**, or any `UNCERTAIN`, goes to joint adjudication by both evaluators; if they cannot agree on an integer, the pair is excluded from primary computation and reported in sensitivity analysis (§6.3 of the protocol). **No pair is ever imputed as 0.**
- **Final label** for a pair: the adjudicated grade if it is in the common sample; otherwise Evaluator A's grade.
- Known limitation, stated in advance: Evaluator A is also the system's author. Blinding to method mitigates but does not remove this; it is listed as a threat to validity in the result document.

### 7.6 Metric

For demand *d* and method *m*, with `top5(d, m)` the method's five highest-ranked eligible candidates:

```text
P@5(d, m) = |{p in top5(d, m) : final_grade(d, p) >= 2}| / (5 - |{p in top5(d, m) : p excluded}|)
```

- Slots with no candidate (the method returned fewer than 5 eligible candidates) count as **non-relevant** and stay in the denominator of 5; the number of short lists per method is reported.
- Pairs excluded under §7.5 leave both numerator and denominator. A demand with all five pairs excluded is dropped from that method's average and the count is reported.
- **Macro average:** `P@5(m) = mean over demands of P@5(d, m)`, each demand weight 1. The primary comparison is paired over the same demand set.

### 7.7 Decision rule

The acceptance criterion is exactly:

> Dense passes if `P@5(dense) >= 0.40` **and** `P@5(dense) - P@5(BM25) >= 0.15` (absolute), evaluated on the population of §7.1 under the human protocol of §7.3–§7.6, with the common sample of §7.5 judged independently by Valentín and Lydia and quadratic-weighted `κ_w >= 0.70`.

| Outcome | Condition |
|---|---|
| `RESOLVED-YES` | `κ_w >= 0.70` and both thresholds met on the point estimates |
| `RESOLVED-NO` | `κ_w >= 0.70` and at least one threshold not met on the point estimates |
| `UNRESOLVED` | `κ_w < 0.70` (the evaluation itself is not reliable) |

- `UNCERTAIN` is never converted to 0; it follows §6.3 of the protocol as in §7.5, and the sensitivity bounds (worst case g=0, best case g=1) are reported next to the primary numbers.
- **Bootstrap is informative only.** A paired bootstrap over demands (10,000 resamples, seed 42, percentile 95% interval, reusing `application/evaluation/statistics/bootstrap.py`) is reported for `P@5(dense)`, `P@5(BM25)` and `Δ = P@5(dense) - P@5(BM25)` to quantify uncertainty. It is not an acceptance gate and never changes an outcome.
- Thresholds are fixed before any judging and never adjusted after the data is seen.
- With 31 demands the intervals are expected to be wide. The result document states this next to the outcome instead of hiding it in a gate.
- Secondary, descriptive, non-decisional: per-demand P@5, per-language-stratum P@5, number of empty or short BM25 and dense lists, truncation rate, generation throughput.

### 7.8 Effort (estimate, not measured)

At most 31 × 10 = 310 pairs for Evaluator A (roughly 2–3 hours) and about 62 pairs for each evaluator on the common sample.

## 8. Deliverables and tests

| Deliverable | Location |
|---|---|
| Text extraction | `scripts/extract_operational_texts.py` |
| Embedding generation | `scripts/generate_operational_embeddings.py` |
| Shared embedding code (texts, frozen index, `PrecomputedEmbedder`) | `backend/src/main/infrastructure/embeddings/` (new package; must not import duckdb, because `infrastructure/matching/__init__.py` does and the isolated generation environment has no DuckDB) |
| Runtime retriever | `backend/src/main/infrastructure/matching/numpy_dense.py` |
| Probe harness (pool build, blind export, scorer) | `experiments/operational-dense-probe/` |
| Pre-registration copy and result document | `docs/` (result written after the judging) |

Tests, named `shouldXWhenY`, mocking only at architectural boundaries:
- `NumpyDenseRetriever`: identical ranking on repeated calls; ties broken by `publication_id`; eligibility filter applied; fewer than `limit` results when the eligible set is small.
- `PrecomputedEmbedder`: returns the stored vector for a known text; raises for an unknown text.
- Probe scorer: P@5 with a short list, with an excluded pair, with a demand fully excluded; bootstrap outcome classification on synthetic cases covering all three outcomes; common-sample draw is reproducible under seed 42.
- Manifest: hash verification fails when any artifact byte changes.

## 9. Risks and open points

- **128-token truncation** drops the tail of long abstracts; measured and reported, not corrected.
- **English fallback abstracts** (about 20% of the corpus, mostly EP) may be machine-translated; `abstract_language` is carried into the judging sheet.
- **Corpus licence is unverified** (Google Patents Public Data): internal use only; nothing built here is redistributed.
- **Small population** (31 demands): low power by construction; the bootstrap interval is reported so the reader sees how wide the uncertainty is, but it does not gate the outcome.
- **Temporal eligibility** is not part of the operational policy (A1); the Lab policy keeps it.
- **CPC coverage** is 64% of the corpus; the CPC channel is not used here.


## Amendment A1 (2026-09-30): operational eligibility policy, made before any probe data exists

**Finding.** `posted_date` is `null` in 39 of 39 demands of `dataset_phase2_demand_corpus_n39.json`. `DefaultPatentEligibilityPolicy` excludes every patent when the demand has no valid `posted_date` (`EXCLUDED_TEMPORAL`), so with that policy the eligible set is empty for all 39 demands: both methods would return empty lists and the probe would measure nothing. The original text of this section assumed parity with the Lab policy without checking the demands' dates. The error was found while specifying the product MVP, before the embeddings finished, before the judging sheets were built, and before any top-5 list was looked at.

**Amendment.** The probe (and the product) use `operational_eligibility_policy`: `country_code == "ES"` AND non-empty title AND non-empty abstract. Nothing else. No date is invented for the demands.

**Two policies, two purposes.**

```text
Lab evaluation           -> DefaultPatentEligibilityPolicy -> temporal constraint -> scientific corpus
Operational MVP / probe  -> operational_eligibility_policy -> ES + title + abstract -> operational corpus
```

The temporal rule is not part of the operational eligibility policy. This is not a judgment that temporality lacks scientific value: it answers the Lab's question (prior art before a demand), not the operational one (which Spanish assets of the operational corpus are candidates for this demand). BM25 and dense compete on exactly the same eligible universe.

**Unchanged:** thresholds, metric, evaluators, common sample, seed, UNCERTAIN handling, bootstrap role.

## Amendment A2 (2026-09-30): model-first judging with human tie-break, made before any judgment exists

**State when written.** The 310-pair judging sheet exists and every grade cell is empty. No human and no model has graded any pair. The provenance file has not been opened. The escalation rule below is fixed now, before the model sees the sheet.

**Reason.** Two humans grading 310 and 62 pairs is disproportionate effort for a prototype decision. The owners chose to delegate clear-cut pairs to a model and keep humans for the pairs that are not clear-cut. This supersedes the evaluator paragraph and the adjudication procedure of section 7.5; `adjudication.csv` is no longer used.

**Evaluators.**
- **Model evaluator (M):** `claude-opus-5-5` in a fresh-context subagent. It receives only a copy of the blinded sheet (no method labels, no provenance, no result files) and the rubric of protocol section 6.2 verbatim. It grades every one of the 310 pairs with a grade 0-3 or `U`, a confidence `high` or `low`, and a one-sentence rationale. It must use only the demand and patent text on the sheet.
- **Human evaluator (H):** one of the two owners, recorded by name in the result document. H is blind to the retrieval method and to M's grades and confidences.

**Escalation rule (fixed).** A pair is escalated to H if M's confidence is `low` OR M's grade is `U`.

**Who grades what.** H grades (a) all 62 pairs of the random common sample, whatever M said, and (b) every escalated pair outside the common sample. H may answer `U`; an unresolved `U` is excluded, never imputed as 0 (protocol 6.3).

**Final label.** H's grade wherever H graded; otherwise M's grade. No `U` from M survives outside H's hands, since every M `U` is escalated.

**Agreement.** `kappa_w` (quadratic) and binary `kappa` between M and H are computed only on the 62 common-sample pairs graded by both (pairs where either answered `U` are excluded and counted). The common sample is random, so this is an unbiased estimate of agreement; escalated pairs are chosen for difficulty and are deliberately not used for agreement. Threshold unchanged: `kappa_w >= 0.70` or the outcome is UNRESOLVED.

**Reporting added (informative only, never a gate).** Number of pairs escalated and their share; M-vs-H disagreement counts on the common sample; P@5 of both methods under M-only labels next to P@5 under final labels.

**Label for the result.** "Judged by an LLM, validated against a human on a 20% random sample, with human resolution of low-confidence pairs." Not "two-human annotation".

**Validity threats added.** (1) M and the system builder are models of the same vendor family and M may prefer text resembling its own style; not testable here. (2) Final labels mix two evaluators; the agreement estimate applies to M overall, not specifically to escalated pairs. (3) M's blindness is procedural (only the sheet copy is given); it is not sandboxed from the repository. (4) H who is also the system's author (if Valentín) keeps the evaluator-builder threat declared in section 9.

**Unchanged.** Thresholds (`P@5 >= 0.40`, delta `>= 0.15`, `kappa_w >= 0.70`), the metric, the population of 31 demands, the common sample and seed 42, UNCERTAIN handling, and the informative role of the bootstrap.
