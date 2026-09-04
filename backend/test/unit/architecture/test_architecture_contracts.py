"""Automated architectural enforcement and contract verification for Nexus 2.0.

Invariants enforced:
1. .importlinter defines and enforces all mandatory contracts:
   - domain isolation (pure domain)
   - application isolation (application cannot import infrastructure)
   - evaluation adapter boundary (only matching_adapter may bridge evaluation to matching)
   - evaluation domain protocol isolation
   - provider SDK isolation (zero external AI/LLM SDK imports in domain and application)
2. Clean Architecture layer dependencies execute cleanly with 0 broken contracts.
3. Behavioral meta-test: verifies that forbidden provider imports are actively caught by CI gate.
"""

import configparser
import os
import subprocess
from pathlib import Path

from domain.protocols.agents import (
    AdversarialAgentProtocol,
    GovernorAgentProtocol,
    InventorAgentProtocol,
)


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_agent_protocols_are_pure():
    """Verify domain agent capability protocols exist and require no vendor SDKs."""
    assert isinstance(InventorAgentProtocol, type)
    assert isinstance(AdversarialAgentProtocol, type)
    assert isinstance(GovernorAgentProtocol, type)


def test_import_linter_config_semantic_rules():
    """Verify exact semantic configuration of each mandatory contract in .importlinter."""
    config_path = _get_repo_root() / ".importlinter"
    assert config_path.exists(), "Missing .importlinter configuration file at repository root."

    config = configparser.ConfigParser()
    config.read(config_path)

    # 1. Root packages
    root_pkgs = set(config.get("importlinter", "root_packages").split())
    assert {"domain", "application", "infrastructure"}.issubset(root_pkgs)

    # 2. Domain isolation contract
    sec_dom = "importlinter:contract:domain-isolation"
    assert config.get(sec_dom, "type") == "forbidden"
    assert "domain" in config.get(sec_dom, "source_modules").split()
    forbidden_dom = set(config.get(sec_dom, "forbidden_modules").split())
    assert "application" in forbidden_dom
    assert "infrastructure" in forbidden_dom

    # 3. Application isolation contract
    sec_app = "importlinter:contract:application-isolation"
    assert config.get(sec_app, "type") == "forbidden"
    assert "application" in config.get(sec_app, "source_modules").split()
    assert "infrastructure" in set(config.get(sec_app, "forbidden_modules").split())

    # 4. Evaluation adapter boundary contract
    sec_adapter = "importlinter:contract:evaluation-adapter-boundary"
    assert config.get(sec_adapter, "type") == "forbidden"
    assert "application.evaluation" in config.get(sec_adapter, "source_modules").split()
    forbidden_adapter = set(config.get(sec_adapter, "forbidden_modules").split())
    assert "domain.models.matching" in forbidden_adapter
    assert "domain.protocols.matching" in forbidden_adapter
    assert "application.matching" in forbidden_adapter
    ignored_lines = [
        line.strip()
        for line in config.get(sec_adapter, "ignore_imports", fallback="").strip().splitlines()
        if line.strip()
    ]
    for line in ignored_lines:
        assert line.startswith("application.evaluation.matching_adapter ->"), (
            f"Only matching_adapter may be exempt from evaluation-adapter-boundary, got: {line}"
        )

    # 5. Evaluation domain protocol isolation
    sec_proto = "importlinter:contract:evaluation-domain-protocol-isolation"
    assert config.get(sec_proto, "type") == "forbidden"
    assert "domain.protocols.evaluation" in config.get(sec_proto, "source_modules").split()
    forbidden_proto = set(config.get(sec_proto, "forbidden_modules").split())
    assert "domain.models.matching" in forbidden_proto
    assert "domain.protocols.matching" in forbidden_proto

    # 6. Provider SDK isolation contract
    sec_provider = "importlinter:contract:provider-sdk-isolation"
    assert config.get(sec_provider, "type") == "forbidden"
    source_pkgs = set(config.get(sec_provider, "source_modules").split())
    assert {"domain", "application"}.issubset(source_pkgs)
    forbidden_providers = set(config.get(sec_provider, "forbidden_modules").split())
    for expected in ("google", "openai", "anthropic", "litellm", "langgraph", "llama_index"):
        assert expected in forbidden_providers, f"Expected forbidden provider '{expected}' in {forbidden_providers}"

    # 7. Embedding-generation-stack isolation contract (ADR 0014): the M1 offline
    # generation stack (torch/transformers/sentence_transformers) belongs only to a
    # standalone generation script, never to the Nexus runtime that consumes its frozen
    # artifact.
    sec_embed = "importlinter:contract:embedding-generation-stack-isolation"
    assert config.get(sec_embed, "type") == "forbidden"
    source_embed = set(config.get(sec_embed, "source_modules").split())
    assert {"domain", "application", "infrastructure"}.issubset(source_embed)
    forbidden_embed = set(config.get(sec_embed, "forbidden_modules").split())
    for expected in ("torch", "transformers", "sentence_transformers"):
        assert expected in forbidden_embed, f"Expected forbidden module '{expected}' in {forbidden_embed}"


def test_lint_imports_executes_cleanly():
    """Verify that lint-imports executes cleanly with 0 broken contracts."""
    repo_root = _get_repo_root()
    backend_src_main = str(repo_root / "backend" / "src" / "main")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_src_main}:{existing_pythonpath}" if existing_pythonpath else backend_src_main

    proc = subprocess.run(
        ["lint-imports", "--no-logo"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"lint-imports failed with exit code {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
    )
    assert "0 broken" in proc.stdout, (
        f"Expected '0 broken' contracts in lint-imports output:\n{proc.stdout}"
    )


def test_provider_sdk_isolation_behaviorally_catches_leaks():
    """Behavioral meta-test: verifies that importing openai inside application actively fails lint-imports."""
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


def test_embedding_generation_stack_isolation_behaviorally_catches_leaks():
    """Behavioral meta-test: importing torch inside infrastructure must fail lint-imports.

    infrastructure is included (unlike provider-sdk-isolation, which only covers
    domain/application) because the M1 artifact loader — a future infrastructure
    component consuming the frozen embedding artifact (ADR 0014) — must never need
    the generation stack; only the standalone scripts/generate_m1_embeddings.py does.
    """
    repo_root = _get_repo_root()
    leak_file = repo_root / "backend" / "src" / "main" / "infrastructure" / "_temp_embedding_leak.py"
    leak_file.write_text("import torch\n", encoding="utf-8")

    backend_src_main = str(repo_root / "backend" / "src" / "main")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_src_main}:{existing_pythonpath}" if existing_pythonpath else backend_src_main

    try:
        proc = subprocess.run(
            ["lint-imports", "--no-logo", "--contract", "embedding-generation-stack-isolation"],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, "lint-imports must fail when torch is imported into infrastructure"
        assert "infrastructure._temp_embedding_leak -> torch" in proc.stdout
    finally:
        if leak_file.exists():
            leak_file.unlink()


def test_check_architecture_script_integrates_import_linter():
    """Verify scripts/check_architecture.py integrates import-linter contracts in CI."""
    script_path = _get_repo_root() / "scripts" / "check_architecture.py"
    code = script_path.read_text(encoding="utf-8")

    assert "check_import_linter_contracts" in code
    assert "lint-imports" in code
    assert ".importlinter" in code
