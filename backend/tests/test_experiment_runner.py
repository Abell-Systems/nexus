import pytest
from pathlib import Path
from scripts.run_spanish_paper_experiment import run_experiment

def test_experiment_runner_end_to_end(tmp_path):
    output_dir = tmp_path / "experiment_out"
    metrics_list, case_studies = run_experiment(
        db_path="data/snapshots/patents_es_snapshot.duckdb",
        output_dir=str(output_dir),
        dry_run_llm=True
    )
    
    assert len(metrics_list) >= 3
    assert (output_dir / "metadata.json").exists()
    assert (output_dir / "demand_patent_alignment_matrix.csv").exists()
    assert (output_dir / "paper_results_summary.md").exists()
