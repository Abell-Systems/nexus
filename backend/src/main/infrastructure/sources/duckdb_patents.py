"""DuckDB datasource adapter for local patent snapshots."""

from pathlib import Path
from typing import Any

import duckdb

from domain.models.runtime_schemas import PatentRecord


class DuckDbPatentsDataSource:
    def __init__(self, db_path: str = "data/snapshots/patents_es_snapshot.duckdb", read_only: bool = True):
        self.db_path = db_path
        if Path(db_path).exists():
            self._conn = duckdb.connect(db_path, read_only=read_only)
        else:
            self._conn = duckdb.connect(":memory:")

    @classmethod
    def from_parquet(cls, parquet_path: str | Path) -> "DuckDbPatentsDataSource":
        instance = cls.__new__(cls)
        instance.db_path = ":memory:"
        instance._conn = duckdb.connect(":memory:")
        parquet_posix = Path(parquet_path).resolve().as_posix()
        instance._conn.execute(f"CREATE VIEW patents AS SELECT * FROM read_parquet('{parquet_posix}')")
        return instance

    def search_patents(self, query: str, domain: str = "", limit: int = 50) -> list[PatentRecord]:
        try:
            if domain:
                sql = "SELECT * FROM patents WHERE (title ILIKE ? OR abstract ILIKE ?) AND (title ILIKE ? OR abstract ILIKE ?) LIMIT ?"
                params = [f"%{query}%", f"%{query}%", f"%{domain}%", f"%{domain}%", limit]
            else:
                sql = "SELECT * FROM patents WHERE title ILIKE ? OR abstract ILIKE ? LIMIT ?"
                params = [f"%{query}%", f"%{query}%", limit]
            df = self._conn.execute(sql, params).df()
            records = []
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                records.append(
                    PatentRecord(
                        publication_number=str(row_dict.get("publication_id") or row_dict.get("publication_number", "")),
                        title=str(row_dict.get("title", "")),
                        abstract=str(row_dict.get("abstract", "")),
                        assignee=row_dict.get("assignees", []),
                        inventors=row_dict.get("inventors", []),
                        filing_date=str(row_dict.get("filing_date", "")),
                        publication_date=str(row_dict.get("publication_date", "")),
                        cpc_codes=row_dict.get("classifications_cpc", []),
                        citation_count=row_dict.get("forward_citation_count"),
                        backward_citation_count=row_dict.get("backward_citation_count"),
                    )
                )
            return records
        except Exception:
            return []

    def get_status(self) -> dict[str, Any]:
        return {"type": "duckdb", "db_path": self.db_path}


def get_duckdb_datasource(parquet_path: str | Path = "data/snapshots/patents_es_corpus.parquet") -> DuckDbPatentsDataSource:
    p = Path(parquet_path)
    if p.exists():
        return DuckDbPatentsDataSource.from_parquet(p)
    return DuckDbPatentsDataSource()
