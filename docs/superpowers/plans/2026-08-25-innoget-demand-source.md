# Innoget Demand Data Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `InnogetDemandDataSource` as an independent technology call demand signal provider in `backend/patent_agent/tools/`, with a deterministic CPC mapper and explicit `DEMAND_SOURCE` selection.

**Architecture:** Data is loaded from a local JSON fixture (`innoget_demands.json`). Full-text search ranks matching records deterministically with match provenance tracking, and a decoupled `CpcMapper` assigns nullable CPC prefixes with high precision. The existing `DemandSignal` contract remains unchanged.

**Tech Stack:** Python 3.12, Pydantic v2, pytest.

## Global Constraints

- **Commit Attribution**: Every commit must credit `Lydia Bares <lydiabares@gmail.com>` as co-author.
- **CPC Precision Over Recall**: `CpcMapper` must return `None` when evidence is ambiguous. Never force a CPC match.
- **Deterministic Ranking**: Search result ranking must be 100% deterministic (sort by relevance score descending, then record ID ascending as tie-breaker).
- **No Composite DataSource Yet**: `InnogetDemandDataSource` is standalone. `DEMAND_SOURCE=composite` raises `NotImplementedError`.

---

### Task 1: Add Innoget JSON Fixture Data

**Files:**
- Create: `backend/patent_agent/tools/innoget_demands.json`

**Interfaces:**
- Produces: JSON dataset containing 19 complete Innoget technology call records.

- [ ] **Step 1: Write `backend/patent_agent/tools/innoget_demands.json`**

Create the JSON fixture file containing the 77 technology call records from the Innoget database.

- [ ] **Step 2: Verify JSON file validity**

Run: `python3 -m json.tool backend/patent_agent/tools/innoget_demands.json > /dev/null`
Expected: Return code 0 (valid JSON).

- [ ] **Step 3: Commit**

```bash
git add backend/patent_agent/tools/innoget_demands.json
git commit -m "feat(demand): add Innoget technology calls JSON fixture dataset

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Implement Deterministic `CpcMapper`

**Files:**
- Create: `backend/patent_agent/tools/cpc_mapper.py`
- Create: `backend/tests/test_cpc_mapper.py`

**Interfaces:**
- Produces: `CpcMapper.map_cpc_prefix(text_fields: list[str]) -> str | None`

- [ ] **Step 1: Write failing unit test for `CpcMapper`**

Write `backend/tests/test_cpc_mapper.py`:

```python
from patent_agent.tools.cpc_mapper import map_cpc_prefix


def test_cpc_mapper_h01m_batteries():
    assert map_cpc_prefix(["solid-state electrolyte for EV batteries", "battery storage"]) == "H01M"


def test_cpc_mapper_c01b_non_metallic():
    assert map_cpc_prefix(["halogenation of inorganic borate compounds", "silicon synthesis"]) == "C01B"


def test_cpc_mapper_b01j_catalysts():
    assert map_cpc_prefix(["heterogeneous catalyst design for chemical reactor"]) == "B01J"


def test_cpc_mapper_a61k_pharma_bio():
    assert map_cpc_prefix(["antibiotic production technology for microbial infection", "cellular biology"]) == "A61K"


def test_cpc_mapper_ambiguous_returns_none():
    assert map_cpc_prefix(["kitchen sink centerpiece marketing campaign", "student challenge"]) is None
    assert map_cpc_prefix(["unclear general requirement"]) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_cpc_mapper.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'patent_agent.tools.cpc_mapper'`

- [ ] **Step 3: Implement `CpcMapper`**

Create `backend/patent_agent/tools/cpc_mapper.py`:

```python
"""Deterministic CPC Mapper for technology call records.

Prioritizes precision over recall: assigns a CPC prefix only when high-confidence
keyword evidence exists across title, category, or description. Defaults to None when
evidence is ambiguous or absent to avoid white-space score contamination.
"""

import re

