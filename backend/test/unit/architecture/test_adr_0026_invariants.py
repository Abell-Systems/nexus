"""Architectural invariant test for ADR 0026 (Experiment/Domain Boundary).

Invariant enforced: backend/src and backend/test never reference the
experiments/ tree by path or import. This is a reference-boundary check, not
a prose linter — a comment or string containing the word "experiments" in
running text (not as a path segment) does not trip it. No magic-number
check is included here by design (ADR 0026 §Enforcement) — expected counts
belong in experiments/<paper>/checks/, manifest-driven.
"""

import re
from pathlib import Path

# Matches "experiments" used as a path segment or import target:
#   from experiments...
#   import experiments...
#   "experiments/..."  or  'experiments/...'
#   Path("experiments/...")
# but NOT plain running-text mentions like "the experiments boundary".
_FORBIDDEN_PATTERN = re.compile(
    r"""
    (?:from|import)\s+experiments\b   # from experiments... / import experiments...
    |
    ['"]experiments/                  # "experiments/..." or 'experiments/...'
    """,
    re.VERBOSE,
)


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _scan(directory: Path) -> list[str]:
    violations = []
    for py_file in directory.rglob("*.py"):
        code = py_file.read_text(encoding="utf-8")
        if _FORBIDDEN_PATTERN.search(code):
            violations.append(str(py_file.relative_to(_get_repo_root())))
    return violations


def test_backend_src_never_references_experiments_tree():
    repo_root = _get_repo_root()
    violations = _scan(repo_root / "backend" / "src" / "main")
    assert not violations, (
        f"Found forbidden experiments/ references in backend/src: {violations}. "
        "Per ADR 0026, Nexus implements generic mechanisms; experiment-specific "
        "config/data/results must stay in experiments/, never referenced from backend/src."
    )


def test_backend_test_never_references_experiments_tree():
    repo_root = _get_repo_root()
    violations = _scan(repo_root / "backend" / "test")
    assert not violations, (
        f"Found forbidden experiments/ references in backend/test: {violations}. "
        "Per ADR 0026, backend/test/unit proves generic invariants against synthetic "
        "fixtures — experiment-specific evidence validation belongs in "
        "experiments/<paper>/checks/, not backend/test."
    )


def test_forbidden_pattern_does_not_trip_on_running_prose():
    """Regression: a comment mentioning 'experiments' in prose (not as a path
    or import) must not be flagged."""
    prose = "# The experiments boundary is enforced by ADR 0026."
    assert not _FORBIDDEN_PATTERN.search(prose)


def test_forbidden_pattern_does_trip_on_a_path_reference():
    assert _FORBIDDEN_PATTERN.search('Path("experiments/wpi-demand-patent-matching/data")')
    assert _FORBIDDEN_PATTERN.search("from experiments.shared import fixtures")
