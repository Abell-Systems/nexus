# TED Construct-Validity Classifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the validated LLM classifier pipeline (control sample, blind human-labeling export, deterministic classifier, two-gate validation check) that must pass before `ted_mapper.py`'s tautological `has_articulated_technical_problem` can be replaced.

**Architecture:** Pure, unit-tested domain/application logic (boundary-stratum + control-sample construction, the two-gate decision rule) backs thin, assertion-heavy I/O scripts (mirroring this repo's existing `experiments/phase2/generate_dense_blindspot_annotation_batch.py` house style) that read the real 114-candidate population, export blind labeling CSVs, run the LLM classifier, and evaluate the gate decision once human labels exist.

**Tech Stack:** Python 3.12, pydantic (existing `TechnicalProblemClassification`-adjacent domain models), the repo's existing `infrastructure/llm` stack (`LlmClientProtocol`, `GroqClient`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md`

## Global Constraints

Copied verbatim from the spec:

- Three classes: `TECHNICAL_PROBLEM`, `GENERIC_PROCUREMENT`, `EMPTY_INSUFFICIENT` (spec SS3).
- Population: the 114 mapped TED candidates in `data/experiments/phase2_v4/candidates_mapped.json` (72 currently accepted + 42 currently rejected under the broken criterion).
- Boundary stratum formula: `|canonical_word_count(description_text) - 25| <= 10` (spec SS4), computed before inspection, included in full (never sampled down).
- Control sample: full boundary stratum + stratified (accepted/rejected x language) random fill to `target_size=30`, `seed=104` (spec SS5). Explicitly an acceptance gate, **not** a powered estimate of population-level classifier performance.
- Labeling: Valentín + Lydia independently, blind to each other and to any LLM output, adjudicated the same way as the 108-pair gold set (spec SS6).
- LLM classifier: deterministic, `temperature=0.0`, uses the existing `infrastructure/llm` stack, classifies from `description_text` alone (spec SS7).
- Gate A (statistical): recall for `TECHNICAL_PROBLEM` >= 90%, specificity against `GENERIC_PROCUREMENT` >= 90%.
- Gate B (safety, zero-tolerance): zero `GENERIC_PROCUREMENT -> TECHNICAL_PROBLEM` misclassifications within the boundary-stratum subset. A single miss here fails validation regardless of Gate A.
- Decision: both gates pass -> LLM classifies all 114. Either gate fails -> full manual classification of all 114, no LLM in the eligibility path. **No tuning after seeing results** (spec SS8).
- This plan builds the pipeline through the human-labeling stopping point only (spec SS9/SS10, wiring the actual `ted_mapper.py` fix, re-running the eligibility measurement, and correcting ADR 0034, are explicitly **out of scope** for this plan — they depend on real human labels this plan cannot produce, and are a follow-up plan once the gate decision is known).

---

### Task 1: Domain model — classification enum + classifier protocol

**Files:**
- Modify: `backend/src/main/domain/models/corpus_expansion.py` (add new class after `PublicationDateEvidenceType`, around line 150)
- Modify: `backend/test/unit/domain/test_corpus_expansion_models.py` (append tests)
- Create: `backend/src/main/domain/protocols/corpus.py`
- Create: `backend/test/unit/domain/test_corpus_protocol.py`

**Interfaces:**
- Produces: `TechnicalProblemClassification(StrEnum)` with members `TECHNICAL_PROBLEM = "technical_problem"`, `GENERIC_PROCUREMENT = "generic_procurement"`, `EMPTY_INSUFFICIENT = "empty_insufficient"`; `TechnicalProblemClassifierProtocol` with method `classify(self, description_text: str) -> TechnicalProblemClassification`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/test/unit/domain/test_corpus_expansion_models.py`:

```python
def test_technical_problem_classification_has_exactly_three_values():
    from domain.models.corpus_expansion import TechnicalProblemClassification

    assert set(TechnicalProblemClassification) == {
        TechnicalProblemClassification.TECHNICAL_PROBLEM,
        TechnicalProblemClassification.GENERIC_PROCUREMENT,
        TechnicalProblemClassification.EMPTY_INSUFFICIENT,
    }


def test_technical_problem_classification_string_values():
    from domain.models.corpus_expansion import TechnicalProblemClassification

    assert TechnicalProblemClassification.TECHNICAL_PROBLEM == "technical_problem"
    assert TechnicalProblemClassification.GENERIC_PROCUREMENT == "generic_procurement"
    assert TechnicalProblemClassification.EMPTY_INSUFFICIENT == "empty_insufficient"
```

Create `backend/test/unit/domain/test_corpus_protocol.py`:

```python
from domain.models.corpus_expansion import TechnicalProblemClassification
from domain.protocols.corpus import TechnicalProblemClassifierProtocol


def test_technical_problem_classifier_protocol_accepts_conforming_implementation():
    class FakeClassifier:
        def classify(self, description_text: str) -> TechnicalProblemClassification:
            return TechnicalProblemClassification.EMPTY_INSUFFICIENT

    assert isinstance(FakeClassifier(), TechnicalProblemClassifierProtocol)


def test_technical_problem_classifier_protocol_rejects_non_conforming_object():
    class NotAClassifier:
        pass

    assert not isinstance(NotAClassifier(), TechnicalProblemClassifierProtocol)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test/unit/domain/test_corpus_expansion_models.py test/unit/domain/test_corpus_protocol.py -v`
Expected: FAIL — `ImportError: cannot import name 'TechnicalProblemClassification'` and `ModuleNotFoundError: No module named 'domain.protocols.corpus'`

- [ ] **Step 3: Write minimal implementation**

In `backend/src/main/domain/models/corpus_expansion.py`, immediately after the `PublicationDateEvidenceType` class definition (around line 150, before `PublicationDateEvidence`):

```python
class TechnicalProblemClassification(StrEnum):
    """Three-way classification of whether description text articulates a genuine
    technical problem, per docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
    SS3."""

    TECHNICAL_PROBLEM = "technical_problem"
    GENERIC_PROCUREMENT = "generic_procurement"
    EMPTY_INSUFFICIENT = "empty_insufficient"
```

Create `backend/src/main/domain/protocols/corpus.py`:

```python
"""Domain protocol for TED construct-eligibility text classification, per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md."""

from typing import Protocol, runtime_checkable

from domain.models.corpus_expansion import TechnicalProblemClassification


@runtime_checkable
class TechnicalProblemClassifierProtocol(Protocol):
    """Classifies whether a candidate's description text articulates a genuine
    technical problem (spec SS3), a generic procurement/scope description, or is
    empty/insufficient."""

    def classify(self, description_text: str) -> TechnicalProblemClassification:
        ...  # pragma: no cover
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test/unit/domain/test_corpus_expansion_models.py test/unit/domain/test_corpus_protocol.py -v`
Expected: PASS (all tests in both files)

- [ ] **Step 5: Run full backend suite to confirm no regression**

Run: `cd backend && python -m pytest test/ -q`
Expected: all previously-passing tests still pass (no count regression)

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/domain/models/corpus_expansion.py backend/src/main/domain/protocols/corpus.py backend/test/unit/domain/test_corpus_expansion_models.py backend/test/unit/domain/test_corpus_protocol.py
git commit -m "feat(domain): add TechnicalProblemClassification and classifier protocol

Domain model for the validated TED construct-eligibility classifier
(docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md).
Three-way classification (TECHNICAL_PROBLEM/GENERIC_PROCUREMENT/
EMPTY_INSUFFICIENT) and the protocol later infrastructure/application
code implements or consumes -- no eligibility logic changes yet.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 2: Boundary-stratum and control-sample construction (pure)

**Files:**
- Create: `backend/src/main/application/corpus/boundary_stratum.py`
- Test: `backend/test/unit/application/corpus/test_boundary_stratum.py`

**Interfaces:**
- Produces: `is_boundary_case(word_count: int, min_word_count: int, tolerance: int = 10) -> bool`; `ControlSample` (frozen dataclass with `boundary_ids: tuple[str, ...]`, `fill_ids: tuple[str, ...]`, property `all_ids -> tuple[str, ...]`); `build_control_sample(candidates: list[dict], min_word_count: int, target_size: int, seed: int, tolerance: int = 10) -> ControlSample`. Each candidate dict requires keys `"demand_id"`, `"word_count"`, `"status"`, `"language_code"`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/test/unit/application/corpus/test_boundary_stratum.py
import pytest

from application.corpus.boundary_stratum import build_control_sample, is_boundary_case


def test_is_boundary_case_true_within_tolerance():
    assert is_boundary_case(word_count=20, min_word_count=25, tolerance=10) is True
    assert is_boundary_case(word_count=35, min_word_count=25, tolerance=10) is True
    assert is_boundary_case(word_count=15, min_word_count=25, tolerance=10) is True


def test_is_boundary_case_false_outside_tolerance():
    assert is_boundary_case(word_count=14, min_word_count=25, tolerance=10) is False
    assert is_boundary_case(word_count=36, min_word_count=25, tolerance=10) is False


def test_build_control_sample_includes_full_boundary_stratum():
    candidates = [
        {"demand_id": "b1", "word_count": 20, "status": "accepted", "language_code": "en"},
        {"demand_id": "b2", "word_count": 30, "status": "rejected", "language_code": "de"},
    ] + [
        {"demand_id": f"r{i}", "word_count": 100, "status": "accepted", "language_code": "en"}
        for i in range(10)
    ]
    sample = build_control_sample(candidates, min_word_count=25, target_size=5, seed=1)
    assert set(sample.boundary_ids) == {"b1", "b2"}
    assert len(sample.fill_ids) == 3
    assert len(set(sample.all_ids)) == 5


def test_build_control_sample_raises_when_target_smaller_than_boundary():
    candidates = [
        {"demand_id": "b1", "word_count": 20, "status": "accepted", "language_code": "en"},
        {"demand_id": "b2", "word_count": 30, "status": "rejected", "language_code": "de"},
    ]
    with pytest.raises(ValueError):
        build_control_sample(candidates, min_word_count=25, target_size=1, seed=1)


def test_build_control_sample_is_deterministic_regardless_of_input_order():
    candidates = [
        {
            "demand_id": f"r{i}",
            "word_count": 100,
            "status": "accepted" if i % 2 == 0 else "rejected",
            "language_code": "en" if i % 3 else "de",
        }
        for i in range(20)
    ]
    s1 = build_control_sample(candidates, min_word_count=25, target_size=10, seed=7)
    s2 = build_control_sample(list(reversed(candidates)), min_word_count=25, target_size=10, seed=7)
    assert s1 == s2


def test_build_control_sample_raises_when_not_enough_candidates():
    candidates = [
        {"demand_id": "r1", "word_count": 100, "status": "accepted", "language_code": "en"},
    ]
    with pytest.raises(ValueError):
        build_control_sample(candidates, min_word_count=25, target_size=5, seed=1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test/unit/application/corpus/test_boundary_stratum.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'application.corpus.boundary_stratum'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/main/application/corpus/boundary_stratum.py
"""Boundary-stratum and control-sample construction for the TED construct-validity
classifier validation, per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS4/SS5. Pure logic, no I/O."""

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class ControlSample:
    boundary_ids: tuple[str, ...]
    fill_ids: tuple[str, ...]

    @property
    def all_ids(self) -> tuple[str, ...]:
        return self.boundary_ids + self.fill_ids


def is_boundary_case(word_count: int, min_word_count: int, tolerance: int = 10) -> bool:
    """SS4: |word_count - min_word_count| <= tolerance."""
    return abs(word_count - min_word_count) <= tolerance


def build_control_sample(
    candidates: list[dict],
    min_word_count: int,
    target_size: int,
    seed: int,
    tolerance: int = 10,
) -> ControlSample:
    """SS5: the full boundary stratum plus a stratified (status x language) random
    fill up to target_size, drawn only from non-boundary candidates. Deterministic
    regardless of the input list's ordering."""
    boundary = sorted(
        c["demand_id"] for c in candidates if is_boundary_case(c["word_count"], min_word_count, tolerance)
    )
    boundary_set = set(boundary)
    remainder = [c for c in candidates if c["demand_id"] not in boundary_set]

    if target_size < len(boundary):
        raise ValueError(
            f"target_size={target_size} is smaller than the boundary stratum ({len(boundary)}); "
            "the boundary stratum is never truncated"
        )
    fill_n = target_size - len(boundary)

    strata: dict[tuple[str, str], list[str]] = {}
    for c in remainder:
        key = (c["status"], c["language_code"])
        strata.setdefault(key, []).append(c["demand_id"])

    rng = random.Random(seed)
    shuffled: dict[tuple[str, str], list[str]] = {}
    for key in sorted(strata):
        ids = sorted(strata[key])
        shuffled[key] = rng.sample(ids, len(ids))

    fill: list[str] = []
    stratum_keys = sorted(strata)
    idx = 0
    while len(fill) < fill_n:
        progressed = False
        for key in stratum_keys:
            if idx < len(shuffled[key]):
                fill.append(shuffled[key][idx])
                progressed = True
                if len(fill) == fill_n:
                    break
        if not progressed:
            break
        idx += 1

    if len(fill) < fill_n:
        raise ValueError(
            f"Not enough non-boundary candidates to fill target_size={target_size} "
            f"(boundary={len(boundary)}, needed fill={fill_n}, only found {len(fill)})"
        )

    return ControlSample(boundary_ids=tuple(boundary), fill_ids=tuple(fill))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test/unit/application/corpus/test_boundary_stratum.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/application/corpus/boundary_stratum.py backend/test/unit/application/corpus/test_boundary_stratum.py
git commit -m "feat(application): boundary-stratum and control-sample construction

Pure implementation of spec SS4 (boundary formula) and SS5 (control
sample: full boundary stratum + stratified deterministic fill to
target_size). No I/O -- consumed by the manifest-generation script.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 3: LLM classifier (infrastructure)

**Files:**
- Create: `backend/src/main/infrastructure/llm/technical_problem_classifier.py`
- Test: `backend/test/unit/infrastructure/llm/test_technical_problem_classifier.py`

**Interfaces:**
- Consumes: `domain.models.corpus_expansion.TechnicalProblemClassification` (Task 1), `domain.protocols.corpus.TechnicalProblemClassifierProtocol` (Task 1), `infrastructure.llm.client_protocol.{LlmChatMessage, LlmChatRequest, LlmChatResponse, LlmClientProtocol}` (existing).
- Produces: `LlmTechnicalProblemClassifier(llm_client: LlmClientProtocol)` with method `classify(self, description_text: str) -> TechnicalProblemClassification`, implementing `TechnicalProblemClassifierProtocol`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/test/unit/infrastructure/llm/test_technical_problem_classifier.py
import json
from unittest.mock import MagicMock

import pytest

from domain.models.corpus_expansion import TechnicalProblemClassification
from domain.protocols.corpus import TechnicalProblemClassifierProtocol
from infrastructure.llm.client_protocol import LlmChatResponse
from infrastructure.llm.technical_problem_classifier import LlmTechnicalProblemClassifier


def _mock_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat_completion.return_value = LlmChatResponse(content=content, model="test")
    return client


def test_classify_returns_technical_problem():
    client = _mock_client(json.dumps({"classification": "TECHNICAL_PROBLEM"}))
    classifier = LlmTechnicalProblemClassifier(client)
    assert classifier.classify("some description") == TechnicalProblemClassification.TECHNICAL_PROBLEM


def test_classify_returns_generic_procurement():
    client = _mock_client(json.dumps({"classification": "GENERIC_PROCUREMENT"}))
    classifier = LlmTechnicalProblemClassifier(client)
    assert classifier.classify("some description") == TechnicalProblemClassification.GENERIC_PROCUREMENT


def test_classify_uses_temperature_zero():
    client = _mock_client(json.dumps({"classification": "EMPTY_INSUFFICIENT"}))
    classifier = LlmTechnicalProblemClassifier(client)
    classifier.classify("x")
    request = client.chat_completion.call_args[0][0]
    assert request.temperature == 0.0


def test_classify_raises_on_malformed_json():
    client = _mock_client("not json")
    classifier = LlmTechnicalProblemClassifier(client)
    with pytest.raises(ValueError):
        classifier.classify("x")


def test_classify_raises_on_unknown_label():
    client = _mock_client(json.dumps({"classification": "MAYBE"}))
    classifier = LlmTechnicalProblemClassifier(client)
    with pytest.raises(ValueError):
        classifier.classify("x")


def test_classifier_conforms_to_protocol():
    client = _mock_client(json.dumps({"classification": "TECHNICAL_PROBLEM"}))
    classifier = LlmTechnicalProblemClassifier(client)
    assert isinstance(classifier, TechnicalProblemClassifierProtocol)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test/unit/infrastructure/llm/test_technical_problem_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.llm.technical_problem_classifier'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/main/infrastructure/llm/technical_problem_classifier.py
"""LLM-backed implementation of TechnicalProblemClassifierProtocol, per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md SS7."""

import json

from domain.models.corpus_expansion import TechnicalProblemClassification
from infrastructure.llm.client_protocol import LlmChatMessage, LlmChatRequest, LlmClientProtocol

_CLASS_DEFINITIONS_PROMPT = """Classify the following public tender description into exactly one of three categories:

TECHNICAL_PROBLEM: the description articulates a specific technical, scientific, or engineering challenge, need, or capability gap that a solution is being sought for -- it describes what is technically difficult or unsolved.

GENERIC_PROCUREMENT: the description specifies a scope of work, deliverable, standard/certification to follow, quantity, or administrative/contractual term, without articulating an underlying technical problem -- it reads as "what to buy/deliver," not "what technical difficulty needs solving."

EMPTY_INSUFFICIENT: the description is empty, near-empty, or so minimal/boilerplate that no meaningful judgment can be made either way.

Respond ONLY in valid JSON matching: {"classification": "TECHNICAL_PROBLEM" | "GENERIC_PROCUREMENT" | "EMPTY_INSUFFICIENT"}"""

_LABEL_TO_CLASSIFICATION = {
    "TECHNICAL_PROBLEM": TechnicalProblemClassification.TECHNICAL_PROBLEM,
    "GENERIC_PROCUREMENT": TechnicalProblemClassification.GENERIC_PROCUREMENT,
    "EMPTY_INSUFFICIENT": TechnicalProblemClassification.EMPTY_INSUFFICIENT,
}


class LlmTechnicalProblemClassifier:
    """Deterministic (temperature=0) classifier per spec SS7. Implements
    TechnicalProblemClassifierProtocol structurally (no explicit inheritance needed --
    the protocol is runtime_checkable)."""

    def __init__(self, llm_client: LlmClientProtocol) -> None:
        self.client = llm_client

    def classify(self, description_text: str) -> TechnicalProblemClassification:
        request = LlmChatRequest(
            messages=[
                LlmChatMessage(role="system", content=_CLASS_DEFINITIONS_PROMPT),
                LlmChatMessage(role="user", content=description_text),
            ],
            temperature=0.0,
            response_format="json_object",
        )
        response = self.client.chat_completion(request)
        try:
            payload = json.loads(response.content)
            label = str(payload["classification"]).strip().upper()
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"Malformed classifier response: {response.content!r}") from exc

        if label not in _LABEL_TO_CLASSIFICATION:
            raise ValueError(f"Unknown classification label from LLM: {label!r}")
        return _LABEL_TO_CLASSIFICATION[label]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test/unit/infrastructure/llm/test_technical_problem_classifier.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/llm/technical_problem_classifier.py backend/test/unit/infrastructure/llm/test_technical_problem_classifier.py
git commit -m "feat(infrastructure): deterministic LLM technical-problem classifier

Implements TechnicalProblemClassifierProtocol using the existing
infrastructure/llm stack (LlmClientProtocol/LlmChatRequest),
temperature=0, class definitions from spec SS3 embedded verbatim in
the prompt. Raises rather than guessing on malformed/unknown output.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 4: Two-gate validation check (pure)

**Files:**
- Create: `backend/src/main/application/corpus/validation_gate.py`
- Test: `backend/test/unit/application/corpus/test_validation_gate.py`

**Interfaces:**
- Consumes: `domain.models.corpus_expansion.TechnicalProblemClassification` (Task 1).
- Produces: `GateResult` (frozen dataclass: `passed: bool`, `recall_technical_problem: float`, `specificity_generic_procurement: float`, `boundary_false_positives: tuple[str, ...]`, `reason: str`); `evaluate_validation_gate(reference_labels: dict[str, TechnicalProblemClassification], llm_labels: dict[str, TechnicalProblemClassification], boundary_ids: frozenset[str], *, recall_threshold: float = 0.90, specificity_threshold: float = 0.90) -> GateResult`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/test/unit/application/corpus/test_validation_gate.py
import pytest

from application.corpus.validation_gate import evaluate_validation_gate
from domain.models.corpus_expansion import TechnicalProblemClassification as C


def test_gate_passes_when_recall_specificity_and_boundary_all_clean():
    reference = {
        "a": C.TECHNICAL_PROBLEM, "b": C.TECHNICAL_PROBLEM,
        "c": C.GENERIC_PROCUREMENT, "d": C.GENERIC_PROCUREMENT,
    }
    llm = dict(reference)
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset({"c"}))
    assert result.passed is True
    assert result.recall_technical_problem == 1.0
    assert result.specificity_generic_procurement == 1.0
    assert result.boundary_false_positives == ()


def test_gate_fails_on_low_recall():
    reference = {"a": C.TECHNICAL_PROBLEM, "b": C.TECHNICAL_PROBLEM}
    llm = {"a": C.GENERIC_PROCUREMENT, "b": C.TECHNICAL_PROBLEM}
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset())
    assert result.passed is False
    assert result.recall_technical_problem == 0.5


def test_gate_b_fails_on_boundary_false_positive_even_with_perfect_aggregate_stats():
    reference = {"a": C.TECHNICAL_PROBLEM, "b": C.GENERIC_PROCUREMENT}
    llm = {"a": C.TECHNICAL_PROBLEM, "b": C.TECHNICAL_PROBLEM}
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset({"b"}))
    assert result.passed is False
    assert result.boundary_false_positives == ("b",)


def test_non_boundary_false_positive_hurts_specificity_but_not_boundary_gate():
    reference = {"a": C.TECHNICAL_PROBLEM, "b": C.GENERIC_PROCUREMENT}
    llm = {"a": C.TECHNICAL_PROBLEM, "b": C.TECHNICAL_PROBLEM}
    result = evaluate_validation_gate(reference, llm, boundary_ids=frozenset())
    assert result.boundary_false_positives == ()
    assert result.specificity_generic_procurement == 0.0
    assert result.passed is False


def test_evaluate_validation_gate_raises_on_mismatched_keys():
    reference = {"a": C.TECHNICAL_PROBLEM}
    llm = {"b": C.TECHNICAL_PROBLEM}
    with pytest.raises(ValueError):
        evaluate_validation_gate(reference, llm, boundary_ids=frozenset())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test/unit/application/corpus/test_validation_gate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'application.corpus.validation_gate'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/main/application/corpus/validation_gate.py
"""Two-gate validation check for the TED construct-validity classifier, per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS8. Pure logic, no I/O."""

from dataclasses import dataclass

from domain.models.corpus_expansion import TechnicalProblemClassification


@dataclass(frozen=True)
class GateResult:
    passed: bool
    recall_technical_problem: float
    specificity_generic_procurement: float
    boundary_false_positives: tuple[str, ...]
    reason: str


def evaluate_validation_gate(
    reference_labels: dict[str, TechnicalProblemClassification],
    llm_labels: dict[str, TechnicalProblemClassification],
    boundary_ids: frozenset[str],
    *,
    recall_threshold: float = 0.90,
    specificity_threshold: float = 0.90,
) -> GateResult:
    """Gate A (statistical recall/specificity >= thresholds) AND Gate B (zero
    GENERIC_PROCUREMENT -> TECHNICAL_PROBLEM misclassifications within
    boundary_ids). Both must pass for the overall result to pass."""
    if set(reference_labels) != set(llm_labels):
        raise ValueError("reference_labels and llm_labels must cover the same demand_ids")

    tp_ids = {d for d, c in reference_labels.items() if c == TechnicalProblemClassification.TECHNICAL_PROBLEM}
    gp_ids = {d for d, c in reference_labels.items() if c == TechnicalProblemClassification.GENERIC_PROCUREMENT}

    recall = (
        sum(1 for d in tp_ids if llm_labels[d] == TechnicalProblemClassification.TECHNICAL_PROBLEM) / len(tp_ids)
        if tp_ids else 1.0
    )
    specificity = (
        sum(1 for d in gp_ids if llm_labels[d] != TechnicalProblemClassification.TECHNICAL_PROBLEM) / len(gp_ids)
        if gp_ids else 1.0
    )

    boundary_false_positives = tuple(sorted(
        d for d in gp_ids
        if d in boundary_ids and llm_labels[d] == TechnicalProblemClassification.TECHNICAL_PROBLEM
    ))

    gate_a = recall >= recall_threshold and specificity >= specificity_threshold
    gate_b = len(boundary_false_positives) == 0

    if gate_a and gate_b:
        reason = "Both gates passed: classifier approved for full-population classification."
    elif not gate_b:
        reason = (
            f"Gate B (boundary safety) failed: {len(boundary_false_positives)} "
            f"GENERIC_PROCUREMENT boundary case(s) misclassified as TECHNICAL_PROBLEM: "
            f"{list(boundary_false_positives)}. Escalate to full manual classification."
        )
    else:
        reason = (
            f"Gate A (statistical) failed: recall={recall:.3f} (threshold {recall_threshold}), "
            f"specificity={specificity:.3f} (threshold {specificity_threshold}). "
            "Escalate to full manual classification."
        )

    return GateResult(
        passed=gate_a and gate_b,
        recall_technical_problem=recall,
        specificity_generic_procurement=specificity,
        boundary_false_positives=boundary_false_positives,
        reason=reason,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test/unit/application/corpus/test_validation_gate.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/application/corpus/validation_gate.py backend/test/unit/application/corpus/test_validation_gate.py
git commit -m "feat(application): two-gate validation check for construct-validity classifier

Pure implementation of spec SS8: Gate A (statistical recall/
specificity >= 90%) and Gate B (zero-tolerance boundary safety gate),
evaluated separately and combined per the pre-registered decision
rule. No I/O -- consumed by the gate-check script.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 5: Control-sample manifest generation script

**Files:**
- Create: `experiments/phase2/build_ted_construct_validity_control_sample.py`

**Interfaces:**
- Consumes: `application.corpus.boundary_stratum.build_control_sample` (Task 2), `domain.models.corpus_expansion.calculate_canonical_word_count` (existing).
- Produces: `data/annotations/ted_construct_validity_control_sample_manifest.json` (+`.sha256`), shape `{"all_ids": [...], "boundary_ids": [...], "fill_ids": [...], "n_boundary": int, "n_fill": int, ...}`, consumed by Tasks 6-8.

- [ ] **Step 1: Write the script**

```python
# experiments/phase2/build_ted_construct_validity_control_sample.py
"""TED construct-validity classifier, step 1: control-sample construction.

Per docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS4/SS5. Reads the frozen 114-candidate mapped population verbatim (no
re-mapping), computes the boundary stratum and a stratified fill to n=30,
writes a manifest for the blind labeling export (step 2) and LLM
classification run (step 3).
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.corpus.boundary_stratum import build_control_sample  # noqa: E402
from domain.models.corpus_expansion import calculate_canonical_word_count  # noqa: E402

MIN_WORD_COUNT = 25
TOLERANCE = 10
TARGET_SIZE = 30
SEED = 104


def generate(mapped_path: Path, accepted_path: Path, out_path: Path) -> dict[str, Any]:
    mapped = json.loads(mapped_path.read_text(encoding="utf-8"))
    accepted_ids = {c["demand_id"] for c in json.loads(accepted_path.read_text(encoding="utf-8"))}

    if len(mapped) != 114:
        raise ValueError(f"Expected 114 mapped candidates, found {len(mapped)}")

    candidates = [
        {
            "demand_id": c["demand_id"],
            "word_count": calculate_canonical_word_count(c["description_text"]),
            "status": "accepted" if c["demand_id"] in accepted_ids else "rejected",
            "language_code": c["language_code"],
        }
        for c in mapped
    ]

    sample = build_control_sample(
        candidates, min_word_count=MIN_WORD_COUNT, target_size=TARGET_SIZE, seed=SEED, tolerance=TOLERANCE
    )

    if len(sample.all_ids) != TARGET_SIZE:
        raise ValueError(f"Expected {TARGET_SIZE} total control-sample ids, got {len(sample.all_ids)}")
    if len(set(sample.all_ids)) != TARGET_SIZE:
        raise ValueError("Control sample contains duplicate demand_ids")

    mapped_bytes = mapped_path.read_bytes()
    out = {
        "dataset_id": "nexus-ted-construct-validity-control-sample-v1",
        "purpose": "TED construct-validity classifier control sample -- "
                   "docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md",
        "source_mapped_candidates_path": str(mapped_path.relative_to(REPO_ROOT)),
        "source_mapped_candidates_sha256": hashlib.sha256(mapped_bytes).hexdigest(),
        "min_word_count": MIN_WORD_COUNT,
        "boundary_tolerance": TOLERANCE,
        "target_size": TARGET_SIZE,
        "seed": SEED,
        "n_boundary": len(sample.boundary_ids),
        "n_fill": len(sample.fill_ids),
        "boundary_ids": list(sample.boundary_ids),
        "fill_ids": list(sample.fill_ids),
        "all_ids": sorted(sample.all_ids),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote {TARGET_SIZE} control-sample ids ({out['n_boundary']} boundary / {out['n_fill']} fill) to {out_path}")
    return out


def main() -> int:
    generate(
        mapped_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "candidates_mapped.json",
        accepted_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "candidates_accepted.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_control_sample_manifest.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `python experiments/phase2/build_ted_construct_validity_control_sample.py`
Expected: prints `Wrote 30 control-sample ids (N boundary / M fill) to .../ted_construct_validity_control_sample_manifest.json`, exit 0. Note the actual boundary/fill split from the real data — record it, don't guess it in advance.

- [ ] **Step 3: Verify by hand**

```bash
python3 -c "
import json
m = json.load(open('data/annotations/ted_construct_validity_control_sample_manifest.json'))
assert m['n_boundary'] + m['n_fill'] == 30
assert len(m['all_ids']) == 30
assert len(set(m['all_ids'])) == 30
assert set(m['boundary_ids']).isdisjoint(set(m['fill_ids']))
print('manifest verified:', m['n_boundary'], 'boundary /', m['n_fill'], 'fill')
"
```

Expected: prints the verified counts, no assertion errors.

- [ ] **Step 4: Commit**

```bash
git add experiments/phase2/build_ted_construct_validity_control_sample.py data/annotations/ted_construct_validity_control_sample_manifest.json data/annotations/ted_construct_validity_control_sample_manifest.sha256
git commit -m "feat(matching): generate TED construct-validity control sample manifest

Computes the boundary stratum (|words-25|<=10) over the real
114-candidate mapped population and a seed=104 stratified fill to 30,
via the pure boundary_stratum module. Manifest feeds the blind
labeling export and the LLM classification run.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 6: Blind labeling CSV export

**Files:**
- Create: `scripts/export_ted_construct_validity_labeling_csv.py`

**Interfaces:**
- Consumes: `data/annotations/ted_construct_validity_control_sample_manifest.json` (Task 5, `all_ids`), `data/experiments/phase2_v4/candidates_mapped.json` (`description_text`, `language_code` per `demand_id`).
- Produces: `data/annotations/ted_construct_validity_labeling_{template,valentin,lydia}.csv`.

- [ ] **Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Exports the TED construct-validity control sample (JSON manifest) to flat CSV
templates for blind human labeling -- demand_id, description_text, language_code,
judgment (blank). Writes three identical blank copies: template, valentin, lydia.
Annotators label TECHNICAL_PROBLEM / GENERIC_PROCUREMENT / EMPTY_INSUFFICIENT per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md SS3,
independently, blind to each other and to any LLM output."""

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIELDNAMES = ["demand_id", "description_text", "language_code", "judgment"]


def main() -> int:
    manifest_path = REPO_ROOT / "data" / "annotations" / "ted_construct_validity_control_sample_manifest.json"
    mapped_path = REPO_ROOT / "data" / "experiments" / "phase2_v4" / "candidates_mapped.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mapped_by_id = {c["demand_id"]: c for c in json.loads(mapped_path.read_text(encoding="utf-8"))}

    rows = []
    for demand_id in manifest["all_ids"]:
        c = mapped_by_id[demand_id]
        rows.append({
            "demand_id": demand_id,
            "description_text": c["description_text"],
            "language_code": c["language_code"],
            "judgment": "",
        })

    for suffix in ("template", "valentin", "lydia"):
        out_path = REPO_ROOT / "data" / "annotations" / f"ted_construct_validity_labeling_{suffix}.csv"
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `python scripts/export_ted_construct_validity_labeling_csv.py`
Expected: prints three `Wrote 30 rows to ...` lines, exit 0.

- [ ] **Step 3: Verify row counts**

```bash
for f in template valentin lydia; do
  n=$(($(wc -l < "data/annotations/ted_construct_validity_labeling_${f}.csv") - 1))
  echo "$f: $n data rows"
  test "$n" -eq 30 || { echo "FAIL: expected 30"; exit 1; }
done
```

Expected: `template: 30 data rows`, `valentin: 30 data rows`, `lydia: 30 data rows`, no FAIL.

- [ ] **Step 4: Commit**

```bash
git add scripts/export_ted_construct_validity_labeling_csv.py data/annotations/ted_construct_validity_labeling_template.csv data/annotations/ted_construct_validity_labeling_valentin.csv data/annotations/ted_construct_validity_labeling_lydia.csv
git commit -m "feat(matching): export blank CSVs for TED construct-validity control-sample labeling

Three identical blank copies (template/valentin/lydia), 30 rows each,
for independent blind labeling into TECHNICAL_PROBLEM/
GENERIC_PROCUREMENT/EMPTY_INSUFFICIENT.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

---

### Task 7: LLM classification run against the control sample

**Files:**
- Create: `experiments/phase2/run_ted_construct_validity_llm_classification.py`

**Interfaces:**
- Consumes: `infrastructure.llm.technical_problem_classifier.LlmTechnicalProblemClassifier` (Task 3), `infrastructure.llm.groq_client.GroqClient` (existing), `data/annotations/ted_construct_validity_control_sample_manifest.json` (Task 5).
- Produces: `data/annotations/ted_construct_validity_llm_classification.json` (+`.sha256`), shape `{"classifications": {demand_id: "technical_problem"|"generic_procurement"|"empty_insufficient"}, ...}`, consumed by Task 8.

**Note before starting:** this script makes real LLM API calls via `GroqClient`, which needs valid credentials/network reachability (see `infrastructure/llm/provider_config.py` for how it reads its API key). If the execution environment has no such credentials or network access, running this script will fail for that reason — report it exactly as that (a real external constraint, per this project's established discipline of disclosing rather than working around blocked infrastructure), not as a code defect, and do not fabricate or hand-write a fake classification output to make the step "pass."

- [ ] **Step 1: Write the script**

```python
# experiments/phase2/run_ted_construct_validity_llm_classification.py
"""TED construct-validity classifier, step 3: LLM classification of the control sample.

Per docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS7. Classifies the same 30 control-sample candidates the blind labeling CSVs
cover, using LlmTechnicalProblemClassifier -- blind to any human label (reads
only description_text)."""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from infrastructure.llm.groq_client import GroqClient  # noqa: E402
from infrastructure.llm.technical_problem_classifier import LlmTechnicalProblemClassifier  # noqa: E402


def generate(manifest_path: Path, mapped_path: Path, out_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mapped_by_id = {c["demand_id"]: c for c in json.loads(mapped_path.read_text(encoding="utf-8"))}

    classifier = LlmTechnicalProblemClassifier(GroqClient())

    results: dict[str, str] = {}
    for demand_id in manifest["all_ids"]:
        description = mapped_by_id[demand_id]["description_text"]
        results[demand_id] = classifier.classify(description).value

    if set(results) != set(manifest["all_ids"]):
        raise ValueError("LLM classification did not cover exactly the control sample's ids")

    out = {
        "dataset_id": "nexus-ted-construct-validity-llm-classification-v1",
        "purpose": "TED construct-validity classifier LLM run against the control sample -- "
                   "docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md",
        "source_manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
        "source_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "classifier": "LlmTechnicalProblemClassifier",
        "temperature": 0.0,
        "classifications": results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote {len(results)} LLM classifications to {out_path}")
    return out


def main() -> int:
    generate(
        manifest_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_control_sample_manifest.json",
        mapped_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "candidates_mapped.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_llm_classification.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `python experiments/phase2/run_ted_construct_validity_llm_classification.py`
Expected (credentials/network available): prints `Wrote 30 LLM classifications to .../ted_construct_validity_llm_classification.json`, exit 0.
Expected (credentials/network unavailable): a clear connection/auth error from `GroqClient`/`httpx` — report this as BLOCKED (real external constraint), stop, do not proceed to Step 3/4 with fabricated data.

- [ ] **Step 3: Verify by hand (only if Step 2 succeeded)**

```bash
python3 -c "
import json
d = json.load(open('data/annotations/ted_construct_validity_llm_classification.json'))
assert len(d['classifications']) == 30
assert set(d['classifications'].values()) <= {'technical_problem', 'generic_procurement', 'empty_insufficient'}
print('LLM classification file verified: 30 entries, values in the expected set')
"
```

- [ ] **Step 4: Commit (only if Step 2 succeeded)**

```bash
git add experiments/phase2/run_ted_construct_validity_llm_classification.py data/annotations/ted_construct_validity_llm_classification.json data/annotations/ted_construct_validity_llm_classification.sha256
git commit -m "feat(matching): run LLM classification over the TED construct-validity control sample

Classifies the 30 control-sample candidates via LlmTechnicalProblemClassifier,
blind to any human label. Feeds the two-gate validation check.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```

If Step 2 was BLOCKED, commit only the script itself (`experiments/phase2/run_ted_construct_validity_llm_classification.py`), with a commit message stating plainly that the run was not executed due to the external constraint encountered, and report this clearly rather than proceeding to Task 8.

---

### Task 8: Validation-gate check and stopping-point results doc

**Files:**
- Create: `experiments/phase2/evaluate_ted_construct_validity_gate.py`
- Create: `docs/ted-construct-validity-classifier-results.md`

**Interfaces:**
- Consumes: `application.corpus.validation_gate.evaluate_validation_gate` (Task 4), `domain.models.corpus_expansion.TechnicalProblemClassification` (Task 1), `data/annotations/ted_construct_validity_control_sample_manifest.json` (Task 5), `data/annotations/ted_construct_validity_labeling_{valentin,lydia}.csv` (Task 6), `data/annotations/ted_construct_validity_llm_classification.json` (Task 7).
- Produces: `data/annotations/ted_construct_validity_gate_decision.json` (+`.sha256`) once real labels exist.

- [ ] **Step 1: Write the script**

```python
# experiments/phase2/evaluate_ted_construct_validity_gate.py
"""TED construct-validity classifier, step 4: validation-gate check.

Per docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
SS6/SS8. Reads the human labeling CSVs (valentin, lydia), adjudicates
disagreements, reads the LLM classification run, and evaluates the two-gate
decision rule. Refuses to run (raises) if any human labeling CSV still has
blank judgment cells -- this script must not silently treat "not yet labeled"
as a valid input."""

import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.corpus.validation_gate import evaluate_validation_gate  # noqa: E402
from domain.models.corpus_expansion import TechnicalProblemClassification  # noqa: E402


def _read_labels(csv_path: Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            labels[row["demand_id"]] = row["judgment"].strip()
    return labels


def _to_classification(raw: str, demand_id: str, annotator: str) -> TechnicalProblemClassification:
    key = raw.strip().upper()
    if not key:
        raise ValueError(
            f"BLOCKED: {annotator}'s labeling CSV has a blank judgment for {demand_id}. "
            "This script refuses to run against incomplete human labels."
        )
    for c in TechnicalProblemClassification:
        if key in (c.value.upper(), c.name):
            return c
    raise ValueError(f"{annotator}: unrecognized judgment {raw!r} for {demand_id}")


def evaluate(
    manifest_path: Path,
    valentin_csv: Path,
    lydia_csv: Path,
    llm_path: Path,
    adjudication_path: Path,
    out_path: Path,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    boundary_ids = frozenset(manifest["boundary_ids"])
    all_ids = set(manifest["all_ids"])

    valentin_raw = _read_labels(valentin_csv)
    lydia_raw = _read_labels(lydia_csv)
    if set(valentin_raw) != all_ids or set(lydia_raw) != all_ids:
        raise ValueError("Labeling CSVs must cover exactly the control sample's demand_ids")

    valentin = {d: _to_classification(v, d, "valentin") for d, v in valentin_raw.items()}
    lydia = {d: _to_classification(v, d, "lydia") for d, v in lydia_raw.items()}

    disagreements = sorted(d for d in all_ids if valentin[d] != lydia[d])
    adjudication: dict[str, str] = {}
    if disagreements:
        if not adjudication_path.is_file():
            raise ValueError(
                f"BLOCKED: {len(disagreements)} disagreement(s) between valentin and lydia "
                f"({disagreements}) require an adjudication file at {adjudication_path}, none found."
            )
        adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
        missing = [d for d in disagreements if d not in adjudication]
        if missing:
            raise ValueError(f"Adjudication file is missing entries for: {missing}")

    reference: dict[str, TechnicalProblemClassification] = {}
    for d in all_ids:
        if d in adjudication:
            reference[d] = _to_classification(adjudication[d], d, "adjudication")
        else:
            reference[d] = valentin[d]

    llm_data = json.loads(llm_path.read_text(encoding="utf-8"))
    llm_labels = {d: _to_classification(v, d, "llm") for d, v in llm_data["classifications"].items()}
    if set(llm_labels) != all_ids:
        raise ValueError("LLM classification file must cover exactly the control sample's demand_ids")

    result = evaluate_validation_gate(reference, llm_labels, boundary_ids=boundary_ids)

    out = {
        "dataset_id": "nexus-ted-construct-validity-gate-decision-v1",
        "purpose": "TED construct-validity classifier validation-gate decision -- "
                   "docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md SS8",
        "n_control_sample": len(all_ids),
        "n_disagreements_human": len(disagreements),
        "disagreement_ids": disagreements,
        "passed": result.passed,
        "recall_technical_problem": result.recall_technical_problem,
        "specificity_generic_procurement": result.specificity_generic_procurement,
        "boundary_false_positives": list(result.boundary_false_positives),
        "reason": result.reason,
        "note": (
            "This n=30 control sample is an acceptance gate for allowing automated "
            "classification, not a powered estimate of population-level classifier "
            "sensitivity or specificity (spec SS5/SS10)."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Gate decision: {'PASS' if result.passed else 'FAIL'} -- {result.reason}")
    return out


def main() -> int:
    evaluate(
        manifest_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_control_sample_manifest.json",
        valentin_csv=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_labeling_valentin.csv",
        lydia_csv=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_labeling_lydia.csv",
        llm_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_llm_classification.json",
        adjudication_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_adjudication.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_construct_validity_gate_decision.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it and confirm it correctly BLOCKS right now**

Run: `python experiments/phase2/evaluate_ted_construct_validity_gate.py`
Expected: raises `ValueError` starting with `BLOCKED: valentin's labeling CSV has a blank judgment for ...` (or `lydia's`, depending on dict iteration order) — this is the **correct, expected outcome** at this point in the plan, since the CSVs from Task 6 are still blank and Task 7 may or may not have produced real LLM output. Do not treat this failure as a bug to fix; it is the script correctly refusing to run against incomplete input.

- [ ] **Step 3: Write the stopping-point results doc**

```markdown
# TED construct-validity classifier -- pipeline built, awaiting human labeling

Spec: docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md
Plan: docs/superpowers/plans/2026-09-23-ted-construct-validity-classifier.md

## What was built

1. `TechnicalProblemClassification` domain enum + `TechnicalProblemClassifierProtocol`
   (backend/src/main/domain/).
2. `boundary_stratum.py` -- pure boundary-formula and stratified control-sample
   construction (backend/src/main/application/corpus/).
3. `LlmTechnicalProblemClassifier` -- deterministic (temperature=0) LLM classifier
   implementing the protocol (backend/src/main/infrastructure/llm/).
4. `validation_gate.py` -- the two-gate (statistical + boundary safety) decision
   rule (backend/src/main/application/corpus/).
5. `build_ted_construct_validity_control_sample.py` -- generated the real control
   sample manifest against the live 114-candidate population.
6. `export_ted_construct_validity_labeling_csv.py` -- exported three blank CSVs
   (template/valentin/lydia), 30 rows each.
7. `run_ted_construct_validity_llm_classification.py` -- ran (or attempted to run,
   see below) the LLM classifier against the same 30.
8. `evaluate_ted_construct_validity_gate.py` -- built and confirmed to correctly
   BLOCK against incomplete human labels (the current state).

## Current state

No human labeling has occurred yet. `data/annotations/ted_construct_validity_labeling_valentin.csv`
and `_lydia.csv` are blank templates. The gate-check script (`evaluate_ted_construct_validity_gate.py`)
correctly refuses to run against them.

## Next step (not done here)

1. Valentín and Lydia independently label the 30-row control-sample CSVs, blind to
   each other and to any LLM output, per the class definitions in spec SS3.
2. Adjudicate any disagreements the same way as the 108-pair gold set, writing
   `data/annotations/ted_construct_validity_adjudication.json`.
3. Run `evaluate_ted_construct_validity_gate.py` for real -- it will report PASS
   or FAIL per the pre-registered thresholds (spec SS8).
4. Only then: a follow-up implementation plan wires the actual fix into
   `ted_mapper.py` (full-114 LLM classification on PASS, full-114 manual
   classification on FAIL), re-runs the affected eligibility measurement, and
   corrects ADR 0034's now-false claim -- explicitly out of scope for this plan
   (spec SS9, plan Global Constraints).
```

- [ ] **Step 4: Commit**

```bash
git add experiments/phase2/evaluate_ted_construct_validity_gate.py docs/ted-construct-validity-classifier-results.md
git commit -m "feat(matching): TED construct-validity gate-check script + stopping-point doc

evaluate_ted_construct_validity_gate.py reads the human labeling CSVs
and LLM classification run, adjudicates disagreements, and evaluates
the two-gate decision rule -- confirmed to correctly BLOCK against
the current blank CSVs rather than silently proceeding. Results doc
records the pipeline's current state and the next step (human
labeling), which is outside this plan's scope.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EnRUdckjunTR3sFbSLeXS2"
```
