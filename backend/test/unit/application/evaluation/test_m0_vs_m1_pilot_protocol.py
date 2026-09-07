"""Tests for the pre-registered M0-vs-M1 pilot study protocol (PR-E).

Invariants verified:
- config/evaluations/comparisons_m0_vs_m1_pilot.json exists and parses.
- Exactly 3 pre-registered hypotheses: nDCG@10 (primary), Recall@5 (secondary),
  MRR (secondary, pre-registered, not reinterpreted from the M0-M6 family).
- protocol_sha256 matches the exact content digest excluding self-reference.
- The file round-trips through domain.models.evaluation.StudyProtocol.
- This file is independent of config/evaluations/comparisons_m0_m6.json — neither
  file references or mutates the other.
"""

import hashlib
import json
from pathlib import Path

from domain.models.evaluation import StudyProtocol


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def get_protocol_path() -> Path:
    return get_repo_root() / "config" / "evaluations" / "comparisons_m0_vs_m1_pilot.json"


def test_m0_vs_m1_pilot_protocol_file_exists_and_parses():
    protocol_path = get_protocol_path()
    assert protocol_path.is_file(), f"Pre-registered M0-vs-M1 protocol missing at {protocol_path}"

    data = json.loads(protocol_path.read_text(encoding="utf-8"))

    assert data["study_id"] == "NEXUS-M0-VS-M1-PILOT"
    assert data["study_version"] == "1.0.0"
    assert data["alpha"] == 0.05
    assert data["multiple_testing_method"] == "benjamini_hochberg"
    assert data["bootstrap_iterations"] == 10000
    assert data["bootstrap_confidence_level"] == 0.95
    assert data["seed"] == 42

    hypotheses = data["hypotheses"]
    assert len(hypotheses) == 3, "Expected exactly 3 pre-registered hypotheses for the M0-vs-M1 pilot"

    expected_ids = ["H01_M0_VS_M1_NDCG10", "H02_M0_VS_M1_RECALL5", "H03_M0_VS_M1_MRR"]
    assert [h["id"] for h in hypotheses] == expected_ids

    expected_metrics = {
        "H01_M0_VS_M1_NDCG10": "ndcg_at_10",
        "H02_M0_VS_M1_RECALL5": "recall_at_5",
        "H03_M0_VS_M1_MRR": "mrr",
    }
    for h in hypotheses:
        assert h["baseline"] == "M0"
        assert h["treatment"] == "M1"
        assert h["metric"] == expected_metrics[h["id"]]
        assert h["scope"] == "strict"
        assert h["alternative"] == "greater"


def test_m0_vs_m1_pilot_protocol_sha256_integrity():
    data = json.loads(get_protocol_path().read_text(encoding="utf-8"))
    declared_sha = data["protocol_sha256"]
    assert len(declared_sha) == 64

    payload = {k: v for k, v in data.items() if k != "protocol_sha256"}
    canonical_bytes = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

    assert declared_sha == computed_sha, f"Protocol digest mismatch: {declared_sha} vs {computed_sha}"


def test_m0_vs_m1_pilot_protocol_round_trips_through_domain_model():
    data = json.loads(get_protocol_path().read_text(encoding="utf-8"))
    protocol = StudyProtocol.model_validate(data)

    assert protocol.study_id == "NEXUS-M0-VS-M1-PILOT"
    assert len(protocol.hypotheses) == 3
    assert protocol.hypotheses[0].metric == "ndcg_at_10"
    assert protocol.hypotheses[0].alternative == "greater"


def test_m0_vs_m1_pilot_protocol_is_independent_of_m0_m6_family():
    m0_m6_path = get_repo_root() / "config" / "evaluations" / "comparisons_m0_m6.json"
    m0_m6_data = json.loads(m0_m6_path.read_text(encoding="utf-8"))
    pilot_data = json.loads(get_protocol_path().read_text(encoding="utf-8"))

    assert m0_m6_data["study_id"] != pilot_data["study_id"]
    m0_m6_ids = {h["id"] for h in m0_m6_data["hypotheses"]}
    pilot_ids = {h["id"] for h in pilot_data["hypotheses"]}
    assert m0_m6_ids.isdisjoint(pilot_ids), "Hypothesis IDs must not collide between the two protocols"
