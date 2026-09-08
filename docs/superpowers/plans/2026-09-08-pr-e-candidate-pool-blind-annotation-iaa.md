# PR-E: Candidate Pool + Blind Dual Annotation + IAA Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the code deliverables of PR-E — an independent candidate-pool builder, a temporal-eligibility policy for the annotation-pool context, a blind-export boundary, an annotation-judgment model, and an IAA (weighted Cohen's κ) calculator — so a human dry-run (demand selection, embedding generation for the selected demands, writing the annotation guide, and the actual annotation) can run on top of it.

**Architecture:** Reuses the existing `PatentCandidateRetriever`/`PatentEligibilityPolicy` protocols and `Candidate`/`CandidatePool` domain models. Adds one new eligibility policy (ADR 0019's `TEMPORAL_UNKNOWN` outcome), one small orchestrator (`CandidatePoolBuilder`) that unions retrievers without ever touching `MatchingAdapter`, a hard blind-export boundary, a minimal per-annotator judgment model, and a dependency-free (numpy-only) weighted-κ calculator.

**Tech Stack:** Python 3.12, Pydantic v2, DuckDB, numpy. No new third-party dependency.

**Spec:** `docs/superpowers/specs/2026-09-08-pr-e-candidate-pool-blind-annotation-iaa-design.md`
**ADR:** `docs/adr/0019-annotation-pool-temporal-eligibility-under-unknown-posting-date.md`

## Global Constraints

- No fabricated/inferred temporal evidence anywhere: `TEMPORAL_UNKNOWN` must never be treated as `ELIGIBLE` (ADR 0019 Enforcement #3).
- `DefaultPatentEligibilityPolicy` (`infrastructure/matching/eligibility.py`) is never modified by this plan.
- Blind-export boundary: nothing in `AnnotationBatch` or downstream may contain `retrieval_scores`, `RetrievalMethod`, or ranking/position (spec §5 contract 2).
- Shuffle order must be deterministic and reproducible from a seed (spec §5 contract 3).
- Annotation judgments use ordinal grade ∈ {0,1,2,3} only — `RelevanceGrade.UNCERTAIN` (-1) is rejected, not silently coerced (per user decision in this session).
- **Import-linter contract compliance (`.importlinter`, verified against the real config before writing this plan):**
  - `application.evaluation.*` (everything except `matching_adapter`) MUST NOT import `domain.models.matching`, `domain.protocols.matching`, or `application.matching`. This means `CandidatePoolBuilder` — which needs `Candidate`/`CandidatePool`/`PatentCandidateRetriever` — cannot live under `application/evaluation/` as the spec's component table originally said. **Correction from the spec:** it lives under `application/matching/candidate_pool_builder.py` instead (same package as the existing `feature_extractor.py`/`evaluator.py` live-matching stack). `iaa.py` has no matching-domain dependency and stays under `application/evaluation/` as specified.
  - `application` MUST NOT import `infrastructure` at all. `AnnotationPoolEligibilityPolicy` therefore lives in `infrastructure/matching/` (not `application/`), matching where `DefaultPatentEligibilityPolicy` already lives.

---

### Task 1: `EligibilityReason.TEMPORAL_UNKNOWN`

**Files:**
- Modify: `backend/src/main/domain/models/matching.py` (the `EligibilityReason` StrEnum, currently at line ~144)
- Test: `backend/test/unit/domain/test_matching.py`

**Interfaces:**
- Produces: `EligibilityReason.TEMPORAL_UNKNOWN` — a new enum member. `EligibilityResult(is_eligible=True, reason=EligibilityReason.TEMPORAL_UNKNOWN, ...)` is now a valid, distinct-from-`ELIGIBLE` construction (the model has no validator coupling `is_eligible` to a specific reason, so no model change is otherwise needed).

- [ ] **Step 1: Write the failing test**

Add to `backend/test/unit/domain/test_matching.py`:

```python
from domain.models.matching import EligibilityReason, EligibilityResult


class EligibilityReasonTest:
    def test_should_expose_temporal_unknown_as_eligible_not_excluded(self):
        result = EligibilityResult(
            publication_id="ES-9001",
            is_eligible=True,
            reason=EligibilityReason.TEMPORAL_UNKNOWN,
            details="demand.posted_date is unresolvable",
        )
        assert result.is_eligible is True
        assert result.reason == EligibilityReason.TEMPORAL_UNKNOWN
        assert result.reason != EligibilityReason.ELIGIBLE
        assert result.reason != EligibilityReason.EXCLUDED_TEMPORAL
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/domain/test_matching.py::EligibilityReasonTest -v`
Expected: FAIL — `AttributeError: TEMPORAL_UNKNOWN` (member does not exist yet).

- [ ] **Step 3: Write minimal implementation**

In `backend/src/main/domain/models/matching.py`, change:

```python
class EligibilityReason(StrEnum):
    ELIGIBLE = "eligible"
    EXCLUDED_TEMPORAL = "excluded_temporal"
    EXCLUDED_JURISDICTION = "excluded_jurisdiction"
    EXCLUDED_MISSING_TEXT = "excluded_missing_text"
```

to:

```python
class EligibilityReason(StrEnum):
    ELIGIBLE = "eligible"
    EXCLUDED_TEMPORAL = "excluded_temporal"
    EXCLUDED_JURISDICTION = "excluded_jurisdiction"
    EXCLUDED_MISSING_TEXT = "excluded_missing_text"
    # ADR 0019: annotation-pool-only outcome. An eligibility OUTCOME, not an
    # exclusion reason — is_eligible must be True whenever this reason is used.
    # DefaultPatentEligibilityPolicy (live retrieval) never produces this value.
    TEMPORAL_UNKNOWN = "temporal_unknown"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/domain/test_matching.py::EligibilityReasonTest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/domain/models/matching.py backend/test/unit/domain/test_matching.py
git commit -m "$(cat <<'EOF'
Add EligibilityReason.TEMPORAL_UNKNOWN (ADR 0019)

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 2: `AnnotationPoolEligibilityPolicy`

**Files:**
- Create: `backend/src/main/infrastructure/matching/annotation_pool_eligibility.py`
- Test: `backend/test/unit/infrastructure/matching/test_annotation_pool_eligibility.py` (new directory: `backend/test/unit/infrastructure/matching/` — check it exists first; if not, it will be created by the test file)

**Interfaces:**
- Consumes: `EligibilityReason.TEMPORAL_UNKNOWN` (Task 1), `EligibilityResult`, `EligibilityReason.ELIGIBLE`/`EXCLUDED_TEMPORAL`/`EXCLUDED_JURISDICTION`/`EXCLUDED_MISSING_TEXT` (`domain/models/matching.py`), `PatentEligibilityPolicy` protocol (`domain/protocols/matching.py`), `PatentDocument` (`domain/models/patent.py`), `DemandRecord`/`DemandSignal` (`domain/models/demand.py`).
- Produces: `AnnotationPoolEligibilityPolicy` class, implementing `PatentEligibilityPolicy.evaluate(patent, demand) -> EligibilityResult`, constructor `AnnotationPoolEligibilityPolicy(target_jurisdiction: str = "ES")`.

- [ ] **Step 1: Write the failing test**

```bash
mkdir -p backend/test/unit/infrastructure/matching
touch backend/test/unit/infrastructure/matching/__init__.py 2>/dev/null || true
```

Create `backend/test/unit/infrastructure/matching/test_annotation_pool_eligibility.py`:

```python
from domain.models.demand import DemandSignal
from domain.models.matching import EligibilityReason
from domain.models.patent import PatentDocument
from infrastructure.matching.annotation_pool_eligibility import (
    AnnotationPoolEligibilityPolicy,
)


def _patent(publication_date: str | None) -> PatentDocument:
    return PatentDocument(
        publication_id="ES-2001",
        country_code="ES",
        doc_number="2001",
        kind_code="A1",
        title="Biodegradable liquid detergent formulation",
        abstract="Aqueous cleaning composition with biodegradable surfactants.",
        publication_date=publication_date,
    )


def _demand(posted_date: str | None) -> DemandSignal:
    return DemandSignal(
        demand_id="INNOGET-9001",
        title="Seeking biodegradable detergent technology",
        description="Looking for eco-friendly surfactant formulations.",
        posted_date=posted_date,
    )


class AnnotationPoolEligibilityPolicyTest:
    def test_should_mark_eligible_when_both_dates_known_and_patent_predates_demand(self):
        policy = AnnotationPoolEligibilityPolicy()
        result = policy.evaluate(_patent("2021-06-15"), _demand("2022-01-01"))
        assert result.is_eligible is True
        assert result.reason == EligibilityReason.ELIGIBLE

    def test_should_exclude_temporal_when_both_dates_known_and_patent_postdates_demand(self):
        policy = AnnotationPoolEligibilityPolicy()
        result = policy.evaluate(_patent("2023-05-01"), _demand("2022-01-01"))
        assert result.is_eligible is False
        assert result.reason == EligibilityReason.EXCLUDED_TEMPORAL

    def test_should_mark_temporal_unknown_not_excluded_when_demand_posted_date_missing(self):
        policy = AnnotationPoolEligibilityPolicy()
        result = policy.evaluate(_patent("2021-06-15"), _demand(None))
        assert result.is_eligible is True
        assert result.reason == EligibilityReason.TEMPORAL_UNKNOWN

    def test_should_mark_temporal_unknown_not_excluded_when_patent_publication_date_missing(self):
        policy = AnnotationPoolEligibilityPolicy()
        result = policy.evaluate(_patent(None), _demand("2022-01-01"))
        assert result.is_eligible is True
        assert result.reason == EligibilityReason.TEMPORAL_UNKNOWN

    def test_should_still_exclude_wrong_jurisdiction_regardless_of_dates(self):
        policy = AnnotationPoolEligibilityPolicy(target_jurisdiction="ES")
        patent = _patent(None)
        patent = patent.model_copy(update={"country_code": "EP"})
        result = policy.evaluate(patent, _demand(None))
        assert result.is_eligible is False
        assert result.reason == EligibilityReason.EXCLUDED_JURISDICTION

    def test_should_still_exclude_missing_text_regardless_of_dates(self):
        policy = AnnotationPoolEligibilityPolicy()
        patent = _patent(None).model_copy(update={"abstract": ""})
        result = policy.evaluate(patent, _demand(None))
        assert result.is_eligible is False
        assert result.reason == EligibilityReason.EXCLUDED_MISSING_TEXT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/infrastructure/matching/test_annotation_pool_eligibility.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'infrastructure.matching.annotation_pool_eligibility'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/main/infrastructure/matching/annotation_pool_eligibility.py`:

```python
from datetime import date

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import EligibilityReason, EligibilityResult
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentEligibilityPolicy


def _parse_iso_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str.split("T")[0])
    except (ValueError, TypeError):
        return None


class AnnotationPoolEligibilityPolicy(PatentEligibilityPolicy):
    """ADR 0019: eligibility policy for PR-E annotation-pool construction only.

    Distinct from DefaultPatentEligibilityPolicy (live retrieval/matching, which
    this class does not modify or replace): when the demand's posted_date or the
    patent's publication_date is unresolvable, this policy returns
    TEMPORAL_UNKNOWN (is_eligible=True, included in the pool, marked) instead of
    excluding the candidate. UNKNOWN is an eligibility outcome, not an exclusion
    reason (ADR 0019 Decision §2) — it must never be read as, or converted to,
    ELIGIBLE by any downstream code.
    """

    def __init__(self, target_jurisdiction: str = "ES") -> None:
        self.target_jurisdiction = target_jurisdiction.upper()

    def evaluate(
        self,
        patent: PatentDocument,
        demand: DemandRecord | DemandSignal,
    ) -> EligibilityResult:
        pub_id = patent.publication_id

        if not patent.country_code or patent.country_code.upper() != self.target_jurisdiction:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_JURISDICTION,
                details=f"Expected jurisdiction {self.target_jurisdiction}, got '{patent.country_code}'",
            )

        title_clean = patent.title.strip() if patent.title else ""
        abstract_clean = patent.abstract.strip() if patent.abstract else ""
        if not title_clean or not abstract_clean:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_MISSING_TEXT,
                details="Patent must have both non-empty title and abstract",
            )

        demand_date = _parse_iso_date(demand.posted_date)
        pub_date = _parse_iso_date(patent.publication_date)

        if demand_date is None or pub_date is None:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=True,
                reason=EligibilityReason.TEMPORAL_UNKNOWN,
                details=(
                    f"Cannot evaluate t_pub < t_demand: demand.posted_date="
                    f"{demand.posted_date!r}, patent.publication_date={patent.publication_date!r}"
                ),
            )

        if pub_date >= demand_date:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_TEMPORAL,
                details=f"Publication date {pub_date} is not strictly prior to demand date {demand_date}",
            )

        return EligibilityResult(
            publication_id=pub_id,
            is_eligible=True,
            reason=EligibilityReason.ELIGIBLE,
            details=f"Eligible: {pub_date} < {demand_date}",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/infrastructure/matching/test_annotation_pool_eligibility.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/matching/annotation_pool_eligibility.py \
        backend/test/unit/infrastructure/matching/test_annotation_pool_eligibility.py \
        backend/test/unit/infrastructure/matching/__init__.py
git commit -m "$(cat <<'EOF'
Add AnnotationPoolEligibilityPolicy (ADR 0019)

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 3: `demand_corpus_item_to_demand_record` converter

**Files:**
- Create: `backend/src/main/application/matching/demand_corpus_adapter.py`
- Test: `backend/test/unit/application/matching/test_demand_corpus_adapter.py`

**Interfaces:**
- Consumes: `DemandCorpusItem` (`domain/models/evaluation.py`), `DemandRecord` (`domain/models/demand.py`), `SpanishOriginLevel` (`domain/models/demand.py`).
- Produces: `demand_corpus_item_to_demand_record(item: DemandCorpusItem) -> DemandRecord`, used by Task 4/callers to feed the frozen N=39 corpus into `PatentCandidateRetriever.retrieve()` (which requires `DemandRecord | DemandSignal`).

- [ ] **Step 1: Write the failing test**

Create `backend/test/unit/application/matching/test_demand_corpus_adapter.py`:

```python
from domain.models.demand import SpanishOriginLevel
from domain.models.evaluation import DemandCorpusItem, EvaluationProvenance
from application.matching.demand_corpus_adapter import demand_corpus_item_to_demand_record


def _corpus_item(**overrides) -> DemandCorpusItem:
    defaults = dict(
        demand_id="INNOGET-1605",
        title="Seeking lightweight innovators",
        description="Do you have a specific idea on how to design lighter vehicles?",
        posted_date=None,
        target_cpc_prefixes=["B60"],
        origin_country="Spain",
        spanish_origin_level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
        external_reference=None,
        provenance=EvaluationProvenance(
            source_authority="innoget",
            source_uri="https://www.innoget.com/technology-calls/1605/example",
            extraction_timestamp="2026-09-07T15:59:43.773584Z",
            raw_payload_sha256="a" * 64,
            modality="observed",
        ),
    )
    defaults.update(overrides)
    return DemandCorpusItem(**defaults)


class DemandCorpusAdapterTest:
    def test_should_map_core_fields(self):
        record = demand_corpus_item_to_demand_record(_corpus_item())
        assert record.demand_id == "INNOGET-1605"
        assert record.title == "Seeking lightweight innovators"
        assert record.description.startswith("Do you have a specific idea")
        assert record.url == "https://www.innoget.com/technology-calls/1605/example"

    def test_should_mark_is_spanish_demand_true_always(self):
        record = demand_corpus_item_to_demand_record(_corpus_item())
        assert record.is_spanish_demand is True

    def test_should_take_first_cpc_prefix(self):
        record = demand_corpus_item_to_demand_record(_corpus_item(target_cpc_prefixes=["B60", "C11"]))
        assert record.cpc_prefix == "B60"

    def test_should_leave_cpc_prefix_none_when_no_prefixes(self):
        record = demand_corpus_item_to_demand_record(_corpus_item(target_cpc_prefixes=[]))
        assert record.cpc_prefix is None

    def test_should_pass_through_null_posted_date(self):
        record = demand_corpus_item_to_demand_record(_corpus_item(posted_date=None))
        assert record.posted_date is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/application/matching/test_demand_corpus_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'application.matching.demand_corpus_adapter'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/main/application/matching/demand_corpus_adapter.py`:

```python
from domain.models.demand import DemandRecord
from domain.models.evaluation import DemandCorpusItem


def demand_corpus_item_to_demand_record(item: DemandCorpusItem) -> DemandRecord:
    """Maps a frozen Phase-2 DemandCorpusItem to the live-matching DemandRecord type.

    DemandCorpusItem's eligibility criterion is Spanish origin (that's what makes
    it a member of the corpus), so is_spanish_demand is always True here — it is
    not re-derived from spanish_origin_level.
    """
    posted_date = item.posted_date.isoformat() if item.posted_date else None
    return DemandRecord(
        demand_id=item.demand_id,
        title=item.title,
        description=item.description,
        origin_country=item.origin_country,
        spanish_origin_level=item.spanish_origin_level,
        is_spanish_demand=True,
        cpc_prefix=item.target_cpc_prefixes[0] if item.target_cpc_prefixes else None,
        posted_date=posted_date,
        url=item.provenance.source_uri,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/application/matching/test_demand_corpus_adapter.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/application/matching/demand_corpus_adapter.py \
        backend/test/unit/application/matching/test_demand_corpus_adapter.py
git commit -m "$(cat <<'EOF'
Add DemandCorpusItem -> DemandRecord converter

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 4: `CandidatePoolBuilder`

**Files:**
- Create: `backend/src/main/application/matching/candidate_pool_builder.py`
- Test: `backend/test/unit/application/matching/test_candidate_pool_builder.py`

**Interfaces:**
- Consumes: `PatentCandidateRetriever`, `PatentEligibilityPolicy` protocols (`domain/protocols/matching.py`); `Candidate`, `CandidatePool`, `EligibilityReason` (`domain/models/matching.py`); `PatentDocument` (`domain/models/patent.py`); `resolve_patent_columns` (`infrastructure/matching/duckdb_helpers.py` — infrastructure importing into `application/matching` would violate the application-isolation contract in the OTHER direction only if `application` imported `infrastructure`; **this import is exactly that forbidden direction**, so it must NOT be used — see Step 3 correction below, which fetches patent rows directly via the injected DuckDB connection with an inline query instead.
- Produces: `CandidatePoolBuildResult` (dataclass: `pool: CandidatePool`, `temporal_reasons: dict[str, EligibilityReason]`), `CandidatePoolBuilder(retrievers: list[PatentCandidateRetriever], eligibility_policy: PatentEligibilityPolicy, connection: duckdb.DuckDBPyConnection, table_name: str = "patents")`, method `.build(demand: DemandRecord | DemandSignal, *, limit_per_method: int = 20) -> CandidatePoolBuildResult`.

**Note on the interfaces block above:** while drafting this task, re-checked `.importlinter` and confirmed `application` (all of it, not just `application.evaluation`) is forbidden from importing `infrastructure`. `resolve_patent_columns` lives in `infrastructure/matching/duckdb_helpers.py`, so `CandidatePoolBuilder` (in `application/matching/`) cannot import it. Step 3 below queries DuckDB directly instead, inlining the small column-resolution logic rather than reusing the infrastructure helper — a deliberate, small duplication forced by the layering contract, not an oversight.

- [ ] **Step 1: Write the failing test**

Create `backend/test/unit/application/matching/test_candidate_pool_builder.py`:

```python
import duckdb
import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, EligibilityReason, RetrievalMethod
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentEligibilityPolicy
from application.matching.candidate_pool_builder import CandidatePoolBuilder


class _FakeRetriever:
    def __init__(self, method: RetrievalMethod, results: dict[str, float]):
        self._method = method
        self._results = results

    def retrieve(self, demand, *, limit: int = 100) -> list[Candidate]:
        return [
            Candidate(publication_id=pub_id, retrieval_scores={self._method: score})
            for pub_id, score in list(self._results.items())[:limit]
        ]


class _AllEligiblePolicy(PatentEligibilityPolicy):
    def evaluate(self, patent, demand):
        from domain.models.matching import EligibilityResult

        return EligibilityResult(
            publication_id=patent.publication_id,
            is_eligible=True,
            reason=EligibilityReason.ELIGIBLE,
        )


class _UnknownForOnePolicy(PatentEligibilityPolicy):
    def __init__(self, unknown_id: str):
        self._unknown_id = unknown_id

    def evaluate(self, patent, demand):
        from domain.models.matching import EligibilityResult

        reason = (
            EligibilityReason.TEMPORAL_UNKNOWN
            if patent.publication_id == self._unknown_id
            else EligibilityReason.ELIGIBLE
        )
        return EligibilityResult(publication_id=patent.publication_id, is_eligible=True, reason=reason)


@pytest.fixture
def memory_duckdb_two_patents():
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE patents (
            publication_id VARCHAR PRIMARY KEY,
            country_code VARCHAR,
            doc_number VARCHAR,
            kind_code VARCHAR,
            title VARCHAR,
            abstract VARCHAR,
            publication_date VARCHAR
        )
        """
    )
    con.execute(
        "INSERT INTO patents VALUES "
        "('ES-3001', 'ES', '3001', 'A1', 'Title A', 'Abstract A', '2021-01-01'), "
        "('ES-3002', 'ES', '3002', 'A1', 'Title B', 'Abstract B', '2021-02-01')"
    )
    yield con
    con.close()


class CandidatePoolBuilderTest:
    def test_should_union_candidates_across_retrievers_without_duplicating(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9, "ES-3002": 0.5})
        cpc = _FakeRetriever(RetrievalMethod.CPC, {"ES-3001": 0.7})
        builder = CandidatePoolBuilder(
            retrievers=[bm25, cpc],
            eligibility_policy=_AllEligiblePolicy(),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D1", title="t", description="d"))
        assert {c.publication_id for c in result.pool.candidates} == {"ES-3001", "ES-3002"}

    def test_should_merge_retrieval_scores_from_multiple_methods_for_same_candidate(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9})
        cpc = _FakeRetriever(RetrievalMethod.CPC, {"ES-3001": 0.7})
        builder = CandidatePoolBuilder(
            retrievers=[bm25, cpc],
            eligibility_policy=_AllEligiblePolicy(),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D1", title="t", description="d"))
        merged = next(c for c in result.pool.candidates if c.publication_id == "ES-3001")
        assert merged.retrieval_scores == {RetrievalMethod.LEXICAL: 0.9, RetrievalMethod.CPC: 0.7}

    def test_should_tag_temporal_reason_per_candidate(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9, "ES-3002": 0.5})
        builder = CandidatePoolBuilder(
            retrievers=[bm25],
            eligibility_policy=_UnknownForOnePolicy(unknown_id="ES-3002"),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D1", title="t", description="d"))
        assert result.temporal_reasons["ES-3001"] == EligibilityReason.ELIGIBLE
        assert result.temporal_reasons["ES-3002"] == EligibilityReason.TEMPORAL_UNKNOWN

    def test_should_reject_empty_retriever_list(self, memory_duckdb_two_patents):
        with pytest.raises(ValueError, match="at least one retriever"):
            CandidatePoolBuilder(
                retrievers=[],
                eligibility_policy=_AllEligiblePolicy(),
                connection=memory_duckdb_two_patents,
            )

    def test_should_stamp_demand_id_on_pool(self, memory_duckdb_two_patents):
        bm25 = _FakeRetriever(RetrievalMethod.LEXICAL, {"ES-3001": 0.9})
        builder = CandidatePoolBuilder(
            retrievers=[bm25],
            eligibility_policy=_AllEligiblePolicy(),
            connection=memory_duckdb_two_patents,
        )
        result = builder.build(DemandSignal(demand_id="D42", title="t", description="d"))
        assert result.pool.demand_id == "D42"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/application/matching/test_candidate_pool_builder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'application.matching.candidate_pool_builder'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/main/application/matching/candidate_pool_builder.py`:

```python
from dataclasses import dataclass

import duckdb

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import Candidate, CandidatePool, EligibilityReason
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentCandidateRetriever, PatentEligibilityPolicy


@dataclass(frozen=True)
class CandidatePoolBuildResult:
    """Output of CandidatePoolBuilder.build(): the union pool plus each candidate's
    temporal eligibility outcome (ADR 0019). Kept separate from CandidatePool itself
    so the shared domain model is not extended for this PR-E-specific concern."""

    pool: CandidatePool
    temporal_reasons: dict[str, EligibilityReason]


class CandidatePoolBuilder:
    """Builds an annotation candidate pool as the union of independently-injected
    first-stage retrievers — deliberately never routes through MatchingAdapter or
    any final ranking, to avoid selection-bias/circularity between what gets
    annotated and what is later evaluated (see PR-E spec §3).
    """

    def __init__(
        self,
        retrievers: list[PatentCandidateRetriever],
        eligibility_policy: PatentEligibilityPolicy,
        connection: duckdb.DuckDBPyConnection,
        table_name: str = "patents",
    ) -> None:
        if not retrievers:
            raise ValueError("CandidatePoolBuilder requires at least one retriever")
        self._retrievers = retrievers
        self._eligibility_policy = eligibility_policy
        self._con = connection
        self._table_name = table_name

    def build(
        self,
        demand: DemandRecord | DemandSignal,
        *,
        limit_per_method: int = 20,
    ) -> CandidatePoolBuildResult:
        merged: dict[str, Candidate] = {}
        for retriever in self._retrievers:
            for candidate in retriever.retrieve(demand, limit=limit_per_method):
                if candidate.publication_id in merged:
                    existing = merged[candidate.publication_id]
                    merged[candidate.publication_id] = Candidate(
                        publication_id=candidate.publication_id,
                        retrieval_scores={**existing.retrieval_scores, **candidate.retrieval_scores},
                    )
                else:
                    merged[candidate.publication_id] = candidate

        patents_by_id = self._fetch_patents(set(merged.keys()))
        temporal_reasons: dict[str, EligibilityReason] = {}
        for pub_id in merged:
            patent = patents_by_id.get(pub_id)
            if patent is None:
                temporal_reasons[pub_id] = EligibilityReason.EXCLUDED_MISSING_TEXT
                continue
            result = self._eligibility_policy.evaluate(patent, demand)
            temporal_reasons[pub_id] = result.reason

        pool = CandidatePool(demand_id=demand.demand_id, candidates=list(merged.values()))
        return CandidatePoolBuildResult(pool=pool, temporal_reasons=temporal_reasons)

    def _fetch_patents(self, publication_ids: set[str]) -> dict[str, PatentDocument]:
        # Inlined instead of reusing infrastructure.matching.duckdb_helpers
        # .resolve_patent_columns: application/ must not import infrastructure/
        # (.importlinter application-isolation contract).
        rows = self._con.execute(
            f"SELECT publication_id, country_code, doc_number, kind_code, "
            f"title, abstract, publication_date FROM {self._table_name}"
        ).fetchall()
        result: dict[str, PatentDocument] = {}
        for row in rows:
            pub_id = str(row[0])
            if pub_id not in publication_ids:
                continue
            result[pub_id] = PatentDocument(
                publication_id=pub_id,
                country_code=str(row[1]) if row[1] is not None else "",
                doc_number=str(row[2]) if row[2] is not None else "",
                kind_code=str(row[3]) if row[3] is not None else "",
                title=str(row[4]) if row[4] is not None else "",
                abstract=str(row[5]) if row[5] is not None else "",
                publication_date=str(row[6]) if row[6] is not None else None,
            )
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/application/matching/test_candidate_pool_builder.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Verify the import-linter contract still holds**

Run: `cd backend && lint-imports` (or `python -m importlinter` if `lint-imports` is not on PATH — check `backend/requirements.txt` for `import-linter`)
Expected: all contracts still pass, in particular `application-isolation` and `evaluation-adapter-boundary`.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/application/matching/candidate_pool_builder.py \
        backend/test/unit/application/matching/test_candidate_pool_builder.py
git commit -m "$(cat <<'EOF'
Add CandidatePoolBuilder: union of independent retrievers, no MatchingAdapter

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 5: `AnnotationJudgment` domain model

**Files:**
- Create: `backend/src/main/domain/models/annotation.py`
- Test: `backend/test/unit/domain/test_annotation.py`

**Interfaces:**
- Consumes: `RelevanceGrade` (`domain/models/evaluation.py`).
- Produces: `AnnotationJudgment(demand_id: str, publication_id: str, annotator_id: str, grade: RelevanceGrade, notes: str = "")` — Pydantic model. Rejects construction when `grade == RelevanceGrade.UNCERTAIN`.

- [ ] **Step 1: Write the failing test**

Create `backend/test/unit/domain/test_annotation.py`:

```python
import pytest
from pydantic import ValidationError

from domain.models.annotation import AnnotationJudgment
from domain.models.evaluation import RelevanceGrade


class AnnotationJudgmentTest:
    def test_should_construct_with_valid_ordinal_grade(self):
        judgment = AnnotationJudgment(
            demand_id="INNOGET-1605",
            publication_id="ES-3001",
            annotator_id="valentin",
            grade=RelevanceGrade.GRADE_2,
        )
        assert judgment.grade == RelevanceGrade.GRADE_2
        assert judgment.annotator_id == "valentin"

    def test_should_reject_uncertain_grade(self):
        with pytest.raises(ValidationError, match="UNCERTAIN"):
            AnnotationJudgment(
                demand_id="INNOGET-1605",
                publication_id="ES-3001",
                annotator_id="valentin",
                grade=RelevanceGrade.UNCERTAIN,
            )

    def test_should_reject_empty_annotator_id(self):
        with pytest.raises(ValidationError):
            AnnotationJudgment(
                demand_id="INNOGET-1605",
                publication_id="ES-3001",
                annotator_id="",
                grade=RelevanceGrade.GRADE_0,
            )

    def test_should_default_notes_to_empty_string(self):
        judgment = AnnotationJudgment(
            demand_id="INNOGET-1605",
            publication_id="ES-3001",
            annotator_id="lydia",
            grade=RelevanceGrade.GRADE_0,
        )
        assert judgment.notes == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/domain/test_annotation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'domain.models.annotation'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/main/domain/models/annotation.py`:

```python
from pydantic import BaseModel, ConfigDict, Field, model_validator

from domain.models.evaluation import RelevanceGrade


class AnnotationJudgment(BaseModel):
    """A single annotator's independent relevance judgment for one demand-patent
    pair, before any fusion, adjudication, or consolidation into a dataset (PR-E
    spec §5, non-negotiable statement 2: annotation judgments cannot alter pool
    membership). Distinct from EvaluationAnnotation (domain/models/evaluation.py),
    which represents an already-consolidated dataset annotation, not an
    individual annotator's raw independent judgment.
    """

    model_config = ConfigDict(frozen=True)

    demand_id: str = Field(min_length=1)
    publication_id: str = Field(min_length=1)
    annotator_id: str = Field(min_length=1)
    grade: RelevanceGrade
    notes: str = ""

    @model_validator(mode="after")
    def validate_grade_is_ordinal(self) -> "AnnotationJudgment":
        if self.grade == RelevanceGrade.UNCERTAIN:
            raise ValueError(
                "AnnotationJudgment.grade must be in {0,1,2,3} — "
                "RelevanceGrade.UNCERTAIN is not a valid PR-E dry-run grade"
            )
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/domain/test_annotation.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/domain/models/annotation.py backend/test/unit/domain/test_annotation.py
git commit -m "$(cat <<'EOF'
Add AnnotationJudgment domain model (ordinal 0-3, per-annotator)

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 6: Blind export boundary

**Files:**
- Create: `backend/src/main/infrastructure/annotation/__init__.py` (empty)
- Create: `backend/src/main/infrastructure/annotation/blind_export.py`
- Test: `backend/test/unit/infrastructure/annotation/test_blind_export.py` (create `backend/test/unit/infrastructure/annotation/__init__.py` too)

**Interfaces:**
- Consumes: `CandidatePool`, `Candidate`, `PatentCandidateEvidence` (`domain/models/matching.py`); `PatentDocument` (`domain/models/patent.py`); `DemandRecord`/`DemandSignal` (`domain/models/demand.py`).
- Produces: `AnnotationCandidateEntry(publication_id: str, evidence: PatentCandidateEvidence)`, `AnnotationBatch(demand_id: str, demand_title: str, demand_description: str, seed: int, entries: list[AnnotationCandidateEntry])`, function `build_annotation_batch(pool: CandidatePool, demand: DemandRecord | DemandSignal, patents_by_id: dict[str, PatentDocument], seed: int) -> AnnotationBatch`.

- [ ] **Step 1: Write the failing test**

```bash
mkdir -p backend/test/unit/infrastructure/annotation
```

Create `backend/test/unit/infrastructure/annotation/test_blind_export.py`:

```python
import pytest

from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, CandidatePool, RetrievalMethod
from domain.models.patent import PatentDocument
from infrastructure.annotation.blind_export import build_annotation_batch


def _pool() -> CandidatePool:
    return CandidatePool(
        demand_id="D1",
        candidates=[
            Candidate(publication_id="ES-1", retrieval_scores={RetrievalMethod.LEXICAL: 0.9}),
            Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.CPC: 0.7}),
            Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.SEMANTIC: 0.5}),
        ],
    )


def _patents() -> dict[str, PatentDocument]:
    return {
        pub_id: PatentDocument(
            publication_id=pub_id,
            country_code="ES",
            doc_number=pub_id.split("-")[1],
            kind_code="A1",
            title=f"Title {pub_id}",
            abstract=f"Abstract {pub_id}",
            classifications_cpc=["C11D1/02"],
        )
        for pub_id in ("ES-1", "ES-2", "ES-3")
    }


def _demand() -> DemandSignal:
    return DemandSignal(demand_id="D1", title="Seeking X", description="Looking for Y")


class BlindExportTest:
    def test_should_exclude_retrieval_scores_from_export(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        serialized = batch.model_dump_json()
        assert "retrieval_scores" not in serialized
        assert "0.9" not in serialized and "0.7" not in serialized and "0.5" not in serialized

    def test_should_exclude_retrieval_method_from_export(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        serialized = batch.model_dump_json()
        assert "lexical" not in serialized
        assert "semantic" not in serialized
        assert "\"cpc\"" not in serialized  # RetrievalMethod.CPC value, not CPC classification codes

    def test_should_exclude_original_ranking_position(self):
        batch = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        for entry in batch.entries:
            assert not hasattr(entry, "rank")
            assert not hasattr(entry, "position")

    def test_should_produce_identical_order_for_same_seed_and_pool(self):
        batch_a = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        batch_b = build_annotation_batch(_pool(), _demand(), _patents(), seed=42)
        assert [e.publication_id for e in batch_a.entries] == [e.publication_id for e in batch_b.entries]

    def test_should_preserve_the_same_candidate_set_across_different_seeds(self):
        batch_a = build_annotation_batch(_pool(), _demand(), _patents(), seed=1)
        batch_b = build_annotation_batch(_pool(), _demand(), _patents(), seed=2)
        assert {e.publication_id for e in batch_a.entries} == {e.publication_id for e in batch_b.entries}

    def test_should_raise_when_pool_candidate_has_no_matching_patent(self):
        patents = _patents()
        del patents["ES-2"]
        with pytest.raises(KeyError, match="ES-2"):
            build_annotation_batch(_pool(), _demand(), patents, seed=42)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/infrastructure/annotation/test_blind_export.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'infrastructure.annotation'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/main/infrastructure/annotation/__init__.py` (empty file).

Create `backend/src/main/infrastructure/annotation/blind_export.py`:

```python
import random

from pydantic import BaseModel, ConfigDict, Field

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import CandidatePool, PatentCandidateEvidence
from domain.models.patent import PatentDocument


class AnnotationCandidateEntry(BaseModel):
    """One candidate as shown to an annotator: observed evidence only. Never
    carries retrieval_scores, RetrievalMethod, or ranking position (PR-E spec
    §5 contract 2 — the blind-export boundary)."""

    model_config = ConfigDict(frozen=True)

    publication_id: str
    evidence: PatentCandidateEvidence


class AnnotationBatch(BaseModel):
    """A frozen, blinded set of candidates for one demand, ready for independent
    annotation. Built once per (pool, seed) and never mutated by annotation
    (PR-E spec §9 non-negotiable statement 2)."""

    model_config = ConfigDict(frozen=True)

    demand_id: str
    demand_title: str
    demand_description: str
    seed: int
    entries: tuple[AnnotationCandidateEntry, ...] = Field(default_factory=tuple)


def build_annotation_batch(
    pool: CandidatePool,
    demand: DemandRecord | DemandSignal,
    patents_by_id: dict[str, PatentDocument],
    seed: int,
) -> AnnotationBatch:
    """Strips retrieval provenance and applies a deterministic seeded shuffle.

    Raises KeyError if a pool candidate has no corresponding patent — an
    AnnotationBatch must never silently drop or skip a pool member.
    """
    publication_ids = [c.publication_id for c in pool.candidates]
    order = list(publication_ids)
    random.Random(seed).shuffle(order)

    entries = []
    for pub_id in order:
        if pub_id not in patents_by_id:
            raise KeyError(pub_id)
        patent = patents_by_id[pub_id]
        evidence = PatentCandidateEvidence(
            publication_id=pub_id,
            publication_date=patent.publication_date,
            classifications_cpc=list(patent.classifications_cpc),
            title=patent.title,
            abstract=patent.abstract,
        )
        entries.append(AnnotationCandidateEntry(publication_id=pub_id, evidence=evidence))

    return AnnotationBatch(
        demand_id=demand.demand_id,
        demand_title=demand.title,
        demand_description=demand.description,
        seed=seed,
        entries=tuple(entries),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/infrastructure/annotation/test_blind_export.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/annotation/ backend/test/unit/infrastructure/annotation/
git commit -m "$(cat <<'EOF'
Add blind-export boundary: AnnotationBatch strips retrieval provenance

Deterministic seeded shuffle; CPC-auto card is just the patent's
observed classifications_cpc (PatentCandidateEvidence), no new
CPC-overlap computation needed for this dry-run.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

### Task 7: IAA calculator (weighted Cohen's κ)

**Files:**
- Create: `backend/src/main/application/evaluation/iaa.py`
- Test: `backend/test/unit/application/evaluation/test_iaa.py`

**Interfaces:**
- Consumes: `AnnotationJudgment` (`domain/models/annotation.py`, Task 5), `RelevanceGrade` (`domain/models/evaluation.py`).
- Produces: `IAAReport(weighted_kappa: float, binary_kappa: float, confusion_matrix: list[list[int]], disagreements: list[Disagreement])`, `Disagreement(demand_id: str, publication_id: str, grade_a: int, grade_b: int)`, function `compute_iaa(judgments_a: list[AnnotationJudgment], judgments_b: list[AnnotationJudgment]) -> IAAReport`.

- [ ] **Step 1: Write the failing test**

Create `backend/test/unit/application/evaluation/test_iaa.py`:

```python
import pytest

from domain.models.annotation import AnnotationJudgment
from domain.models.evaluation import RelevanceGrade
from application.evaluation.iaa import compute_iaa


def _judgment(demand_id, pub_id, annotator, grade) -> AnnotationJudgment:
    return AnnotationJudgment(
        demand_id=demand_id, publication_id=pub_id, annotator_id=annotator, grade=RelevanceGrade(grade)
    )


class IaaTest:
    def test_should_return_kappa_one_for_perfect_agreement(self):
        judgments_a = [_judgment("D1", "P1", "valentin", 2), _judgment("D1", "P2", "valentin", 0)]
        judgments_b = [_judgment("D1", "P1", "lydia", 2), _judgment("D1", "P2", "lydia", 0)]
        report = compute_iaa(judgments_a, judgments_b)
        assert report.weighted_kappa == pytest.approx(1.0)
        assert report.binary_kappa == pytest.approx(1.0)
        assert report.disagreements == []

    def test_should_penalize_distant_disagreement_more_than_adjacent(self):
        # Pair 1: adjacent disagreement (2 vs 3). Pair 2: distant disagreement (0 vs 3).
        judgments_a_adjacent = [_judgment("D1", "P1", "valentin", 2)]
        judgments_b_adjacent = [_judgment("D1", "P1", "lydia", 3)]
        judgments_a_distant = [_judgment("D1", "P1", "valentin", 0)]
        judgments_b_distant = [_judgment("D1", "P1", "lydia", 3)]

        # Need >1 pair with variance for kappa to be defined; pad with an agreeing pair.
        pad_a = _judgment("D1", "P2", "valentin", 1)
        pad_b = _judgment("D1", "P2", "lydia", 1)

        report_adjacent = compute_iaa(judgments_a_adjacent + [pad_a], judgments_b_adjacent + [pad_b])
        report_distant = compute_iaa(judgments_a_distant + [pad_a], judgments_b_distant + [pad_b])

        assert report_distant.weighted_kappa < report_adjacent.weighted_kappa

    def test_should_report_disagreements_explicitly_without_resolving_them(self):
        judgments_a = [_judgment("D1", "P1", "valentin", 3), _judgment("D1", "P2", "valentin", 1)]
        judgments_b = [_judgment("D1", "P1", "lydia", 1), _judgment("D1", "P2", "lydia", 1)]
        report = compute_iaa(judgments_a, judgments_b)
        assert len(report.disagreements) == 1
        assert report.disagreements[0].publication_id == "P1"
        assert report.disagreements[0].grade_a == 3
        assert report.disagreements[0].grade_b == 1

    def test_should_compute_binary_kappa_on_grade_gte_2_view(self):
        # A: [2,1] -> binary [True, False]. B: [3,0] -> binary [True, False]. Agree both.
        judgments_a = [_judgment("D1", "P1", "valentin", 2), _judgment("D1", "P2", "valentin", 1)]
        judgments_b = [_judgment("D1", "P1", "lydia", 3), _judgment("D1", "P2", "lydia", 0)]
        report = compute_iaa(judgments_a, judgments_b)
        assert report.binary_kappa == pytest.approx(1.0)

    def test_should_produce_4x4_confusion_matrix(self):
        judgments_a = [_judgment("D1", "P1", "valentin", 2), _judgment("D1", "P2", "valentin", 0)]
        judgments_b = [_judgment("D1", "P1", "lydia", 2), _judgment("D1", "P2", "lydia", 1)]
        report = compute_iaa(judgments_a, judgments_b)
        assert len(report.confusion_matrix) == 4
        assert all(len(row) == 4 for row in report.confusion_matrix)
        assert sum(sum(row) for row in report.confusion_matrix) == 2

    def test_should_raise_on_mismatched_publication_id_sets(self):
        judgments_a = [_judgment("D1", "P1", "valentin", 2)]
        judgments_b = [_judgment("D1", "P2", "lydia", 2)]
        with pytest.raises(ValueError, match="same set"):
            compute_iaa(judgments_a, judgments_b)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/application/evaluation/test_iaa.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'application.evaluation.iaa'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/main/application/evaluation/iaa.py`:

```python
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel

from domain.models.annotation import AnnotationJudgment

_NUM_GRADES = 4  # RelevanceGrade 0..3; UNCERTAIN is already rejected by AnnotationJudgment


@dataclass(frozen=True)
class Disagreement:
    demand_id: str
    publication_id: str
    grade_a: int
    grade_b: int


class IAAReport(BaseModel):
    weighted_kappa: float
    binary_kappa: float
    confusion_matrix: list[list[int]]
    disagreements: list[Disagreement]

    model_config = {"arbitrary_types_allowed": True}


def _weighted_kappa(labels_a: list[int], labels_b: list[int]) -> tuple[float, list[list[int]]]:
    """Linear-weighted Cohen's kappa: penalizes distant disagreements (e.g. 0 vs 3)
    proportionally more than adjacent ones (e.g. 2 vs 3), per PR-E spec §7."""
    n = len(labels_a)
    confusion = [[0] * _NUM_GRADES for _ in range(_NUM_GRADES)]
    for a, b in zip(labels_a, labels_b):
        confusion[a][b] += 1
    observed = np.array(confusion, dtype=float)

    row_marginals = observed.sum(axis=1)
    col_marginals = observed.sum(axis=0)
    expected = np.outer(row_marginals, col_marginals) / n

    weights = np.array(
        [[abs(i - j) / (_NUM_GRADES - 1) for j in range(_NUM_GRADES)] for i in range(_NUM_GRADES)]
    )

    weighted_observed_disagreement = float((weights * observed).sum())
    weighted_expected_disagreement = float((weights * expected).sum())
    if weighted_expected_disagreement == 0:
        return 1.0, confusion
    kappa = 1.0 - (weighted_observed_disagreement / weighted_expected_disagreement)
    return kappa, confusion


def _binary_kappa(labels_a: list[int], labels_b: list[int]) -> float:
    """Simple (unweighted) Cohen's kappa over the derived relevant_binary = grade >= 2 view."""
    n = len(labels_a)
    bin_a = [1 if g >= 2 else 0 for g in labels_a]
    bin_b = [1 if g >= 2 else 0 for g in labels_b]
    observed_agreement = sum(1 for a, b in zip(bin_a, bin_b) if a == b) / n

    p_a1 = sum(bin_a) / n
    p_b1 = sum(bin_b) / n
    expected_agreement = p_a1 * p_b1 + (1 - p_a1) * (1 - p_b1)

    if expected_agreement == 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def compute_iaa(
    judgments_a: list[AnnotationJudgment],
    judgments_b: list[AnnotationJudgment],
) -> IAAReport:
    keys_a = {(j.demand_id, j.publication_id) for j in judgments_a}
    keys_b = {(j.demand_id, j.publication_id) for j in judgments_b}
    if keys_a != keys_b:
        raise ValueError(
            "Both annotators must judge the same set of (demand_id, publication_id) pairs — "
            f"got {len(keys_a)} vs {len(keys_b)} pairs, symmetric difference: {keys_a ^ keys_b}"
        )

    by_key_a = {(j.demand_id, j.publication_id): j for j in judgments_a}
    by_key_b = {(j.demand_id, j.publication_id): j for j in judgments_b}

    ordered_keys = sorted(keys_a)
    labels_a = [int(by_key_a[k].grade) for k in ordered_keys]
    labels_b = [int(by_key_b[k].grade) for k in ordered_keys]

    weighted_kappa, confusion = _weighted_kappa(labels_a, labels_b)
    binary_kappa = _binary_kappa(labels_a, labels_b)

    disagreements = [
        Disagreement(demand_id=k[0], publication_id=k[1], grade_a=ga, grade_b=gb)
        for k, ga, gb in zip(ordered_keys, labels_a, labels_b)
        if ga != gb
    ]

    return IAAReport(
        weighted_kappa=weighted_kappa,
        binary_kappa=binary_kappa,
        confusion_matrix=confusion,
        disagreements=disagreements,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/application/evaluation/test_iaa.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Verify the import-linter contract still holds**

Run: `cd backend && lint-imports`
Expected: `application.evaluation.iaa` imports only `domain.models.annotation`/`domain.models.evaluation`/`numpy`/`pydantic` — none of the forbidden `domain.models.matching`/`domain.protocols.matching`/`application.matching`/`infrastructure` modules. All contracts pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/application/evaluation/iaa.py backend/test/unit/application/evaluation/test_iaa.py
git commit -m "$(cat <<'EOF'
Add IAA calculator: linear-weighted Cohen's kappa, confusion matrix, binary kappa

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

## After this plan: what remains manual, not code

Per the PR-E spec's scope (§2) and this session's decisions — deliberately NOT part of this implementation plan:

1. **Select the 6-8 dry-run demands** from the N=39 corpus (diversity/difficulty stress test, documented rationale) — an editorial decision, not code.
2. **Generate the frozen semantic embedding artifact** for those selected demands (same pipeline/schema as `embeddings_pilot_benchmark.json`, ADR 0014) — needed only if the semantic retriever is included in the dry-run's `CandidatePoolBuilder(retrievers=[...])` list; the builder works with any non-empty subset of retrievers, so BM25+CPC alone is a valid way to run it before semantic embeddings exist.
3. **Write the annotation guide** (`docs/annotation/phase2-guide.md`) with 0-3 scale examples and 1↔2/2↔3 boundary criteria.
4. **Run the actual annotation** — Valentín and Lydia independently producing `AnnotationJudgment` records (this plan's models/tools support storing and loading these; the plan does not include a UI or CLI for data entry, which was not requested).
5. **Freeze each annotator's judgments as a hashed artifact**, same pattern as `dataset_phase2_demand_corpus_n39.*` — reuse `infrastructure/matching/corpus_manifest.py::compute_file_sha256` for the hash sidecar; no new code needed.
6. **Run `compute_iaa`** (Task 7) over the two frozen judgment sets and review the confusion matrix per PR-E spec §10 exit criteria.
