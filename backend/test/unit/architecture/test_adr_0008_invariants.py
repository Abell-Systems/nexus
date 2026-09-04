"""Automated architectural enforcement tests for ADR 0008 (Machine-Verifiable Contracts & Import Linter).

Invariants enforced:
1. .importlinter configuration exists at repository root and defines all mandatory contracts.
2. lint-imports executes cleanly with zero broken contracts.
3. Clean Architecture layer contracts:
   - domain is isolated from application and infrastructure
   - application is isolated from infrastructure
4. Subsystem decoupling:
   - application.evaluation.metrics is functionally pure (no matching or infrastructure imports)
   - application.evaluation.runner is decoupled from matching domain (no matching models or protocols)
   - domain.protocols.evaluation is decoupled from matching domain
5. 4-level enforcement stack integration in CI (check_architecture.py invokes lint-imports).
"""

import configparser
import os
import subprocess
from pathlib import Path


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_import_linter_config_exists_and_contains_mandatory_contracts():
    """ADR 0008 §1: .importlinter must exist and declare the required layer contracts."""
    config_path = _get_repo_root() / ".importlinter"
    assert config_path.exists(), "Missing .importlinter configuration file at repository root."

    config = configparser.ConfigParser()
    config.read(config_path)

    # Verify root packages
    assert "importlinter" in config.sections(), "Missing [importlinter] section in .importlinter"
    root_pkgs = config.get("importlinter", "root_packages", fallback="").split()
    for expected_pkg in ("domain", "application", "infrastructure"):
        assert expected_pkg in root_pkgs, (
            f"Root package '{expected_pkg}' missing from [importlinter] root_packages: {root_pkgs}"
        )

    # Mandatory contracts
    expected_contracts = {
        "importlinter:contract:domain-isolation",
        "importlinter:contract:application-isolation",
        "importlinter:contract:evaluation-metrics-purity",
        "importlinter:contract:evaluation-runner-isolation",
        "importlinter:contract:evaluation-domain-protocol-isolation",
    }
    actual_sections = set(config.sections())
    for contract in expected_contracts:
        assert contract in actual_sections, f"Mandatory contract section '{contract}' missing from .importlinter"


def test_lint_imports_executes_cleanly():
    """ADR 0008 §1: lint-imports must pass with 0 broken contracts across all modules."""
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


def test_check_architecture_script_integrates_import_linter():
    """ADR 0008 §2: scripts/check_architecture.py must execute import-linter contracts in CI."""
    script_path = _get_repo_root() / "scripts" / "check_architecture.py"
    code = script_path.read_text(encoding="utf-8")

    assert "check_import_linter_contracts" in code, (
        "scripts/check_architecture.py must define check_import_linter_contracts"
    )
    assert "lint-imports" in code, (
        "scripts/check_architecture.py must invoke lint-imports"
    )
    assert ".importlinter" in code, (
        "scripts/check_architecture.py must reference .importlinter"
    )
