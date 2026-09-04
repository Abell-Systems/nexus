"""Tests for pre-registered study protocol configuration under ADR 0011.

Invariants verified:
- Study protocol configuration exists at config/evaluations/comparisons_m0_m6.json.
- Protocol defines immutable study metadata: study_id, version, sha256, alpha, seed.
- Family of hypotheses (H01-H06) is pre-registered across M0-M6 model variants.
- Every hypothesis defines stable ID, baseline, treatment, metric, scope, and alternative.
- Hash of the protocol file is verifiable and fails fast on tampering.
"""

import hashlib
import json
from pathlib import Path

import pytest


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def test_study_protocol_file_exists_and_parses():
    """Verify that comparisons_m0_m6.json exists and conforms to protocol requirements."""
    repo_root = get_repo_root()
    protocol_path = repo_root / "config" / "evaluations" / "comparisons_m0_m6.json"
    assert protocol_path.is_file(), f"Pre-registered study protocol missing at {protocol_path}"

    content = protocol_path.read_text(encoding="utf-8")
    data = json.loads(content)

    assert data["study_id"] == "NEXUS-PHASE2-ABLATION-M0-M6"
    assert data["study_version"] == "1.0.0"
    assert data["alpha"] == 0.05
    assert data["multiple_testing_method"] == "benjamini_hochberg"
    assert data["bootstrap_iterations"] == 10000
    assert data["bootstrap_confidence_level"] == 0.95
    assert data["seed"] == 42

    hypotheses = data["hypotheses"]
    assert len(hypotheses) == 6, "Expected exactly 6 pre-registered hypotheses for M0-M6"

    expected_ids = [
        "H01_M1_vs_M0_MRR",
        "H02_M2_vs_M0_MRR",
        "H03_M3_vs_M0_MRR",
        "H04_M4_vs_M0_MRR",
        "H05_M5_vs_M0_MRR",
        "H06_M6_vs_M0_MRR",
    ]
    actual_ids = [h["id"] for h in hypotheses]
    assert actual_ids == expected_ids

    for h in hypotheses:
        assert h["baseline"] == "M0"
        assert h["metric"] in ("mrr", "ndcg_at_5", "precision_at_3", "recall_at_3")
        assert h["scope"] in ("strict", "broad")
        assert h["alternative"] in ("greater", "two-sided", "less")


def test_study_protocol_sha256_integrity():
    """Verify that protocol_sha256 matches the exact content digest when excluding self-reference."""
    repo_root = get_repo_root()
    protocol_path = repo_root / "config" / "evaluations" / "comparisons_m0_m6.json"
    data = json.loads(protocol_path.read_text(encoding="utf-8"))

    declared_sha = data["protocol_sha256"]
    assert len(declared_sha) == 64

    # The payload without protocol_sha256 field must match declared_sha
    payload = {k: v for k, v in data.items() if k != "protocol_sha256"}
    canonical_bytes = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

    assert declared_sha == computed_sha, f"Protocol digest mismatch: {declared_sha} vs {computed_sha}"
