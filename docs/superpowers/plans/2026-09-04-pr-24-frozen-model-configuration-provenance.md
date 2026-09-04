# PR #24: Frozen Model Configuration Provenance (No Tuning) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the current M0–M6 model configurations as-is, with full provenance metadata and an explicit declaration that no independent development set exists and no tuning was performed on the frozen benchmark, producing an integrity-checked (not cryptographically sealed) configuration artifact that PR #25 (ablation) and PR #26 (final inference) can cite without re-litigating epistemic status.

**Architecture:** A single new provenance artifact (`config/evaluations/model_configurations_m0_m6.json`) records, once, the freeze date and tuning status, and per model variant M0–M6, its ranker, weights, version, and provenance category — integrity-checked with the same self-referential SHA-256 pattern already used for `MatchingPolicyConfig.policy_sha256` and `StudyProtocol.protocol_sha256`. This hash is tamper-evident, not a cryptographic seal: real freezing comes from Git history and PR review, not the digest. A new frozen Pydantic model (`ModelConfigurationManifest`, `ModelConfigurationRecord`) in `domain/models/evaluation.py`, using `Literal` types for the closed status fields, machine-checks that the artifact never *declares* a tuned/optimized status — it cannot and does not prevent someone from tuning against the benchmark operationally; that requires process/review, not a Pydantic model. No new tuning code, no dev-set synthesis, no new abstractions, no enforcement machinery for PR #25/#26.

**Tech Stack:** Python 3.12 / Pydantic v2 / pytest.

**Spec:** This plan implements the user's directive of 2026-09-04 ("Opción C — Freeze configurations as-is + provenance, no tuning") and extends ADR 0011's provenance chain with a new ADR 0012.

## Global Constraints

- **No tuning of any kind:** no grid search, no Bayesian optimization, no cross-validation, no optimizing `alpha/beta/gamma` against the frozen benchmark's 3 demands.
- **No synthetic demands presented as evidence, no artificial development set.**
- **Do not modify ADR 0011, the frozen benchmark, or `comparisons_m0_m6.json`.**
- **No new frameworks/abstractions:** no `TuningEngine`, no generic "configuration engine" — a single flat JSON artifact plus one validation model, matching the existing `MatchingPolicyConfig` pattern exactly.
- **Weights are declared `PRE_EXISTING_INITIAL_CONFIGURATION` / `INHERITED` as specified below; `provenance_status` and `tuning_status` are closed at the type level with `Literal`**, not by convention alone. This stops the Pydantic model from accepting `TUNED`/`OPTIMIZED`/`VALIDATED` — it does not stop someone from editing the raw JSON outside the model; that is a review concern, not a type-system one.
- Preserve all 7 Import Linter contracts in `.importlinter`.
- Zero changes to `infrastructure/cli.py` and `landscape/` (ADR 0011 §1).

---

## File Structure

| File | Role |
| :--- | :--- |
| `docs/adr/0012-frozen-model-configuration-provenance.md` | ADR 0012: records the freeze decision, the absence of an independent dev set, and the epistemic status of current weights |
| `config/evaluations/model_configurations_m0_m6.json` | Integrity-checked, self-referentially hashed provenance record for M0–M6 configurations |
| `backend/src/main/domain/models/evaluation.py` | Add `ModelConfigurationRecord`, `ModelConfigurationManifest` (frozen, validated, closed status enums) |
| `backend/test/unit/domain/test_frozen_model_configurations.py` | Guard tests: hash integrity, tamper rejection, closed status enums reject `"TUNED"`/`"OPTIMIZED"`, M6 weights match `default_matching_policy.json` |

---

## Tasks

### Task 1: ADR 0012 — Freeze Decision & Epistemic Status

**Files:**
- Create: `docs/adr/0012-frozen-model-configuration-provenance.md`

**Interfaces:**
- Consumes: ADR 0006, ADR 0007, ADR 0011
- Produces: recorded decision that PR #24 freezes configurations as-is; no dev set exists; PR #25 and PR #26 must treat `model_configurations_m0_m6.json` as the frozen configuration baseline — any change to it requires an explicitly documented new development phase and a superseding ADR (process rule, not automated enforcement — no CI check requiring the literal string "ADR 0012" in a PR body).

