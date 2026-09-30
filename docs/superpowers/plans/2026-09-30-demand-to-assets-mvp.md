# Demand → Spanish Assets MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the 39 pre-embedded example demands over the operational corpus through a read-only API and a three-step React screen, using the frozen dense retriever, with no score or quality claim exposed.

**Architecture:** An operational eligibility policy (ES + title + abstract) is defined once and shared by the API and the probe builder. A use case in `application/matching/` ranks assets for a known demand through the existing `PatentCandidateRetriever` port. An `infrastructure/operational/` package verifies hashes at startup, builds the retriever and answers two routes, mounted behind `NEXUS_MVP_ENABLED=1`. The frontend adds a separate entry (`/matches`) and leaves the legacy flow untouched.

**Tech Stack:** Python 3.12, FastAPI, numpy, pyarrow, pydantic; React 19 + TypeScript + vitest + Testing Library; existing Import Linter and `check_architecture.py` gates.

**Spec:** `docs/superpowers/specs/2026-09-30-demand-to-assets-mvp-design.md` (and, for the engine, `2026-09-30-operational-dense-retrieval-design.md` including Amendment A1). Read both.

## Global Constraints

- Clean Architecture: `domain` ← `application` ← `infrastructure`; `application` imports only `domain`. Backend never imports `experiments/` (ADR 0026). Runtime never imports `torch`, `transformers`, `sentence_transformers` (ADR 0014).
- Operational eligibility policy is exactly: `country_code == "ES"` AND non-empty title AND non-empty abstract. No temporal rule. It is written in one function, `operational_eligibility_policy()`; the API and `build_probe_sheets.py` both call it. `DefaultPatentEligibilityPolicy` (Lab) is not modified.
- API responses contain `rank` only as an ordering signal: no raw score, no `similarity`, no `band`/`relevance_band` key at any depth.
- `limit` is 1..10, default 5. Fewer eligible assets than `limit` returns fewer, never padded.
- Routes exist only when `NEXUS_MVP_ENABLED=1`; when enabled, any missing or hash-mismatched artifact aborts startup. No fallback to BM25 or a live model.
- Four fixed notices are served by the backend (spec section 7); the UI renders what it receives.
- No "Señales de coincidencia" block (the 39 demands carry no CPC).
- Tests are named `test_should_...` in `*Test` classes (backend, `pytest.ini`); frontend tests live in `frontend/test/unit/`.
- Every commit carries: `Co-Authored-By: Lydia Bares <lydiabares@gmail.com>`, `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, `Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H`.
- Data under `data/snapshots/operational_corpus_v1/` is **not committed** (licence unverified). Tests use synthetic fixtures only.
- Gates that must stay green: `pytest`, `ruff check backend/src/main backend/test scripts`, `mypy backend/src/main --ignore-missing-imports`, `python scripts/check_architecture.py`, `PYTHONPATH=backend/src/main lint-imports`, and in `frontend/`: `npm run typecheck`, `npm run lint`, `npm test`.

## Review Focus

- `limit=0` and `limit=11` return 422; `limit` larger than the eligible set returns fewer results, never padded. (Task 5)
- A demand with `posted_date = null` (all 39) still returns results; the policy must not depend on dates. (Task 1, Task 4)
- The JSON never contains a score-like key at any depth, including inside `meta`. (Task 4, Task 5)
- An embeddings index generated for a different corpus or a different demand file must abort startup, not serve shifted results. (Task 4)
- The SPA catch-all route must not shadow `/api/matches` and `/api/demand-examples`. (Task 5)

---

### Task 1: Operational eligibility policy and asset loader

**Files:**
- Modify: `backend/src/main/infrastructure/matching/operational_corpus.py`
- Modify: `experiments/operational-dense-probe/build_probe_sheets.py`
- Test: `backend/test/unit/infrastructure/matching/test_operational_corpus.py` (extend)

**Interfaces:**
- Consumes: `PatentDocument`, `EligibilityResult`, `EligibilityReason`, `PatentEligibilityPolicy`, `DemandSignal`.
- Produces in `operational_corpus.py`:
  - `class OperationalEligibilityPolicy(PatentEligibilityPolicy)` with `evaluate(patent, demand) -> EligibilityResult`
  - `operational_eligibility_policy() -> OperationalEligibilityPolicy`
  - `@dataclass(frozen=True) class OperationalAsset` with `patent: PatentDocument`, `ip_type: str`, `abstract_language: str`
  - `load_operational_assets(parquet_path: Path) -> list[OperationalAsset]` (parquet order; optional columns default when absent: `ip_type` → `"unknown"`, `abstract_language` → `""`, lists → `[]`, dates/family → `None`)
  - `load_operational_patents(parquet_path)` keeps its signature and now returns `[a.patent for a in load_operational_assets(...)]`.

- [ ] **Step 1: Write the failing tests** (append to the existing test file; keep the existing test)

```python
# append to backend/test/unit/infrastructure/matching/test_operational_corpus.py
from pathlib import Path

from domain.models.demand import DemandSignal
from domain.models.matching import EligibilityReason
from domain.models.patent import PatentDocument
from infrastructure.matching.operational_corpus import (
    load_operational_assets,
    operational_eligibility_policy,
)

REPO_ROOT = Path(__file__).resolve().parents[5]


def _patent(country="ES", title="T", abstract="A", published="2020-01-01"):
    return PatentDocument(
        publication_id=f"{country}-1-A1", country_code=country, doc_number="1", kind_code="A1",
        title=title, abstract=abstract, publication_date=published,
    )


def _demand(posted_date=None):
    return DemandSignal(demand_id="D", title="t", description="d", posted_date=posted_date)


class OperationalEligibilityPolicyTest:
    def test_should_accept_es_asset_when_demand_has_no_posted_date(self):
        result = operational_eligibility_policy().evaluate(_patent(), _demand(posted_date=None))
        assert result.is_eligible and result.reason == EligibilityReason.ELIGIBLE

    def test_should_accept_asset_published_after_demand_date_because_no_temporal_rule_exists(self):
        result = operational_eligibility_policy().evaluate(_patent(published="2030-01-01"), _demand("2018-01-01"))
        assert result.is_eligible

    def test_should_exclude_ep_asset_when_jurisdiction_is_not_es(self):
        result = operational_eligibility_policy().evaluate(_patent(country="EP"), _demand())
        assert not result.is_eligible and result.reason == EligibilityReason.EXCLUDED_JURISDICTION

    def test_should_exclude_asset_when_abstract_is_blank(self):
        result = operational_eligibility_policy().evaluate(_patent(abstract="   "), _demand())
        assert not result.is_eligible and result.reason == EligibilityReason.EXCLUDED_MISSING_TEXT

    def test_should_exclude_asset_when_title_is_blank(self):
        result = operational_eligibility_policy().evaluate(_patent(title=""), _demand())
        assert not result.is_eligible and result.reason == EligibilityReason.EXCLUDED_MISSING_TEXT

    def test_should_obtain_policy_from_the_single_factory_when_building_probe_sheets(self):
        source = (REPO_ROOT / "experiments" / "operational-dense-probe" / "build_probe_sheets.py").read_text(encoding="utf-8")
        assert "operational_eligibility_policy()" in source
        assert "DefaultPatentEligibilityPolicy" not in source


class LoadOperationalAssetsTest:
    def test_should_fill_holders_cpc_type_and_language_when_optional_columns_exist(self, tmp_path):
        table = pa.table(
            {
                "publication_number": ["ES-2594181-U"],
                "country_code": ["ES"],
                "kind_code": ["U"],
                "title": ["Dispositivo"],
                "abstract": ["Un dispositivo."],
                "publication_date": ["2016-12-16"],
                "ip_type": ["utility_model"],
                "abstract_language": ["es"],
                "assignees": [["ACME SA"]],
                "inventors": [["ANA", "LUIS"]],
                "cpc_codes": [["B60K1/00"]],
                "filing_date": ["2016-01-02"],
                "family_id": ["123"],
            }
        )
        path = tmp_path / "publications.parquet"
        pq.write_table(table, path)

        asset = load_operational_assets(path)[0]

        assert asset.ip_type == "utility_model" and asset.abstract_language == "es"
        assert asset.patent.assignees == ["ACME SA"] and asset.patent.inventors == ["ANA", "LUIS"]
        assert asset.patent.classifications_cpc == ["B60K1/00"]
        assert asset.patent.filing_date == "2016-01-02" and asset.patent.family_id == "123"

    def test_should_default_optional_fields_when_columns_are_absent(self, tmp_path):
        table = pa.table(
            {
                "publication_number": ["ES-1-A1"], "country_code": ["ES"], "kind_code": ["A1"],
                "title": ["T"], "abstract": ["A"], "publication_date": ["2020-01-01"],
            }
        )
        path = tmp_path / "publications.parquet"
        pq.write_table(table, path)

        asset = load_operational_assets(path)[0]

        assert asset.ip_type == "unknown" and asset.abstract_language == ""
        assert asset.patent.assignees == [] and asset.patent.classifications_cpc == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/test/unit/infrastructure/matching/test_operational_corpus.py -v`
Expected: FAIL with `ImportError: cannot import name 'load_operational_assets'`

- [ ] **Step 3: Write the implementation**

Replace the content of `backend/src/main/infrastructure/matching/operational_corpus.py` with:

```python
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq

