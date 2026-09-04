"""Guard tests for ADR 0012: frozen M0-M6 configuration provenance, no tuning."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from domain.models.evaluation import (
    ModelConfigurationManifest,
    ModelConfigurationRecord,
    SourcePolicyReference,
)
from domain.models.matching import MatchingPolicyConfig


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@pytest.fixture
def manifest_path() -> Path:
    return get_repo_root() / "config" / "evaluations" / "model_configurations_m0_m6.json"


class FrozenModelConfigurationTest:
    """Guards for ModelConfigurationManifest (ADR 0012): the frozen manifest is the authority
    for M0-M6 configuration; nothing here checks the manifest against implementation defaults —
    that direction of comparison is exactly the inversion ADR 0012 exists to prevent. Wiring
    tests proving the manifest's declared values actually reach execution belong with the
    component that consumes them (see MatchingAdapterTest in test_matching_adapter.py).
    """

    def test_should_load_manifest_when_valid(self, manifest_path: Path) -> None:
        manifest = ModelConfigurationManifest.load_from_json(manifest_path)
        assert manifest.tuning_status == "NOT_TUNED_NO_INDEPENDENT_DEV_SET"
        assert manifest.development_set is None

    def test_should_reject_manifest_when_tampered(self, manifest_path: Path, tmp_path: Path) -> None:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["models"][0]["version"] = "9.9.9"
        tampered = tmp_path / "tampered.json"
        tampered.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(ValueError, match="integrity verification failed"):
            ModelConfigurationManifest.load_from_json(tampered)

    def test_should_reject_record_when_provenance_status_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelConfigurationRecord(
                model_id="M0",
                description="Lexical BM25 baseline",
                ranker="compute_bm25_scores",
                weights=None,
                version="1.0.0",
                provenance_status="TUNED",
            )

    def test_should_reject_manifest_when_tuning_status_is_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ModelConfigurationManifest(
                study_id="NEXUS-PHASE2-M0-M6-CONFIG-FREEZE",
                frozen_at="2026-09-04",
                tuning_status="TUNED_VIA_GRID_SEARCH",
                development_set=None,
                source_policy=SourcePolicyReference(
                    path="config/policies/matching/default_matching_policy.json",
                    policy_sha256="0" * 64,
                ),
                models=[
                    ModelConfigurationRecord(
                        model_id="M0",
                        description="Lexical BM25 baseline",
                        ranker="compute_bm25_scores",
                        weights=None,
                        version="1.0.0",
                        provenance_status="PRE_EXISTING_INITIAL_CONFIGURATION",
                    )
                ],
                config_sha256="0" * 64,
            )

    def test_should_match_default_matching_policy_when_reading_m6_weights(self, manifest_path: Path) -> None:
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

    def test_should_represent_exactly_m0_through_m6_when_loading_manifest(self, manifest_path: Path) -> None:
        manifest = ModelConfigurationManifest.load_from_json(manifest_path)
        assert {r.model_id for r in manifest.models} == {"M0", "M1", "M2", "M3", "M4", "M5", "M6"}

    def test_should_match_current_default_policy_when_verifying_source_policy(self, manifest_path: Path) -> None:
        manifest = ModelConfigurationManifest.load_from_json(manifest_path)
        policy_path = get_repo_root() / "config" / "policies" / "matching" / "default_matching_policy.json"
        policy = MatchingPolicyConfig.load_from_json(policy_path)

        assert manifest.source_policy.path == "config/policies/matching/default_matching_policy.json"
        manifest.verify_source_policy(policy)  # must not raise

    def test_should_raise_value_error_when_source_policy_has_drifted(self, manifest_path: Path) -> None:
        manifest = ModelConfigurationManifest.load_from_json(manifest_path)
        policy_path = get_repo_root() / "config" / "policies" / "matching" / "default_matching_policy.json"
        policy = MatchingPolicyConfig.load_from_json(policy_path)

        drifted_manifest = manifest.model_copy(
            update={
                "source_policy": SourcePolicyReference(
                    path=manifest.source_policy.path,
                    policy_sha256="0" * 64,
                )
            }
        )

        with pytest.raises(ValueError, match="Source policy drift detected"):
            drifted_manifest.verify_source_policy(policy)