- [ ] **Step 1: Write ADR 0012**

```markdown
# ADR 0012: Frozen Model Configuration Provenance (No Tuning)

**Status:** Accepted
**Date:** 2026-09-04
**Scope:** `config/evaluations/model_configurations_m0_m6.json`, `domain/models/evaluation.py`

---

## Context

The frozen benchmark (ADR 0006, ADR 0011) contains exactly 3 annotated demands,
and those same 3 demands constitute the entire frozen inferential benchmark
(PR #23). No independent, unannotated development set exists. Optimizing any
model hyperparameter (e.g. the `HybridRanker` fusion weights `alpha`, `beta`,
`gamma`) against these 3 demands would contaminate the final inferential
evaluation (PR #26): the same data used to select a configuration cannot also
be used to test it.

The current `HybridRanker` weights (`alpha=0.35`, `beta=0.45`, `gamma=0.20`,
`config/policies/matching/default_matching_policy.json`) match the weights
already present in the PR #23 pilot run (`scripts/evaluation/run_pilot_benchmark.py`
labels them "Frozen Pilot-16 heuristic weights"). No evidence of
benchmark-based hyperparameter tuning (grid search, Bayesian optimization,
cross-validation) was identified in a repository audit. Absence of a tuning
harness does not prove tuning never happened by some undocumented means, but
combined with the matching pilot provenance it is the strongest claim this
repository's evidence supports: these are pre-existing initial values, not a
result this team can claim was validated or optimized.

M3 (tripartite evidence assessment), M4 (origin policy resolution), and M5
(multi-agent synthesis) are downstream pipeline stages
(`DefaultEvidenceEvaluator`, `origin_resolver.py`, `synthesis_engine.py`) layered
on top of the same `HybridRanker` output. The codebase defines exactly one
`MatchingPolicyConfig`/`RankerWeights` — there is no per-stage weight
variant for M3, M4, or M5. They inherit M6's weights because there is
nothing else in the code to give them.

## Decision

1. **No development set is created.** Fabricating a synthetic split of the
   3 annotated demands to justify tuning would misrepresent statistical
   power that does not exist. None is created for PR #24 or later.
2. **All M0–M6 configurations are frozen as-is** in
   `config/evaluations/model_configurations_m0_m6.json`, recording once
   (`frozen_at`, `tuning_status`) and per model (ranker, weights where
   applicable, version, provenance category).
3. **Provenance categories are closed to three values:**
   `PRE_EXISTING_INITIAL_CONFIGURATION`, `INHERITED`, `DERIVED`, enforced via
   a `Literal` type on `ModelConfigurationRecord.provenance_status`. The
   values `TUNED`, `OPTIMIZED`, and `VALIDATED` cannot be expressed.
4. **The manifest carries a top-level `tuning_status` field fixed to the
   single `Literal` value `"NOT_TUNED_NO_INDEPENDENT_DEV_SET"`**, so the
   artifact itself states the epistemic boundary rather than relying on
   prose alone.
5. **The artifact is integrity-checked** with a self-referential SHA-256
   (`config_sha256`), following the exact pattern already used for
   `MatchingPolicyConfig.policy_sha256` and `StudyProtocol.protocol_sha256`.
   This detects accidental drift or corruption of the file at load time — it
   is **not** a cryptographic seal: anyone with write access can edit the
   payload and recompute the digest. The `ModelConfigurationManifest` model
   verifies internal consistency of the artifact's *claims*; it cannot
   verify, and does not claim to verify, that no tuning against the
   benchmark ever occurred outside this artifact. That guarantee comes from
   Git history and PR review, not from this file.
6. Should additional annotated demands become available later, tuning may
   be considered in a **new, explicitly named development phase** — never by
   editing this frozen artifact in place.

## Consequences

### Positive
- The final inferential evaluation (PR #26) is defensible: no hyperparameter
  was fit on the data used to test it, and the artifact's own epistemic
  claims are machine-validated rather than asserted only in prose.
- Provenance is explicit per model variant.

### Negative
- `alpha/beta/gamma` may be suboptimal. This is accepted; correctness of the
  evaluation matters more than the score it produces.
- This artifact cannot, by itself, stop someone from tuning against the
  benchmark in a future PR. That risk is managed by review, not tooling.

## Enforcement

A Pull Request is **non-compliant** if it:
1. Sets any M0–M6 provenance status to `TUNED`, `OPTIMIZED`, or `VALIDATED`
   (the `Literal` type makes this a validation error, not a style nit).
2. Changes `tuning_status` away from `"NOT_TUNED_NO_INDEPENDENT_DEV_SET"`
   without a new ADR superseding this one.
3. Introduces a grid search, Bayesian optimization, or cross-validation
   routine that consumes the frozen benchmark.
4. Modifies `config/evaluations/model_configurations_m0_m6.json` weights to
   improve a metric on the frozen benchmark.
```

