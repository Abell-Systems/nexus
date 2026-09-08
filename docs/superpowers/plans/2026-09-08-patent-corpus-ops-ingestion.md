# PatentCorpus + Multi-Jurisdiction OPS Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and freeze `PatentCorpus` (`P`) — a jurisdiction/grant/window-determined, demand-blind, deterministically-selected patent artifact — via a fixture-testable EPO OPS multi-jurisdiction ingestion pipeline, so PR-E1 (already designed) can resume step 6.

**Architecture:** Reuse existing real infrastructure end-to-end: `EpoOpsClient` (OPS fetch, already fixture-replayable), a generalized `OepmXmlNormalizer` (already tag/attribute-generic, not OEPM-specific in practice — verified here by contract test rather than assumed), and `PatentValidator` (dedup). Add three small, pure, independently-testable pieces around them: a CQL query builder, an enumerability-safe OPS pagination loop, and a deterministic `sha256(publication_id)`-order selection function. A new `scripts/freeze_patent_corpus.py` orchestrates these into a frozen `PatentCorpus` artifact (dataset JSON + manifest + sha256 sidecar), following the exact freezing discipline already established by `scripts/freeze_phase2_demand_corpus.py` for `DemandCorpus` — not the `IngestionPipeline`/`EnhancedManifest` production-ingestion path, which is schema-bound to the single-jurisdiction OEPM canonical store (`jurisdiction: "ES"` is hardcoded in `EnhancedManifestBuilder`) and not a fit for a frozen multi-jurisdiction experimental artifact.

**Tech Stack:** Python 3.12, Pydantic v2, `httpx` (via `EpoOpsClient`), `pytest`, existing `xml.etree.ElementTree`-based normalization.

**Spec:** `docs/adr/0020-experimental-corpus-architecture-demand-times-patent.md` (ADR 0020, approved).

## Global Constraints

- Jurisdictions: EP, US, JP, CN, KR, WO (PCT) — ADR 0020 §2. No others.
- Publication type: grants only — ADR 0020 §2. Kind codes B1/B2 (WIPO ST.16, which is what EPO OPS/DOCDB normalizes all offices' kind codes to); applications (A1/A2), utility models (U), and translations (T3) are excluded from `P` even though `OepmXmlNormalizer` accepts them for the OEPM/ES pipeline.
- Temporal window: publication date within the 10 years preceding the freeze cutoff — ADR 0020 §2.
- No CPC/topical curation of any kind — ADR 0020 §2.
- Selection: sort candidates by `sha256(publication_id)`, take first `N_final` — ADR 0020 §3. No other ordering (API delivery order, filing date, etc.) may determine which records are kept.
- `target_N = 50000`; `N_final = min(target_N, eligible_available_records)`; `minimum_acceptable_N = 5000` — below this, corpus construction is a hard failure, not a shrunken-but-accepted corpus — ADR 0020 §4.
- **Enumerability requirement (not yet in ADR text, but a hard requirement per the user's explicit instruction — see project memory `project_pr_e0_patent_corpus_adr`):** `eligible_available_records` must be the full universe satisfying the inclusion contract, not whatever a pagination loop happened to fetch before hitting a limit/timeout. The ingestion must either enumerate the true universe completely (verified against EPO OPS's own `total-result-count`) or fail loudly — never silently sample a truncated fetch.
- Demand-blindness: nothing in this plan may read, import, or branch on `DemandCorpus`, the 8 selected demands, or their CPC/domain content (ADR 0020 §1, §7 enforcement item 1). None of the tasks below touch `domain/models/demand.py`, `AnnotationPoolEligibilityPolicy`, or `CandidatePoolBuilder`.
- Live EPO OPS credentials (`EPO_OPS_KEY`/`EPO_OPS_SECRET`) are not required for anything in this plan — every task is fixture-testable (ADR 0020 §6). The final live run (Task 6, invoked with real credentials, at N≈50,000) is an operational step for a human to run after this plan's code is merged, not something the test suite performs.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/src/main/domain/models/evaluation.py` (modify) | Add `PatentCorpusItem`/`PatentCorpus` frozen Pydantic models, symmetric to `DemandCorpusItem`/`DemandCorpus`. |
| `backend/src/main/infrastructure/sources/patent/ops_query.py` (new) | Pure CQL query builder encoding jurisdictions + grants-only + temporal window. |
| `backend/src/main/infrastructure/sources/patent/ops_pagination.py` (new) | Enumerability-safe pagination loop over `EpoOpsClient.fetch_batches`, verified against OPS's `total-result-count`. |
| `backend/src/main/application/ingestion/normalizers/oepm_xml_normalizer.py` (modify) | Add `allowed_kind_codes` constructor param (default unchanged) so the same normalizer can be restricted to grants-only for `P` without touching OEPM/ES behavior. |
| `backend/src/main/application/evaluation/patent_corpus_builder.py` (new) | `select_frozen_patents()` — dedup + `sha256(publication_id)` ordering + `N_final`/floor enforcement (ADR 0020 §3, §4). |
| `scripts/freeze_patent_corpus.py` (new) | Orchestration script: query → paginated fetch → normalize (grants-only, multi-jurisdiction) → select → freeze (JSON + manifest + sha256), mirroring `scripts/freeze_phase2_demand_corpus.py`'s discipline. |
| `backend/test/fixtures/epo_ops_multi_jurisdiction_sample.xml` (new) | Fixture: EP/US/JP/CN/KR/WO documents, mixed grant/application kind codes, for contract-testing normalizer generalization. |

---

### Task 1: `PatentCorpusItem` / `PatentCorpus` domain models

**Files:**
- Modify: `backend/src/main/domain/models/evaluation.py`
- Test: `backend/test/unit/domain/test_patent_corpus_model.py`

**Interfaces:**
- Produces: `PatentCorpusItem(publication_id, country_code, kind_code, title, abstract, publication_date, classifications_cpc, provenance)`, `PatentCorpus(dataset_id, schema_version, dataset_version, description, patents: list[PatentCorpusItem])`. Both `model_config = ConfigDict(frozen=True)`, mirroring `DemandCorpusItem`/`DemandCorpus` in the same file. Field names/types match `PatentDocument`'s core fields 1:1 (minus `doc_number`, `application_number`, `assignees`, `inventors`, `classifications_ipc`, citation counts, `family_id`, `filing_date`, `priority_date` — none of those are required by `AnnotationPoolEligibilityPolicy.evaluate` or `DuckDbBM25Retriever`/`DuckDbCPCRetriever`, and ADR 0020 §5 explicitly does not require reusing `PatentDocument`'s full shape) so a later PR-E1 step can trivially map `PatentCorpusItem → PatentDocument`.

- [ ] **Step 1: Write the failing test**