from domain.models.demand import DemandRecord, DemandSignal
from domain.models.matching import EligibilityReason, EligibilityResult
from domain.models.patent import PatentDocument
from domain.protocols.matching import PatentEligibilityPolicy

_REQUIRED = ["publication_number", "country_code", "kind_code", "title", "abstract", "publication_date"]
_OPTIONAL = ["ip_type", "abstract_language", "assignees", "inventors", "cpc_codes", "filing_date", "family_id"]
OPERATIONAL_JURISDICTION = "ES"


class OperationalEligibilityPolicy(PatentEligibilityPolicy):
    """Which Spanish assets of the operational corpus are candidates for a demand.

    Jurisdiction ES AND non-empty title AND non-empty abstract, nothing else. The temporal prior-art rule
    belongs to the Lab's DefaultPatentEligibilityPolicy and is deliberately not part of this policy
    (retrieval spec, Amendment A1): it answers a different question, and the demand corpus has no dates.
    """

    def evaluate(self, patent: PatentDocument, demand: DemandRecord | DemandSignal) -> EligibilityResult:
        pub_id = patent.publication_id
        if (patent.country_code or "").upper() != OPERATIONAL_JURISDICTION:
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_JURISDICTION,
                details=f"Expected jurisdiction {OPERATIONAL_JURISDICTION}, got '{patent.country_code}'",
            )
        if not (patent.title or "").strip() or not (patent.abstract or "").strip():
            return EligibilityResult(
                publication_id=pub_id,
                is_eligible=False,
                reason=EligibilityReason.EXCLUDED_MISSING_TEXT,
                details="Asset must have both non-empty title and abstract",
            )
        return EligibilityResult(publication_id=pub_id, is_eligible=True, reason=EligibilityReason.ELIGIBLE)


def operational_eligibility_policy() -> OperationalEligibilityPolicy:
    """The single place the operational eligibility rule is obtained (API and probe builder)."""
    return OperationalEligibilityPolicy()


@dataclass(frozen=True)
class OperationalAsset:
    patent: PatentDocument
    ip_type: str
    abstract_language: str


def load_operational_assets(parquet_path: Path) -> list[OperationalAsset]:
    """Loads the operational corpus snapshot, preserving parquet row order."""
    available = set(pq.read_schema(parquet_path).names)
    columns = _REQUIRED + [c for c in _OPTIONAL if c in available]
    rows = pq.read_table(parquet_path, columns=columns).to_pylist()
    assets: list[OperationalAsset] = []
    for row in rows:
        publication_id = str(row["publication_number"])
        parts = publication_id.split("-")
        patent = PatentDocument(
            publication_id=publication_id,
            country_code=str(row["country_code"] or ""),
            doc_number=parts[1] if len(parts) > 1 else "",
            kind_code=str(row["kind_code"] or ""),
            title=str(row["title"] or ""),
            abstract=str(row["abstract"] or ""),
            publication_date=str(row["publication_date"]) if row["publication_date"] else None,
            assignees=list(row.get("assignees") or []),
            inventors=list(row.get("inventors") or []),
            classifications_cpc=list(row.get("cpc_codes") or []),
            filing_date=str(row["filing_date"]) if row.get("filing_date") else None,
            family_id=str(row["family_id"]) if row.get("family_id") else None,
        )
        assets.append(
            OperationalAsset(
                patent=patent,
                ip_type=str(row.get("ip_type") or "unknown"),
                abstract_language=str(row.get("abstract_language") or ""),
            )
        )
    return assets


def load_operational_patents(parquet_path: Path) -> list[PatentDocument]:
    return [asset.patent for asset in load_operational_assets(parquet_path)]
```

In `experiments/operational-dense-probe/build_probe_sheets.py` make two edits: replace the import line
`from infrastructure.matching.eligibility import DefaultPatentEligibilityPolicy  # noqa: E402` with
`from infrastructure.matching.operational_corpus import load_operational_patents, operational_eligibility_policy  # noqa: E402`
(and delete the separate `from infrastructure.matching.operational_corpus import load_operational_patents  # noqa: E402` line), and replace
`policy = DefaultPatentEligibilityPolicy(target_jurisdiction="ES")` with `policy = operational_eligibility_policy()`.

- [ ] **Step 4: Run tests and gates**

Run: `pytest backend/test/unit/infrastructure/matching backend/test/unit/infrastructure/embeddings experiments/operational-dense-probe -q && ruff check backend/src/main backend/test scripts experiments/operational-dense-probe && mypy backend/src/main --ignore-missing-imports`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/matching/operational_corpus.py backend/test/unit/infrastructure/matching/test_operational_corpus.py experiments/operational-dense-probe/build_probe_sheets.py
git commit -m "feat(matching): operational eligibility policy without temporal rule (A1)" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 2: Demand snapshot script and repository

**Files:**
- Create: `scripts/build_demands_snapshot.py`
- Create: `backend/src/main/domain/protocols/demand_repository.py`
- Create: `backend/src/main/infrastructure/operational/__init__.py`
- Create: `backend/src/main/infrastructure/operational/demands.py`
- Test: `backend/test/unit/test_demands_snapshot_script.py`
- Test: `backend/test/unit/infrastructure/operational/__init__.py` (empty) and `backend/test/unit/infrastructure/operational/test_demands.py`

**Interfaces:**
- Produces:
  - `scripts/build_demands_snapshot.py::build_snapshot(demand_corpus_path: Path) -> dict` → `{"source_sha256": str, "demands": [{demand_id, title, description, posted_date, origin_country, source_url}]}` (corpus order; `source_url` = `provenance.source_uri`, `""` when absent)
  - `DemandRepository` Protocol (`domain/protocols/demand_repository.py`): `get(demand_id: str) -> DemandSignal | None`, `list_all() -> list[DemandSignal]`
  - `JsonDemandRepository(path: Path)` with the two methods above and `source_sha256: str` property (the value stored in the snapshot).

- [ ] **Step 1: Write the failing tests**

```python
# backend/test/unit/test_demands_snapshot_script.py
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BuildDemandsSnapshotTest:
    def test_should_keep_corpus_order_and_copy_text_verbatim_when_building_snapshot(self, tmp_path):
        corpus = tmp_path / "demands.json"
        corpus.write_text(
            json.dumps(
                {
                    "demands": [
                        {"demand_id": "D-2", "title": "Two", "description": "second\nline", "posted_date": None,
                         "origin_country": "Spain", "provenance": {"source_uri": "https://x.org/2"}},
                        {"demand_id": "D-1", "title": "One", "description": "first", "posted_date": None,
                         "origin_country": "ES", "provenance": {}},
                    ]
                }
            ),
            encoding="utf-8",
        )

        snapshot = _load_script("build_demands_snapshot").build_snapshot(corpus)

        assert [d["demand_id"] for d in snapshot["demands"]] == ["D-2", "D-1"]
        assert snapshot["demands"][0]["description"] == "second\nline"
        assert snapshot["demands"][0]["source_url"] == "https://x.org/2"
        assert snapshot["demands"][1]["source_url"] == ""
        assert len(snapshot["source_sha256"]) == 64
```