ADR 0012 is committed together with the manifest and models at the end of
Task 2 (one commit for the docs, one for the code — see Task 2 Step 6). Do
not commit it alone here.

---

### Task 2: Domain Models — `ModelConfigurationRecord` & `ModelConfigurationManifest`

**Files:**
- Modify: `backend/src/main/domain/models/evaluation.py`
- Test: `backend/test/unit/domain/test_frozen_model_configurations.py` (created in this task, extended in Task 4)

**Interfaces:**
- Consumes: nothing new (pure `pydantic.BaseModel`, `field_validator`, `re`, `date` — all already imported at the top of `domain/models/evaluation.py`; add `Literal` from `typing`).
- Produces:
  - `ModelConfigurationRecord(model_id: str, description: str, ranker: str, weights: dict[str, float] | None, version: str, provenance_status: Literal["PRE_EXISTING_INITIAL_CONFIGURATION", "INHERITED", "DERIVED"])`
  - `ModelConfigurationManifest(study_id: str, frozen_at: date, tuning_status: Literal["NOT_TUNED_NO_INDEPENDENT_DEV_SET"], development_set: str | None, models: list[ModelConfigurationRecord], config_sha256: str)`
  - `ModelConfigurationManifest.load_from_json(file_path) -> ModelConfigurationManifest` (self-referential hash verification, same algorithm as `MatchingPolicyConfig.load_from_json` at `domain/models/matching.py:359-393`).

`frozen_at` lives once on the manifest, not per record — all M0–M6 entries are
frozen by the same PR #24 event, so a per-record `date` would be duplicated
data with no distinguishing information.

- [ ] **Step 1: Write the failing tests**

Six tests, each covering one real failure mode (not one per field):

Create `backend/test/unit/domain/test_frozen_model_configurations.py`:

```python
"""Guard tests for ADR 0012: frozen M0-M6 configuration provenance, no tuning."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from domain.models.evaluation import ModelConfigurationManifest, ModelConfigurationRecord
from domain.models.matching import MatchingPolicyConfig


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@pytest.fixture
def manifest_path() -> Path:
    return get_repo_root() / "config" / "evaluations" / "model_configurations_m0_m6.json"


def test_valid_manifest_loads(manifest_path: Path) -> None:
    manifest = ModelConfigurationManifest.load_from_json(manifest_path)
    assert manifest.tuning_status == "NOT_TUNED_NO_INDEPENDENT_DEV_SET"
    assert manifest.development_set is None


def test_frozen_manifest_tamper_rejection(manifest_path: Path, tmp_path: Path) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["models"][0]["version"] = "9.9.9"
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="integrity verification failed"):
        ModelConfigurationManifest.load_from_json(tampered)


def test_invalid_provenance_status_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelConfigurationRecord(
            model_id="M0",
            description="Lexical BM25 baseline",
            ranker="LexicalRanker",
            weights=None,
            version="1.0.0",
            provenance_status="TUNED",
        )


def test_invalid_tuning_status_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelConfigurationManifest(
            study_id="NEXUS-PHASE2-M0-M6-CONFIG-FREEZE",
            frozen_at="2026-09-04",
            tuning_status="TUNED_VIA_GRID_SEARCH",
            development_set=None,
            models=[
                ModelConfigurationRecord(
                    model_id="M0",
                    description="Lexical BM25 baseline",
                    ranker="LexicalRanker",
                    weights=None,
                    version="1.0.0",
                    provenance_status="PRE_EXISTING_INITIAL_CONFIGURATION",
                )
            ],
            config_sha256="0" * 64,
        )


def test_m6_weights_match_default_matching_policy(manifest_path: Path) -> None:
    manifest = ModelConfigurationManifest.load_from_json(manifest_path)
    m6 = next(r for r in manifest.models if r.model_id == "M6")

    policy_path = get_repo_root() / "config" / "policies" / "matching" / "default_matching_policy.json"
    policy = MatchingPolicyConfig.load_from_json(policy_path)

    assert m6.weights == {
        "alpha": policy.weights.alpha,
        "beta": policy.weights.beta,
        "gamma": policy.weights.gamma,
    }
    assert m6.provenance_status == "PRE_EXISTING_INITIAL_CONFIGURATION"


def test_exactly_m0_through_m6_represented(manifest_path: Path) -> None:
    manifest = ModelConfigurationManifest.load_from_json(manifest_path)
    assert {r.model_id for r in manifest.models} == {"M0", "M1", "M2", "M3", "M4", "M5", "M6"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=src/main pytest test/unit/domain/test_frozen_model_configurations.py -v`
