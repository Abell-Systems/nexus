# Family-Aware Evaluation Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, versioned, fail-fast `family_policy` (`allow | collapse | exclude_related`) to the evaluation harness, so a run can honestly declare and enforce a patent-family policy — without inventing family membership from any relevance-adjacent signal.

**Architecture:** `EvaluationPatent` gains an optional `family_id: str | None` field that is only ever *accepted* from externally-supplied dataset metadata, never inferred (no title/CPC/assignee-similarity heuristic ships in this PR). `EvaluationExecutionContext` gains a mandatory `family_policy` field, following the exact explicit-injection precedent `temporal_pool_mode` already established (ADR 0018). `DefaultEvaluationRunner.run_evaluation` fails fast — before any ranking happens — if `family_policy` is `collapse` or `exclude_related` and any patent in the sealed universe is missing `family_id` (`FAMILY_METADATA_UNAVAILABLE`). When metadata is present, a new pre-ranking pool transform (`_apply_family_policy`, sitting next to the existing `_filter_temporally_eligible_patents`) either passes the pool through unchanged (`allow`), collapses each family to one deterministic representative (`collapse`), or drops every patent belonging to a multi-member family (`exclude_related`). `EvaluationRunReport` records whether family metadata was actually available for the run, so the audit trail is honest even under `allow`.

**Tech Stack:** Python 3.12, Pydantic v2 (frozen models), pytest.

**Spec:** `docs/roadmap.md` §6 (gap identified: "Patent-family-aware evaluation: no family/duplicate-detection policy exists anywhere in the codebase or protocol"); `docs/adr/0018-temporal-pool-eligibility-contract.md` (direct structural precedent for this ADR/contract); this plan's own Task 1 produces `docs/adr/0027-family-aware-evaluation-contract.md`, which becomes the authoritative spec for the mechanism.

## Global Constraints

