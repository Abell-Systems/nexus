"""Patent data source adapters (BigQuery, DuckDB, Mock fixtures)."""

import os
from typing import Any
from domain.models.runtime_schemas import PatentRecord
from .fixtures import FIXTURE_PATENTS


class MockPatentsDataSource:
    def __init__(self):
        self.patents = [PatentRecord(**p) for p in FIXTURE_PATENTS]

    def search_patents(self, query: str, domain: str = "", limit: int = 20) -> list[PatentRecord]:
        q = query.lower()
        matched = [p for p in self.patents if q in p.title.lower() or q in p.abstract.lower()]
        return (matched or self.patents)[:limit]

    def get_status(self) -> dict[str, Any]:
        return {"type": "mock", "patent_count": len(self.patents)}


class BigQueryPatentsDataSource(MockPatentsDataSource):
    """BigQuery patent data source adapter with fallback to mock."""
    def __init__(self, project_id: str | None = None):
        super().__init__()
        self.project_id = project_id or os.getenv("GCP_PROJECT", "test-project")

    def get_status(self) -> dict[str, Any]:
        return {"type": "bigquery", "project_id": self.project_id, "mock": True}


_DATASOURCE_INSTANCE = MockPatentsDataSource()


def get_patents_datasource() -> Any:
    use_duckdb = os.getenv("PATENTS_DATA_SOURCE", "").lower() == "duckdb"
    if use_duckdb:
        from .duckdb_patents import get_duckdb_datasource
        return get_duckdb_datasource()
    return _DATASOURCE_INSTANCE
