"""E2E test for the M0 vs M1 pilot comparison CLI (PR-E).

Runs the real script against the real sealed dataset, real frozen M1 artifact,
and real pre-registered protocol — no mocks, no synthetic fixtures. Verifies
the acceptance bar this PR closes: a reproducible M0-vs-M1 comparative result
with explicit denominators/exclusions and full provenance.
"""

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "scripts" / "run_m0_vs_m1_comparison.py"


def _run_cli(output_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--output-dir", str(output_dir)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_m0_vs_m1_comparison_cli_exits_zero_and_writes_artifacts(tmp_path: Path):
    output_dir = tmp_path / "run_a"
    result = _run_cli(output_dir)

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert (output_dir / "m0_run_report.json").is_file()
    assert (output_dir / "m1_run_report.json").is_file()
    assert (output_dir / "m0_vs_m1_comparative_report.json").is_file()


def test_m0_vs_m1_comparative_report_has_three_pre_registered_hypotheses(tmp_path: Path):
    output_dir = tmp_path / "run_a"
    _run_cli(output_dir)

    comparative = json.loads((output_dir / "m0_vs_m1_comparative_report.json").read_text())

    assert comparative["study_protocol_id"] == "NEXUS-M0-VS-M1-PILOT"
    assert comparative["study_status"] == "PILOT"
    assert set(comparative["run_ids"].keys()) == {"M0", "M1"}

    ids = [r["hypothesis_id"] for r in comparative["results"]]
    assert ids == ["H01_M0_VS_M1_NDCG10", "H02_M0_VS_M1_RECALL5", "H03_M0_VS_M1_MRR"]

    for r in comparative["results"]:
        # 3 sealed demand queries (NOT 45 pairs): evaluate_study_protocol
        # performs paired inference at the demand level, so n_paired tops out
        # at 3 even though the sealed benchmark has 45 demand-patent pairs.
        assert r["n_paired"] + len(r["excluded_demand_ids"]) == 3
        assert "wilcoxon" in r and "p_value" in r["wilcoxon"]
        assert "bootstrap_ci" in r and "ci_lower" in r["bootstrap_ci"]


def test_m0_run_report_has_no_embedding_provenance_m1_does(tmp_path: Path):
    output_dir = tmp_path / "run_a"
    _run_cli(output_dir)

    m0 = json.loads((output_dir / "m0_run_report.json").read_text())
    m1 = json.loads((output_dir / "m1_run_report.json").read_text())

    assert m0["embedding_provenance"] is None
    assert m1["embedding_provenance"] is not None
    assert m1["embedding_provenance"]["artifact_id"]
    assert m0["model_config_sha256"]
    assert m1["model_config_sha256"] == m0["model_config_sha256"]


def test_m0_vs_m1_comparison_cli_is_deterministic_across_runs(tmp_path: Path):
    """Clean-clone reproducibility gate (ADR 0007 style), with an EXPLICIT boundary:

    MUST be identical across independent runs (scientific result + accounting):
    dataset/policy/model-config hashes, macro metrics, paired-observation
    accounting (n_paired, excluded_demand_ids), and every statistical outcome
    (Wilcoxon p-value, BH-adjusted q-value, rejection decision).

    MUST NOT be compared for equality (execution identity, not a result):
    run_id and created_at. These are asserted to *differ* below, precisely to
    make the boundary intentional rather than an oversight.
    """
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"
    _run_cli(dir_a)
    _run_cli(dir_b)

    comp_a = json.loads((dir_a / "m0_vs_m1_comparative_report.json").read_text())
    comp_b = json.loads((dir_b / "m0_vs_m1_comparative_report.json").read_text())

    for ra, rb in zip(comp_a["results"], comp_b["results"], strict=True):
        assert ra["hypothesis_id"] == rb["hypothesis_id"]
        assert ra["n_paired"] == rb["n_paired"]
        assert ra["excluded_demand_ids"] == rb["excluded_demand_ids"]
        assert ra["wilcoxon"]["p_value"] == rb["wilcoxon"]["p_value"]
        assert ra["adjusted_q_value"] == rb["adjusted_q_value"]
        assert ra["rejected"] == rb["rejected"]

    m0_a = json.loads((dir_a / "m0_run_report.json").read_text())
    m0_b = json.loads((dir_b / "m0_run_report.json").read_text())
    assert m0_a["dataset_sha256"] == m0_b["dataset_sha256"]
    assert m0_a["policy_sha256"] == m0_b["policy_sha256"]
    assert m0_a["model_config_sha256"] == m0_b["model_config_sha256"]
    assert m0_a["macro_strict"] == m0_b["macro_strict"]
    assert m0_a["macro_broad"] == m0_b["macro_broad"]
    assert m0_a["macro_denominators"] == m0_b["macro_denominators"]

    # Execution identity is NOT a scientific result: it is expected to differ,
    # and this test documents that expectation instead of silently ignoring it.
    assert m0_a["run_id"] != m0_b["run_id"]
    assert m0_a["created_at"] != m0_b["created_at"]
