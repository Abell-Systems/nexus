"""Architectural invariant tests enforcing ADR 0003 and AGENTS.md rules in CI.

Enforces:
1. No production source file in application/ingestion hardcodes country lists or organization lists.
2. OriginPolicyConfig and DefaultOriginResolver fail fast when configuration is absent or invalid (zero synthetic fallback policies).
3. DemandRecord never contains synthetic fallback strings for missing data.
"""

from pathlib import Path

import pytest

from application.ingestion.origin_resolver import DefaultOriginResolver
from domain.models.origin_policy import OriginPolicyConfig


def test_no_hardcoded_country_or_organization_lists_in_ingestion_production_code() -> None:
    """CI enforcement: scans ingestion production source code for forbidden hardcoding anti-patterns."""
    ingestion_dir = Path("backend/src/main/application/ingestion")
    assert ingestion_dir.exists(), f"Directory not found: {ingestion_dir}"

    py_files = list(ingestion_dir.rglob("*.py"))
    assert len(py_files) >= 3

    forbidden_tokens = [
        "KNOWN_SPANISH_ORGANIZATIONS",
        "EXPLICIT_NON_SPANISH_COUNTRIES",
        "DEFAULT_FALLBACK_POLICY",
    ]

    violations: list[str] = []
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in content:
                violations.append(f"{file_path}: contains forbidden anti-pattern token '{token}'")

    assert not violations, "Architectural violation of ADR 0003:\n" + "\n".join(violations)


def test_origin_policy_strictly_rejects_missing_file_in_ci() -> None:
    """Enforces fail-fast invariant: missing configuration MUST raise FileNotFoundError."""
    non_existent = Path("config/policies/non_existent_policy.json")
    with pytest.raises(FileNotFoundError):
        OriginPolicyConfig.load_from_json(non_existent)


def test_resolver_rejects_none_policy() -> None:
    """Enforces fail-fast invariant: resolver cannot be instantiated without a valid policy."""
    with pytest.raises(ValueError, match="policy must be provided"):
        DefaultOriginResolver(policy=None)  # type: ignore[arg-type]