```python
# backend/test/unit/infrastructure/operational/test_demands.py
import json

from infrastructure.operational.demands import JsonDemandRepository


def _write(tmp_path):
    path = tmp_path / "demands_v1.json"
    path.write_text(
        json.dumps(
            {
                "source_sha256": "ab" * 32,
                "demands": [
                    {"demand_id": "D-1", "title": "One", "description": "first", "posted_date": None,
                     "origin_country": "Spain", "source_url": "https://x.org/1"},
                    {"demand_id": "D-2", "title": "Two", "description": "second", "posted_date": None,
                     "origin_country": "Spain", "source_url": ""},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


class JsonDemandRepositoryTest:
    def test_should_list_demands_in_file_order_when_loaded(self, tmp_path):
        repository = JsonDemandRepository(_write(tmp_path))
        assert [d.demand_id for d in repository.list_all()] == ["D-1", "D-2"]

    def test_should_return_demand_with_source_url_when_id_is_known(self, tmp_path):
        demand = JsonDemandRepository(_write(tmp_path)).get("D-1")
        assert demand is not None and demand.url == "https://x.org/1" and demand.posted_date is None

    def test_should_return_none_when_id_is_unknown(self, tmp_path):
        assert JsonDemandRepository(_write(tmp_path)).get("D-9") is None

    def test_should_expose_source_hash_when_loaded(self, tmp_path):
        assert JsonDemandRepository(_write(tmp_path)).source_sha256 == "ab" * 32
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/test/unit/test_demands_snapshot_script.py backend/test/unit/infrastructure/operational -v`
Expected: FAIL (`FileNotFoundError` for the script; `ModuleNotFoundError: infrastructure.operational`)

- [ ] **Step 3: Write the implementation**

```python
# backend/src/main/domain/protocols/demand_repository.py
from typing import Protocol, runtime_checkable

from domain.models.demand import DemandSignal


@runtime_checkable
class DemandRepository(Protocol):
    """Port for the demands a product screen may offer."""

    def get(self, demand_id: str) -> DemandSignal | None: ...

    def list_all(self) -> list[DemandSignal]: ...
```

```python
# backend/src/main/infrastructure/operational/__init__.py
"""Operational MVP adapters: demand snapshot, verified matching service, HTTP router."""
```

```python
# backend/src/main/infrastructure/operational/demands.py
import json
from pathlib import Path

from domain.models.demand import DemandSignal
from domain.protocols.demand_repository import DemandRepository


class JsonDemandRepository(DemandRepository):
    """Reads the product demand snapshot written by scripts/build_demands_snapshot.py."""

    def __init__(self, path: Path) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.source_sha256: str = raw["source_sha256"]
        self._demands = [
            DemandSignal(
                demand_id=d["demand_id"],
                title=d["title"],
                description=d["description"],
                posted_date=d.get("posted_date"),
                origin_country=d.get("origin_country"),
                url=d.get("source_url", ""),
            )
            for d in raw["demands"]
        ]
        self._by_id = {d.demand_id: d for d in self._demands}

    def get(self, demand_id: str) -> DemandSignal | None:
        return self._by_id.get(demand_id)

    def list_all(self) -> list[DemandSignal]:
        return list(self._demands)
```

```python
# scripts/build_demands_snapshot.py
"""Writes the product demand snapshot from the frozen n39 demand corpus.

The backend must not read from experiments/ (ADR 0026), so the demands the MVP serves are copied once,
verbatim, into data/snapshots/operational_corpus_v1/demands_v1.json together with the sha256 of the source
file. The embedding generation records the same hash, which lets the service check the two belong together.
"""

import argparse
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    REPO_ROOT / "experiments" / "wpi-demand-patent-matching" / "data" / "dataset_phase2_demand_corpus_n39.json"
)
DEFAULT_OUT = REPO_ROOT / "data" / "snapshots" / "operational_corpus_v1" / "demands_v1.json"


def build_snapshot(demand_corpus_path: Path) -> dict:
    raw_bytes = demand_corpus_path.read_bytes()
    demands = json.loads(raw_bytes.decode("utf-8"))["demands"]
    return {
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "demands": [
            {
                "demand_id": d["demand_id"],
                "title": d["title"],
                "description": d["description"],
                "posted_date": d.get("posted_date"),
                "origin_country": d.get("origin_country"),
                "source_url": (d.get("provenance") or {}).get("source_uri", ""),
            }
            for d in demands
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the product demand snapshot")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    snapshot = build_snapshot(args.source)
    args.out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {args.out}: {len(snapshot['demands'])} demands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests and lint**

Run: `pytest backend/test/unit/test_demands_snapshot_script.py backend/test/unit/infrastructure/operational -v && ruff check backend/src/main backend/test scripts && mypy backend/src/main --ignore-missing-imports`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_demands_snapshot.py backend/src/main/domain/protocols/demand_repository.py backend/src/main/infrastructure/operational backend/test/unit/test_demands_snapshot_script.py backend/test/unit/infrastructure/operational
git commit -m "feat(operational): demand snapshot script and JSON demand repository" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 3: `find_assets_for_demand` use case

**Files:**
- Create: `backend/src/main/application/matching/find_assets.py`
- Test: `backend/test/unit/application/matching/test_find_assets.py`

**Interfaces:**
- Consumes: `DemandRepository` (Task 2), `PatentCandidateRetriever`, `Candidate`, `DemandSignal`.
- Produces: `@dataclass(frozen=True) class AssetMatch` (`rank: int`, `publication_id: str`); `class UnknownDemandError(KeyError)`; `find_assets_for_demand(demand_id: str, limit: int, *, demands: DemandRepository, retriever: PatentCandidateRetriever) -> tuple[DemandSignal, list[AssetMatch]]` (ranks start at 1, order exactly as the retriever returned).

- [ ] **Step 1: Write the failing test**

```python
# backend/test/unit/application/matching/test_find_assets.py
import pytest

from application.matching.find_assets import AssetMatch, UnknownDemandError, find_assets_for_demand
from domain.models.demand import DemandSignal
from domain.models.matching import Candidate, RetrievalMethod


class _Demands:
    def __init__(self, demands):
        self._by_id = {d.demand_id: d for d in demands}

    def get(self, demand_id):
        return self._by_id.get(demand_id)

    def list_all(self):
        return list(self._by_id.values())


class _Retriever:
    """Boundary fake: the retrieval port, not an internal layer."""

    def __init__(self, ids):
        self._ids = ids
        self.calls = []

    def retrieve(self, demand, *, limit=100):
        self.calls.append((demand.demand_id, limit))
        return [Candidate(publication_id=i, retrieval_scores={RetrievalMethod.SEMANTIC: 0.5}) for i in self._ids[:limit]]


def _demand(demand_id="D-1"):
    return DemandSignal(demand_id=demand_id, title="t", description="d")


