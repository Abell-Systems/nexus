"""Architectural invariant test for ADR 0026 (Experiment/Domain Boundary).

Invariant enforced: backend/src and backend/test never reference the
experiments/ tree by path or import. This is a reference-boundary check, not
a prose linter — a comment or string containing the word "experiments" in
running text (not as a path segment) does not trip it.

The experiments/shared/ exemption is asymmetric (Finding 4, ADR 0026
Enforcement): backend/test may legitimately reference experiments/shared/
(reusable fixture data, not paper-specific evidence) in integration tests,
but backend/src (production code) gets ZERO exemptions — per ADR 0006's
stricter existing precedent, domain/application/infrastructure code must
never hardcode any dataset path, shared or not. The guard also excludes its
own file from self-scanning. No magic-number check is included here by
design (ADR 0026 §Enforcement) — expected counts belong in
experiments/<paper>/checks/, manifest-driven.
"""

import re
from pathlib import Path

# Matches "experiments" used as a path segment or import target:
#   from experiments...
#   import experiments...
#   "experiments/..."  or  'experiments/...'
#   Path("experiments/...")
#   repo_root / "experiments" / "wpi-..." (split-path form)
# but NOT plain running-text mentions like "the experiments boundary", and
# (this pattern only) NOT experiments/shared/ (reusable fixture data, exempt
# from the path check for backend/test — see _FORBIDDEN_PATTERN_STRICT for
# backend/src, which has no such exemption).
_FORBIDDEN_PATTERN = re.compile(
    r"""
    (?:from|import)\s+experiments\b                    # from experiments... / import experiments...
    |
    ['"]experiments/(?!shared/)                         # "experiments/..." or 'experiments/...', except experiments/shared/
    |
    (?<!["']\s/\s)['"]experiments['"]\s*/\s*['"](?!shared['"])
        # repo_root / "experiments" / "wpi-..." split-path form, except .../"shared".
        # The leading lookbehind excludes "experiments" nested under a DIFFERENT
        # quoted segment (e.g. "data" / "experiments" / "power_analysis_....json",
        # which is an unrelated data/experiments/ tree, not this ADR's experiments/
        # root) -- only a bare identifier/call (e.g. repo_root, _get_repo_root())
        # immediately before the "/ " divider counts as a real top-level reference.
    """,
    re.VERBOSE,
)

# Same as _FORBIDDEN_PATTERN but with no experiments/shared/ exemption at
# all -- used for backend/src, which per ADR 0006 must never hardcode any
# experiments/ dataset path, shared or paper-specific.
_FORBIDDEN_PATTERN_STRICT = re.compile(
    r"""
    (?:from|import)\s+experiments\b            # from experiments... / import experiments...
    |
    ['"]experiments/                           # "experiments/..." or 'experiments/...' (no exemption)
    |
    (?<!["']\s/\s)['"]experiments['"]\s*/\s*['"]   # "experiments" / "..." split-path form (no exemption)
    """,
    re.VERBOSE,
)


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _scan(directory: Path, pattern: re.Pattern[str]) -> list[str]:
    self_path = Path(__file__).resolve()
    violations = []
    for py_file in directory.rglob("*.py"):
        if py_file.resolve() == self_path:
            continue
        code = py_file.read_text(encoding="utf-8")
        if pattern.search(code):
            violations.append(str(py_file.relative_to(_get_repo_root())))
    return violations


def test_backend_src_never_references_experiments_tree():
    repo_root = _get_repo_root()
    violations = _scan(repo_root / "backend" / "src" / "main", _FORBIDDEN_PATTERN_STRICT)
    assert not violations, (
        f"Found forbidden experiments/ references in backend/src: {violations}. "
        "Per ADR 0026, Nexus implements generic mechanisms; experiment-specific "
        "config/data/results must stay in experiments/, never referenced from backend/src. "
        "backend/src gets no experiments/shared/ exemption (ADR 0006)."
    )


def test_backend_test_never_references_experiments_tree():
    repo_root = _get_repo_root()
    violations = _scan(repo_root / "backend" / "test", _FORBIDDEN_PATTERN)
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


def test_forbidden_pattern_trips_on_split_path_form():
    """Regression (Finding 2): repo_root / "experiments" / "wpi-..." is this
    codebase's dominant path-construction style and must be caught."""
    assert _FORBIDDEN_PATTERN.search(
        'repo_root / "experiments" / "wpi-demand-patent-matching" / "data"'
    )


def test_forbidden_pattern_split_path_form_exempts_shared():
    """Regression (Finding 2): the split-path form of experiments/shared/
    must remain exempt, consistent with the quoted form."""
    assert not _FORBIDDEN_PATTERN.search(
        'repo_root / "experiments" / "shared" / "dataset_pilot_benchmark.json"'
    )


def test_strict_pattern_has_no_shared_exemption():
    """Regression (Finding 4): backend/src's strict pattern must reject
    experiments/shared/ too -- production code gets zero exemptions."""
    assert _FORBIDDEN_PATTERN_STRICT.search('Path("experiments/shared/dataset_pilot_benchmark.json")')
    assert _FORBIDDEN_PATTERN_STRICT.search(
        'repo_root / "experiments" / "shared" / "dataset_pilot_benchmark.json"'
    )


def test_forbidden_pattern_does_not_trip_on_unrelated_nested_experiments_segment():
    """Regression: repo_root / "data" / "experiments" / "power_analysis_....json"
    (backend/test/unit/application/evaluation/test_power_analysis_coherence.py)
    is an unrelated data/experiments/ tree, not this ADR's top-level experiments/
    tree -- the split-path form must not flag "experiments" nested under another
    quoted path segment."""
    assert not _FORBIDDEN_PATTERN.search(
        'repo_root / "data" / "experiments" / "power_analysis_wilcoxon.json"'
    )
    assert not _FORBIDDEN_PATTERN_STRICT.search(
        'repo_root / "data" / "experiments" / "power_analysis_wilcoxon.json"'
    )
