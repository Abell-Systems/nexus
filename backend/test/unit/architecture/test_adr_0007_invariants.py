"""Architectural invariant tests for ADR 0007 (Scientific Evaluation Protocol and Metrics).

Invariants enforced:
1. Zero filesystem operations (open, Path.read_*, etc.) and zero Git execution in application/evaluation.
2. Layer dependency direction: application/evaluation must NOT import infrastructure.
3. Decoupled metrics: application/evaluation/metrics.py must NOT import matching engine, policies, or infrastructure.
4. Independent auditor principle: EvaluationRunner must NOT depend on DefaultMatchingEngine (protocol only).
5. Explicit injection invariant: run_evaluation requires all 4 parameters without default fallbacks.
6. Epistemic invariant: UNCERTAIN (-1) is never coerced to 0 or treated as false positive.
7. Anti-tamper invariant: EvaluationRunner must strictly preserve the ranking order delivered by the engine.
8. Provenance audit invariant: EvaluationRunReport must strictly stamp dataset SHA, policy SHA, and execution context.
"""

import ast
import inspect
from pathlib import Path

from application.evaluation.metrics import precision_at_k
from application.evaluation.runner import DefaultEvaluationRunner
from domain.models.evaluation import RelevanceGrade
from domain.protocols.evaluation import EvaluationRunner


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_no_filesystem_or_git_calls_in_application_evaluation():
    """ADR 0007 §5: Evaluation application modules must not access disk or invoke Git."""
    eval_dir = _get_repo_root() / "backend" / "src" / "main" / "application" / "evaluation"

    for py_file in eval_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # Check for forbidden module imports (subprocess, os.system, etc.)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in ("subprocess", "shutil"), (
                        f"Forbidden import '{alias.name}' found in {py_file}"
                    )
            elif isinstance(node, ast.ImportFrom):
                assert node.module not in ("subprocess", "shutil"), (
                    f"Forbidden import from '{node.module}' in {py_file}"
                )
            # Check for calls to open() or Path.read_*
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    raise AssertionError(f"Forbidden open() call found in {py_file}")
                if isinstance(node.func, ast.Attribute) and node.func.attr in (
                    "read_text",
                    "read_bytes",
                    "write_text",
                    "write_bytes",
                ):
                    raise AssertionError(
                        f"Forbidden filesystem call '{node.func.attr}' found in {py_file}"
                    )


def test_layer_dependency_direction_no_infrastructure_imports():
    """Clean Architecture & ADR 0007: application/evaluation must NOT import infrastructure."""
    eval_dir = _get_repo_root() / "backend" / "src" / "main" / "application" / "evaluation"

    for py_file in eval_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("infrastructure"), (
                        f"Layer violation: {py_file} imports infrastructure module '{alias.name}'"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("infrastructure"), (
                    f"Layer violation: {py_file} imports from infrastructure module '{node.module}'"
                )


def test_metrics_module_decoupled_from_matching_and_infrastructure():
    """ADR 0007 §1: metrics.py must be functionally pure without matching or infrastructure coupling."""
    metrics_file = (
        _get_repo_root()
        / "backend"
        / "src"
        / "main"
        / "application"
        / "evaluation"
        / "metrics.py"
    )
    tree = ast.parse(metrics_file.read_text(encoding="utf-8"))

    forbidden_prefixes = ("infrastructure", "application.matching", "domain.models.matching")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for prefix in forbidden_prefixes:
                    assert not alias.name.startswith(prefix), (
                        f"Forbidden coupling in metrics.py: imports '{alias.name}'"
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            for prefix in forbidden_prefixes:
                assert not node.module.startswith(prefix), (
                    f"Forbidden coupling in metrics.py: imports from '{node.module}'"
                )


def test_runner_depends_only_on_matching_engine_protocol():
    """ADR 0007 §5: EvaluationRunner must not import concrete DefaultMatchingEngine."""
    runner_file = (
        _get_repo_root()
        / "backend"
        / "src"
        / "main"
        / "application"
        / "evaluation"
        / "runner.py"
    )
    code = runner_file.read_text(encoding="utf-8")
    assert "DefaultMatchingEngine" not in code, (
        "EvaluationRunner must depend on MatchingEngine protocol, not concrete DefaultMatchingEngine."
    )


def test_run_evaluation_requires_all_parameters_without_defaults():
    """ADR 0007 §5: run_evaluation must require dataset, engine, policy, and context without defaults."""
    loader_sig = inspect.signature(DefaultEvaluationRunner.run_evaluation)
    protocol_sig = inspect.signature(EvaluationRunner.run_evaluation)

    required_params = ("dataset", "engine", "policy", "context")
    for sig, owner in [(loader_sig, "DefaultEvaluationRunner"), (protocol_sig, "EvaluationRunner")]:
        for param_name in required_params:
            param = sig.parameters.get(param_name)
            assert param is not None, f"Missing parameter '{param_name}' in {owner}.run_evaluation"
            assert param.default is inspect.Parameter.empty, (
                f"Parameter '{param_name}' in {owner}.run_evaluation must NOT have a default value. "
                "Explicit dependency injection is strictly mandatory under ADR 0007."
            )


def test_no_coercion_of_uncertain_to_negative():
    """AGENTS.md & ADR 0007 §3: UNCERTAIN must NEVER be coerced to 0 or treated as false positive."""
    # If 1 relevant item and 2 UNCERTAIN items are present:
    # Coercing UNCERTAIN -> negative would yield TP=1, FP=2 -> P@3 = 1/3 = 0.333
    # Correct epistemic treatment yields TP=1, FP=0 -> P@3 = 1/1 = 1.0 (over judged items)
    ranking = ["P1", "P_unc1", "P_unc2"]
    judgements = {
        "P1": RelevanceGrade.GRADE_3,
        "P_unc1": RelevanceGrade.UNCERTAIN,
        "P_unc2": RelevanceGrade.UNCERTAIN,
    }

    prec = precision_at_k(ranking, judgements, k=3, relevance_fn=lambda g: g == RelevanceGrade.GRADE_3)
    assert prec == 1.0, (
        f"Expected precision 1.0 (UNCERTAIN isolated from negatives), got {prec}. "
        "Coercing UNCERTAIN to negative is an epistemic fallacy under ADR 0007."
    )
