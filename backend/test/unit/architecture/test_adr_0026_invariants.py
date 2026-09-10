"""Architectural invariant test for ADR 0026 (Experiment/Domain Boundary).

Invariant enforced: backend/src and backend/test never reference the
experiments/ tree by path or import. This is a reference-boundary check, not
a prose linter — a comment or string containing the word "experiments" in
running text (not as a path segment) does not trip it.
experiments/shared/ (reusable fixture data, not paper-specific evidence) is
exempt from the path-string check; the guard also excludes its own file from
self-scanning. No magic-number check is included here by design (ADR 0026
§Enforcement) — expected counts belong in experiments/<paper>/checks/,
manifest-driven.
"""

import re
from pathlib import Path

# Matches "experiments" used as a path segment or import target:
#   from experiments...
#   import experiments...
#   "experiments/..."  or  'experiments/...'
#   Path("experiments/...")
# but NOT plain running-text mentions like "the experiments boundary", and
# NOT experiments/shared/ (reusable fixture data, exempt from the path check).
_FORBIDDEN_PATTERN = re.compile(
    r"""
    (?:from|import)\s+experiments\b   # from experiments... / import experiments...
    |
    ['"]experiments/(?!shared/)       # "experiments/..." or 'experiments/...', except experiments/shared/
    """,
    re.VERBOSE,
)


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _scan(directory: Path) -> list[str]:
    self_path = Path(__file__).resolve()
    violations = []
    for py_file in directory.rglob("*.py"):
        if py_file.resolve() == self_path:
            continue
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


def test_forbidden_pattern_does_not_trip_on_shared_fixture_paths():
    """Regression: experiments/shared/ holds reusable fixture data, not
    paper-specific evidence -- referencing it (e.g. to load a real shared
    dataset for an integration test) must not trip the guard."""
    assert not _FORBIDDEN_PATTERN.search('Path("experiments/shared/dataset_pilot_benchmark.json")')


def test_forbidden_pattern_does_trip_on_a_paper_specific_path_reference():
    assert _FORBIDDEN_PATTERN.search('Path("experiments/wpi-demand-patent-matching/data")')
    assert _FORBIDDEN_PATTERN.search("from experiments.shared import fixtures")