```python
# backend/test/unit/domain/test_patent_corpus_model.py
"""Unit tests for PatentCorpus/PatentCorpusItem (ADR 0020 §5)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from domain.models.evaluation import DataModality, EvaluationProvenance, PatentCorpus, PatentCorpusItem


def _provenance() -> EvaluationProvenance:
    return EvaluationProvenance(
        source_authority="European Patent Office (EPO OPS 3.2)",
        source_uri="https://ops.epo.org",
        extraction_timestamp=datetime.now(UTC),
        raw_payload_sha256="a" * 64,
        modality=DataModality.OBSERVED,
    )


def _item(pub_id: str, country: str = "US") -> PatentCorpusItem:
    return PatentCorpusItem(
        publication_id=pub_id,
        country_code=country,
        kind_code="B2",
        title="A widget",
        abstract="A widget that does things.",
        publication_date="2020-01-01",
        classifications_cpc=["B65D1/00"],
        provenance=_provenance(),
    )


def test_patent_corpus_item_is_frozen():
    item = _item("US1234567B2")
    with pytest.raises(ValidationError):
        item.title = "changed"  # type: ignore[misc]


def test_patent_corpus_rejects_duplicate_publication_ids():
    with pytest.raises(ValidationError, match="Duplicate publication_id"):
        PatentCorpus(
            dataset_id="nexus-patent-corpus-p-v1",
            schema_version="1.0.0",
            dataset_version="1.0.0",
            description="test",
            patents=[_item("US1234567B2"), _item("US1234567B2")],
        )


def test_patent_corpus_accepts_multi_jurisdiction_items():
    corpus = PatentCorpus(
        dataset_id="nexus-patent-corpus-p-v1",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        description="test",
        patents=[_item("US1234567B2", "US"), _item("JP1234567B2", "JP")],
    )
    assert {p.country_code for p in corpus.patents} == {"US", "JP"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/domain/test_patent_corpus_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'PatentCorpus'`

- [ ] **Step 3: Add the models**

In `backend/src/main/domain/models/evaluation.py`, immediately after the `DemandCorpus` class (before `EvaluationDatasetManifest`), add:

```python
class PatentCorpusItem(BaseModel):
    """Frozen patent record for the demand-blind patent-side experimental artifact (ADR 0020).

    Field set matches PatentDocument's core retrieval/eligibility-relevant fields, not its
    full shape (ADR 0020 §5 explicitly does not require reusing PatentDocument's exact
    schema) -- enough for a later PR-E1 step to map 1:1 into PatentDocument for retrieval.
    """

    model_config = ConfigDict(frozen=True)

    publication_id: str = Field(min_length=1)
    country_code: str = Field(min_length=2, max_length=2)
    kind_code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    abstract: str = Field(min_length=1)
    publication_date: str | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    provenance: EvaluationProvenance


class PatentCorpus(BaseModel):
    """Frozen, demand-blind patent corpus (ADR 0020's `P`).

    Composition is fixed by jurisdiction + grant + temporal-window inclusion contract
    (ADR 0020 §2) and sha256(publication_id)-order selection (ADR 0020 §3) -- never by
    any demand-side property. See scripts/freeze_patent_corpus.py for the construction
    pipeline that produces this artifact.
    """

    model_config = ConfigDict(frozen=True)

    dataset_id: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    patents: list[PatentCorpusItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_publication_ids(self) -> "PatentCorpus":
        seen: set[str] = set()
        for p in self.patents:
            if p.publication_id in seen:
                raise ValueError(f"Duplicate publication_id in corpus: {p.publication_id}")
            seen.add(p.publication_id)
        return self
```

No new imports are needed — `BaseModel`, `ConfigDict`, `Field`, `model_validator` are already imported in this file.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/domain/test_patent_corpus_model.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/domain/models/evaluation.py backend/test/unit/domain/test_patent_corpus_model.py
git commit -m "$(cat <<'EOF'
feat: add PatentCorpus/PatentCorpusItem frozen domain models (ADR 0020)

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 2: OPS CQL query builder

**Files:**
- Create: `backend/src/main/infrastructure/sources/patent/ops_query.py`
- Test: `backend/test/unit/infrastructure/sources/patent/test_ops_query.py`

**Interfaces:**
- Consumes: nothing (pure function).
- Produces: `build_patent_corpus_cql(jurisdictions: list[str], min_publication_year: int, max_publication_year: int) -> str` — used by Task 6's freeze script and passed straight into `EpoOpsClient.fetch_batches(cql_query=...)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/test/unit/infrastructure/sources/patent/test_ops_query.py
"""Unit tests for the OPS CQL query builder (ADR 0020 §2, §3)."""

import pytest

from infrastructure.sources.patent.ops_query import build_patent_corpus_cql


def test_build_query_encodes_all_jurisdictions_and_window():
    query = build_patent_corpus_cql(
        jurisdictions=["EP", "US", "JP", "CN", "KR", "WO"],
        min_publication_year=2016,
        max_publication_year=2026,
    )
    assert 'pn=EP or pn=US or pn=JP or pn=CN or pn=KR or pn=WO' in query
    assert "pd within \"20160101 20261231\"" in query


def test_build_query_is_deterministic():
    args = dict(jurisdictions=["EP", "US"], min_publication_year=2020, max_publication_year=2021)
    assert build_patent_corpus_cql(**args) == build_patent_corpus_cql(**args)


def test_build_query_rejects_empty_jurisdictions():
    with pytest.raises(ValueError, match="jurisdictions"):
        build_patent_corpus_cql(jurisdictions=[], min_publication_year=2016, max_publication_year=2026)


def test_build_query_rejects_inverted_window():
    with pytest.raises(ValueError, match="min_publication_year"):
        build_patent_corpus_cql(jurisdictions=["EP"], min_publication_year=2026, max_publication_year=2016)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/infrastructure/sources/patent/test_ops_query.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.sources.patent.ops_query'`

- [ ] **Step 3: Implement the builder**

