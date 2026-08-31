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