class FindAssetsForDemandTest:
    def test_should_rank_from_one_in_retriever_order_when_demand_is_known(self):
        retriever = _Retriever(["ES-2-A1", "ES-1-A1"])
        demand, matches = find_assets_for_demand("D-1", 5, demands=_Demands([_demand()]), retriever=retriever)
        assert demand.demand_id == "D-1"
        assert matches == [AssetMatch(1, "ES-2-A1"), AssetMatch(2, "ES-1-A1")]

    def test_should_pass_limit_to_retriever_when_searching(self):
        retriever = _Retriever(["A", "B", "C"])
        _, matches = find_assets_for_demand("D-1", 2, demands=_Demands([_demand()]), retriever=retriever)
        assert retriever.calls == [("D-1", 2)] and len(matches) == 2

    def test_should_return_empty_list_when_retriever_finds_nothing(self):
        _, matches = find_assets_for_demand("D-1", 5, demands=_Demands([_demand()]), retriever=_Retriever([]))
        assert matches == []

    def test_should_raise_unknown_demand_when_id_is_not_in_repository(self):
        with pytest.raises(UnknownDemandError):
            find_assets_for_demand("D-9", 5, demands=_Demands([_demand()]), retriever=_Retriever([]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/test/unit/application/matching/test_find_assets.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'application.matching.find_assets'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/main/application/matching/find_assets.py
from dataclasses import dataclass

from domain.models.demand import DemandSignal
from domain.protocols.demand_repository import DemandRepository
from domain.protocols.matching import PatentCandidateRetriever


class UnknownDemandError(KeyError):
    """The demand is not one of the demands this product offers."""


@dataclass(frozen=True)
class AssetMatch:
    rank: int
    publication_id: str


def find_assets_for_demand(
    demand_id: str,
    limit: int,
    *,
    demands: DemandRepository,
    retriever: PatentCandidateRetriever,
) -> tuple[DemandSignal, list[AssetMatch]]:
    """Ranks eligible assets for a known demand. The rank is the only ordering signal exposed to callers."""
    demand = demands.get(demand_id)
    if demand is None:
        raise UnknownDemandError(demand_id)
    candidates = retriever.retrieve(demand, limit=limit)
    return demand, [AssetMatch(rank=i, publication_id=c.publication_id) for i, c in enumerate(candidates, start=1)]
```

- [ ] **Step 4: Run tests and gates**

Run: `pytest backend/test/unit/application/matching -q && ruff check backend/src/main backend/test && mypy backend/src/main --ignore-missing-imports && python scripts/check_architecture.py`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/application/matching/find_assets.py backend/test/unit/application/matching/test_find_assets.py
git commit -m "feat(matching): find_assets_for_demand use case" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 4: Links, notices and the verified matching service

**Files:**
- Create: `backend/src/main/infrastructure/operational/links.py`
- Create: `backend/src/main/infrastructure/operational/notices.py`
- Create: `backend/src/main/infrastructure/operational/service.py`
- Create: `backend/test/unit/infrastructure/operational/conftest.py`
- Test: `backend/test/unit/infrastructure/operational/test_links.py`
- Test: `backend/test/unit/infrastructure/operational/test_service.py`

**Interfaces:**
- Consumes: `load_operational_assets`, `operational_eligibility_policy`, `OperationalAsset` (Task 1); `JsonDemandRepository` (Task 2); `find_assets_for_demand`, `UnknownDemandError` (Task 3); `load_index`, `PrecomputedEmbedder`, `demand_embedding_text`, `NumpyDenseRetriever`.
- Produces:
  - `links.source_links(publication_id: str) -> dict[str, str]` with keys `google_patents`, `espacenet`
  - `notices.NOTICES: tuple[str, str, str, str]`
  - `OperationalMatchingService.from_directory(directory: Path) -> OperationalMatchingService`; `.examples() -> dict` (`{"demands": [...], "notices": [...]}`); `.matches(demand_id: str, limit: int = 5) -> dict` (contract of spec 4.2; raises `UnknownDemandError`).

- [ ] **Step 1: Write the fixtures and failing tests**

```python
# backend/test/unit/infrastructure/operational/conftest.py
import hashlib
import json

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from infrastructure.embeddings.frozen_embedding_index import save_index

DEMANDS = [
    {"demand_id": "D-1", "title": "Lighter vehicles", "description": "Seeking new materials", "posted_date": None,
     "origin_country": "Spain", "source_url": "https://example.org/d1"},
    {"demand_id": "D-2", "title": "Water sensors", "description": "Cheap sensing", "posted_date": None,
     "origin_country": "Spain", "source_url": "https://example.org/d2"},
]
DEMAND_SOURCE_SHA = "cd" * 32
# id, country, kind, ip_type, title, abstract, language, assignees, inventors, cpc, filing, publication, family
ROWS = [
    ("ES-1000001-A1", "ES", "A1", "patent", "Title one", "Abstract one", "es", ["ACME SA"], ["ANA"], ["B60K1/00"], "2019-01-01", "2020-01-01", "F1"),
    ("ES-1000002-U", "ES", "U", "utility_model", "Title two", "Abstract two", "es", ["BETA SL"], [], [], "2019-02-01", "2020-02-01", "F2"),
    ("ES-1000003-A1", "ES", "A1", "patent", "Title three", "Abstract three", "en", ["GAMMA SA"], ["LUIS"], ["G01N1/00"], "2019-03-01", "2030-03-01", "F3"),
    ("EP-1000004-B1", "EP", "B1", "patent", "Title four", "Abstract four", "en", ["DELTA SA"], [], [], "2019-04-01", "2020-04-01", "F4"),
]
PATENT_VECTORS = [[1.0, 0.0], [0.0, 1.0], [0.6, 0.8], [1.0, 0.0]]
DEMAND_VECTORS = {"D-1": [0.0, 1.0], "D-2": [1.0, 0.0]}


def _table(rows):
    cols = ["publication_number", "country_code", "kind_code", "ip_type", "title", "abstract",
            "abstract_language", "assignees", "inventors", "cpc_codes", "filing_date", "publication_date", "family_id"]
    return pa.table({c: [r[i] for r in rows] for i, c in enumerate(cols)})


def _fields(parquet_sha):
    return {
        "model_name": "test-model", "model_revision": "rev", "generation_device": "cpu", "batch_size": 1,
        "library_versions": {}, "generation_script_path": "scripts/x.py", "generation_script_commit": "abc",
        "truncated_fraction": 0.0,
        "source_sha256": {"publications.parquet": parquet_sha, "demand_corpus_n39": DEMAND_SOURCE_SHA},
    }


def build_operational_dir(directory, *, rows=ROWS, demands=DEMANDS):
    directory.mkdir(parents=True, exist_ok=True)
    parquet = directory / "publications.parquet"
    pq.write_table(_table(rows), parquet)
    sha = hashlib.sha256(parquet.read_bytes()).hexdigest()
    (directory / "manifest.json").write_text(
        json.dumps({"dataset_id": "NEXUS-OPERATIONAL-CORPUS-V1", "parquet_sha256": sha}), encoding="utf-8"
    )
    (directory / "demands_v1.json").write_text(
        json.dumps({"source_sha256": DEMAND_SOURCE_SHA, "demands": demands}), encoding="utf-8"
    )
    save_index(directory, "embeddings_patents_v1", [r[0] for r in rows],
               np.array(PATENT_VECTORS, dtype=np.float32), **_fields(sha))
    save_index(directory, "embeddings_demands_v1", list(DEMAND_VECTORS),
               np.array(list(DEMAND_VECTORS.values()), dtype=np.float32), **_fields(sha))
    return directory


@pytest.fixture
def operational_dir(tmp_path):
    return build_operational_dir(tmp_path / "operational")
```

```python
# backend/test/unit/infrastructure/operational/test_links.py
from infrastructure.operational.links import source_links


class SourceLinksTest:
    def test_should_build_google_and_espacenet_links_when_publication_is_spanish(self):
        links = source_links("ES-2594181-A1")
        assert links["google_patents"] == "https://patents.google.com/patent/ES2594181A1"
        assert links["espacenet"] == "https://worldwide.espacenet.com/patent/search?q=pn%3DES2594181A1"

    def test_should_build_links_when_publication_is_european(self):
        assert source_links("EP-3000000-B1")["google_patents"] == "https://patents.google.com/patent/EP3000000B1"
```

```python
# backend/test/unit/infrastructure/operational/test_service.py
import json

import pyarrow.parquet as pq
import pytest

from application.matching.find_assets import UnknownDemandError
from infrastructure.operational.notices import NOTICES
from infrastructure.operational.service import OperationalMatchingService

from .conftest import DEMANDS, ROWS, build_operational_dir

_SCORE_KEYS = {"score", "scores", "retrieval_scores", "similarity", "band", "relevance_band", "distance"}


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _keys(item)


class OperationalMatchingServiceTest:
    def test_should_rank_assets_by_dense_similarity_when_demand_is_known(self, operational_dir):
        result = OperationalMatchingService.from_directory(operational_dir).matches("D-1")
        assert [a["publication_id"] for a in result["assets"]] == ["ES-1000002-U", "ES-1000003-A1", "ES-1000001-A1"]
        assert [a["rank"] for a in result["assets"]] == [1, 2, 3]

    def test_should_return_results_when_demand_has_no_posted_date(self, operational_dir):
        result = OperationalMatchingService.from_directory(operational_dir).matches("D-2")
        assert result["demand"]["demand_id"] == "D-2" and len(result["assets"]) == 3

    def test_should_not_pad_when_limit_exceeds_eligible_assets(self, operational_dir):
        result = OperationalMatchingService.from_directory(operational_dir).matches("D-1", limit=10)
        assert len(result["assets"]) == 3 and result["meta"]["eligible_count"] == 3

    def test_should_respect_limit_when_fewer_requested(self, operational_dir):
        assert len(OperationalMatchingService.from_directory(operational_dir).matches("D-1", limit=2)["assets"]) == 2

    def test_should_exclude_ep_asset_when_jurisdiction_is_not_es(self, operational_dir):
        ids = [a["publication_id"] for a in OperationalMatchingService.from_directory(operational_dir).matches("D-1")["assets"]]
        assert "EP-1000004-B1" not in ids

    def test_should_expose_holders_type_abstract_cpc_and_links_when_asset_is_returned(self, operational_dir):
        asset = OperationalMatchingService.from_directory(operational_dir).matches("D-1")["assets"][0]
        assert asset["ip_type"] == "utility_model" and asset["assignees"] == ["BETA SL"]
        assert asset["abstract"] == "Abstract two" and asset["abstract_language"] == "es"
        assert asset["source_links"]["google_patents"].endswith("ES1000002U")
        assert asset["cpc_codes"] == [] and asset["publication_date"] == "2020-02-01"

    def test_should_not_expose_any_score_like_key_when_serialising_matches_and_examples(self, operational_dir):
        service = OperationalMatchingService.from_directory(operational_dir)
        keys = set(_keys(service.matches("D-1"))) | set(_keys(service.examples()))
        assert not keys & _SCORE_KEYS

    def test_should_serve_four_fixed_notices_when_listing_examples_and_matches(self, operational_dir):
        service = OperationalMatchingService.from_directory(operational_dir)
        assert len(NOTICES) == 4
        assert service.examples()["notices"] == list(NOTICES)
        assert service.matches("D-1")["meta"]["notices"] == list(NOTICES)

    def test_should_list_example_demands_in_corpus_order_when_asked(self, operational_dir):
        demands = OperationalMatchingService.from_directory(operational_dir).examples()["demands"]
        assert [d["demand_id"] for d in demands] == ["D-1", "D-2"] and demands[0]["source_url"] == "https://example.org/d1"

    def test_should_raise_unknown_demand_when_id_is_not_offered(self, operational_dir):
        with pytest.raises(UnknownDemandError):
            OperationalMatchingService.from_directory(operational_dir).matches("D-9")

    def test_should_report_corpus_identity_when_serving_matches(self, operational_dir):
        meta = OperationalMatchingService.from_directory(operational_dir).matches("D-1")["meta"]
        assert meta["retrieval"] == "dense" and meta["corpus_id"] == "NEXUS-OPERATIONAL-CORPUS-V1"
        assert len(meta["corpus_parquet_sha256"]) == 64 and len(meta["embedding_index_sha256"]) == 64


class OperationalMatchingStartupTest:
    def test_should_abort_when_corpus_parquet_changed_after_manifest(self, operational_dir):
        pq.write_table(pq.read_table(operational_dir / "publications.parquet").slice(0, 2), operational_dir / "publications.parquet")
        with pytest.raises(ValueError, match="sha256"):
            OperationalMatchingService.from_directory(operational_dir)

    def test_should_abort_when_embeddings_were_generated_for_another_corpus(self, tmp_path):
        directory = build_operational_dir(tmp_path / "op")
        manifest_path = directory / "embeddings_patents_v1.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_sha256"]["publications.parquet"] = "00" * 32
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="corpus"):
            OperationalMatchingService.from_directory(directory)

    def test_should_abort_when_demand_snapshot_differs_from_the_embedded_demand_corpus(self, operational_dir):
        path = operational_dir / "demands_v1.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["source_sha256"] = "11" * 32
        path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ValueError, match="demand"):
            OperationalMatchingService.from_directory(operational_dir)

    def test_should_abort_when_a_served_demand_has_no_embedding(self, tmp_path):
        extra = DEMANDS + [{"demand_id": "D-3", "title": "Extra", "description": "Not embedded", "posted_date": None,
                            "origin_country": "Spain", "source_url": ""}]
        directory = build_operational_dir(tmp_path / "op", rows=ROWS, demands=extra)
        with pytest.raises(ValueError, match="D-3"):
            OperationalMatchingService.from_directory(directory)

    def test_should_abort_when_embedding_matrix_bytes_changed(self, operational_dir):
        npy = operational_dir / "embeddings_patents_v1.npy"
        npy.write_bytes(npy.read_bytes()[:-1] + b"\x01")
        with pytest.raises(ValueError, match="sha256"):
            OperationalMatchingService.from_directory(operational_dir)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/test/unit/infrastructure/operational -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.operational.links'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/main/infrastructure/operational/links.py