- Contract → test → code ordering, strictly (CLAUDE.md, this repo's established discipline).
- Clean Architecture layering: domain/application/infrastructure (CLAUDE.md). This feature touches only `domain/models/evaluation.py`, `application/evaluation/runner.py`, and `scripts/` — no infrastructure changes.
- `domain/protocols/evaluation.py`'s existing invariant is untouched: the evaluation subsystem imports NOTHING from `domain.models.matching` / `domain.protocols.matching`. `family_id` lives on `EvaluationPatent` itself (evaluation-domain type) — no cross-boundary import is introduced.
- No detector ships in this PR: no title/CPC/assignee-similarity heuristic, no INPADOC lookup, no new dependency. `family_id` is only ever accepted as given on the dataset.
- No implicit defaults for `family_policy`: it is mandatory on `EvaluationExecutionContext`, exactly like `temporal_pool_mode` (ADR 0005 explicit-injection principle).
- `collapse` / `exclude_related` without complete family metadata on the sealed patent universe must raise `ValueError` containing `FAMILY_METADATA_UNAVAILABLE` — never silently degrade to `allow`.
- Every commit message ends with the two attribution trailers from this session (Lydia Bares co-author per CLAUDE.md, plus the Claude Code session trailers already given in this conversation's system context).
- Run tests with: `cd backend && python -m pytest test/unit/domain/test_evaluation_protocol_models.py test/unit/application/test_evaluation_runner.py test/unit/application/test_metrics_endpoint.py test/unit/application/evaluation/test_comparative_evaluation.py test/e2e/test_m0_vs_m1_comparison_cli.py -v` (adjust to the single file being worked on per task; run the full set again at the end of Task 4).

---

## File Structure

- `docs/adr/0027-family-aware-evaluation-contract.md` — new. Records the decision (mirrors ADR 0018's shape): explicit `family_policy` field, accept-don't-infer `family_id`, fail-fast on missing metadata, pre-ranking pool transform location, no detector in scope.
- `backend/src/main/domain/models/evaluation.py` — modify. Add `EvaluationPatent.family_id: str | None = None`, `EvaluationExecutionContext.family_policy: Literal["allow", "collapse", "exclude_related"]`, `EvaluationRunReport.family_metadata_available: bool`.
- `backend/src/main/application/evaluation/runner.py` — modify. Add `family_metadata_available(patents) -> bool`, `validate_family_policy_feasible(family_policy, patents) -> None`, `_apply_family_policy(family_policy, patents) -> list[EvaluationPatent]`; wire all three into `DefaultEvaluationRunner.run_evaluation`.
- `backend/test/unit/domain/test_evaluation_protocol_models.py` — modify. New field-contract tests + fixture updates (add `family_policy="allow"` to existing `EvaluationExecutionContext(...)` calls, `family_metadata_available=True` to the existing `EvaluationRunReport(...)` call).
- `backend/test/unit/application/test_evaluation_runner.py` — modify. Fixture updates (`family_policy="allow"` on `sample_context`/`strict_context`) + new tests for fail-fast, `allow`, `collapse`, `exclude_related`, and `family_metadata_available` reporting.
- `backend/test/unit/application/test_metrics_endpoint.py` — modify. Fixture updates only (`family_policy="allow"`, `family_metadata_available=True`).
- `backend/test/unit/application/evaluation/test_comparative_evaluation.py` — modify. Fixture updates only (`family_policy="allow"`, `family_metadata_available=True`).
- `scripts/run_scientific_evaluation.py` — modify. Add mandatory `--family-policy` CLI flag, thread into `EvaluationExecutionContext`.
- `scripts/run_m0_vs_m1_comparison.py` — modify. Same as above.
- `backend/test/e2e/test_m0_vs_m1_comparison_cli.py` — modify. `_run_cli` passes `--family-policy allow`.

---

### Task 1: Domain contract — `family_id`, `family_policy`, `family_metadata_available` + ADR 0027

**Files:**
- Create: `docs/adr/0027-family-aware-evaluation-contract.md`
- Modify: `backend/src/main/domain/models/evaluation.py` (EvaluationPatent ~line 104-110, EvaluationExecutionContext ~line 323-345, EvaluationRunReport ~line 397-421)
- Test: `backend/test/unit/domain/test_evaluation_protocol_models.py`
- Modify (fixture-only, no new tests): `backend/test/unit/application/test_metrics_endpoint.py`, `backend/test/unit/application/evaluation/test_comparative_evaluation.py`

**Interfaces:**
- Produces: `EvaluationPatent.family_id: str | None` (default `None`), `EvaluationExecutionContext.family_policy: Literal["allow", "collapse", "exclude_related"]` (mandatory), `EvaluationRunReport.family_metadata_available: bool` (mandatory). Later tasks construct/consume these exact names.

- [ ] **Step 1: Write the ADR**

Create `docs/adr/0027-family-aware-evaluation-contract.md`:

```markdown
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
```

- [ ] **Step 2: Commit the ADR**

```bash
git add docs/adr/0027-family-aware-evaluation-contract.md
git commit -m "$(cat <<'EOF'
docs(adr): add ADR 0027 — family-aware evaluation contract

Closes the family-aware-evaluation gap from docs/roadmap.md §6 by
contract: family_id is only ever accepted from dataset metadata, never
inferred from title/CPC/assignee similarity, which would make "family"
circular with the relevance signals under evaluation. collapse/
exclude_related fail fast when metadata is incomplete rather than
degrading silently to allow.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

- [ ] **Step 3: Write the failing domain-model tests**

Add to `backend/test/unit/domain/test_evaluation_protocol_models.py` (near the other `EvaluationPatent`/`EvaluationExecutionContext` tests — check the file's existing imports already include `EvaluationPatent`, `EvaluationExecutionContext`, `EvaluationRunReport`, `date`, `pytest`):

```python
def test_evaluation_patent_family_id_defaults_to_none():
    patent = EvaluationPatent(
        publication_id="P-1",
        publication_date=date(2022, 1, 1),
        classifications_cpc=["E03C"],
        title="Patent",
        abstract="Abstract",
        provenance=_sample_provenance(),
    )
    assert patent.family_id is None


def test_evaluation_patent_accepts_explicit_family_id():
    patent = EvaluationPatent(
        publication_id="P-1",
        publication_date=date(2022, 1, 1),
        classifications_cpc=["E03C"],
        title="Patent",
        abstract="Abstract",
        provenance=_sample_provenance(),
        family_id="FAM-42",
    )
    assert patent.family_id == "FAM-42"


def test_evaluation_execution_context_requires_family_policy():
    with pytest.raises(ValidationError):
        EvaluationExecutionContext(
            engine_name="Test",
            engine_version="1.0",
            engine_commit_hash="a321b0c",
            execution_timestamp=datetime.now(UTC),
            environment="test",
            temporal_pool_mode="unconstrained",
        )


def test_evaluation_execution_context_rejects_invalid_family_policy():
    with pytest.raises(ValidationError):
        EvaluationExecutionContext(
            engine_name="Test",
            engine_version="1.0",
            engine_commit_hash="a321b0c",
            execution_timestamp=datetime.now(UTC),
            environment="test",
            temporal_pool_mode="unconstrained",
            family_policy="infer_from_title",
        )
```

If the file has no `_sample_provenance()` helper and no `EvaluationPatent`/`ValidationError` import yet, add:

```python
from pydantic import ValidationError
```

and a small local helper next to the other fixtures in that file:

```python
def _sample_provenance() -> EvaluationProvenance:
    return EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com/p",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="1" * 64,
        modality=DataModality.OBSERVED,
    )
```

(reuse it if an equivalent already exists under a different name — check the file first; do not duplicate).

- [ ] **Step 4: Run the new tests to verify they fail**

Run: `cd backend && python -m pytest test/unit/domain/test_evaluation_protocol_models.py -k "family_id or family_policy" -v`
Expected: FAIL — `family_id`/`family_policy` are unrecognized fields (Pydantic extra-field or missing-required errors), or `ImportError`/`AttributeError` if `EvaluationPatent`/`ValidationError` aren't imported yet.

- [ ] **Step 5: Implement the domain model fields**

In `backend/src/main/domain/models/evaluation.py`, modify `EvaluationPatent`:

```python
class EvaluationPatent(BaseModel):
    """Normalized, frozen patent publication record for scientific evaluation."""

    model_config = ConfigDict(frozen=True)

    publication_id: str = Field(min_length=1)
    publication_date: date | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)
    provenance: EvaluationProvenance
    # ADR 0027: externally-supplied patent-family identifier (e.g. from a future
    # INPADOC/OPS-backed corpus source). None means "no family metadata available
    # for this publication" -- this field is NEVER inferred here from title, CPC,
    # or assignee similarity; only ever accepted as given on the sealed dataset.
    family_id: str | None = None
```

Modify `EvaluationExecutionContext` (add the field right after `temporal_pool_mode`):

```python
    temporal_pool_mode: Literal["strict", "unconstrained"]
    # ADR 0027: family-aware evaluation policy. Mandatory, no default (ADR 0005
    # explicit-injection principle, same as temporal_pool_mode / ADR 0018).
    # "allow": no family-based collapsing/exclusion (pre-ADR-0027 baseline).
    # "collapse": pool is reduced to one representative per family_id before ranking.
    # "exclude_related": every patent in a multi-member family is dropped before ranking.
    family_policy: Literal["allow", "collapse", "exclude_related"]
```

Modify `EvaluationRunReport` (add the field after `uncertainty_rate`):

```python
    uncertainty_rate: float = Field(ge=0.0, le=1.0)
    # ADR 0027: whether every patent in this run's sealed universe carried family_id.
    # Recorded unconditionally (even under family_policy="allow") so the audit trail
    # is honest about whether a family-sensitive policy could have been requested.
    family_metadata_available: bool
```

- [ ] **Step 6: Run the new tests to verify they pass**

Run: `cd backend && python -m pytest test/unit/domain/test_evaluation_protocol_models.py -k "family_id or family_policy" -v`
Expected: PASS

- [ ] **Step 7: Fix the now-broken existing fixtures in the same file**

`test_evaluation_protocol_models.py` has 4 pre-existing `EvaluationExecutionContext(...)` constructions (lines ~24, ~41, ~52, ~63) and 1 `EvaluationRunReport(...)` construction (line ~121). Add `family_policy="allow",` right after each existing `temporal_pool_mode="unconstrained",` line, and add `family_metadata_available=True,` right after `uncertainty_rate=0.10,` in the `EvaluationRunReport(...)` call.

- [ ] **Step 8: Fix the fixtures in the two other affected test files**

In `backend/test/unit/application/test_metrics_endpoint.py`: the `EvaluationExecutionContext(...)` call (~line 184) gets `family_policy="allow",` added after `temporal_pool_mode="unconstrained",`; the `EvaluationRunReport(...)` call (~line 263) gets `family_metadata_available=True,` added after `uncertainty_rate=0.0,`.

In `backend/test/unit/application/evaluation/test_comparative_evaluation.py`: the module-level `_CTX = EvaluationExecutionContext(...)` (~line 30) gets `family_policy="allow",` added after `temporal_pool_mode="unconstrained",`; the `_run(...)` helper's `EvaluationRunReport(...)` call (~line 75) gets `family_metadata_available=True,` added after `uncertainty_rate=0.0,`.

- [ ] **Step 9: Run the full affected test suite to verify nothing else broke**

Run: `cd backend && python -m pytest test/unit/domain/test_evaluation_protocol_models.py test/unit/application/test_metrics_endpoint.py test/unit/application/evaluation/test_comparative_evaluation.py test/unit/application/test_evaluation_runner.py -v`
Expected: the 4 new tests PASS; `test_evaluation_runner.py` FAILS (its own `sample_context`/`strict_context`/`EvaluationRunReport` construction sites are fixed in Task 3, not here) — confirm the failures there are exactly `family_policy`/`family_metadata_available` missing-field errors, nothing else.

- [ ] **Step 10: Commit**

```bash
git add backend/src/main/domain/models/evaluation.py \
        backend/test/unit/domain/test_evaluation_protocol_models.py \
        backend/test/unit/application/test_metrics_endpoint.py \
        backend/test/unit/application/evaluation/test_comparative_evaluation.py
git commit -m "$(cat <<'EOF'
feat(evaluation): add family_id, family_policy, family_metadata_available fields (ADR 0027)

Contract-only step: EvaluationPatent.family_id is accepted metadata,
never inferred; EvaluationExecutionContext.family_policy is mandatory
(allow|collapse|exclude_related); EvaluationRunReport.family_metadata_available
is recorded unconditionally. No behavior wired into the runner yet.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 2: Fail-fast validator (pure functions, no dataset execution)

**Files:**
- Modify: `backend/src/main/application/evaluation/runner.py`
- Test: `backend/test/unit/application/test_evaluation_runner.py`

**Interfaces:**
- Consumes: `EvaluationPatent` (Task 1, has `.family_id`).
- Produces: `family_metadata_available(patents: list[EvaluationPatent]) -> bool` and `validate_family_policy_feasible(family_policy: str, patents: list[EvaluationPatent]) -> None` (raises `ValueError` with `"FAMILY_METADATA_UNAVAILABLE"` in the message). Task 3 wires both into `run_evaluation`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/test/unit/application/test_evaluation_runner.py`, near the existing `validate_temporal_pool_mode_consistency` tests at the bottom of the file:

```python
# ---------------------------------------------------------------------------
# ADR 0027: family-aware evaluation fail-fast validator
# ---------------------------------------------------------------------------


def test_family_metadata_available_true_when_all_patents_have_family_id(sample_validated_dataset):
    patents = [
        p.model_copy(update={"family_id": f"FAM-{i}"})
        for i, p in enumerate(sample_validated_dataset.dataset.patents)
    ]
    assert family_metadata_available(patents) is True


def test_family_metadata_available_false_when_any_patent_missing_family_id(sample_validated_dataset):
    patents = list(sample_validated_dataset.dataset.patents)  # family_id is None on all of these
    assert family_metadata_available(patents) is False


def test_validate_family_policy_feasible_allows_allow_regardless_of_metadata(sample_validated_dataset):
    validate_family_policy_feasible("allow", sample_validated_dataset.dataset.patents)


def test_validate_family_policy_feasible_raises_for_collapse_without_metadata(sample_validated_dataset):
    with pytest.raises(ValueError, match="FAMILY_METADATA_UNAVAILABLE"):
        validate_family_policy_feasible("collapse", sample_validated_dataset.dataset.patents)


def test_validate_family_policy_feasible_raises_for_exclude_related_without_metadata(sample_validated_dataset):
    with pytest.raises(ValueError, match="FAMILY_METADATA_UNAVAILABLE"):
        validate_family_policy_feasible("exclude_related", sample_validated_dataset.dataset.patents)


def test_validate_family_policy_feasible_accepts_collapse_with_full_metadata(sample_validated_dataset):
    patents = [
        p.model_copy(update={"family_id": f"FAM-{i}"})
        for i, p in enumerate(sample_validated_dataset.dataset.patents)
    ]
    validate_family_policy_feasible("collapse", patents)
```

Update the import block at the top of the file:

```python
from application.evaluation.runner import (
    DefaultEvaluationRunner,
    family_metadata_available,
    validate_family_policy_feasible,
    validate_temporal_pool_mode_consistency,
)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest test/unit/application/test_evaluation_runner.py -k "family_metadata_available or validate_family_policy_feasible" -v`
Expected: FAIL with `ImportError: cannot import name 'family_metadata_available'`.

- [ ] **Step 3: Implement the pure functions**

In `backend/src/main/application/evaluation/runner.py`, add right after `validate_temporal_pool_mode_consistency` (before `_filter_temporally_eligible_patents`):

```python
def family_metadata_available(patents: list[EvaluationPatent]) -> bool:
    """ADR 0027: True iff every patent in the given pool carries a non-None family_id.

    A single missing family_id makes the pool's family composition only partially
    known -- treated as fully unavailable, since a partial collapse/exclusion would
    silently distort metrics for the unlabelled patents in a way indistinguishable
    from inventing the metadata.
    """
    return all(p.family_id is not None for p in patents)


def validate_family_policy_feasible(family_policy: str, patents: list[EvaluationPatent]) -> None:
    """ADR 0027 §3: fails fast when the requested policy cannot be honestly applied.

    "allow" never requires family metadata. "collapse" and "exclude_related" require
    it on every patent in the pool being validated -- never silently degrade to
    "allow" and never partially apply the policy.
    """
    if family_policy == "allow":
        return
    if not family_metadata_available(patents):
        raise ValueError(
            f"FAMILY_METADATA_UNAVAILABLE: family_policy='{family_policy}' requires "
            "family_id to be populated on every patent in the candidate universe, "
            "but at least one patent is missing it. Use family_policy='allow', or "
            "supply a dataset with complete family metadata (ADR 0027 §1: family_id "
            "is only ever accepted from the sealed dataset, never inferred here)."
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd backend && python -m pytest test/unit/application/test_evaluation_runner.py -k "family_metadata_available or validate_family_policy_feasible" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/application/evaluation/runner.py backend/test/unit/application/test_evaluation_runner.py
git commit -m "$(cat <<'EOF'
feat(evaluation): add family-policy fail-fast validator (ADR 0027)

family_metadata_available() and validate_family_policy_feasible() are
pure functions, not yet wired into run_evaluation. collapse/
exclude_related raise FAMILY_METADATA_UNAVAILABLE when any patent in
the pool lacks family_id; allow always succeeds.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 3: Pre-ranking pool transform + wiring into `run_evaluation`

**Files:**
- Modify: `backend/src/main/application/evaluation/runner.py`
- Test: `backend/test/unit/application/test_evaluation_runner.py`

**Interfaces:**
- Consumes: `family_metadata_available`, `validate_family_policy_feasible` (Task 2); `EvaluationPatent.family_id`, `EvaluationExecutionContext.family_policy`, `EvaluationRunReport.family_metadata_available` (Task 1).
- Produces: `_apply_family_policy(family_policy: str, patents: list[EvaluationPatent]) -> list[EvaluationPatent]`, and `DefaultEvaluationRunner.run_evaluation` now fails fast on infeasible policies and stamps `family_metadata_available` on the returned report.

- [ ] **Step 1: Fix the two now-broken context fixtures first**

In `backend/test/unit/application/test_evaluation_runner.py`, add `family_policy="allow",` after `temporal_pool_mode="unconstrained",` in `sample_context` and after `temporal_pool_mode="strict",` in `strict_context`. Run: `cd backend && python -m pytest test/unit/application/test_evaluation_runner.py -v` and confirm the only remaining failures are about `family_metadata_available` missing from `EvaluationRunReport` construction inside `run_evaluation` itself (i.e. every test that calls `runner.run_evaluation(...)` now fails with a Pydantic validation error on the report, not on the context) — this confirms the fixtures are fixed and isolates the remaining gap to Task 3's implementation.

- [ ] **Step 2: Write the failing pool-transform and integration tests**

Add to `backend/test/unit/application/test_evaluation_runner.py`:

```python
# ---------------------------------------------------------------------------
# ADR 0027: family-aware pool transform, wired into run_evaluation
# ---------------------------------------------------------------------------


@pytest.fixture
def dataset_with_known_family() -> ValidatedDataset:
    """Two patents sharing FAM-A (P-A1, P-A2), one singleton family FAM-B (P-B1)."""
    prov = EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com/p",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="1" * 64,
        modality=DataModality.OBSERVED,
    )
    demand = EvaluationDemand(
        demand_id="D-FAM",
        title="Sanitary Fixtures",
        description="Drainage equipment",
        posted_date=date(2023, 1, 1),
        target_cpc_prefixes=["E03C"],
        provenance=prov,
    )
    patents = [
        EvaluationPatent(
            publication_id="P-A1", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent A1", abstract="Abstract",
            provenance=prov, family_id="FAM-A",
        ),
        EvaluationPatent(
            publication_id="P-A2", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent A2", abstract="Abstract",
            provenance=prov, family_id="FAM-A",
        ),
        EvaluationPatent(
            publication_id="P-B1", publication_date=date(2022, 1, 1),
            classifications_cpc=["E03C"], title="Patent B1", abstract="Abstract",
            provenance=prov, family_id="FAM-B",
        ),
    ]
    annotations = [
        EvaluationAnnotation(
            demand_id="D-FAM", publication_id=pid, grade=RelevanceGrade.GRADE_2,
            annotator_role="expert", modality=DataModality.EXPERT_LABELLED,
        )
        for pid in ("P-A1", "P-A2", "P-B1")
    ]
    dataset = EvaluationDataset(
        dataset_id="eval-corpus-family", schema_version="1.0.0", dataset_version="1.0.0",
        description="Family test corpus", demands=[demand], patents=patents, annotations=annotations,
    )
    manifest = EvaluationDatasetManifest(
        dataset_id="eval-corpus-family", schema_version="1.0.0", dataset_version="1.0.0",
        source_authorities=["oepm"], demand_count=1, patent_count=3, annotation_count=3,
        content_sha256="f" * 64,
    )
    return ValidatedDataset(dataset=dataset, manifest=manifest)


def _family_context(family_policy: str) -> EvaluationExecutionContext:
    return EvaluationExecutionContext(
        engine_name="FakeRankingPort", engine_version="1.0.0", engine_commit_hash="a321b0c",
        execution_timestamp=datetime(2026, 9, 3, 14, 0, 0, tzinfo=UTC), environment="test",
        temporal_pool_mode="unconstrained", family_policy=family_policy,
    )


def test_runner_allow_policy_passes_full_pool_unchanged(
    dataset_with_known_family, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-A2", "P-B1"])
    runner = DefaultEvaluationRunner()

    runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("allow"),
    )

    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    assert received_ids == {"P-A1", "P-A2", "P-B1"}


def test_runner_collapse_policy_keeps_one_representative_per_family(
    dataset_with_known_family, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-A2", "P-B1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("collapse"),
    )

    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    # FAM-A has two members (P-A1, P-A2): only the lexicographically smallest
    # publication_id (P-A1) survives. FAM-B is a singleton and survives whole.
    assert received_ids == {"P-A1", "P-B1"}
    assert report.demand_reports[0].candidate_count == 2


def test_runner_exclude_related_policy_drops_every_multi_member_family(
    dataset_with_known_family, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-A2", "P-B1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("exclude_related"),
    )

    received_ids = {p.publication_id for p in ranking_port.received_patents[0]}
    # FAM-A has two members: both are dropped entirely. FAM-B is a singleton: kept.
    assert received_ids == {"P-B1"}
    assert report.demand_reports[0].candidate_count == 1


def test_run_evaluation_raises_when_collapse_requested_without_family_metadata(
    sample_validated_dataset, sample_policy
):
    """sample_validated_dataset's patents all have family_id=None (Task 1 default)."""
    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    with pytest.raises(ValueError, match="FAMILY_METADATA_UNAVAILABLE"):
        runner.run_evaluation(
            dataset=sample_validated_dataset, ranking_port=ranking_port,
            policy=sample_policy, context=_family_context("collapse"),
        )


def test_run_evaluation_records_family_metadata_available_false_under_allow(
    sample_validated_dataset, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-1", "P-2", "P-3", "P-4", "P-5"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=sample_validated_dataset, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("allow"),
    )

    assert report.family_metadata_available is False


def test_run_evaluation_records_family_metadata_available_true_under_collapse(
    dataset_with_known_family, sample_policy
):
    ranking_port = FakeRankingPort(fixed_order=["P-A1", "P-A2", "P-B1"])
    runner = DefaultEvaluationRunner()

    report = runner.run_evaluation(
        dataset=dataset_with_known_family, ranking_port=ranking_port,
        policy=sample_policy, context=_family_context("collapse"),
    )

    assert report.family_metadata_available is True
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend && python -m pytest test/unit/application/test_evaluation_runner.py -k "family" -v`
Expected: FAIL — `run_evaluation` doesn't yet call `validate_family_policy_feasible`, doesn't apply any pool transform, and doesn't populate `family_metadata_available` on the report (Pydantic `ValidationError: field required`).

- [ ] **Step 4: Implement `_apply_family_policy` and wire it into `run_evaluation`**

In `backend/src/main/application/evaluation/runner.py`, add right after `validate_family_policy_feasible`:

```python
def _apply_family_policy(family_policy: str, patents: list[EvaluationPatent]) -> list[EvaluationPatent]:
    """ADR 0027 §2/§4: pre-ranking pool transform, mirroring _filter_temporally_eligible_patents's
    placement. Caller must have already called validate_family_policy_feasible -- this function
    assumes family_id is populated on every patent when family_policy != "allow".
    """
    if family_policy == "allow":
        return list(patents)

    if family_policy == "collapse":
        best_by_family: dict[str, EvaluationPatent] = {}
        for p in sorted(patents, key=lambda p: p.publication_id):
            if p.family_id not in best_by_family:
                best_by_family[p.family_id] = p
        return sorted(best_by_family.values(), key=lambda p: p.publication_id)

    # exclude_related
    family_counts: dict[str, int] = {}
    for p in patents:
        family_counts[p.family_id] = family_counts.get(p.family_id, 0) + 1
    return [p for p in patents if family_counts[p.family_id] == 1]
```

Modify `DefaultEvaluationRunner.run_evaluation`: right after `patent_universe = eval_dataset.patents`, add the fail-fast call; inside the per-demand loop, apply the transform after the temporal filter and before ranking; and add `family_metadata_available` to the `EvaluationRunReport(...)` construction:

```python
        # Sealed candidate universe: all patents in the dataset
        patent_universe = eval_dataset.patents

        # ADR 0027: fail fast, once, on the full sealed universe -- before any
        # per-demand work happens -- if the requested policy cannot be honestly
        # applied to this dataset.
        validate_family_policy_feasible(context.family_policy, patent_universe)

        demand_reports: list[DemandMetricsReport] = []

        for eval_demand in eval_dataset.demands:
            d_id = eval_demand.demand_id

            if context.temporal_pool_mode == "strict":
                eligible_patents = _filter_temporally_eligible_patents(eval_demand, patent_universe)
            else:
                eligible_patents = patent_universe

            # ADR 0027: family-policy pool transform, applied after temporal
            # eligibility and before ranking -- same insertion point convention
            # ADR 0018 established for _filter_temporally_eligible_patents.
            eligible_patents = _apply_family_policy(context.family_policy, eligible_patents)

            ranked_ids = ranking_port.rank_candidates(eval_demand, eligible_patents)
```

(the rest of the loop body is unchanged). And in the final `EvaluationRunReport(...)` construction, add:

```python
            macro_denominators=macro_denominators,
            uncertainty_rate=overall_uncertainty_rate,
            family_metadata_available=family_metadata_available(patent_universe),
        )
```

Update the module's import line to include the new names it now calls internally (they're defined in the same file, so no new import statement is needed — `family_metadata_available`, `validate_family_policy_feasible`, and `_apply_family_policy` are all module-level functions already in `runner.py`).

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && python -m pytest test/unit/application/test_evaluation_runner.py -v`
Expected: PASS, full file (all pre-existing tests plus every new one from Tasks 2 and 3).

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/application/evaluation/runner.py backend/test/unit/application/test_evaluation_runner.py
git commit -m "$(cat <<'EOF'
feat(evaluation): wire family-policy pool transform into run_evaluation (ADR 0027)

allow/collapse/exclude_related now actually shape the pre-ranking pool.
run_evaluation fails fast (FAMILY_METADATA_UNAVAILABLE) before any
ranking happens when the requested policy can't be honestly applied to
the sealed dataset. EvaluationRunReport.family_metadata_available is
stamped on every run.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 4: CLI wiring (`--family-policy`)

**Files:**
- Modify: `scripts/run_scientific_evaluation.py` (~line 137-165, wherever `--temporal-pool-mode` is defined and used)
- Modify: `scripts/run_m0_vs_m1_comparison.py` (same pattern)
- Modify: `backend/test/e2e/test_m0_vs_m1_comparison_cli.py` (`_run_cli`, ~line 30-40)

**Interfaces:**
- Consumes: `EvaluationExecutionContext.family_policy` (Task 1).
- Produces: nothing new consumed by later tasks — this is the plan's final task.

- [ ] **Step 1: Add the CLI flag to `scripts/run_scientific_evaluation.py`**

Right after the existing `--temporal-pool-mode` `parser.add_argument(...)` block, add:

```python
    parser.add_argument(
        "--family-policy",
        type=str,
        choices=["allow", "collapse", "exclude_related"],
        required=True,
        dest="family_policy",
        help=(
            "ADR 0027: mandatory, no default (same explicit-injection principle as "
            "--temporal-pool-mode) -- the patent-family policy must always be a "
            "conscious choice. 'allow': no family-based pool changes. 'collapse'/"
            "'exclude_related' require every patent in the dataset to carry a "
            "family_id (ADR 0027 §1: never inferred here) or the run fails fast "
            "with FAMILY_METADATA_UNAVAILABLE."
        ),
    )
```

Then update the `EvaluationExecutionContext(...)` construction (~line 222-229) to add `family_policy=args.family_policy,` after `temporal_pool_mode=args.temporal_pool_mode,`.

- [ ] **Step 2: Add the identical CLI flag to `scripts/run_m0_vs_m1_comparison.py`**

Same `parser.add_argument(...)` block as Step 1, and add `family_policy=args.family_policy,` after `temporal_pool_mode=args.temporal_pool_mode,` in both `EvaluationExecutionContext(...)` constructions in that file (~lines 218-225 build one context reused for both M0 and M1 runs per the file's existing structure — confirm by reading the surrounding function before editing whether it's one shared context or two separate ones, and apply the same one-line addition to each).

- [ ] **Step 3: Update the e2e CLI test**

In `backend/test/e2e/test_m0_vs_m1_comparison_cli.py`, modify `_run_cli`:

```python
def _run_cli(output_dir: Path) -> subprocess.CompletedProcess:
    # ADR 0018: --temporal-pool-mode is mandatory. "strict" is used here (not
    # ...(keep existing comment)...
    return subprocess.run(
        [
            sys.executable, str(_SCRIPT), "--output-dir", str(output_dir),
            "--temporal-pool-mode", "strict",
            "--family-policy", "allow",
        ],
        ...
```

(keep every other argument/kwarg in the existing `subprocess.run(...)` call exactly as-is — only add the two new list items).

- [ ] **Step 4: Run the e2e test to verify it still passes**

Run: `cd backend && python -m pytest test/e2e/test_m0_vs_m1_comparison_cli.py -v`
Expected: PASS. If it fails with an argparse error about `--family-policy` being unrecognized, re-check Step 2 edited the correct script (`test_m0_vs_m1_comparison_cli.py`'s `_SCRIPT` constant names the exact script file being invoked — confirm which one before editing further).

- [ ] **Step 5: Run the full affected test suite one last time**

Run:
```bash
cd backend && python -m pytest \
  test/unit/domain/test_evaluation_protocol_models.py \
  test/unit/application/test_evaluation_runner.py \
  test/unit/application/test_metrics_endpoint.py \
  test/unit/application/evaluation/test_comparative_evaluation.py \
  test/e2e/test_m0_vs_m1_comparison_cli.py \
  -v
```
Expected: PASS, everything green.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_scientific_evaluation.py scripts/run_m0_vs_m1_comparison.py backend/test/e2e/test_m0_vs_m1_comparison_cli.py
git commit -m "$(cat <<'EOF'
feat(evaluation): thread --family-policy through the CLI harness (ADR 0027)

Both evaluation-running scripts now require an explicit --family-policy
flag, mirroring --temporal-pool-mode's mandatory, no-default pattern.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

## Self-Review

**Spec coverage** (against the user's explicit decision this session):
1. `family_policy: allow|collapse|exclude_related`, explicit/versioned/traceable — Task 1 (field + ADR 0027) + Task 4 (CLI).
2. Infrastructure accepts external family metadata, never invents it — Task 1 (`EvaluationPatent.family_id`, accept-only by construction: nothing in Tasks 2-4 computes it).
3. `collapse`/`exclude_related` without metadata → fail-fast, never silent `allow` — Task 2 (`validate_family_policy_feasible`) + Task 3 (wired before ranking).
4. `allow` must be explicit, no implicit default — Task 1 (`family_policy` mandatory, no default value in the Pydantic field).
5. Tests first, covering: known family + collapse, known family + exclude_related, allow (no-op), metadata-absent fail-fast, provenance records policy + metadata availability — all six covered by Task 3's test list plus Task 1's field-contract tests.
6. Out of scope respected — no detector, no heuristic, no new metric, no Product/Observatory/L2/L3 touch anywhere in this plan.

**Placeholder scan:** no TBD/TODO, every step has literal runnable code, every test has real assertions, no "similar to Task N" reuse-by-reference.

**Type consistency:** `family_metadata_available` (module function) vs `EvaluationRunReport.family_metadata_available` (field) intentionally share a name the way `family_policy` (field) and `"family_policy"` (CLI dest) do elsewhere in this codebase's existing `temporal_pool_mode` precedent — verified no collision (the field access is always `report.family_metadata_available`, the function call is always `family_metadata_available(patents)`, never ambiguous at any call site written above). `_apply_family_policy` signature `(family_policy: str, patents: list[EvaluationPatent]) -> list[EvaluationPatent]` is consistent between its Task 3 definition and its one call site.

---

**Plan complete and saved to `docs/superpowers/plans/2026-09-11-family-aware-evaluation-contract.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
