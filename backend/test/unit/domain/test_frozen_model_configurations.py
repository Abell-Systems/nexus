"""Guard tests for ADR 0012: frozen M0-M6 configuration provenance, no tuning."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from domain.models.evaluation import ModelConfigurationManifest, ModelConfigurationRecord
from domain.models.matching import MatchingPolicyConfig


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@pytest.fixture
def manifest_path() -> Path:
    return get_repo_root() / "config" / "evaluations" / "model_configurations_m0_m6.json"


def test_valid_manifest_loads(manifest_path: Path) -> None:
    manifest = ModelConfigurationManifest.load_from_json(manifest_path)
    assert manifest.tuning_status == "NOT_TUNED_NO_INDEPENDENT_DEV_SET"
    assert manifest.development_set is None


def test_frozen_manifest_tamper_rejection(manifest_path: Path, tmp_path: Path) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["models"][0]["version"] = "9.9.9"
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="integrity verification failed"):
        ModelConfigurationManifest.load_from_json(tampered)


def test_invalid_provenance_status_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelConfigurationRecord(
            model_id="M0",
            description="Lexical BM25 baseline",
            ranker="LexicalRanker",
            weights=None,
            version="1.0.0",
            provenance_status="TUNED",
        )


def test_invalid_tuning_status_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelConfigurationManifest(
            study_id="NEXUS-PHASE2-M0-M6-CONFIG-FREEZE",
            frozen_at="2026-09-04",
            tuning_status="TUNED_VIA_GRID_SEARCH",
            development_set=None,
            models=[
                ModelConfigurationRecord(
                    model_id="M0",
                    description="Lexical BM25 baseline",
                    ranker="LexicalRanker",
                    weights=None,
                    version="1.0.0",
                    provenance_status="PRE_EXISTING_INITIAL_CONFIGURATION",
                )
            ],
            config_sha256="0" * 64,
        )


def test_m6_weights_match_default_matching_policy(manifest_path: Path) -> None:
    manifest = ModelConfigurationManifest.load_from_json(manifest_path)
    m6 = next(r for r in manifest.models if r.model_id == "M6")

    policy_path = get_repo_root() / "config" / "policies" / "matching" / "default_matching_policy.json"
    policy = MatchingPolicyConfig.load_from_json(policy_path)

    assert m6.weights == {
        "alpha": policy.weights.alpha,
        "beta": policy.weights.beta,
        "gamma": policy.weights.gamma,
    }
    assert m6.provenance_status == "PRE_EXISTING_INITIAL_CONFIGURATION"


def test_exactly_m0_through_m6_represented(manifest_path: Path) -> None:
    manifest = ModelConfigurationManifest.load_from_json(manifest_path)
    assert {r.model_id for r in manifest.models} == {"M0", "M1", "M2", "M3", "M4", "M5", "M6"}