```python
# backend/src/main/infrastructure/sources/patent/ops_query.py
"""EPO OPS CQL query construction for PatentCorpus's jurisdiction+grant+window inclusion
contract (ADR 0020 §2). Pure and deterministic -- given the same arguments, always
produces the same query string, independent of any demand-side information."""


def build_patent_corpus_cql(
    jurisdictions: list[str],
    min_publication_year: int,
    max_publication_year: int,
) -> str:
    """Build a CQL query for EPO OPS `published-data/search/biblio` scoped to the given
    jurisdictions and publication-year window. Grant-vs-application filtering is NOT
    encoded here -- OPS's CQL kind-code filtering is unreliable across offices, so
    grants-only is enforced downstream by the normalizer (see oepm_xml_normalizer.py's
    `allowed_kind_codes`), not by this query.
    """
    if not jurisdictions:
        raise ValueError("jurisdictions must be a non-empty list")
    if min_publication_year > max_publication_year:
        raise ValueError(
            f"min_publication_year ({min_publication_year}) must be <= "
            f"max_publication_year ({max_publication_year})"
        )

    jurisdiction_clause = " or ".join(f"pn={j.upper()}" for j in jurisdictions)
    window_clause = f'pd within "{min_publication_year}0101 {max_publication_year}1231"'
    return f"({jurisdiction_clause}) and {window_clause}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/infrastructure/sources/patent/test_ops_query.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/sources/patent/ops_query.py backend/test/unit/infrastructure/sources/patent/test_ops_query.py
git commit -m "$(cat <<'EOF'
feat: add EPO OPS CQL query builder for PatentCorpus inclusion contract

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 3: Enumerability-safe OPS pagination

**Files:**
- Create: `backend/src/main/infrastructure/sources/patent/ops_pagination.py`
- Test: `backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py`

**Interfaces:**
- Consumes: `EpoOpsClient` (Task 6 constructs one, real or fixture-mode), `domain.protocols.sources.RawPayload`.
- Produces: `parse_total_result_count(xml_bytes: bytes) -> int | None`, `fetch_all_ops_batches(client: EpoOpsClient, cql_query: str, page_size: int = 100, max_records: int = 60000) -> Iterator[RawPayload]`. Raises `RuntimeError` (not silent truncation) if the total count can't be determined, changes mid-run, or exceeds `max_records` before being fully paginated — this is the enumerability requirement from the ADR-0020 project memory.

- [ ] **Step 1: Write the failing test**

```python
# backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py
"""Unit tests for OPS pagination + enumerability verification (ADR 0020 §3, §4 support)."""

from collections.abc import Iterator

import pytest

from domain.protocols.sources import RawPayload
from infrastructure.sources.patent.ops_pagination import (
    fetch_all_ops_batches,
    parse_total_result_count,
)

ONE_DOC_PAGE = b"""<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns:ops="http://ops.epo.org">
  <ops:biblio-search total-result-count="3">
    <exchange-documents><exchange-document country="US" doc-number="1" kind="B2"/></exchange-documents>
  </ops:biblio-search>
</ops:world-patent-data>"""

NO_COUNT_PAGE = b"""<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns:ops="http://ops.epo.org">
  <ops:biblio-search><exchange-documents/></ops:biblio-search>
</ops:world-patent-data>"""


def test_parse_total_result_count_reads_attribute():
    assert parse_total_result_count(ONE_DOC_PAGE) == 3


def test_parse_total_result_count_returns_none_when_absent():
    assert parse_total_result_count(NO_COUNT_PAGE) is None


class _FakeClient:
    """Test double: EpoOpsClient-shaped, returns one canned page per call, by range."""

    def __init__(self, pages_by_range: dict[tuple[int, int], bytes]) -> None:
        self._pages = pages_by_range
        self.calls: list[tuple[int, int]] = []

    def fetch_batches(
        self, cql_query: str = "", range_start: int = 1, range_end: int = 25
    ) -> Iterator[RawPayload]:
        self.calls.append((range_start, range_end))
        yield RawPayload(
            source_id="epo_ops",
            batch_id=f"batch_{range_start}_{range_end}",
            payload_bytes=self._pages[(range_start, range_end)],
            metadata={},
        )


def test_fetch_all_ops_batches_stops_at_total_result_count():
    page1 = b'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org"><ops:biblio-search total-result-count="3"/></ops:world-patent-data>'
    page2 = b'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org"><ops:biblio-search total-result-count="3"/></ops:world-patent-data>'
    client = _FakeClient({(1, 2): page1, (3, 4): page2})

    batches = list(fetch_all_ops_batches(client, cql_query="pn=US", page_size=2))

    assert len(batches) == 2
    assert client.calls == [(1, 2), (3, 4)]


def test_fetch_all_ops_batches_raises_on_missing_total_count():
    client = _FakeClient({(1, 100): NO_COUNT_PAGE})
    with pytest.raises(RuntimeError, match="total-result-count"):
        list(fetch_all_ops_batches(client, cql_query="pn=US"))


def test_fetch_all_ops_batches_raises_when_max_records_reached_before_total():
    huge_total = b'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org"><ops:biblio-search total-result-count="1000"/></ops:world-patent-data>'
    client = _FakeClient({(1, 10): huge_total})
    with pytest.raises(RuntimeError, match="max_records"):
        list(fetch_all_ops_batches(client, cql_query="pn=US", page_size=10, max_records=10))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.sources.patent.ops_pagination'`

- [ ] **Step 3: Implement pagination + enumerability check**

```python
# backend/src/main/infrastructure/sources/patent/ops_pagination.py
"""Enumerability-safe pagination over EpoOpsClient.fetch_batches.

Per ADR 0020 §4 (and the explicit implementation-time requirement it does not yet
codify in text): eligible_available_records must be the FULL universe satisfying the
inclusion contract, never a fetch that was silently truncated by an API/pagination
limit. This module either enumerates the true universe completely -- verified against
EPO OPS's own `total-result-count` -- or raises, so a truncated fetch can never
silently become "the" corpus.
"""

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import Protocol

from domain.protocols.sources import RawPayload


class _PaginatedPatentSource(Protocol):
    def fetch_batches(
        self, cql_query: str = "", range_start: int = 1, range_end: int = 25
    ) -> Iterator[RawPayload]: ...


def parse_total_result_count(xml_bytes: bytes) -> int | None:
    """Extract ops:biblio-search's total-result-count attribute, namespace-agnostic."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    for elem in root.iter():
        tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag_local == "biblio-search" and "total-result-count" in elem.attrib:
            try:
                return int(elem.attrib["total-result-count"])
            except ValueError:
                return None
    return None


def fetch_all_ops_batches(
    client: _PaginatedPatentSource,
    cql_query: str,
    page_size: int = 100,
    max_records: int = 60000,
) -> Iterator[RawPayload]:
    """Page through `client.fetch_batches` until EPO OPS's own total-result-count is
    fully covered. Raises RuntimeError instead of returning a partial set if the total
    count is missing, changes mid-run, or exceeds `max_records` before completion.
    """
    range_start = 1
    known_total: int | None = None

    while True:
        range_end = range_start + page_size - 1
        batch = next(iter(client.fetch_batches(cql_query=cql_query, range_start=range_start, range_end=range_end)))
        yield batch

        page_total = parse_total_result_count(batch.payload_bytes)
        if page_total is None:
            raise RuntimeError(
                f"EPO OPS response for range {range_start}-{range_end} is missing "
                "total-result-count; cannot verify complete enumeration of the eligible "
                "universe (ADR 0020 §4 enumerability requirement)."
            )
        if known_total is None:
            known_total = page_total
        elif page_total != known_total:
            raise RuntimeError(
                f"EPO OPS total-result-count changed mid-pagination ({known_total} -> "
                f"{page_total}); the universe is not stable, cannot guarantee complete "
                "enumeration."
            )

        if range_end >= known_total:
            return
        if range_end >= max_records:
            raise RuntimeError(
                f"EPO OPS pagination reached max_records={max_records} before covering "
                f"total_result_count={known_total} for query {cql_query!r}. Raise "
                "max_records or narrow the query -- do not silently accept a truncated fetch."
            )
        range_start = range_end + 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/sources/patent/ops_pagination.py backend/test/unit/infrastructure/sources/patent/test_ops_pagination.py
git commit -m "$(cat <<'EOF'
feat: add enumerability-safe OPS pagination for PatentCorpus ingestion

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 4: Grants-only kind-code filter on `OepmXmlNormalizer`

**Files:**
- Modify: `backend/src/main/application/ingestion/normalizers/oepm_xml_normalizer.py`
- Test: `backend/test/unit/application/ingestion/test_oepm_xml_normalizer_kind_code_filter.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `OepmXmlNormalizer.__init__(..., allowed_kind_codes: frozenset[str] | None = None)` — when `None` (default), behavior is byte-for-byte unchanged (`NORMATIVE_KIND_CODES`, i.e. the existing OEPM/ES pipeline is untouched). Task 6 passes `allowed_kind_codes=frozenset({"B1", "B2"})` for grants-only `P` construction.

