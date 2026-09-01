import pytest
from pathlib import Path
from backend.patent_agent.tools.duckdb_patents import DuckDbPatentsDataSource
from backend.patent_agent.tools.schemas import PatentRecord

def test_duckdb_patents_crud(tmp_path):
    db_file = tmp_path / "test_patents.duckdb"
    ds = DuckDbPatentsDataSource(db_path=str(db_file))
    
    # Seed test record
    rec = PatentRecord(
        publication_number="ES-2849102-A1",
        title="Composición detergente ecológica a baja temperatura",
        abstract="Formulación líquida con tensioactivos biodegradables para lavado en frío.",
        assignee="Universidad Complutense de Madrid",
        filing_date="2021-04-15",
        publication_date="2022-10-20",
        cpc_codes=["C11D1/00", "C11D3/386"],
        citation_count=4,
        backward_citation_count=8,
    )
    ds.insert_patents([rec])
    
    # Retrieve by CPC prefix
    results = ds.search_patents(cpc_prefix="C11D")
    assert len(results) == 1
    assert results[0].publication_number == "ES-2849102-A1"
    assert results[0].citation_count == 4
    assert results[0].backward_citation_count == 8

    # Cluster stats
    stats = ds.get_cluster_stats("C11D", ref_year=2026)
    assert stats["patent_count"] == 1
    assert stats["mean_age"] == 5.0  # 2026 - 2021
