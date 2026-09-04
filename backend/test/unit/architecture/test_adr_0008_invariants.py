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


def test_import_linter_config_semantic_rules():
    """ADR 0008 §1: Verify exact semantic configuration of each mandatory contract.

    Tests not just section existence, but exact source_modules, forbidden_modules,
    and ignore_imports boundaries so contracts cannot be silently diluted.
    """
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
    # Ignored imports must strictly be limited to matching_adapter
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


def test_evaluation_adapter_boundary_behaviorally_catches_violations(tmp_path):
    """ADR 0008: Behaviorally verifies that importing matching from a non-adapter evaluation module breaks lint-imports."""
    repo_root = _get_repo_root()
    violation_file = repo_root / "backend" / "src" / "main" / "application" / "evaluation" / "_temp_leak_test.py"
    violation_file.write_text("from domain.models.matching import Candidate\n", encoding="utf-8")

    backend_src_main = str(repo_root / "backend" / "src" / "main")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{backend_src_main}:{existing_pythonpath}" if existing_pythonpath else backend_src_main

    try:
        proc = subprocess.run(
            ["lint-imports", "--no-logo", "--contract", "evaluation-adapter-boundary"],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0, (
            "Expected lint-imports to FAIL when a non-adapter evaluation module imports matching domain, but it passed."
        )
        assert "application.evaluation._temp_leak_test -> domain.models.matching" in proc.stdout
    finally:
        if violation_file.exists():
            violation_file.unlink()


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