_GOOGLE = "https://patents.google.com/patent/"
_ESPACENET = "https://worldwide.espacenet.com/patent/search?q=pn%3D"


def source_links(publication_id: str) -> dict[str, str]:
    compact = publication_id.replace("-", "")
    return {"google_patents": f"{_GOOGLE}{compact}", "espacenet": f"{_ESPACENET}{compact}"}
```

```python
# backend/src/main/infrastructure/operational/notices.py
"""Fixed on-screen notices (spec section 7). Served by the backend so the UI never hard-codes them.

NOTICE_QUALITY is deliberately a single constant. It changes only when docs/operational-dense-probe-result.md
exists, and then it states the outcome as written there.
"""

NOTICE_RANKING = "Ordenado por similitud de recuperación. No garantiza que el activo resuelva la demanda."
NOTICE_DATA = "Datos: Google Patents Public Data. Licencia en verificación; uso interno."
NOTICE_COVERAGE = (
    "Cobertura: patentes y modelos de utilidad ES de solicitantes españoles. "
    "Las solicitudes EP con solicitante español aún no se incluyen."
)
NOTICE_QUALITY = "Calidad del ranking en evaluación (probe preregistrado)."

NOTICES = (NOTICE_RANKING, NOTICE_DATA, NOTICE_COVERAGE, NOTICE_QUALITY)
```

```python
# backend/src/main/infrastructure/operational/service.py
import hashlib
import json
from pathlib import Path
from typing import Any

from application.matching.find_assets import find_assets_for_demand
from domain.models.demand import DemandSignal
from domain.protocols.demand_repository import DemandRepository
from domain.protocols.matching import PatentCandidateRetriever, PatentEligibilityPolicy
from infrastructure.embeddings.embedding_texts import demand_embedding_text
from infrastructure.embeddings.frozen_embedding_index import load_index
from infrastructure.embeddings.precomputed_embedder import PrecomputedEmbedder
from infrastructure.matching.numpy_dense import NumpyDenseRetriever
from infrastructure.matching.operational_corpus import (
    OperationalAsset,
    load_operational_assets,
    operational_eligibility_policy,
)
from infrastructure.operational.demands import JsonDemandRepository
from infrastructure.operational.links import source_links
from infrastructure.operational.notices import NOTICES

PATENT_INDEX = "embeddings_patents_v1"
DEMAND_INDEX = "embeddings_demands_v1"


def _demand_payload(demand: DemandSignal) -> dict[str, Any]:
    return {
        "demand_id": demand.demand_id,
        "title": demand.title,
        "description": demand.description,
        "origin_country": demand.origin_country,
        "posted_date": demand.posted_date,
        "source_url": demand.url,
    }


