"""Unit tests for DuckDbPatentsDataSource adapter."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from infrastructure.sources.duckdb_patents import DuckDbPatentsDataSource, get_duckdb_datasource


def _create_dummy_parquet(target_path: Path):
    table = pa.Table.from_arrays(
        [
            pa.array(["ES-2849102-B2", "ES-2849103-B2"]),
            pa.array(["Solid State Battery Electrolyte", "Detergent composition"]),
            pa.array(["Novel sulfide electrolyte formulation", "Biodegradable surfactants"]),
            pa.array([["Bilper"], ["Repsol"]]),
            pa.array([["Inventor A"], ["Inventor B"]]),
            pa.array(["2020-01-01", "2021-01-01"]),
            pa.array(["2021-11-25", "2022-05-10"]),
            pa.array([["H01M10/0562"], ["C11D1/00"]]),
            pa.array([5, None]),
            pa.array([2, 1]),
        ],
        names=[
            "publication_id",
            "title",
            "abstract",
            "assignees",
            "inventors",
            "filing_date",
            "publication_date",
            "classifications_cpc",
            "forward_citation_count",
            "backward_citation_count",
        ],
    )
    pq.write_table(table, target_path)


def test_duckdb_datasource_from_parquet(tmp_path: Path):
    pq_file = tmp_path / "sample.parquet"
    _create_dummy_parquet(pq_file)

    ds = DuckDbPatentsDataSource.from_parquet(pq_file)
    assert ds.get_status()["type"] == "duckdb"

    # Search without domain
    results = ds.search_patents(query="electrolyte")
    assert len(results) == 1
    assert results[0].publication_number == "ES-2849102-B2"
    assert results[0].citation_count == 5

    # Search with domain
    results_domain = ds.search_patents(query="electrolyte", domain="Solid")
    assert len(results_domain) == 1
    assert results_domain[0].publication_number == "ES-2849102-B2"

    # Search with non-matching query
    results_empty = ds.search_patents(query="nonexistent_xyz")
    assert len(results_empty) == 0


def test_get_duckdb_datasource_factory(tmp_path: Path):
    pq_file = tmp_path / "corpus.parquet"
    _create_dummy_parquet(pq_file)

    ds_existing = get_duckdb_datasource(pq_file)
    assert ds_existing is not None
    assert len(ds_existing.search_patents("electrolyte")) == 1

    ds_missing = get_duckdb_datasource(tmp_path / "missing.parquet")
    assert ds_missing is not None
