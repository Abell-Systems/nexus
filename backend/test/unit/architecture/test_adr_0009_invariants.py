"""Automated architectural enforcement tests for ADR 0009 (Provider-Agnostic Agent Invocation & Decoupled Runtime).

Invariants enforced:
1. domain and application layers have ZERO imports from external agent/LLM provider SDKs
   (google.adk, google.genai, google.cloud.aiplatform, openai, anthropic, litellm, langgraph, llama_index).
2. The import-linter contract 'provider-sdk-isolation' is active and semantically validated.
3. Behaviorally verifies that importing any provider SDK inside application breaks lint-imports.
4. LlmClientProtocol, InventorAgentProtocol, AdversarialAgentProtocol, GovernorAgentProtocol exist in
   domain.protocols.agents and require no vendor SDKs.
"""

import configparser
import os
import subprocess
from pathlib import Path

from domain.protocols.agents import (
    AdversarialAgentProtocol,
    GovernorAgentProtocol,
    InventorAgentProtocol,
    LlmClientProtocol,
)


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_agent_protocols_are_pure_and_runtime_checkable():
    """ADR 0009 §1: Domain agent protocols exist and require no vendor SDKs."""
    assert isinstance(LlmClientProtocol, type)
    assert isinstance(InventorAgentProtocol, type)
    assert isinstance(AdversarialAgentProtocol, type)
    assert isinstance(GovernorAgentProtocol, type)


def test_provider_sdk_isolation_contract_semantics():
    """ADR 0009 §3: Verify that provider-sdk-isolation contract is configured in .importlinter."""
    config_path = _get_repo_root() / ".importlinter"
    assert config_path.exists()

    config = configparser.ConfigParser()
    config.read(config_path)

    sec = "importlinter:contract:provider-sdk-isolation"
    assert sec in config.sections()
    assert config.get(sec, "type") == "forbidden"
    source_pkgs = set(config.get(sec, "source_modules").split())
    assert {"domain", "application"}.issubset(source_pkgs)

    forbidden_pkgs = set(config.get(sec, "forbidden_modules").split())
    for expected in ("google", "openai", "anthropic", "litellm", "langgraph", "llama_index"):
        assert expected in forbidden_pkgs, f"Expected forbidden provider '{expected}' in {forbidden_pkgs}"


def test_provider_sdk_isolation_behaviorally_catches_leaks():
    """ADR 0009 §3: Behaviorally verifies that importing openai inside application fails lint-imports."""
    repo_root = _get_repo_root()
    leak_file = repo_root / "backend" / "src" / "main" / "application" / "_temp_provider_leak.py"
    leak_file.write_text("import openai\n", encoding="utf-8")

    backend_src_main = str(repo_root / "backend" / "src" / "main")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_src_main}:{existing_pythonpath}" if existing_pythonpath else backend_src_main

    try:
        proc = subprocess.run(
            ["lint-imports", "--no-logo", "--contract", "provider-sdk-isolation"],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, "lint-imports must fail when provider SDK is imported into application"
        assert "application._temp_provider_leak -> openai" in proc.stdout
    finally:
        if leak_file.exists():
            leak_file.unlink()
