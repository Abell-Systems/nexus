# Design Specification: Innoget Demand Data Source Integration

**Date:** 2026-08-25  
**Author:** Patent Innovation Agent Team / Antigravity  
**Status:** Approved by User  

---

## 1. Overview

This document specifies the integration of the **Innoget Technology Calls** dataset into the **IP Matchmaker** backend as an independent market-pull demand signal provider (`InnogetDemandDataSource`).

The integration aligns with the existing architecture:
- Data sources supply structured `DemandSignal` records.
- `cluster_patents()` in `clustering.py` evaluates white-space scores without assuming textual matches equal verified cluster demand.
- The `DemandSignal` contract remains unchanged.

---

## 2. Requirements & Key Principles

1. **Explicit Data Source Selection**:
   Controlled by environment variable `DEMAND_SOURCE`:
   - `mock` (default): `MockDemandDataSource`
   - `innoget`: `InnogetDemandDataSource`
   - `composite`: Reserved for future multi-source aggregation (raises `NotImplementedError` for now).

2. **Decoupled & Deterministic CPC Mapping**:
   `Innoget record` $\rightarrow$ `DemandSignal` $\rightarrow$ `CpcMapper`.
   - CPC prefixes are assigned **only** when there is explicit, high-confidence evidence in categories, keywords, or title/description.
   - If evidence is insufficient or ambiguous, `cpc_prefix` **must be `None`**.
   - No forced or guessed CPC assignments to avoid polluting white-space scores.

3. **Independent Data Source**:
   - `InnogetDemandDataSource` acts as a standalone implementation of `DemandDataSource`.
   - `CompositeDemandDataSource` is excluded in this initial phase to prevent duplicated demand signals and score distortion.

4. **Matching Provenance & Traceability**:
   - Internal matching provenance is captured during search queries (query/domain terms $\rightarrow$ matched record fields: `title`, `description`, `category`, `keywords`).
   - Exposed via internal methods/metadata for testability and explainability.

5. **Strict Architectural Boundary**:
   - Innoget provides raw demand observations.
   - The clustering engine (`clustering.py`) determines how demand signals impact `white_space_score`.
   - Match relevance is calculated cleanly without altering the `PatentCluster` or `white_space_score` formulas.

---

## 3. Architecture & Data Flow

```text
[backend/patent_agent/tools/innoget_demands.json]
                        │
                        ▼
            [InnogetDemandDataSource]
            ├── Full-text search & Matching Provenance
            └── CpcMapper (Deterministic, returns CPC or None)
                        │
                        ▼
                 list[DemandSignal]
                        │
                        ▼
            [cluster_patents() in clustering.py]
            ├── Patent Density (0.40)
            ├── Recency (0.20)
            ├── Citation Velocity (0.15)
            └── Demand Signals (0.25)
                        │
                        ▼
               white_space_score
```

---

## 4. Component Details

### 4.1 JSON Fixture Store
- **File**: `backend/patent_agent/tools/innoget_demands.json`
- Stores the 19 complete Innoget technology call records parsed from the input dataset.

### 4.2 Deterministic CPC Mapper (`backend/patent_agent/tools/cpc_mapper.py`)
- Standardizes keyword and category matching to CPC prefixes:
  - `H01M`: Batteries, energy storage, fuel cells, solid-state electrolytes
  - `C01B`: Non-metallic elements, inorganic chemistry, silicon/borate/halide compounds
  - `B01J`: Catalysts, chemical processes, reactors
  - `H01L`: Semiconductors, electronic components
  - `C08L`: Polymers, resins, plastic compositions
  - `G01N`: Materials analysis, substance detection, analytical tools
  - `A61K`: Biological sciences, pharmaceuticals, medical health
  - `A23L` / Agrofood: Food industry technologies, beverages, ingredients
- Returns `str | None`. If no rule matches with high confidence, returns `None`.

### 4.3 Innoget Demand Data Source (`backend/patent_agent/tools/demand_sources.py`)
- `InnogetDemandDataSource`:
  - Loads records from `innoget_demands.json` on initialization.
  - Implements `search_demand(query: str, domain: str, max_results: int = 20) -> list[DemandSignal]`
  - Computes search relevance score based on query & domain keyword occurrences in record `title`, `description`, `category`, `content`, and `related_keywords`.
  - Produces internal `MatchProvenance` (e.g., `matched_fields: ["title", "related_keywords"], score: 3.5`).
  - Converts matched records into `DemandSignal(source="innoget", id=..., title=..., description=..., cpc_prefix=CpcMapper.map(...), posted_date=..., url=...)`.

### 4.4 Data Source Selection (`get_demand_datasource()`)
- Evaluates `DEMAND_SOURCE` environment variable (falling back to `USE_MOCK_DEMAND` if unset for backward compatibility):
  - `"mock"` $\rightarrow$ `MockDemandDataSource()`
  - `"innoget"` $\rightarrow$ `InnogetDemandDataSource()`
  - `"composite"` $\rightarrow$ `raise NotImplementedError("Composite demand source not implemented yet.")`

---

## 5. Verification & Testing Plan

1. **`test_cpc_mapper.py`**:
   - Test explicit CPC assignments for battery/materials/biotech keywords.
   - Test fallback to `None` for generic or unmapped queries ("kitchen sink", "marketing campaign").
2. **`test_innoget_demand.py`**:
   - Test fixture loading and parsing.
   - Test search queries returning valid `DemandSignal` objects.
   - Test matching provenance tracking.
   - Verify compliance with `DemandSignal` contract (`source=="innoget"`).
3. **`test_demand_sources_factory.py`**:
   - Test `DEMAND_SOURCE=innoget` factory configuration.
   - Test backward compatibility with `USE_MOCK_DEMAND`.
4. **End-to-End Pipeline Verification**:
   - Run `cluster_patents_tool` with `DEMAND_SOURCE=innoget` and verify clusters incorporate real Innoget demand signals into `white_space_score`.

---

## 6. Spec Self-Review Checklist

- [x] Placeholder scan: No TBD/TODO items remaining.
- [x] Internal consistency: Models and interfaces match `backend/patent_agent/tools/schemas.py`.
- [x] Scope check: Focused strictly on adding `InnogetDemandDataSource` and `CpcMapper`.
- [x] Ambiguity check: Nullable `cpc_prefix` behavior and `DEMAND_SOURCE` selector rules are explicit.
