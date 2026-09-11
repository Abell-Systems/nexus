# ADR 0027: Family-Aware Evaluation Contract

**Status:** Accepted
**Date:** 2026-09-11
**Scope:** Closes one of the two genuine gaps flagged in `docs/roadmap.md` §6 (external scientific-rigor review, P1, before PR-F efficacy claims): "no family/duplicate-detection policy exists anywhere in the codebase or protocol." Resolves the ambiguity by contract; a *detector* that populates real family metadata for the OEPM corpus is an explicit non-goal of this ADR and its implementation PR (see "What this ADR does not do").

## Context

A single invention can produce multiple patent publications (continuations, divisionals, national-phase filings of the same priority claim). If a benchmark's candidate universe contains several such publications and a ranking engine surfaces more than one, standard IR metrics (Precision@k, Recall@k, nDCG) can overstate the engine's apparent diversity of coverage — one invention contributing multiple ranked hits inflates the observed score without reflecting genuine additional relevance.

The evaluation domain (`domain/models/evaluation.py`) has no concept of patent family today. `EvaluationPatent` carries only `publication_id`, dates, CPC codes, title/abstract, and provenance. A structurally similar but INPADOC-shaped model already exists in `domain/models/patent.py` (`PatentDocument.family_id`, `PatentFamily`, `FamilyMembership`) for the matching/ingestion bounded context, but:

1. It belongs to `domain.models.matching`'s import boundary, which the evaluation subsystem is architecturally forbidden from depending on directly (`domain/protocols/evaluation.py`'s own docstring invariant: "domain/protocols/evaluation.py MUST NOT import from domain.protocols.matching or domain.models.matching").
2. It is unpopulated for the real corpus in use. `data/snapshots/patents_es_corpus.jsonl` (the ingested OEPM Spanish patent corpus) carries only `publication_number`, `title`, `abstract`, `assignee`, `filing_date`, `publication_date`, `cpc_codes`, and citation counts — no `application_number`, no `family_id`, for any record inspected.

This means a family-aware evaluation policy cannot, today, be backed by real family identity. The temptation is to approximate family membership with a heuristic — same assignee plus high title/abstract/CPC similarity. This ADR explicitly rejects that path: a heuristic built from the same signals (title/abstract text, CPC) that the ranking engines being evaluated *also* use to establish relevance would make "family" partially circular with "relevance," contaminating exactly the study family-awareness is meant to make more rigorous. A false-positive family match under such a heuristic would silently suppress a genuinely distinct, relevant patent from the ranked output.

## Decision

### 1. `family_id` is accepted, never inferred

`EvaluationPatent` gains one new optional field:

```python
family_id: str | None = None
```

`None` means "no family metadata available for this publication." This field is populated only by whatever produced the sealed dataset (e.g. a future corpus-construction step backed by real INPADOC/OPS family data) — never computed at evaluation time from title, abstract, CPC, or assignee similarity. No such computation exists anywhere in this ADR's implementation.

### 2. Three explicit, named policies — never inferred, never defaulted

A run declares exactly one of, on `EvaluationExecutionContext.family_policy` (mandatory, no default — ADR 0005's explicit-injection principle, the same one `temporal_pool_mode` already follows per ADR 0018):

- **`allow`** — no family-based collapsing or exclusion. Pre-ADR-0027 baseline behavior, preserved exactly.
- **`collapse`** — before ranking, the candidate pool is reduced to one deterministic representative per `family_id` (the member with the lexicographically smallest `publication_id`). Simulates "count each invention once."
- **`exclude_related`** — before ranking, every patent belonging to a family with more than one member in the pool is dropped entirely. A stricter condition than `collapse`: no representative is kept for a multi-member family.

### 3. Fail fast when metadata cannot support the requested policy

`collapse` and `exclude_related` require `family_id` to be populated (non-`None`) for **every** patent in the sealed candidate universe for the run. If any patent is missing it, the run raises `ValueError` (message contains the literal string `FAMILY_METADATA_UNAVAILABLE`) before any ranking happens. It never silently falls back to `allow`, and never partially applies the policy to only the patents that happen to carry metadata — a partial application would distort metrics for annotated-but-unlabelled patents in a way that is exactly as misleading as inventing the metadata.

`allow` requires no metadata and always succeeds, whether or not any patent carries `family_id`.

### 4. Pool construction happens in `DefaultEvaluationRunner`, never in the adapter or engine

Exactly the same placement decision ADR 0018 made for `temporal_pool_mode`: the transform runs in `DefaultEvaluationRunner.run_evaluation`, immediately after the existing temporal-eligibility filter and before `ranking_port.rank_candidates` is called. `DefaultMatchingAdapter`'s closed-universe guarantee is untouched — it still receives whatever patent list it's given.

### 5. Provenance: the run records whether metadata was actually available

`EvaluationRunReport` gains `family_metadata_available: bool`, populated from the sealed patent universe regardless of which policy was selected. This makes an `allow` run's report distinguishable from a `collapse`-eligible run's report without re-deriving the fact from the raw dataset — the audit trail stays honest even when no family-sensitive policy was requested.

## What this ADR does not do

- Does not implement, or authorize implementing, any family/duplicate *detector* — heuristic (title/CPC/assignee similarity) or authoritative (INPADOC/OPS family lookup). Sourcing real `family_id` values into the OEPM corpus is a separate, future data-dependency PR.
- Does not run, or report, any family-aware sensitivity re-run of the Phase-2 benchmark — there is no populated `family_id` data yet for this corpus to run it on.
- Does not change `nDCG@10`'s status as the confirmatory endpoint, `MetricSet`, or any fusion/BM25/CPC scoring logic.
- Does not touch `domain/models/patent.py`'s `PatentFamily`/`FamilyMembership` (matching/ingestion bounded context) or import it from the evaluation domain.

## Consequences

### Positive

- Closes the roadmap's family-aware-evaluation gap with a precise, testable, honest contract instead of a heuristic that would have contaminated the very validity question it exists to answer.
- `comparative.py`'s existing paired-run harness (ADR 0011) can compare an `allow` run against a `collapse`/`exclude_related` run the moment real family metadata exists, with zero new statistical-harness code — it already operates generically on any two `EvaluationRunReport`s.

### Negative

- Until a real family-metadata source is sourced into the corpus, `collapse`/`exclude_related` are unusable on the live OEPM dataset — the fail-fast is a feature, not a limitation, but it does mean this ADR alone does not yet produce a family-aware Phase-2 result.
- Adds a third axis of run identity (alongside `temporal_pool_mode`) that comparative pairing must account for — comparing runs with different `family_policy` values compares pools of different composition, not a like-for-like ranking comparison, unless deliberately intended.

## Enforcement

A future PR is **non-compliant** with this ADR if it:

1. Computes or infers `family_id` from title, abstract, CPC, assignee, or any other relevance-adjacent signal, anywhere in the evaluation pipeline.
2. Implements `collapse`/`exclude_related` filtering inside `DefaultMatchingAdapter` or `DefaultMatchingEngine` rather than in `DefaultEvaluationRunner` before `ranking_port.rank_candidates` is called.
3. Permits a run with `family_policy` in `{"collapse", "exclude_related"}` to execute against a patent universe with incomplete `family_id` coverage without failing fast.
4. Imports `domain.models.matching` or `domain.protocols.matching` from `domain/models/evaluation.py` or `domain/protocols/evaluation.py` to source family data.
5. Reports a family-aware Phase-2 sensitivity result before a real family-metadata source has been sourced, reviewed, and sealed into the corpus.