class OperationalMatchingService:
    """Answers the two MVP routes from verified, frozen artifacts. Never embeds text at runtime."""

    def __init__(
        self,
        *,
        assets: list[OperationalAsset],
        demands: DemandRepository,
        retriever: PatentCandidateRetriever,
        policy: PatentEligibilityPolicy,
        corpus_id: str,
        corpus_sha256: str,
        embedding_index_sha256: str,
    ) -> None:
        self._assets = assets
        self._by_id = {a.patent.publication_id: a for a in assets}
        self._demands = demands
        self._retriever = retriever
        self._policy = policy
        self._meta = {
            "retrieval": "dense",
            "corpus_id": corpus_id,
            "corpus_parquet_sha256": corpus_sha256,
            "embedding_index_sha256": embedding_index_sha256,
            "notices": list(NOTICES),
        }

    @classmethod
    def from_directory(cls, directory: Path) -> "OperationalMatchingService":
        parquet = directory / "publications.parquet"
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        corpus_sha = hashlib.sha256(parquet.read_bytes()).hexdigest()
        if corpus_sha != manifest["parquet_sha256"]:
            raise ValueError("publications.parquet sha256 does not match manifest.json")

        assets = load_operational_assets(parquet)
        patent_index = load_index(directory, PATENT_INDEX)
        demand_index = load_index(directory, DEMAND_INDEX)
        if patent_index.ids != tuple(a.patent.publication_id for a in assets):
            raise ValueError("Patent embedding ids are not aligned with the corpus row order")
        if patent_index.manifest.source_sha256.get("publications.parquet") != corpus_sha:
            raise ValueError("Patent embeddings were generated for a different corpus")

        demands = JsonDemandRepository(directory / "demands_v1.json")
        if demand_index.manifest.source_sha256.get("demand_corpus_n39") != demands.source_sha256:
            raise ValueError("Demand snapshot does not match the demand corpus the embeddings were built from")

        vectors: dict[str, Any] = {}
        for demand in demands.list_all():
            if demand.demand_id not in demand_index.ids:
                raise ValueError(f"Demand {demand.demand_id} has no frozen embedding")
            vectors[demand_embedding_text(demand.title, demand.description)] = demand_index.matrix[
                demand_index.ids.index(demand.demand_id)
            ]

        policy = operational_eligibility_policy()
        retriever = NumpyDenseRetriever(
            [a.patent for a in assets], patent_index.matrix, PrecomputedEmbedder(vectors), policy
        )
        return cls(
            assets=assets,
            demands=demands,
            retriever=retriever,
            policy=policy,
            corpus_id=manifest["dataset_id"],
            corpus_sha256=corpus_sha,
            embedding_index_sha256=patent_index.manifest.matrix_sha256,
        )

    def examples(self) -> dict[str, Any]:
        return {"demands": [_demand_payload(d) for d in self._demands.list_all()], "notices": list(NOTICES)}

    def matches(self, demand_id: str, limit: int = 5) -> dict[str, Any]:
        demand, found = find_assets_for_demand(demand_id, limit, demands=self._demands, retriever=self._retriever)
        eligible = sum(1 for a in self._assets if self._policy.evaluate(a.patent, demand).is_eligible)
        return {
            "demand": {k: v for k, v in _demand_payload(demand).items() if k != "posted_date" and k != "origin_country"},
            "assets": [self._asset_payload(m.rank, self._by_id[m.publication_id]) for m in found],
            "meta": {**self._meta, "eligible_count": eligible},
        }

    @staticmethod
    def _asset_payload(rank: int, asset: OperationalAsset) -> dict[str, Any]:
        patent = asset.patent
        return {
            "rank": rank,
            "publication_id": patent.publication_id,
            "title": patent.title,
            "ip_type": asset.ip_type,
            "country_code": patent.country_code,
            "kind_code": patent.kind_code,
            "assignees": patent.assignees,
            "inventors": patent.inventors,
            "publication_date": patent.publication_date,
            "abstract": patent.abstract,
            "abstract_language": asset.abstract_language,
            "cpc_codes": patent.classifications_cpc,
            "source_links": source_links(patent.publication_id),
        }
```

- [ ] **Step 4: Run tests and gates**

Run: `pytest backend/test/unit/infrastructure/operational -v && ruff check backend/src/main backend/test && mypy backend/src/main --ignore-missing-imports && python scripts/check_architecture.py && PYTHONPATH=backend/src/main lint-imports`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/operational backend/test/unit/infrastructure/operational
git commit -m "feat(operational): verified matching service, links and fixed notices" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 5: HTTP router, conditional mount, `api.py` wiring

**Files:**
- Create: `backend/src/main/infrastructure/operational/router.py`
- Create: `backend/src/main/infrastructure/operational/mount.py`
- Modify: `backend/src/main/infrastructure/api.py` (one import, one call placed before the `@app.get("/")` route)
- Test: `backend/test/unit/infrastructure/operational/test_router.py`
- Test: `backend/test/unit/infrastructure/operational/test_mount.py`

**Interfaces:**
- Consumes: `OperationalMatchingService`, `UnknownDemandError` (Tasks 3-4).
- Produces: `build_router(service: OperationalMatchingService) -> APIRouter` (routes `GET /api/demand-examples`, `GET /api/matches`); `mount_operational_mvp(app: FastAPI) -> bool` (env `NEXUS_MVP_ENABLED=1`, dir env `NEXUS_OPERATIONAL_DIR`, default repo `data/snapshots/operational_corpus_v1`).

- [ ] **Step 1: Write the failing tests**

```python
# backend/test/unit/infrastructure/operational/test_router.py
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.operational.router import build_router
from infrastructure.operational.service import OperationalMatchingService


@pytest.fixture
def client(operational_dir):
    app = FastAPI()
    app.include_router(build_router(OperationalMatchingService.from_directory(operational_dir)))
    return TestClient(app)


class OperationalRouterTest:
    def test_should_list_example_demands_with_notices_when_requested(self, client):
        body = client.get("/api/demand-examples").json()
        assert [d["demand_id"] for d in body["demands"]] == ["D-1", "D-2"] and len(body["notices"]) == 4

    def test_should_return_ranked_assets_with_default_limit_when_demand_is_known(self, client):
        response = client.get("/api/matches", params={"demand_id": "D-1"})
        assert response.status_code == 200
        assert [a["rank"] for a in response.json()["assets"]] == [1, 2, 3]

    def test_should_return_404_when_demand_is_unknown(self, client):
        assert client.get("/api/matches", params={"demand_id": "D-9"}).status_code == 404

    @pytest.mark.parametrize("limit", [0, 11, -1])
    def test_should_return_422_when_limit_is_outside_one_to_ten(self, client, limit):
        assert client.get("/api/matches", params={"demand_id": "D-1", "limit": limit}).status_code == 422

    def test_should_return_422_when_demand_id_is_missing(self, client):
        assert client.get("/api/matches").status_code == 422

    def test_should_honour_limit_when_fewer_assets_requested(self, client):
        assert len(client.get("/api/matches", params={"demand_id": "D-1", "limit": 1}).json()["assets"]) == 1
```

```python
# backend/test/unit/infrastructure/operational/test_mount.py
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.operational.mount import mount_operational_mvp

API_SOURCE = Path(__file__).resolve().parents[5] / "backend" / "src" / "main" / "infrastructure" / "api.py"


def _paths(app):
    return {getattr(r, "path", None) for r in app.routes}


class MountOperationalMvpTest:
    def test_should_not_mount_routes_when_flag_is_unset(self, monkeypatch):
        monkeypatch.delenv("NEXUS_MVP_ENABLED", raising=False)
        app = FastAPI()
        assert mount_operational_mvp(app) is False
        assert "/api/matches" not in _paths(app)

    def test_should_mount_routes_when_flag_is_set_and_artifacts_verify(self, monkeypatch, operational_dir):
        monkeypatch.setenv("NEXUS_MVP_ENABLED", "1")
        monkeypatch.setenv("NEXUS_OPERATIONAL_DIR", str(operational_dir))
        app = FastAPI()
        assert mount_operational_mvp(app) is True
        assert TestClient(app).get("/api/matches", params={"demand_id": "D-1"}).status_code == 200

    def test_should_abort_startup_when_flag_is_set_and_directory_is_missing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("NEXUS_MVP_ENABLED", "1")
        monkeypatch.setenv("NEXUS_OPERATIONAL_DIR", str(tmp_path / "missing"))
        with pytest.raises(FileNotFoundError):
            mount_operational_mvp(FastAPI())

    def test_should_mount_before_the_spa_catch_all_route_in_api_module(self):
        source = API_SOURCE.read_text(encoding="utf-8")
        assert "mount_operational_mvp(app)" in source
        assert source.index("mount_operational_mvp(app)") < source.index('@app.get("/{full_path:path}")')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest backend/test/unit/infrastructure/operational/test_router.py backend/test/unit/infrastructure/operational/test_mount.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'infrastructure.operational.router'`

- [ ] **Step 3: Write the implementation**

```python
# backend/src/main/infrastructure/operational/router.py
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from application.matching.find_assets import UnknownDemandError
from infrastructure.operational.service import OperationalMatchingService


def build_router(service: OperationalMatchingService) -> APIRouter:
    router = APIRouter()

    @router.get("/api/demand-examples")
    def demand_examples() -> dict[str, Any]:
        return service.examples()

    @router.get("/api/matches")
    def matches(
        demand_id: str = Query(..., min_length=1),
        limit: int = Query(5, ge=1, le=10),
    ) -> dict[str, Any]:
        try:
            return service.matches(demand_id, limit)
        except UnknownDemandError as err:
            raise HTTPException(status_code=404, detail=f"Demand '{demand_id}' not found.") from err

    return router
```

```python
# backend/src/main/infrastructure/operational/mount.py
import os
from pathlib import Path

from fastapi import FastAPI

from infrastructure.operational.router import build_router
from infrastructure.operational.service import OperationalMatchingService

ENABLE_ENV = "NEXUS_MVP_ENABLED"
DIR_ENV = "NEXUS_OPERATIONAL_DIR"
_DEFAULT_DIR = Path(__file__).resolve().parents[5] / "data" / "snapshots" / "operational_corpus_v1"


