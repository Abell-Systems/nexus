"""ADR 0028 reproducibility guarantee: this PR (and any future PR) must never
overwrite the frozen pre-ADR-0028 experiment artifacts under data/experiments/ --
they were computed under the old, defective denominator semantics and must stay
byte-for-byte as historical evidence of what that produced, distinguishable from
any future re-run under the fixed eligible-universe semantics.

If this test fails, a file listed below was edited. That is only ever the correct
outcome as a DELIBERATE, separately reviewed re-freeze -- never as a side effect
of an unrelated change. Update the corresponding hash here only when that is true.
"""

import hashlib
from pathlib import Path

import pytest

_EXPECTED_SHA256 = {
    "dataset_identity_audit.json": "7d9152ab5fcd9b2a1cfa712dda5ce492f3072768f0754a9b372c9d20a846bc02",
    "m0_run_report.json": "86aaefefdba75c4575a82b21210c42b78f8c809b08f3a6fcadbb6a4b697fca9b",
    "m0_run_report_strict.json": "2f680d9a0673acad0bb60738f8737d32b22ba9ce374b82b772931bd97979a6d4",
    "m0_vs_m1_comparative_report.json": "cc0b4bb1433c0bf627a5c447598411b3edb8ee707f4335f34c74ebd7c905da0c",
    "m0_vs_m1_comparative_report_strict.json": "ce9417c794b391c87b5bc497eded29c6632446101b75103d78a73340f61e6d10",
    "m1_run_report.json": "203c694db657212f0a554f3779903b33b2d7b3a4dbdf876a6923e3fc238a5581",
    "m1_run_report_strict.json": "62f33196c770a441042b56fea2dfd7c15d65b7d23214e5d11645c30083137a79",
    "pilot_evaluation_report.json": "792e7e078ff467c7cf430792bd5727ba7f4f01f9ae2f4393e97944f55e95dbe4",
    "power_analysis_wilcoxon.json": "8d41d3d28efe60bfe2712257639db9a36b313f0327704ffc356fe31583bf9d87",
    "power_analysis_wilcoxon_n39_sensitivity.json": "793bb6b648672ca321f1c0325abb33385222b9f9e053f0c37f024cf3a3fc095a",
    "power_analysis_wilcoxon_n43_sensitivity.json": "ee06886e6f86d9defdc46efb5025b7d50b3a85d8afa811f44eabccfe583e3bd5",
    "power_analysis_wilcoxon_n48_sensitivity.json": "98e1d195047407c02f2abef59108fa208a9f77b81b6436a34d2504f604ae4f84",
}


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("filename,expected_sha256", sorted(_EXPECTED_SHA256.items()))
def test_frozen_experiment_artifact_unmodified(filename: str, expected_sha256: str) -> None:
    path = _get_repo_root() / "data" / "experiments" / filename
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == expected_sha256, (
        f"data/experiments/{filename} has changed content (sha256 {actual} != "
        f"expected {expected_sha256}). These files were frozen under the "
        "pre-ADR-0028 denominator semantics -- if this is a deliberate, "
        "separately-reviewed re-freeze, update the expected hash here; "
        "otherwise this file was edited by accident."
    )


def test_frozen_experiment_artifacts_directory_has_no_untracked_new_files() -> None:
    """Catches the complementary mistake: a new file dropped into data/experiments/
    without updating _EXPECTED_SHA256 above to account for it."""
    actual_files = {
        p.name for p in (_get_repo_root() / "data" / "experiments").glob("*.json")
    }
    assert actual_files == set(_EXPECTED_SHA256.keys()), (
        f"data/experiments/*.json contents changed: {actual_files ^ set(_EXPECTED_SHA256.keys())}. "
        "Update _EXPECTED_SHA256 in this test to match."
    )