Expected: FAIL with `ImportError: cannot import name 'ModelConfigurationManifest'`

- [ ] **Step 3: Add the models to `domain/models/evaluation.py`**

Add `Literal` to the existing `typing` import (or add `from typing import Literal` if
no `typing` import exists yet), then append to the end of
`backend/src/main/domain/models/evaluation.py`:

```python
ProvenanceStatus = Literal[
    "PRE_EXISTING_INITIAL_CONFIGURATION",
    "INHERITED",
    "DERIVED",
]

TuningStatus = Literal["NOT_TUNED_NO_INDEPENDENT_DEV_SET"]


class ModelConfigurationRecord(BaseModel):
    """Frozen, provenance-tagged configuration for a single M0-M6 model variant (ADR 0012).

    provenance_status is closed by the ProvenanceStatus Literal: TUNED / OPTIMIZED /
    VALIDATED cannot be expressed, because no hyperparameter search process exists
    in this codebase to justify those claims.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    ranker: str = Field(min_length=1)
    weights: dict[str, float] | None = None
    version: str = Field(min_length=1)
    provenance_status: ProvenanceStatus


class ModelConfigurationManifest(BaseModel):
    """Integrity-checked freeze record for M0-M6 configurations (ADR 0012).

    config_sha256 is self-referential (verified against the rest of the payload on
    load, same pattern as MatchingPolicyConfig.policy_sha256 in domain/models/matching.py).
    This is tamper-evidence, not a cryptographic seal — it detects accidental drift,
    not deliberate edits made by someone who also updates the hash. The real freeze
    guarantee comes from Git history and PR review.
    """

    model_config = ConfigDict(frozen=True)

    study_id: str = Field(min_length=1)
    frozen_at: date
    tuning_status: TuningStatus
    development_set: str | None
    models: list[ModelConfigurationRecord] = Field(min_length=1)
    config_sha256: str = Field(min_length=64, max_length=64)

    @field_validator("config_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if not re.match(r"^[0-9a-f]{64}$", v.lower()):
            raise ValueError(f"Invalid SHA-256 digest format: {v}")
        return v.lower()

    @classmethod
    def load_from_json(cls, file_path: str) -> "ModelConfigurationManifest":
        import hashlib
        import json as _json
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Model configuration manifest not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            data = _json.load(f)

        declared_sha = data.pop("config_sha256", None)
        if not declared_sha:
            raise ValueError(
                f"Cryptographic integrity verification failed for {path}: "
                f"missing mandatory declared 'config_sha256'"
            )

        canonical_bytes = _json.dumps(data, sort_keys=True, indent=2).encode("utf-8")
        computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

        if declared_sha.lower() != computed_sha.lower():
            raise ValueError(
                f"Cryptographic integrity verification failed for {path}: "
                f"declared {declared_sha}, computed {computed_sha}"
            )

        data["config_sha256"] = computed_sha
        return cls(**data)
```