def mount_operational_mvp(app: FastAPI) -> bool:
    """Mounts the MVP routes only when NEXUS_MVP_ENABLED=1; then any bad artifact aborts startup."""
    if os.getenv(ENABLE_ENV) != "1":
        return False
    directory = Path(os.getenv(DIR_ENV, str(_DEFAULT_DIR)))
    app.include_router(build_router(OperationalMatchingService.from_directory(directory)))
    return True
```

In `backend/src/main/infrastructure/api.py`: add `from infrastructure.operational.mount import mount_operational_mvp` after the `from infrastructure.api_dependencies import (...)` block, and add the call `mount_operational_mvp(app)` on its own line immediately before the line `@app.get("/")` (after the `_initial_dist` static mount `if` block), preceded by the comment `# Must precede the SPA catch-all below, or it shadows /api/matches.`

Also edit the spec sentence in section 4.2 only if it disagrees with this behaviour (it was amended already; verify, do not rewrite).

- [ ] **Step 4: Run tests and full gates**

Run: `pytest -q && ruff check backend/src/main backend/test scripts && mypy backend/src/main --ignore-missing-imports && python scripts/check_architecture.py && PYTHONPATH=backend/src/main lint-imports`
Expected: all pass (the existing `test_api_endpoints.py` still passes: flag unset means no change).

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/infrastructure/operational backend/src/main/infrastructure/api.py backend/test/unit/infrastructure/operational
git commit -m "feat(operational): /api/matches and /api/demand-examples behind NEXUS_MVP_ENABLED" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 6: Frontend screen (`/matches`)

**Files:**
- Create: `frontend/src/main/domain/operational.ts`
- Create: `frontend/src/main/infrastructure/operationalClient.ts`
- Create: `frontend/src/main/components/Matches/MatchesView.tsx`
- Create: `frontend/src/main/components/Matches/MatchesPage.tsx`
- Modify: `frontend/src/main/main.tsx`
- Test: `frontend/test/unit/MatchesView.test.tsx`

**Interfaces:**
- Consumes: backend contract of spec section 4.
- Produces: types `DemandExample`, `DemandExamplesResponse`, `AssetResult`, `MatchesResponse`; `getDemandExamples(): Promise<DemandExamplesResponse>`, `getMatches(demandId: string, limit?: number): Promise<MatchesResponse>`; `<MatchesView api?={...} />`; `<MatchesPage />`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/test/unit/MatchesView.test.tsx
import { describe, it, expect } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MatchesView } from "../../src/main/components/Matches/MatchesView";
import type { DemandExamplesResponse, MatchesResponse } from "../../src/main/domain/operational";

const NOTICES = ["Aviso 1", "Aviso 2", "Aviso 3", "Aviso 4"];

const EXAMPLES: DemandExamplesResponse = {
  demands: [
    { demand_id: "D-1", title: "Lighter vehicles", description: "Seeking new materials", origin_country: "Spain", posted_date: null, source_url: "https://example.org/d1" },
    { demand_id: "D-2", title: "Water sensors", description: "Cheap sensing", origin_country: "Spain", posted_date: null, source_url: "" },
  ],
  notices: NOTICES,
};

function matches(assets: MatchesResponse["assets"]): MatchesResponse {
  return {
    demand: { demand_id: "D-1", title: "Lighter vehicles", description: "Seeking new materials", source_url: "https://example.org/d1" },
    assets,
    meta: { retrieval: "dense", eligible_count: assets.length, corpus_id: "C", corpus_parquet_sha256: "a", embedding_index_sha256: "b", notices: NOTICES },
  };
}

const ASSET = {
  rank: 1, publication_id: "ES-1000002-U", title: "Dispositivo ligero", ip_type: "utility_model", country_code: "ES",
  kind_code: "U", assignees: ["BETA SL"], inventors: ["ANA"], publication_date: "2020-02-01",
  abstract: "Un dispositivo ligero.", abstract_language: "es", cpc_codes: ["B60K1/00"],
  source_links: { google_patents: "https://patents.google.com/patent/ES1000002U", espacenet: "https://worldwide.espacenet.com/patent/search?q=pn%3DES1000002U" },
};

function api(result: MatchesResponse | Error) {
  return {
    getDemandExamples: () => Promise.resolve(EXAMPLES),
    getMatches: () => (result instanceof Error ? Promise.reject(result) : Promise.resolve(result)),
  };
}