- [ ] **Step 1: Write the failing test**

```python
# backend/test/unit/application/ingestion/test_oepm_xml_normalizer_kind_code_filter.py
"""Unit test: allowed_kind_codes lets callers restrict to grants-only without changing
the default (OEPM/ES) behavior (ADR 0020 §2 grants-only requirement)."""

from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer
from domain.models.ingestion import ExclusionReason, RecordDisposition
from domain.protocols.sources import RawPayload

APPLICATION_XML = b"""<?xml version="1.0"?>
<exchange-document country="US" doc-number="1234567" kind="A1">
  <invention-title>A gadget</invention-title>
  <abstract><p>A gadget that gadgets.</p></abstract>
</exchange-document>"""

GRANT_XML = b"""<?xml version="1.0"?>
<exchange-document country="US" doc-number="1234567" kind="B2">
  <invention-title>A gadget</invention-title>
  <abstract><p>A gadget that gadgets.</p></abstract>
</exchange-document>"""


def _payload(xml_bytes: bytes) -> RawPayload:
    return RawPayload(source_id="epo_ops", batch_id="b1", payload_bytes=xml_bytes, metadata={})


def test_default_allowed_kind_codes_unchanged_includes_applications():
    normalizer = OepmXmlNormalizer()
    results = list(normalizer.normalize_results(_payload(APPLICATION_XML)))
    assert results[0].disposition == RecordDisposition.INCLUDED


def test_grants_only_excludes_applications():
    normalizer = OepmXmlNormalizer(allowed_kind_codes=frozenset({"B1", "B2"}))
    results = list(normalizer.normalize_results(_payload(APPLICATION_XML)))
    assert results[0].disposition == RecordDisposition.EXCLUDED
    assert results[0].excluded.reason == ExclusionReason.UNSUPPORTED_KIND_CODE


def test_grants_only_includes_grants():
    normalizer = OepmXmlNormalizer(allowed_kind_codes=frozenset({"B1", "B2"}))
    results = list(normalizer.normalize_results(_payload(GRANT_XML)))
    assert results[0].disposition == RecordDisposition.INCLUDED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/application/ingestion/test_oepm_xml_normalizer_kind_code_filter.py -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'allowed_kind_codes'`

- [ ] **Step 3: Add the parameter**

In `backend/src/main/application/ingestion/normalizers/oepm_xml_normalizer.py`, modify `__init__`:

```python
    def __init__(
        self,
        extraction_version: str = "2.0.0",
        target_country: str = "ES",
        min_publication_year: int = 2016,
        max_publication_year: int = 2024,
        allowed_kind_codes: frozenset[str] | None = None,
    ) -> None:
        self.extraction_version = extraction_version
        self.target_country = target_country
        self.min_publication_year = min_publication_year
        self.max_publication_year = max_publication_year
        self.allowed_kind_codes = allowed_kind_codes or NORMATIVE_KIND_CODES
```

And in `_normalize_single_element`, change the existing check:

```python
        # 3. Validation against Kind-Code Universe
        if kind_code not in NORMATIVE_KIND_CODES:
```

to:

```python
        # 3. Validation against Kind-Code Universe
        if kind_code not in self.allowed_kind_codes:
```

