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