describe("MatchesView", () => {
  it("shows example demands and the four fixed notices before any selection", async () => {
    render(<MatchesView api={api(matches([ASSET]))} />);
    expect(await screen.findByText("Lighter vehicles")).toBeDefined();
    NOTICES.forEach((n) => expect(screen.getByText(n)).toBeDefined());
  });

  it("shows rank, title, type label, holder and source link after choosing a demand", async () => {
    render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText("Dispositivo ligero")).toBeDefined();
    expect(screen.getByText("#1")).toBeDefined();
    expect(screen.getByText("Modelo de utilidad")).toBeDefined();
    expect(screen.getByText(/BETA SL/)).toBeDefined();
    const link = screen.getByText("Google Patents").closest("a");
    expect(link?.getAttribute("href")).toBe("https://patents.google.com/patent/ES1000002U");
  });

  it("shows the asset's own CPC under 'Datos del activo' and no match-signals block", async () => {
    render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    await screen.findByText("Dispositivo ligero");
    expect(screen.getByText(/Datos del activo/)).toBeDefined();
    expect(screen.getByText(/B60K1\/00/)).toBeDefined();
    expect(screen.queryByText(/Señales de coincidencia/)).toBeNull();
  });

  it("shows an empty state when no eligible asset exists", async () => {
    render(<MatchesView api={api(matches([]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText(/No hay activos elegibles/)).toBeDefined();
  });

  it("shows an error message when the request fails", async () => {
    render(<MatchesView api={api(new Error("boom"))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    expect(await screen.findByText(/No se pudieron cargar los resultados/)).toBeDefined();
  });

  it("never renders a similarity score or percentage", async () => {
    const { container } = render(<MatchesView api={api(matches([ASSET]))} />);
    fireEvent.click(await screen.findByText("Lighter vehicles"));
    await screen.findByText("Dispositivo ligero");
    expect(container.textContent).not.toMatch(/\d\.\d{2,}|%|score|similitud:/i);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (in `frontend/`): `npx vitest run test/unit/MatchesView.test.tsx`
Expected: FAIL (cannot resolve `../../src/main/components/Matches/MatchesView`)

- [ ] **Step 3: Write the implementation**

```ts
// frontend/src/main/domain/operational.ts
export interface DemandExample {
  demand_id: string;
  title: string;
  description: string;
  origin_country: string | null;
  posted_date: string | null;
  source_url: string;
}

export interface DemandExamplesResponse {
  demands: DemandExample[];
  notices: string[];
}

export interface AssetResult {
  rank: number;
  publication_id: string;
  title: string;
  ip_type: string;
  country_code: string;
  kind_code: string;
  assignees: string[];
  inventors: string[];
  publication_date: string | null;
  abstract: string;
  abstract_language: string;
  cpc_codes: string[];
  source_links: { google_patents: string; espacenet: string };
}

export interface MatchesResponse {
  demand: { demand_id: string; title: string; description: string; source_url: string };
  assets: AssetResult[];
  meta: {
    retrieval: string;
    eligible_count: number;
    corpus_id: string;
    corpus_parquet_sha256: string;
    embedding_index_sha256: string;
    notices: string[];
  };
}
```

```ts
// frontend/src/main/infrastructure/operationalClient.ts
import type { DemandExamplesResponse, MatchesResponse } from "../domain/operational";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export function getDemandExamples(): Promise<DemandExamplesResponse> {
  return getJson<DemandExamplesResponse>(`${API_BASE_URL}/api/demand-examples`);
}

export function getMatches(demandId: string, limit = 5): Promise<MatchesResponse> {
  const params = new URLSearchParams({ demand_id: demandId, limit: String(limit) });
  return getJson<MatchesResponse>(`${API_BASE_URL}/api/matches?${params}`);
}
```

```tsx
// frontend/src/main/components/Matches/MatchesView.tsx
import { useEffect, useRef, useState } from "react";
import type { AssetResult, DemandExamplesResponse, MatchesResponse } from "../../domain/operational";
import * as defaultApi from "../../infrastructure/operationalClient";

type Api = Pick<typeof defaultApi, "getDemandExamples" | "getMatches">;

const IP_TYPE_LABEL: Record<string, string> = {
  patent: "Patente",
  utility_model: "Modelo de utilidad",
};

function Notices({ notices }: { readonly notices: readonly string[] }) {
  return (
    <aside aria-label="Avisos" className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100 space-y-1">
      {notices.map((notice) => (
        <p key={notice}>{notice}</p>
      ))}
    </aside>
  );
}

function AssetCard({ asset }: { readonly asset: AssetResult }) {
  return (
    <article className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-2">
      <header className="flex items-baseline gap-3">
        <span className="text-lg font-semibold text-violet-300">#{asset.rank}</span>
        <h3 className="font-semibold">{asset.title}</h3>
      </header>
      <p className="text-sm text-slate-300">
        <span>{IP_TYPE_LABEL[asset.ip_type] ?? asset.ip_type}</span>
        {" · "}
        <span>{asset.publication_id}</span>
        {asset.publication_date ? ` · ${asset.publication_date}` : ""}
      </p>
      <p className="text-sm">Titular: {asset.assignees.length > 0 ? asset.assignees.join(", ") : "No disponible"}</p>
      <details className="text-sm">
        <summary className="cursor-pointer text-violet-300">Datos del activo</summary>
        <p className="mt-2 text-slate-200">{asset.abstract}</p>
        {asset.inventors.length > 0 && <p className="mt-2">Inventores: {asset.inventors.join(", ")}</p>}
        {asset.cpc_codes.length > 0 && <p className="mt-2">CPC del activo: {asset.cpc_codes.join(", ")}</p>}
      </details>
      <p className="text-sm">
        Fuente:{" "}
        <a className="text-violet-300 underline" href={asset.source_links.google_patents} target="_blank" rel="noreferrer">
          Google Patents
        </a>
        {" · "}
        <a className="text-violet-300 underline" href={asset.source_links.espacenet} target="_blank" rel="noreferrer">
          Espacenet
        </a>
      </p>
    </article>
  );
}

export function MatchesView({ api = defaultApi }: { readonly api?: Api }) {
  const [examples, setExamples] = useState<DemandExamplesResponse | null>(null);
  const [result, setResult] = useState<MatchesResponse | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0);

  useEffect(() => {
    api.getDemandExamples().then(setExamples).catch(() => setError("No se pudieron cargar las demandas de ejemplo."));
  }, [api]);

  const choose = (demandId: string) => {
    const request = ++latestRequest.current;
    setSelected(demandId);
    setResult(null);
    setError(null);
    setLoading(true);
    api
      .getMatches(demandId)
      .then((response) => {
        if (request === latestRequest.current) setResult(response);
      })
      .catch(() => {
        if (request === latestRequest.current) setError("No se pudieron cargar los resultados.");
      })
      .finally(() => {
        if (request === latestRequest.current) setLoading(false);
      });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">De una demanda real a activos españoles</h1>
      <p className="text-slate-300 text-sm">
        Demandas de ejemplo ingeridas desde Innoget. Elige una para ver qué activos de propiedad industrial españoles
        pueden ser relevantes.
      </p>
      {examples && <Notices notices={examples.notices} />}

      <section aria-label="Demandas" className="grid gap-2 sm:grid-cols-2">
        {examples?.demands.map((demand) => (
          <button
            key={demand.demand_id}
            type="button"
            onClick={() => choose(demand.demand_id)}
            aria-pressed={selected === demand.demand_id}
            className={`text-left rounded-lg border p-3 ${
              selected === demand.demand_id ? "border-violet-400 bg-slate-800" : "border-slate-700 hover:border-slate-500"
            }`}
          >
            <span className="font-medium">{demand.title}</span>
          </button>
        ))}
      </section>

      {loading && <p>Buscando activos…</p>}
      {error && <p role="alert" className="text-rose-300">{error}</p>}
      {result && result.assets.length === 0 && <p>No hay activos elegibles para esta demanda.</p>}
      {result && result.assets.length > 0 && (
        <section aria-label="Resultados" className="space-y-3">
          {result.assets.map((asset) => (
            <AssetCard key={asset.publication_id} asset={asset} />
          ))}
        </section>
      )}
    </div>
  );
}
```

```tsx
// frontend/src/main/components/Matches/MatchesPage.tsx
import { BrandHeader } from "../shared/BrandHeader";
import { MatchesView } from "./MatchesView";

export function MatchesPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <BrandHeader />
      <main className="flex-1 max-w-5xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <MatchesView />
      </main>
    </div>
  );
}
```

In `frontend/src/main/main.tsx` import `MatchesPage` from `./components/Matches/MatchesPage.tsx`, add `const Root = window.location.pathname.startsWith("/matches") ? MatchesPage : App;` above `createRoot(...)`, and render `<Root />` instead of `<App />`. The legacy `App` is not modified.

- [ ] **Step 4: Run tests and frontend gates**

Run (in `frontend/`): `npx vitest run test/unit/MatchesView.test.tsx && npm run typecheck && npm run lint && npm test`
Expected: all pass (no regression in existing frontend tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/main/domain/operational.ts frontend/src/main/infrastructure/operationalClient.ts frontend/src/main/components/Matches frontend/src/main/main.tsx frontend/test/unit/MatchesView.test.tsx
git commit -m "feat(frontend): /matches screen, demand to Spanish assets" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```

---

### Task 7: Real-data smoke, runbook, manual acceptance

Runs after the embedding generation of the retrieval plan has finished (`Wrote indexes` in its log). Produces data and documentation; no production code.

**Files:**
- Create (not committed): `data/snapshots/operational_corpus_v1/demands_v1.json`
- Create: `docs/operational-mvp-runbook.md`

- [ ] **Step 1: Build the demand snapshot**

Run: `python scripts/build_demands_snapshot.py`
Expected: `Wrote .../demands_v1.json: 39 demands`

- [ ] **Step 2: Start-up verification on real artifacts**

Run:
```bash
python - <<'E'
import sys, time
sys.path.insert(0, "backend/src/main")
from pathlib import Path
from infrastructure.operational.service import OperationalMatchingService
t = time.perf_counter()
service = OperationalMatchingService.from_directory(Path("data/snapshots/operational_corpus_v1"))
print(f"startup {time.perf_counter()-t:.1f}s")
demand = service.examples()["demands"][0]
t = time.perf_counter()
result = service.matches(demand["demand_id"])
print(f"request {time.perf_counter()-t:.2f}s eligible={result['meta']['eligible_count']} results={len(result['assets'])}")
E
```
Expected: no exception (all hashes verify); `eligible_count` > 40000; 5 results. The startup time and per-request time are recorded in the runbook. If a request takes over 1 s, stop and report (the eligible-count loop is the suspect).

- [ ] **Step 3: Serve and look at it**

Run: `(cd frontend && npm run build) && NEXUS_MVP_ENABLED=1 uvicorn main:app --app-dir backend/src/main --port 8080` and open `http://127.0.0.1:8080/matches`. Choose three demands. Check by eye, and write down in the runbook: the four notices are visible, no number or percentage appears, links open the right public page, an unexplained or empty result is reported rather than hidden. This is a look, not a judgment of quality and not part of the probe. **Do not open `experiments/operational-dense-probe/outputs/provenance_DO_NOT_OPEN.json`.**

- [ ] **Step 4: Write the runbook**

Create `docs/operational-mvp-runbook.md` with: purpose (one paragraph); how to regenerate artifacts (`build_operational_corpus.py`, `extract_operational_texts.py`, generation, `build_demands_snapshot.py`); the start command and the two environment variables; what the screen claims and does not claim (copy the list from spec section 9); measured startup and request times from Step 2; the known limits (39 demands only, EP excluded, licence unverified, quality in evaluation). State that the ranking-quality sentence is updated only after `docs/operational-dense-probe-result.md` exists.

- [ ] **Step 5: Full gates and commit**

Run: `python scripts/check_docs_correctness.py && pytest -q && ruff check backend/src/main backend/test scripts && mypy backend/src/main --ignore-missing-imports && python scripts/check_architecture.py && PYTHONPATH=backend/src/main lint-imports && (cd frontend && npm run typecheck && npm run lint && npm test)`
Expected: all pass.

```bash
git add docs/operational-mvp-runbook.md
git commit -m "docs: operational MVP runbook" -m "Co-Authored-By: Lydia Bares <lydiabares@gmail.com>" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01RtNtHiivWULzRbcvasgd8H"
```
