"""Unit tests for concept-to-CPC taxonomy mapping under ADR 0004 and ADR 0005.

Invariants:
- All mapping functions require an explicitly injected MatchingPolicyConfig.
- Zero implicit filesystem loading or repository-relative paths.
"""

from pathlib import Path

import pytest

from application.landscape.cpc_taxonomy import (
    get_cpc_description,
    map_concept_to_cpc,
    map_demand_to_cpc,
)
from domain.models.matching import MatchingPolicyConfig


@pytest.fixture
def policy():
    # Anchored to repo root so this resolves regardless of pytest's invocation cwd
    # (e.g. `pytest` from repo root vs `cd backend && pytest`).
    repo_root = Path(__file__).resolve().parents[5]
    policy_path = repo_root / "config" / "policies" / "matching" / "default_matching_policy.json"
    return MatchingPolicyConfig.load_from_json(policy_path)


def test_map_concept_to_cpc(policy):
    cpc_codes = map_concept_to_cpc("solid electrolyte interphase", policy=policy)
    assert "H01M10/0562" in cpc_codes
    assert "H01M10/0525" in cpc_codes


def test_map_demand_to_cpc(policy):
    prefixes = map_demand_to_cpc(
        "Concentrated industrial detergent formulation",
        "Biodegradable surfactants",
        policy=policy,
    )
    assert "C11D" in prefixes


def test_get_cpc_description(policy):
    desc = get_cpc_description("H01M10/0562", policy=policy)
    assert "Solid electrolytes" in desc or "inorganic" in desc