- [ ] **Step 3.5: Verify against current HEAD before writing the manifest — do not proceed on assumption**

The manifest is a record of facts, not a proposed architecture. Before writing
Step 4's JSON, re-run these checks against the actual working tree (not memory
of an earlier read) and confirm each one:

- [ ] `grep -n "class.*Ranker" backend/src/main/application/matching/rankers.py` — confirms the only ranker classes are `LexicalRanker`, `SemanticRanker`, `CPCRanker`, `HybridRanker` (M0/M1/M2/M6 mapping).
- [ ] `grep -rn "RankerWeights(\|MatchingPolicyConfig" backend/src/main --include=*.py` — confirms there is exactly one weights type and no per-stage (M3/M4/M5) weight configuration in production code.
- [ ] `cat config/policies/matching/default_matching_policy.json | python3 -c "import json,sys; print(json.load(sys.stdin)['weights'])"` — confirms the current `alpha/beta/gamma` values to embed (do not hardcode from memory of this plan).
- [ ] `grep -n "evidence\|origin_resolver\|synthesis_engine" backend/src/main/application/matching/engine.py backend/src/main/application/synthesis/synthesis_engine.py backend/src/main/application/ingestion/origin_resolver.py 2>/dev/null` — confirms M3/M4/M5 are downstream stages, not alternate rankers.
- [ ] `grep -n "0.35\|0.45\|0.20\|0.2" scripts/evaluation/run_pilot_benchmark.py` — confirms the pilot script's weights match the current policy (the ADR's provenance claim).

**If any assertion differs from what this plan states, STOP.** Update the ADR
text, the manifest content, and the provenance/status classifications to
match what is actually in the repo — do not force the pre-written JSON to fit.

- [ ] **Step 4: Create the frozen artifact `config/evaluations/model_configurations_m0_m6.json`**

First write it with `config_sha256` set to `"0" * 64`, then compute and patch in the
real digest (same two-step process as `default_matching_policy.json` and
`comparisons_m0_m6.json` were sealed):

