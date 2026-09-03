"""Unit tests for Demand data sources."""

import json
from pathlib import Path

from infrastructure.sources.demand_sources import (
    CORDISDemandDataSource,
    InnogetDemandDataSource,
    MockDemandDataSource,
    SBIRDemandDataSource,
    get_demand_datasource,
)


def test_innoget_demand_source_default_fallback():
    ds = InnogetDemandDataSource(snapshot_path="nonexistent_snapshot_path.json")
    demands = ds.get_spanish_demands()
    assert len(demands) >= 3

    # Cluster filter
    c11d = ds.get_demands_for_cluster("C11D")
    assert any(d.cpc_prefix == "C11D" for d in c11d)

    # Search with query
    detergent = ds.search_demand(query="detergent")
    assert any("detergent" in d.title.lower() for d in detergent)


def test_innoget_demand_source_from_json(tmp_path: Path):
    json_path = tmp_path / "challenges.json"
    data = [
        {
            "id": "CUSTOM-1",
            "title": "Custom Battery Challenge",
            "description": "Solid state electrolyte request",
            "cpc_prefix": "H01M",
            "posted_date": "2024-01-01",
            "url": "https://custom.com/1",
        }
    ]
    json_path.write_text(json.dumps(data), encoding="utf-8")

    ds = InnogetDemandDataSource(snapshot_path=str(json_path))
    demands = ds.get_spanish_demands()
    assert len(demands) == 1
    assert demands[0].id == "CUSTOM-1"


def test_innoget_demand_source_corrupt_json(tmp_path: Path):
    json_path = tmp_path / "corrupt.json"
    json_path.write_text("not json content", encoding="utf-8")

    ds = InnogetDemandDataSource(snapshot_path=str(json_path))
    assert ds.get_spanish_demands() == []


def test_sbir_demand_datasource():
    ds = SBIRDemandDataSource()
    results = ds.search_demand(query="electrolyte", domain="H01M")
    assert len(results) == 1
    assert results[0].source == "sbir"


def test_cordis_demand_datasource():
    ds = CORDISDemandDataSource()
    results = ds.search_demand(query="battery")
    assert len(results) == 1
    assert results[0].source == "cordis"


def test_mock_demand_datasource():
    ds = MockDemandDataSource()
    assert len(ds.search_demand()) == 2


def test_get_demand_datasource_factory(monkeypatch):
    assert isinstance(get_demand_datasource("cordis"), CORDISDemandDataSource)
    assert isinstance(get_demand_datasource("sbir"), SBIRDemandDataSource)
    assert isinstance(get_demand_datasource("innoget"), InnogetDemandDataSource)

    monkeypatch.setenv("DEMAND_SOURCE", "innoget")
    assert isinstance(get_demand_datasource("auto"), InnogetDemandDataSource)

    monkeypatch.delenv("DEMAND_SOURCE", raising=False)
    assert isinstance(get_demand_datasource("unknown"), MockDemandDataSource)