(leave the error message's `sorted(NORMATIVE_KIND_CODES)` as `sorted(self.allowed_kind_codes)` in the same block, so the reported detail matches what was actually enforced).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/application/ingestion/test_oepm_xml_normalizer_kind_code_filter.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full existing normalizer test suite to confirm no regression**

Run: `pytest backend/test/unit/application/ingestion/ backend/test/integration/infrastructure/sources/test_epo_ops.py -v`
Expected: PASS, no change in existing OEPM/ES test outcomes (default `allowed_kind_codes` preserves `NORMATIVE_KIND_CODES` exactly).

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/application/ingestion/normalizers/oepm_xml_normalizer.py backend/test/unit/application/ingestion/test_oepm_xml_normalizer_kind_code_filter.py
git commit -m "$(cat <<'EOF'
feat: add allowed_kind_codes param to OepmXmlNormalizer for grants-only filtering

Default preserves existing OEPM/ES behavior exactly (NORMATIVE_KIND_CODES); PatentCorpus
construction (ADR 0020 §2) passes {B1, B2} to exclude applications/utility models/translations.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 5: Contract test — normalizer generalizes to non-ES/OEPM XML

This is ADR 0020 §6's core requirement: `OepmXmlNormalizer`'s reusability for other jurisdictions is *verified*, not assumed. This task adds the fixture and the test; it does not change production code (Task 4 already made the one behavioral change needed).

**Files:**
- Create: `backend/test/fixtures/epo_ops_multi_jurisdiction_sample.xml`
- Test: `backend/test/integration/infrastructure/sources/test_epo_ops_multi_jurisdiction_normalization.py`

**Interfaces:**
- Consumes: `EpoOpsClient.from_fixture_file`, `OepmXmlNormalizer(allowed_kind_codes=...)` (Task 4).
- Produces: nothing new — a pass/fail contract test.

- [ ] **Step 1: Create the multi-jurisdiction fixture**

```xml
<!-- backend/test/fixtures/epo_ops_multi_jurisdiction_sample.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns:ops="http://ops.epo.org" xmlns="http://www.epo.org/exchange">
  <ops:biblio-search total-result-count="6">
    <ops:range begin="1" end="6"/>
  </ops:biblio-search>
  <exchange-documents>
    <exchange-document country="EP" doc-number="3000001" kind="B1">
      <bibliographic-data>
        <publication-reference>
          <document-id document-id-type="epodoc"><doc-number>EP3000001</doc-number><date>20210115</date></document-id>
        </publication-reference>
        <invention-title lang="en">Heat exchanger assembly</invention-title>
        <patent-classifications><patent-classification><classification-symbol>F28D1/00</classification-symbol></patent-classification></patent-classifications>
      </bibliographic-data>
      <abstract lang="en"><p>A heat exchanger assembly for industrial cooling.</p></abstract>
    </exchange-document>
    <exchange-document country="US" doc-number="11223344" kind="B2">
      <bibliographic-data>
        <publication-reference>
          <document-id document-id-type="epodoc"><doc-number>US11223344</doc-number><date>20200601</date></document-id>
        </publication-reference>
        <invention-title lang="en">Battery management circuit</invention-title>
        <patent-classifications><patent-classification><classification-symbol>H01M10/48</classification-symbol></patent-classification></patent-classifications>
      </bibliographic-data>
      <abstract lang="en"><p>A circuit for managing rechargeable battery cells.</p></abstract>
    </exchange-document>
    <exchange-document country="JP" doc-number="6912345" kind="B2">
      <bibliographic-data>
        <publication-reference>
          <document-id document-id-type="epodoc"><doc-number>JP6912345</doc-number><date>20190310</date></document-id>
        </publication-reference>
        <invention-title lang="en">Semiconductor packaging method</invention-title>
        <patent-classifications><patent-classification><classification-symbol>H01L21/56</classification-symbol></patent-classification></patent-classifications>
      </bibliographic-data>
      <abstract lang="en"><p>A method for packaging semiconductor devices.</p></abstract>
    </exchange-document>
    <exchange-document country="CN" doc-number="112233445" kind="B">
      <bibliographic-data>
        <publication-reference>
          <document-id document-id-type="epodoc"><doc-number>CN112233445</doc-number><date>20220220</date></document-id>
        </publication-reference>
        <invention-title lang="en">Water purification membrane</invention-title>
        <patent-classifications><patent-classification><classification-symbol>C02F1/44</classification-symbol></patent-classification></patent-classifications>
      </bibliographic-data>
      <abstract lang="en"><p>A membrane for purifying industrial wastewater.</p></abstract>
    </exchange-document>
    <exchange-document country="KR" doc-number="1023456780" kind="B1">
      <bibliographic-data>
        <publication-reference>
          <document-id document-id-type="epodoc"><doc-number>KR1023456780</doc-number><date>20180705</date></document-id>
        </publication-reference>
        <invention-title lang="en">Robotic arm joint mechanism</invention-title>
        <patent-classifications><patent-classification><classification-symbol>B25J17/00</classification-symbol></patent-classification></patent-classifications>
      </bibliographic-data>
      <abstract lang="en"><p>A joint mechanism for industrial robotic arms.</p></abstract>
    </exchange-document>
    <exchange-document country="WO" doc-number="2021123456" kind="A1">
      <bibliographic-data>
        <publication-reference>
          <document-id document-id-type="epodoc"><doc-number>WO2021123456</doc-number><date>20210715</date></document-id>
        </publication-reference>
        <invention-title lang="en">Solar panel mounting frame (pending application)</invention-title>
        <patent-classifications><patent-classification><classification-symbol>H02S20/00</classification-symbol></patent-classification></patent-classifications>
      </bibliographic-data>
      <abstract lang="en"><p>A mounting frame for photovoltaic solar panels.</p></abstract>
    </exchange-document>
  </exchange-documents>
</ops:world-patent-data>
```

Note the last record (`WO2021123456`) is deliberately `kind="A1"` (a published application, not a grant) — it exercises the grants-only filter from Task 4 within the same multi-jurisdiction batch.

- [ ] **Step 2: Write the contract test**

```python
# backend/test/integration/infrastructure/sources/test_epo_ops_multi_jurisdiction_normalization.py
"""Contract test: OepmXmlNormalizer generalizes to multi-jurisdiction EPO OPS XML
(EP/US/JP/CN/KR/WO), restricted to grants-only. ADR 0020 §6: this is verified here,
not assumed."""

from pathlib import Path

from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer
from domain.models.ingestion import RecordDisposition
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient

FIXTURE = Path("backend/test/fixtures/epo_ops_multi_jurisdiction_sample.xml")


def test_normalizer_extracts_grants_across_all_target_jurisdictions():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    normalizer = OepmXmlNormalizer(allowed_kind_codes=frozenset({"B1", "B2"}))

    results = []
    for payload in client.fetch_batches():
        results.extend(normalizer.normalize_results(payload))

    included = [r for r in results if r.disposition == RecordDisposition.INCLUDED]
    excluded = [r for r in results if r.disposition == RecordDisposition.EXCLUDED]

    included_countries = {r.document.country_code for r in included}
    assert included_countries == {"EP", "US", "JP", "KR"}, (
        f"Expected EP/US/JP/KR grants included, got {included_countries}. "
        "If this fails, OepmXmlNormalizer does NOT generalize cleanly to non-ES XML -- "
        "per ADR 0020 §6/§7 item 5, do not assume it does; a jurisdiction-specific "
        "adapter is required scope, not this plan's Task 5."
    )

    # CN fixture uses kind="B" (not B1/B2) -- exercises that non-normative single-letter
    # grant codes from some offices are NOT silently accepted; this is expected to
    # exclude, and documents the boundary rather than hiding it.
    excluded_ids = {r.excluded.publication_id for r in excluded}
    assert "CN112233445B" in excluded_ids
    assert "WO2021123456A1" in excluded_ids  # pending application, correctly excluded

    us_doc = next(r.document for r in included if r.document.country_code == "US")
    assert us_doc.title == "Battery management circuit"
    assert us_doc.classifications_cpc == ["H01M10/48"]
    assert us_doc.publication_date == "2020-06-01"
```

- [ ] **Step 3: Run the test**

Run: `pytest backend/test/integration/infrastructure/sources/test_epo_ops_multi_jurisdiction_normalization.py -v`

Expected outcome is *not* predetermined — this is the contract check ADR 0020 §6 calls for. Two valid outcomes:
  a. **PASS as written** — the normalizer generalizes for EP/US/JP/KR as designed; CN's `kind="B"` and WO's `kind="A1"` are correctly excluded by the grants-only filter. Proceed to Step 4.
  b. **FAIL** — if, e.g., CN's real-world OPS kind-code convention needs to be added to `allowed_kind_codes`, or another jurisdiction's tag layout isn't matched by `_get_element_text`'s pattern list. If this happens: fix the specific gap found (either widen `allowed_kind_codes` with a code you can justify as "grant" per WIPO ST.16, or extend the tag pattern lists in `oepm_xml_normalizer.py`), re-run, and note the concrete gap found in the commit message. Do **not** loosen the test's assertions to paper over an unverified gap.

- [ ] **Step 4: Commit**

```bash
git add backend/test/fixtures/epo_ops_multi_jurisdiction_sample.xml backend/test/integration/infrastructure/sources/test_epo_ops_multi_jurisdiction_normalization.py
git commit -m "$(cat <<'EOF'
test: verify OepmXmlNormalizer generalizes to multi-jurisdiction EPO OPS XML

Contract test per ADR 0020 §6 -- normalizer reusability for non-ES jurisdictions
is verified here, not assumed.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 6: Deterministic selection — `select_frozen_patents`

**Files:**
- Create: `backend/src/main/application/evaluation/patent_corpus_builder.py`
- Test: `backend/test/unit/application/evaluation/test_patent_corpus_builder.py`

**Interfaces:**
- Consumes: `domain.models.patent.PatentDocument` (from normalizer output, already deduped by `PatentValidator`).
- Produces: `select_frozen_patents(documents: list[PatentDocument], target_n: int, minimum_acceptable_n: int) -> list[PatentDocument]` — raises `PatentCorpusConstructionError` (new, defined in this file) if `len(documents) < minimum_acceptable_n`. Used by Task 7's freeze script with `target_n=50000, minimum_acceptable_n=5000` for the real run, and small values in tests.

- [ ] **Step 1: Write the failing test**

```python
# backend/test/unit/application/evaluation/test_patent_corpus_builder.py
"""Unit tests for deterministic sha256(publication_id)-order selection (ADR 0020 §3, §4)."""

import hashlib

import pytest

from application.evaluation.patent_corpus_builder import (
    PatentCorpusConstructionError,
    select_frozen_patents,
)
from domain.models.patent import PatentDocument


def _doc(pub_id: str) -> PatentDocument:
    return PatentDocument(
        publication_id=pub_id,
        country_code=pub_id[:2],
        doc_number=pub_id[2:],
        kind_code="B2",
        title=f"Title {pub_id}",
        abstract=f"Abstract for {pub_id}.",
    )


def test_selection_is_sorted_by_sha256_of_publication_id():
    docs = [_doc("US1"), _doc("US2"), _doc("US3")]
    selected = select_frozen_patents(docs, target_n=3, minimum_acceptable_n=1)

    expected_order = sorted(docs, key=lambda d: hashlib.sha256(d.publication_id.encode()).hexdigest())
    assert [d.publication_id for d in selected] == [d.publication_id for d in expected_order]


def test_selection_caps_at_target_n():
    docs = [_doc(f"US{i}") for i in range(10)]
    selected = select_frozen_patents(docs, target_n=4, minimum_acceptable_n=1)
    assert len(selected) == 4


def test_selection_takes_all_when_below_target():
    docs = [_doc(f"US{i}") for i in range(3)]
    selected = select_frozen_patents(docs, target_n=100, minimum_acceptable_n=1)
    assert len(selected) == 3


def test_selection_raises_below_floor():
    docs = [_doc(f"US{i}") for i in range(3)]
    with pytest.raises(PatentCorpusConstructionError, match="eligible_available_records"):
        select_frozen_patents(docs, target_n=100, minimum_acceptable_n=5)


def test_selection_is_reproducible_across_calls():
    docs = [_doc(f"US{i}") for i in range(20)]
    first = select_frozen_patents(docs, target_n=10, minimum_acceptable_n=1)
    second = select_frozen_patents(list(reversed(docs)), target_n=10, minimum_acceptable_n=1)
    assert [d.publication_id for d in first] == [d.publication_id for d in second]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/application/evaluation/test_patent_corpus_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'application.evaluation.patent_corpus_builder'`

- [ ] **Step 3: Implement**

```python
# backend/src/main/application/evaluation/patent_corpus_builder.py
"""Deterministic, demand-blind selection for PatentCorpus (ADR 0020 §3, §4).

sha256(publication_id)-order selection is deterministic (same universe -> same N
records, byte-identical), auditable (recomputable by anyone from the raw fetched
set), and independent of API delivery order or any demand-side property.
"""

import hashlib

from domain.models.patent import PatentDocument


class PatentCorpusConstructionError(Exception):
    """Raised when the eligible universe is below ADR 0020 §4's minimum_acceptable_N
    floor -- corpus construction is treated as failed, never silently accepted shrunken."""


def select_frozen_patents(
    documents: list[PatentDocument],
    target_n: int,
    minimum_acceptable_n: int,
) -> list[PatentDocument]:
    """Deduplicate by publication_id, sort by sha256(publication_id), and take the
    first min(target_n, eligible_available_records). Raises PatentCorpusConstructionError
    if eligible_available_records < minimum_acceptable_n (ADR 0020 §4)."""
    unique_by_id = {doc.publication_id: doc for doc in documents}
    eligible_available_records = len(unique_by_id)

    if eligible_available_records < minimum_acceptable_n:
        raise PatentCorpusConstructionError(
            f"PatentCorpus construction failed: eligible_available_records="
            f"{eligible_available_records} < minimum_acceptable_N={minimum_acceptable_n} "
            "(ADR 0020 §4). Resolving this means revisiting the inclusion contract "
            "(§2) explicitly -- not silently accepting a shrunken corpus."
        )

    ordered = sorted(
        unique_by_id.values(),
        key=lambda doc: hashlib.sha256(doc.publication_id.encode("utf-8")).hexdigest(),
    )
    n_final = min(target_n, eligible_available_records)
    return ordered[:n_final]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/unit/application/evaluation/test_patent_corpus_builder.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/application/evaluation/patent_corpus_builder.py backend/test/unit/application/evaluation/test_patent_corpus_builder.py
git commit -m "$(cat <<'EOF'
feat: add deterministic sha256(publication_id)-order patent selection (ADR 0020 §3/§4)

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 7: `scripts/freeze_patent_corpus.py` orchestration + end-to-end fixture test

**Files:**
- Create: `scripts/freeze_patent_corpus.py`
- Test: `backend/test/integration/scripts/test_freeze_patent_corpus.py`

**Interfaces:**
- Consumes: `EpoOpsClient` (Task 3's `fetch_all_ops_batches`), `OepmXmlNormalizer` (Task 4), `PatentValidator` (existing, dedup), `select_frozen_patents` (Task 6), `PatentCorpus`/`PatentCorpusItem` (Task 1), `ops_query.build_patent_corpus_cql` (Task 2).
- Produces: a callable `build_patent_corpus(client: EpoOpsClient, cql_query: str, target_n: int, minimum_acceptable_n: int, dataset_id: str, dataset_version: str, description: str) -> PatentCorpus` that the test imports directly (refactored out of `main()` exactly as `freeze_phase2_demand_corpus.py`'s `process()`/`main()` split does), plus a `main()` CLI entrypoint that writes `data/evaluation/dataset_patent_corpus_p.{json,manifest.json,sha256}`.

- [ ] **Step 1: Write the end-to-end fixture test first**

```python
# backend/test/integration/scripts/test_freeze_patent_corpus.py
"""End-to-end fixture test for scripts/freeze_patent_corpus.py's build_patent_corpus().

No live EPO OPS credentials required (ADR 0020 §6) -- runs entirely against the
multi-jurisdiction fixture from Task 5.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from freeze_patent_corpus import build_patent_corpus  # noqa: E402

from application.evaluation.patent_corpus_builder import PatentCorpusConstructionError  # noqa: E402
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient  # noqa: E402

FIXTURE = REPO_ROOT / "backend" / "test" / "fixtures" / "epo_ops_multi_jurisdiction_sample.xml"


def test_build_patent_corpus_from_fixture_succeeds_below_target():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    corpus = build_patent_corpus(
        client=client,
        cql_query="(pn=EP or pn=US or pn=JP or pn=CN or pn=KR or pn=WO) and pd within \"20160101 20261231\"",
        target_n=50000,
        minimum_acceptable_n=1,
        dataset_id="nexus-patent-corpus-p-test",
        dataset_version="0.0.1-test",
        description="test run over fixture",
    )

    # Fixture has 6 docs; CN (kind=B) and WO (kind=A1) are excluded by grants-only filter.
    assert len(corpus.patents) == 4
    assert {p.country_code for p in corpus.patents} == {"EP", "US", "JP", "KR"}


def test_build_patent_corpus_raises_below_floor():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    with pytest.raises(PatentCorpusConstructionError):
        build_patent_corpus(
            client=client,
            cql_query="(pn=EP) and pd within \"20160101 20261231\"",
            target_n=50000,
            minimum_acceptable_n=1000,  # far above the 4 grants the fixture yields
            dataset_id="nexus-patent-corpus-p-test",
            dataset_version="0.0.1-test",
            description="test run over fixture",
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/integration/scripts/test_freeze_patent_corpus.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'freeze_patent_corpus'`

- [ ] **Step 3: Implement the script**

```python
#!/usr/bin/env python3
# scripts/freeze_patent_corpus.py
"""Freezes PatentCorpus (`P`), ADR 0020's demand-blind, jurisdiction/grant/window-
determined patent artifact, into a hashed, reproducible dataset artifact.

Mirrors scripts/freeze_phase2_demand_corpus.py's freezing discipline: reproducible
acquisition -> committed dataset file -> manifest JSON -> sha256 sidecar. Unlike that
script, this one is fixture-testable end-to-end without live credentials (ADR 0020 §6);
`main()` requires EPO_OPS_KEY/EPO_OPS_SECRET for the real ~50,000-record run.

Outputs (data/evaluation/):
- dataset_patent_corpus_p.json            canonical patent corpus (PatentCorpus)
- dataset_patent_corpus_p.manifest.json   identity/hash manifest
- dataset_patent_corpus_p.sha256          sha256sum-compatible sidecar
"""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.evaluation.patent_corpus_builder import select_frozen_patents  # noqa: E402
from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer  # noqa: E402
from application.ingestion.validator import PatentValidator  # noqa: E402
from domain.models.evaluation import DataModality, EvaluationProvenance, PatentCorpus, PatentCorpusItem  # noqa: E402
from domain.models.ingestion import RecordDisposition  # noqa: E402
from domain.models.patent import PatentDocument  # noqa: E402
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient  # noqa: E402
from infrastructure.sources.patent.ops_pagination import fetch_all_ops_batches  # noqa: E402
from infrastructure.sources.patent.ops_query import build_patent_corpus_cql  # noqa: E402

OUT_DIR = REPO_ROOT / "data" / "evaluation"
OUT_BASENAME = "dataset_patent_corpus_p"

JURISDICTIONS = ["EP", "US", "JP", "CN", "KR", "WO"]
GRANT_KIND_CODES = frozenset({"B1", "B2"})
TARGET_N = 50000
MINIMUM_ACCEPTABLE_N = 5000
DATASET_ID = "nexus-patent-corpus-p-v1"
SCHEMA_VERSION = "1.0.0"
DATASET_VERSION = "1.0.0"


def build_patent_corpus(
    client: EpoOpsClient,
    cql_query: str,
    target_n: int,
    minimum_acceptable_n: int,
    dataset_id: str,
    dataset_version: str,
    description: str,
) -> PatentCorpus:
    """Fetch (enumerability-verified), normalize (grants-only, multi-jurisdiction),
    dedupe, select (sha256-order, ADR 0020 §3), and assemble a PatentCorpus. Raises
    PatentCorpusConstructionError if the eligible universe is below the floor."""
    normalizer = OepmXmlNormalizer(allowed_kind_codes=GRANT_KIND_CODES)
    validator = PatentValidator()

    documents: list[PatentDocument] = []
    provenance_by_pub_id: dict[str, EvaluationProvenance] = {}

    for raw_payload in fetch_all_ops_batches(client, cql_query=cql_query):
        for result in normalizer.normalize_results(raw_payload):
            validated = validator.validate_normalization_result(result)
            if validated.disposition != RecordDisposition.INCLUDED or validated.document is None:
                continue
            documents.append(validated.document)
            provenance_by_pub_id[validated.document.publication_id] = EvaluationProvenance(
                source_authority="European Patent Office (EPO OPS 3.2)",
                source_uri="https://ops.epo.org",
                extraction_timestamp=raw_payload.retrieval_timestamp,
                raw_payload_sha256=raw_payload.payload_sha256,
                modality=DataModality.OBSERVED,
            )

    selected = select_frozen_patents(documents, target_n=target_n, minimum_acceptable_n=minimum_acceptable_n)

    items = [
        PatentCorpusItem(
            publication_id=doc.publication_id,
            country_code=doc.country_code,
            kind_code=doc.kind_code,
            title=doc.title,
            abstract=doc.abstract,
            publication_date=doc.publication_date,
            classifications_cpc=doc.classifications_cpc,
            provenance=provenance_by_pub_id[doc.publication_id],
        )
        for doc in selected
    ]

    return PatentCorpus(
        dataset_id=dataset_id,
        schema_version=SCHEMA_VERSION,
        dataset_version=dataset_version,
        description=description,
        patents=items,
    )


def main() -> None:
    current_year = datetime.now(UTC).year
    cql_query = build_patent_corpus_cql(
        jurisdictions=JURISDICTIONS,
        min_publication_year=current_year - 10,
        max_publication_year=current_year,
    )
    client = EpoOpsClient()  # reads EPO_OPS_KEY/EPO_OPS_SECRET from env

    print(f"Fetching PatentCorpus universe: {cql_query}")
    corpus = build_patent_corpus(
        client=client,
        cql_query=cql_query,
        target_n=TARGET_N,
        minimum_acceptable_n=MINIMUM_ACCEPTABLE_N,
        dataset_id=DATASET_ID,
        dataset_version=DATASET_VERSION,
        description=(
            f"Nexus PatentCorpus (P): {', '.join(JURISDICTIONS)} grants, "
            f"{current_year - 10}-{current_year}. See docs/adr/"
            "0020-experimental-corpus-architecture-demand-times-patent.md."
        ),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = OUT_DIR / f"{OUT_BASENAME}.json"
    dataset_json = corpus.model_dump_json(indent=2) + "\n"
    dataset_path.write_text(dataset_json, encoding="utf-8")

    content_sha256 = hashlib.sha256(dataset_json.encode("utf-8")).hexdigest()

    manifest_path = OUT_DIR / f"{OUT_BASENAME}.manifest.json"
    manifest = {
        "dataset_id": DATASET_ID,
        "schema_version": SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "source_authorities": ["European Patent Office (EPO OPS 3.2)"],
        "jurisdictions": JURISDICTIONS,
        "patent_count": len(corpus.patents),
        "content_sha256": content_sha256,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    sha256_path = OUT_DIR / f"{OUT_BASENAME}.sha256"
    sha256_path.write_text(f"{content_sha256}  {dataset_path.name}\n", encoding="utf-8")

    print(f"\nFrozen {len(corpus.patents)} patents.")
    print(f"  {dataset_path}")
    print(f"  {manifest_path}")
    print(f"  {sha256_path}")
    print(f"  content_sha256={content_sha256}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/test/integration/scripts/test_freeze_patent_corpus.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/freeze_patent_corpus.py backend/test/integration/scripts/test_freeze_patent_corpus.py
git commit -m "$(cat <<'EOF'
feat: add scripts/freeze_patent_corpus.py orchestrating PatentCorpus construction

Fixture-testable end-to-end without live EPO OPS credentials (ADR 0020 §6).
main() performs the real ~50,000-record run once credentials are available.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01HcLSNApMGvtCP9ZBYgnvTJ
EOF
)"
```

---

### Task 8: Full-suite regression check

**Files:** none (verification only).

- [ ] **Step 1: Run the entire backend test suite**

Run: `pytest -q`
Expected: all tests pass, including every test from Tasks 1-7 and the pre-existing suite (especially `backend/test/integration/infrastructure/sources/test_epo_ops.py`, `backend/test/unit/domain/test_phase2_demand_corpus_frozen.py`, and anything under `backend/test/unit/application/ingestion/` — Task 4's normalizer change must not alter their outcomes).

- [ ] **Step 2: If anything regressed, fix forward**

Do not weaken assertions in pre-existing tests to accommodate this change; the `allowed_kind_codes` default is designed to make Task 4 a no-op for every existing caller. A regression here means the default wiring is wrong — fix `OepmXmlNormalizer.__init__`, not the failing test.

- [ ] **Step 3: No commit needed for this task** (verification-only; any fixes made in Step 2 get their own commit under the task they belong to).

---

## What this plan does not do (ADR 0020 §7, explicitly out of scope)

- Does not run the real ~50,000-record live EPO OPS ingestion — that's a human running `python scripts/freeze_patent_corpus.py` once `EPO_OPS_KEY`/`EPO_OPS_SECRET` are available, producing the actual `data/evaluation/dataset_patent_corpus_p.*` files. This plan makes that run possible and fixture-verified; it does not perform it.
- Does not modify `DemandCorpus`, `AnnotationPoolEligibilityPolicy`, or `CandidatePoolBuilder`. Note for whoever resumes PR-E1 (not this plan's job): `AnnotationPoolEligibilityPolicy.__init__` currently defaults `target_jurisdiction="ES"`, which would reject every `P` patent (all EP/US/JP/CN/KR/WO) if left at its default when pool-building resumes — that's a PR-E1-time wiring decision (which jurisdiction(s) to pass), not something to pre-decide here.
- Does not reopen PR-E1's 8-demand selection, guide, or boundary criteria.
- Does not add CPC/topical stratification anywhere in the pipeline (ADR 0020 §2, enforcement item 4).
- Does not touch `BigQueryPatentsDataSource` (confirmed non-functional mock, not used, ADR 0020 context).

## Self-Review

**1. Spec coverage:**
- ADR §2 jurisdictions EP/US/JP/CN/KR/WO → Task 2 (query), Task 4/5 (normalizer, grants filter across jurisdictions). ✓
- ADR §2 grants only → Task 4, Task 5's WO/CN exclusion assertions. ✓
- ADR §2 10-year window → Task 2's `min_publication_year`/`max_publication_year`, Task 7's `main()` computing `current_year - 10`. ✓
- ADR §2 no CPC curation → nowhere in the pipeline filters/sorts by CPC; `select_frozen_patents` (Task 6) sorts only by `sha256(publication_id)`. ✓
- ADR §3 sha256(publication_id) ordering → Task 6. ✓
- ADR §4 target/floor/`N_final` → Task 6 (`select_frozen_patents`), Task 7 (`TARGET_N`/`MINIMUM_ACCEPTABLE_N` wiring). ✓
- ADR §5 freezing discipline (manifest + sha256 sidecar, mirroring `freeze_phase2_demand_corpus.py`) → Task 7. ✓
- ADR §6 fixture testability → every task's tests run without credentials; `EpoOpsClient.from_fixture_file` used throughout. ✓
- Enumerability requirement (project memory, not yet in ADR text) → Task 3 (`fetch_all_ops_batches` raising instead of truncating). ✓
- Demand-blindness (ADR §1, §7 item 1) → no task imports or references demand data; called out explicitly in Global Constraints and the "what this plan does not do" section. ✓

**2. Placeholder scan:** No TBD/TODO markers; every step has runnable code and exact file paths.

**3. Type consistency:** `PatentDocument` (Task 6/7) vs `PatentCorpusItem` (Task 1) field names cross-checked: `publication_id`, `country_code`, `kind_code`, `title`, `abstract`, `publication_date`, `classifications_cpc` all match by name and type across Tasks 1, 6, and 7's `build_patent_corpus`. `select_frozen_patents`'s signature (`documents, target_n, minimum_acceptable_n`) is used identically in Task 6's tests and Task 7's `build_patent_corpus`. `fetch_all_ops_batches(client, cql_query, page_size, max_records)` signature from Task 3 matches its Task 7 call site (positional/keyword compatible). `OepmXmlNormalizer(allowed_kind_codes=...)` from Task 4 matches its usage in Task 5 and Task 7.