```json
{
  "study_id": "NEXUS-PHASE2-M0-M6-CONFIG-FREEZE",
  "frozen_at": "2026-09-04",
  "tuning_status": "NOT_TUNED_NO_INDEPENDENT_DEV_SET",
  "development_set": null,
  "models": [
    {
      "model_id": "M0",
      "description": "Lexical BM25 baseline",
      "ranker": "LexicalRanker",
      "weights": null,
      "version": "1.0.0",
      "provenance_status": "PRE_EXISTING_INITIAL_CONFIGURATION"
    },
    {
      "model_id": "M1",
      "description": "Dense semantic retrieval",
      "ranker": "SemanticRanker",
      "weights": null,
      "version": "1.0.0",
      "provenance_status": "PRE_EXISTING_INITIAL_CONFIGURATION"
    },
    {
      "model_id": "M2",
      "description": "CPC concordance / structural taxonomy",
      "ranker": "CPCRanker",
      "weights": null,
      "version": "1.0.0",
      "provenance_status": "PRE_EXISTING_INITIAL_CONFIGURATION"
    },
    {
      "model_id": "M3",
      "description": "Tripartite evidence assessment layered on the hybrid-ranked pool (DefaultEvidenceEvaluator); no independent weight config exists for this stage",
      "ranker": "HybridRanker",
      "weights": {"alpha": 0.35, "beta": 0.45, "gamma": 0.2},
      "version": "1.0.0",
      "provenance_status": "INHERITED"
    },
    {
      "model_id": "M4",
      "description": "Origin policy resolution layered on the hybrid-ranked pool (origin_resolver.py); no independent weight config exists for this stage",
      "ranker": "HybridRanker",
      "weights": {"alpha": 0.35, "beta": 0.45, "gamma": 0.2},
      "version": "1.0.0",
      "provenance_status": "INHERITED"
    },
    {
      "model_id": "M5",
      "description": "Multi-agent synthesis (inventor/adversarial agents) layered on the hybrid-ranked pool; no independent weight config exists for this stage",
      "ranker": "HybridRanker",
      "weights": {"alpha": 0.35, "beta": 0.45, "gamma": 0.2},
      "version": "1.0.0",
      "provenance_status": "INHERITED"
    },
    {
      "model_id": "M6",
      "description": "Nexus complete pipeline; uses the frozen HybridRanker weights from default_matching_policy.json",
      "ranker": "HybridRanker",
      "weights": {"alpha": 0.35, "beta": 0.45, "gamma": 0.2},
      "version": "1.0.0",
      "provenance_status": "PRE_EXISTING_INITIAL_CONFIGURATION"
    }
  ],
  "config_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

Compute the real digest and patch it in:

```bash
cd /home/valentin/code/nexus
python3 - <<'EOF'
import hashlib, json
path = "config/evaluations/model_configurations_m0_m6.json"
data = json.load(open(path))
data.pop("config_sha256")
canonical = json.dumps(data, sort_keys=True, indent=2).encode("utf-8")
digest = hashlib.sha256(canonical).hexdigest()
data["config_sha256"] = digest
json.dump(data, open(path, "w"), indent=2)
print(digest)
EOF
```

M3/M4/M5 are marked `INHERITED`, verified against the actual pipeline code
(not assumed): `application/matching/engine.py` and
`test_matching_complete_pipeline_acceptance.py` show only four rankers exist
— `LexicalRanker` (M0), `SemanticRanker` (M1), `CPCRanker` (M2), and
`HybridRanker` (M6's fusion). M3 (`DefaultEvidenceEvaluator`), M4
(`origin_resolver.py`), and M5 (`synthesis_engine.py`) are downstream
pipeline stages that operate on the same hybrid-ranked pool — there is
exactly one `MatchingPolicyConfig`/`RankerWeights` in the codebase, so these
stages inherit M6's weights because there is no other weight configuration
for them to have.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && PYTHONPATH=src/main pytest test/unit/domain/test_frozen_model_configurations.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit — two commits total for this PR**

```bash
git add docs/adr/0012-frozen-model-configuration-provenance.md
git commit -m "$(cat <<'EOF'
docs(adr): record ADR 0012 freezing M0-M6 configurations without tuning

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DxaHkUae6W5HcDjjVeWz4k
EOF
)"

git add backend/src/main/domain/models/evaluation.py \
        backend/test/unit/domain/test_frozen_model_configurations.py \
        config/evaluations/model_configurations_m0_m6.json
git commit -m "$(cat <<'EOF'
feat(evaluation): freeze M0-M6 configuration provenance (ADR 0012)

Adds ModelConfigurationManifest/Record with Literal-closed provenance-status
and tuning-status fields, integrity-checked via self-referential SHA-256
(tamper-evident, not a cryptographic seal — see ADR 0012 §5). M3-M5 are
recorded as INHERITED from M6's weights, verified against
application/matching/engine.py: no per-stage weight config exists in the
pipeline for those variants.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01DxaHkUae6W5HcDjjVeWz4k
EOF
)"
```

---

### Task 3: Quality Gate

**Files:**
- Verify: Ruff, Mypy, Import Linter, full pytest suite

- [ ] **Step 1: Run `ruff check .`**
- [ ] **Step 2: Run `mypy backend/src/main`**
- [ ] **Step 3: Run `python scripts/check_architecture.py && PYTHONPATH=backend/src/main lint-imports`**
- [ ] **Step 4: Run full test pipeline** — `cd backend && PYTHONPATH=src/main pytest`
- [ ] **Step 5: Push branch `feature/frozen-model-configuration-provenance` and open PR #24**

PR description must state explicitly (mirroring the user's own framing):
> No hyperparameter tuning was performed. `alpha=0.35, beta=0.45, gamma=0.20`
> are pre-existing initial values, not tuned/validated/optimized. No
> independent development set exists; none was created. Configurations are
> frozen as-is under ADR 0012 ahead of PR #25 (ablation) and PR #26 (final
> inference).