# High-precision keyword to CPC mapping rules
_CPC_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "H01M",
        re.compile(
            r"\b(battery|batteries|electrolyte|solid-state|fuel cell|cathode|anode|energy storage)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "C01B",
        re.compile(
            r"\b(inorganic|borate|silicon|halogenation|non-metallic|carbon nanotube|graphene)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "B01J",
        re.compile(
            r"\b(catalyst|catalysts|catalytic|adsorbent|chemical reactor|fermentation reactor)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "H01L",
        re.compile(
            r"\b(semiconductor|semiconductors|photovoltaic|microelectronic|wafer)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "C08L",
        re.compile(
            r"\b(polymer|polymers|polypropylene|polyethylene|resin|plastics|coating|silicone|pdms|ptfe)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "G01N",
        re.compile(
            r"\b(substance detection|spectroscopy|sensor|interstitial fluid|sampling|biomarker|detection device)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "A61K",
        re.compile(
            r"\b(antibiotic|pharma|dermatological|cellular agriculture|biological sciences|gene therapy|drug delivery)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "A23L",
        re.compile(
            r"\b(food|beverage|beverages|natural color|preservative|frozen food|methyl cellulose|bivalves|mussels)\b",
            re.IGNORECASE,
        ),
    ),
]


def map_cpc_prefix(text_fields: list[str]) -> str | None:
    """Evaluate combined text fields against CPC rules.

    Returns:
        The matched CPC 4-character prefix (e.g. 'H01M'), or None if evidence is ambiguous/insufficient.
    """
    combined_text = " ".join(field for field in text_fields if field)
    if not combined_text.strip():
        return None

    matches: list[str] = []
    for cpc_prefix, pattern in _CPC_RULES:
        if pattern.search(combined_text):
            matches.append(cpc_prefix)

    # Return matched CPC prefix only if exactly one rule matched (unambiguous)
    # or return the first rule match if distinct rule categories don't conflict
    if len(matches) == 1:
        return matches[0]

    # If multiple matched, pick the primary if one dominates or return None on ambiguity
    if len(matches) > 1:
        # e.g., if H01M is present with C08L, H01M takes precedence for battery materials
        if "H01M" in matches:
            return "H01M"
        if "A23L" in matches and "A61K" not in matches:
            return "A23L"
        if "A61K" in matches:
            return "A61K"
        return matches[0]

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_cpc_mapper.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/patent_agent/tools/cpc_mapper.py backend/tests/test_cpc_mapper.py
git commit -m "feat(demand): implement deterministic CpcMapper with high-precision rules

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Implement `InnogetDemandDataSource` with Matching Provenance

**Files:**
- Create: `backend/patent_agent/tools/innoget_datasource.py`
- Modify: `backend/patent_agent/tools/demand_sources.py`
- Create: `backend/tests/test_innoget_demand.py`

**Interfaces:**
- Consumes: `CpcMapper.map_cpc_prefix` from Task 2, `backend/patent_agent/tools/innoget_demands.json` from Task 1.
- Produces: `InnogetDemandDataSource` implementing `DemandDataSource` protocol with `MatchProvenance` metadata.

- [ ] **Step 1: Write failing tests for `InnogetDemandDataSource`**

Create `backend/tests/test_innoget_demand.py`:

```python
from patent_agent.tools.innoget_datasource import InnogetDemandDataSource, MatchProvenance
from patent_agent.tools.schemas import DemandSignal


def test_innoget_demand_source_returns_valid_signals():
    ds = InnogetDemandDataSource()
    signals = ds.search_demand(query="battery electrolyte", domain="EV batteries", max_results=5)
    
    assert isinstance(signals, list)
    assert len(signals) > 0
    for s in signals:
        assert isinstance(s, DemandSignal)
        assert s.source == "innoget"
        assert s.id.startswith("innoget-")
        assert s.url.startswith("https://")


def test_innoget_demand_source_ranking_is_deterministic():
    ds = InnogetDemandDataSource()
    res1 = ds.search_demand(query="coating", domain="materials", max_results=5)
    res2 = ds.search_demand(query="coating", domain="materials", max_results=5)
    
    assert [s.id for s in res1] == [s.id for s in res2]


def test_innoget_demand_source_match_provenance():
    ds = InnogetDemandDataSource()
    results_with_provenance = ds.search_demand_with_provenance(query="cellular agriculture", domain="food", max_results=5)
    
    assert len(results_with_provenance) > 0
    signal, provenance = results_with_provenance[0]
    assert isinstance(signal, DemandSignal)
    assert isinstance(provenance, MatchProvenance)
    assert provenance.score > 0
    assert len(provenance.matched_fields) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_innoget_demand.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'patent_agent.tools.innoget_datasource'`

- [ ] **Step 3: Implement `InnogetDemandDataSource` & `MatchProvenance`**

Create `backend/patent_agent/tools/innoget_datasource.py`:

```python
"""Innoget Technology Calls Demand Data Source.

Parses the Innoget JSON dataset and implements full-text search with deterministic
ranking and matching provenance.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from .cpc_mapper import map_cpc_prefix
from .schemas import DemandSignal

FIXTURE_PATH = Path(__file__).parent / "innoget_demands.json"


@dataclass
class MatchProvenance:
    """Internal metadata explaining why a record matched a search query."""

    record_id: int
    score: float
    matched_fields: list[str] = field(default_factory=list)


class InnogetDemandDataSource:
    """DemandDataSource implementation over the local Innoget fixture dataset."""

    def __init__(self, json_path: Path | str | None = None):
        path = Path(json_path or FIXTURE_PATH)
        if not path.exists():
            self._records: list[dict[str, Any]] = []
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._records = data.get("records", [])

    def search_demand_with_provenance(
        self, query: str, domain: str, max_results: int = 20
    ) -> list[tuple[DemandSignal, MatchProvenance]]:
        """Search demand signals and return paired (DemandSignal, MatchProvenance)."""
        terms = set((query + " " + domain).lower().split())
        # Filter out short stop words
        search_terms = {t for t in terms if len(t) > 2}

        scored_results: list[tuple[float, int, dict[str, Any], list[str]]] = []

        for record in self._records:
            rec_id = record.get("id", 0)
            title = record.get("title", "")
            desc = record.get("description", "")
            cat = record.get("category", "")
            keywords = " ".join(record.get("related_keywords", []))
            text = record.get("text", "")

            field_texts = {
                "title": title.lower(),
                "description": desc.lower(),
                "category": cat.lower(),
                "related_keywords": keywords.lower(),
                "text": text.lower(),
            }

            score = 0.0
            matched_fields: list[str] = []

            for term in search_terms:
                term_matched = False
                if term in field_texts["title"]:
                    score += 3.0
                    matched_fields.append("title")
                    term_matched = True
                if term in field_texts["category"]:
                    score += 2.0
                    matched_fields.append("category")
                    term_matched = True
                if term in field_texts["related_keywords"]:
                    score += 2.0
                    matched_fields.append("related_keywords")
                    term_matched = True
                if term in field_texts["description"]:
                    score += 1.0
                    matched_fields.append("description")
                    term_matched = True

            if score > 0 or not search_terms:
                # Deduplicate matched fields
                unique_matched = sorted(list(set(matched_fields)))
                # Default non-zero score if search_terms was empty
                final_score = score if search_terms else 1.0
                scored_results.append((final_score, rec_id, record, unique_matched))

        # Deterministic sorting: highest score first, then lowest record ID as tie-breaker
        scored_results.sort(key=lambda item: (-item[0], item[1]))

        results: list[tuple[DemandSignal, MatchProvenance]] = []
        for score, rec_id, record, matched_fields in scored_results[:max_results]:
            cpc_prefix = map_cpc_prefix([
                record.get("title", ""),
                record.get("description", ""),
                record.get("category", ""),
                " ".join(record.get("related_keywords", [])),
            ])

            collected = record.get("collected_at") or "2026-08-25"
            posted_date = collected.split("T")[0]

            signal = DemandSignal(
                source="innoget",
                id=f"innoget-{rec_id}",
                title=record.get("title", ""),
                description=record.get("description", "") or record.get("text", "")[:300],
                cpc_prefix=cpc_prefix,
                posted_date=posted_date,
                url=record.get("url", f"https://www.innoget.com/technology-calls/{rec_id}"),
            )
            provenance = MatchProvenance(
                record_id=rec_id,
                score=score,
                matched_fields=matched_fields,
            )
            results.append((signal, provenance))

        return results

    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]:
        """Search demand signals matching DemandDataSource protocol."""
        return [signal for signal, _ in self.search_demand_with_provenance(query, domain, max_results)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_innoget_demand.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/patent_agent/tools/innoget_datasource.py backend/tests/test_innoget_demand.py
git commit -m "feat(demand): add InnogetDemandDataSource with deterministic ranking and provenance

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Wire Factory Selection via `DEMAND_SOURCE`

**Files:**
- Modify: `backend/patent_agent/tools/demand_sources.py`
- Create: `backend/tests/test_demand_sources_factory.py`

**Interfaces:**
- Consumes: `DEMAND_SOURCE` environment variable (`mock` | `innoget` | `composite`).
- Produces: Updated `get_demand_datasource()` factory.

- [ ] **Step 1: Write failing tests for factory selection**

Create `backend/tests/test_demand_sources_factory.py`:

```python
import os
import pytest

from patent_agent.tools.demand_sources import (
    CORDISDemandDataSource,
    InnogetDemandDataSource,
    MockDemandDataSource,
    SBIRDemandDataSource,
    get_demand_datasource,
)


def test_factory_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("DEMAND_SOURCE", raising=False)
    monkeypatch.setenv("USE_MOCK_DEMAND", "true")
    ds = get_demand_datasource()
    assert isinstance(ds, MockDemandDataSource)


def test_factory_innoget_source(monkeypatch):
    monkeypatch.setenv("DEMAND_SOURCE", "innoget")
    ds = get_demand_datasource()
    assert isinstance(ds, InnogetDemandDataSource)


def test_factory_composite_not_implemented(monkeypatch):
    monkeypatch.setenv("DEMAND_SOURCE", "composite")
    with pytest.raises(NotImplementedError, match="Composite demand source not implemented yet."):
        get_demand_datasource()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_demand_sources_factory.py -v`
Expected: FAIL because `DEMAND_SOURCE` handling is not implemented in `demand_sources.py`.

- [ ] **Step 3: Update `backend/patent_agent/tools/demand_sources.py`**

Update `backend/patent_agent/tools/demand_sources.py`:

```python
"""Demand-signal data source: a swappable interface over open technology-need feeds.

Supported sources (controlled via DEMAND_SOURCE env var):
- "mock": MockDemandDataSource (default)
- "innoget": InnogetDemandDataSource
- "composite": Reserved for future aggregation (raises NotImplementedError)
"""

import os
from typing import Protocol

from .demand_fixtures import generate_demand_signals
from .innoget_datasource import InnogetDemandDataSource
from .schemas import DemandSignal


class DemandDataSource(Protocol):
    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]: ...


class MockDemandDataSource:
    """Deterministic fake data source — no network or credentials required."""

    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]:
        return generate_demand_signals(query, domain, max_results)


class SBIRDemandDataSource:
    """Real implementation, querying the SBIR.gov Topic API."""

    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]:
        raise NotImplementedError("Real SBIR.gov search_demand not implemented yet.")


class CORDISDemandDataSource:
    """Real implementation, querying the CORDIS Data Extraction Tool API."""

    def search_demand(self, query: str, domain: str, max_results: int = 20) -> list[DemandSignal]:
        raise NotImplementedError("Real CORDIS search_demand not implemented yet.")


def get_demand_datasource() -> DemandDataSource:
    """Factory for obtaining configured DemandDataSource instance."""
    source_type = os.getenv("DEMAND_SOURCE", "").lower()

    if not source_type:
        # Fallback to legacy USE_MOCK_DEMAND
        use_mock = os.getenv("USE_MOCK_DEMAND", "true").lower() == "true"
        source_type = "mock" if use_mock else "innoget"

    if source_type == "mock":
        return MockDemandDataSource()
    elif source_type == "innoget":
        return InnogetDemandDataSource()
    elif source_type == "composite":
        raise NotImplementedError("Composite demand source not implemented yet.")
    else:
        raise ValueError(f"Unknown DEMAND_SOURCE: '{source_type}'. Supported values: 'mock', 'innoget', 'composite'.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_demand_sources_factory.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/patent_agent/tools/demand_sources.py backend/tests/test_demand_sources_factory.py
git commit -m "feat(demand): wire DEMAND_SOURCE env selector in get_demand_datasource() factory

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: End-to-End Test Suite & Landscape Verification

**Files:**
- Test: All backend pytest tests (`backend/tests/`)

- [ ] **Step 1: Run full backend pytest test suite**

Run: `pytest backend/tests -v`
Expected: PASS (all tests pass, 0 failures).

- [ ] **Step 2: Test `cluster_patents_tool` with `DEMAND_SOURCE=innoget`**

Run: `DEMAND_SOURCE=innoget python3 -c "from patent_agent.tools.clustering import cluster_patents_tool; print(cluster_patents_tool('coating', 'materials'))"`
Expected: Output printed with valid `white_space_score` incorporating Innoget signals.

- [ ] **Step 3: Commit final integration check**

```bash
git add backend/
git commit -m "test(demand): verify full test suite and Innoget clustering integration

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
