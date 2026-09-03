"""Zero-copy DuckDB analytical query engine over canonical Parquet dataset stores."""

from pathlib import Path
from typing import Any

import duckdb

from domain.protocols.storage import QueryEngineProtocol

PARQUET_GLOB = "*.parquet"


class DuckDbQueryEngine(QueryEngineProtocol):
    """Analytical query engine executing in-memory zero-copy queries against Parquet datasets."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self.conn = connection

    @classmethod
    def from_parquet_dir(cls, dataset_dir: Path | str) -> "DuckDbQueryEngine":
        """Initialize in-memory DuckDB connection and register zero-copy views over Parquet files."""
        dataset_path = Path(dataset_dir).resolve()
        conn = duckdb.connect(":memory:")

        # Register patents view
        patents_dir = dataset_path / "patents"
        if patents_dir.is_dir() and list(patents_dir.glob(PARQUET_GLOB)):
            patents_pattern = (patents_dir / PARQUET_GLOB).as_posix()
            conn.execute(f"CREATE VIEW patents AS SELECT * FROM read_parquet('{patents_pattern}')")
        elif (dataset_path / "patents.parquet").is_file():
            conn.execute(
                f"CREATE VIEW patents AS SELECT * FROM read_parquet('{(dataset_path / 'patents.parquet').as_posix()}')"
            )
        elif list(dataset_path.glob(PARQUET_GLOB)):
            conn.execute(
                f"CREATE VIEW patents AS SELECT * FROM read_parquet('{(dataset_path / PARQUET_GLOB).as_posix()}')"
            )

        # Register observations view
        observations_dir = dataset_path / "observations"
        if observations_dir.is_dir() and list(observations_dir.glob(PARQUET_GLOB)):
            obs_pattern = (observations_dir / PARQUET_GLOB).as_posix()
            conn.execute(f"CREATE VIEW observations AS SELECT * FROM read_parquet('{obs_pattern}')")
        elif (dataset_path / "observations.parquet").is_file():
            conn.execute(
                f"CREATE VIEW observations AS SELECT * FROM read_parquet('{(dataset_path / 'observations.parquet').as_posix()}')"
            )

        return cls(connection=conn)

    def search_by_cpc_prefix(self, cpc_prefix: str, limit: int = 1000) -> list[dict[str, Any]]:
        """Search patents containing any CPC classification matching the given prefix."""
        query = """
        SELECT *
        FROM patents
        WHERE classifications_cpc IS NOT NULL
          AND len(list_filter(classifications_cpc, x -> starts_with(x, ?))) > 0
        LIMIT ?
        """
        cur = self.conn.execute(query, [cpc_prefix, limit])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]

    def get_cluster_aggregates(self, cpc_prefix: str, ref_year: int = 2026) -> dict[str, Any]:
        """Compute cluster aggregates for patents matching the given CPC prefix.

        Scientific Invariant Gate 1: None != 0. Unobserved forward citations
        (NULL) do not drag the average down.
        """
        query = """
        SELECT
            COUNT(*)::INT AS patent_count,
            COUNT(forward_citation_count)::INT AS observed_citations_count,
            AVG(forward_citation_count)::DOUBLE AS avg_forward_citations
        FROM patents
        WHERE classifications_cpc IS NOT NULL
          AND len(list_filter(classifications_cpc, x -> starts_with(x, ?))) > 0
        """
        cur = self.conn.execute(query, [cpc_prefix])
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        if not row:
            return {
                "patent_count": 0,
                "observed_citations_count": 0,
                "avg_forward_citations": None,
            }

        res = dict(zip(cols, row, strict=False))
        if res.get("observed_citations_count", 0) == 0:
            res["avg_forward_citations"] = None

        return res
