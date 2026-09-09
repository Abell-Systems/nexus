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
import sys
from pathlib import Path

from domain.protocols.agents import (
    AdversarialAgentProtocol,
    GovernorAgentProtocol,
    InventorAgentProtocol,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from check_architecture import check_monorepo_boundaries  # noqa: E402


def _get_repo_root() -> Path:
    return _REPO_ROOT


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
    script_path = _REPO_ROOT / "scripts" / "check_architecture.py"
    code = script_path.read_text(encoding="utf-8")

    assert "check_import_linter_contracts" in code
    assert "lint-imports" in code
    assert ".importlinter" in code


def test_monorepo_boundaries_passes_on_current_repository():
    """Verify ADR 0024 monorepo boundaries pass on the actual repository."""
    errors: list[str] = []
    check_monorepo_boundaries(errors, repo_root=_REPO_ROOT)
    assert errors == [], f"Expected 0 boundary violations, got: {errors}"


def test_monorepo_boundaries_passes_on_valid_fixture(tmp_path: Path):
    """Positive behavioral test: valid local imports inside each workspace pass with 0 errors."""
    # Setup clean fixture
    frontend_src = tmp_path / "frontend" / "src" / "main"
    frontend_src.mkdir(parents=True)
    (frontend_src / "App.tsx").write_text(
        "import React from 'react';\nimport { Header } from './Header';\n",
        encoding="utf-8",
    )

    status_dir = tmp_path / "nexus-status"
    (status_dir / "frontend" / "src" / "ui").mkdir(parents=True)
    (status_dir / "README.md").write_text("# Nexus Status\n", encoding="utf-8")
    (status_dir / "frontend" / "src" / "ui" / "App.tsx").write_text(
        "import React from 'react';\nimport { status } from '../domain/status';\nimport { Badge } from './Badge';\n",
        encoding="utf-8",
    )

    errors: list[str] = []
    check_monorepo_boundaries(errors, repo_root=tmp_path)
    assert errors == [], f"Expected clean fixture to pass, got: {errors}"


def test_monorepo_boundaries_catches_frontend_to_status_relative_leak(tmp_path: Path):
    """Negative behavioral test: frontend relative import of nexus-status is rejected."""
    frontend_src = tmp_path / "frontend" / "src" / "main"
    frontend_src.mkdir(parents=True)
    (frontend_src / "App.tsx").write_text(
        "import { StatusBadge } from '../../nexus-status/frontend/src/ui/StatusBadge';\n",
        encoding="utf-8",
    )

    status_dir = tmp_path / "nexus-status"
    (status_dir / "frontend" / "src" / "ui").mkdir(parents=True)
    (status_dir / "README.md").write_text("# Nexus Status\n", encoding="utf-8")

    errors: list[str] = []
    check_monorepo_boundaries(errors, repo_root=tmp_path)
    assert len(errors) == 1
    assert "frontend cannot import nexus-status" in errors[0]


def test_monorepo_boundaries_catches_frontend_to_status_package_leak(tmp_path: Path):
    """Negative behavioral test: frontend package/alias import of nexus-status is rejected."""
    frontend_src = tmp_path / "frontend" / "src" / "main"
    frontend_src.mkdir(parents=True)
    (frontend_src / "App.tsx").write_text(
        "import { StatusBadge } from 'nexus-status-frontend/ui/StatusBadge';\n",
        encoding="utf-8",
    )

    status_dir = tmp_path / "nexus-status"
    (status_dir / "frontend" / "src" / "ui").mkdir(parents=True)
    (status_dir / "README.md").write_text("# Nexus Status\n", encoding="utf-8")

    errors: list[str] = []
    check_monorepo_boundaries(errors, repo_root=tmp_path)
    assert len(errors) == 1
    assert "frontend cannot import nexus-status" in errors[0]


def test_monorepo_boundaries_catches_status_to_frontend_relative_leak(tmp_path: Path):
    """Negative behavioral test: nexus-status relative import of frontend is rejected."""
    (tmp_path / "frontend" / "src" / "main").mkdir(parents=True)
    status_dir = tmp_path / "nexus-status"
    ui_dir = status_dir / "frontend" / "src" / "ui"
    ui_dir.mkdir(parents=True)
    (status_dir / "README.md").write_text("# Nexus Status\n", encoding="utf-8")
    (ui_dir / "App.tsx").write_text(
        "import { ResultsView } from '../../../../frontend/src/main/components/ResultsView';\n",
        encoding="utf-8",
    )

    errors: list[str] = []
    check_monorepo_boundaries(errors, repo_root=tmp_path)
    assert len(errors) == 1
    assert "nexus-status cannot import frontend" in errors[0]


def test_monorepo_boundaries_catches_status_to_frontend_package_leak(tmp_path: Path):
    """Negative behavioral test: nexus-status package import of frontend is rejected."""
    (tmp_path / "frontend" / "src" / "main").mkdir(parents=True)
    status_dir = tmp_path / "nexus-status"
    ui_dir = status_dir / "frontend" / "src" / "ui"
    ui_dir.mkdir(parents=True)
    (status_dir / "README.md").write_text("# Nexus Status\n", encoding="utf-8")
    (ui_dir / "App.tsx").write_text(
        "import { ResultsView } from 'patent-innovation-agent-frontend/components/ResultsView';\n",
        encoding="utf-8",
    )

    errors: list[str] = []
    check_monorepo_boundaries(errors, repo_root=tmp_path)
    assert len(errors) == 1
    assert "nexus-status cannot import core backend/frontend" in errors[0]


def test_monorepo_boundaries_catches_status_to_backend_relative_leak(tmp_path: Path):
    """Negative behavioral test: nexus-status relative import of backend is rejected."""
    (tmp_path / "backend" / "src" / "main" / "domain").mkdir(parents=True)
    status_dir = tmp_path / "nexus-status"
    ui_dir = status_dir / "frontend" / "src" / "ui"
    ui_dir.mkdir(parents=True)
    (status_dir / "README.md").write_text("# Nexus Status\n", encoding="utf-8")
    (ui_dir / "App.tsx").write_text(
        "import { Patent } from '../../../../backend/src/main/domain/patent';\n",
        encoding="utf-8",
    )

    errors: list[str] = []
    check_monorepo_boundaries(errors, repo_root=tmp_path)
    assert len(errors) == 1
    assert "nexus-status cannot import backend" in errors[0]


def test_monorepo_boundaries_catches_stray_file_in_status_root(tmp_path: Path):
    """Structural invariant test: unexpected entries in nexus-status root are rejected."""
    status_dir = tmp_path / "nexus-status"
    (status_dir / "frontend").mkdir(parents=True)
    (status_dir / "README.md").write_text("# Nexus Status\n", encoding="utf-8")
    (status_dir / "stray_script.py").write_text("print('rogue')\n", encoding="utf-8")

    errors: list[str] = []
    check_monorepo_boundaries(errors, repo_root=tmp_path)
    assert len(errors) == 1
    assert "unexpected entry in nexus-status workspace root" in errors[0]


