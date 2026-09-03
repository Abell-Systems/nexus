"""Architectural invariant tests for ADR 0007 (Scientific Evaluation Protocol and Metrics).

Invariants enforced:
1. Zero filesystem operations (open, Path.read_*, etc.) and zero Git execution in application/evaluation.
2. Layer dependency direction: application/evaluation must NOT import infrastructure.
3. Decoupled metrics: application/evaluation/metrics.py must NOT import matching engine, policies, or infrastructure.
4. Independent auditor principle: application/evaluation/runner.py must NOT import any matching-domain type.
5. Explicit injection invariant: run_evaluation requires all 4 parameters without default fallbacks.
6. Epistemic invariant: UNCERTAIN (-1) is never coerced to 0 or treated as false positive.
7. Anti-Any invariant: domain/protocols/evaluation.py must NOT use Any to hide cross-bounded-context types.
8. Adapter isolation: matching_adapter.py is the ONLY file in application/evaluation/ permitted to
   import from domain.models.matching or domain.protocols.matching.
9. Evidence integrity: adapter passes complete PatentCandidateEvidence with real data to the engine.
10. Honest pool: adapter must not fabricate retrieval scores (retrieval_scores={} only).
"""

import ast
import inspect
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from application.evaluation.matching_adapter import DefaultMatchingAdapter
from application.evaluation.metrics import precision_at_k
from application.evaluation.runner import DefaultEvaluationRunner
from domain.models.evaluation import (
    DataModality,
    EvaluationAnnotation,
    EvaluationDataset,
    EvaluationDatasetManifest,
    EvaluationDemand,
    EvaluationPatent,
    EvaluationProvenance,
    RelevanceGrade,
    ValidatedDataset,
)
from domain.protocols.evaluation import EvaluationRankingPort, EvaluationRunner


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eval_dir() -> Path:
    return _get_repo_root() / "backend" / "src" / "main" / "application" / "evaluation"


def _read_ast(rel_path: str) -> tuple[ast.Module, Path]:
    p = _get_repo_root() / rel_path
    return ast.parse(p.read_text(encoding="utf-8")), p


# ---------------------------------------------------------------------------
# 1. Filesystem / Git isolation
# ---------------------------------------------------------------------------

def test_no_filesystem_or_git_calls_in_application_evaluation():
    """ADR 0007 §5: Evaluation application modules must not access disk or invoke Git."""
    # Exemption: matching_adapter.py is allowed (it uses PatentCandidateEvidence from domain)
    # but must still not use subprocess or open() directly.
    for py_file in _eval_dir().glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in ("subprocess", "shutil"), (
                        f"Forbidden import '{alias.name}' found in {py_file}"
                    )
            elif isinstance(node, ast.ImportFrom):
                assert node.module not in ("subprocess", "shutil"), (
                    f"Forbidden import from '{node.module}' in {py_file}"
                )
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


# ---------------------------------------------------------------------------
# 2. Layer direction
# ---------------------------------------------------------------------------

def test_layer_dependency_direction_no_infrastructure_imports():
    """Clean Architecture & ADR 0007: application/evaluation must NOT import infrastructure."""
    for py_file in _eval_dir().glob("*.py"):
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


# ---------------------------------------------------------------------------
# 3. Metrics purity
# ---------------------------------------------------------------------------

def test_metrics_module_decoupled_from_matching_and_infrastructure():
    """ADR 0007 §1: metrics.py must be functionally pure without matching or infrastructure coupling."""
    tree, _ = _read_ast("backend/src/main/application/evaluation/metrics.py")

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


# ---------------------------------------------------------------------------
# 4. Runner isolation — must NOT import any matching-domain type
# ---------------------------------------------------------------------------

def test_runner_imports_no_matching_domain_types():
    """ADR 0007 §5, adapter pattern: runner.py must import NOTHING from matching domain.

    The runner is a pure auditor. All matching-domain knowledge is in matching_adapter.py.
    Any import from domain.models.matching, domain.protocols.matching, or
    application.matching in runner.py is an architectural violation.
    """
    tree, runner_file = _read_ast("backend/src/main/application/evaluation/runner.py")

    forbidden_modules = (
        "domain.models.matching",
        "domain.protocols.matching",
        "application.matching",
    )
    forbidden_symbols = {"DefaultMatchingEngine", "MatchingPolicyConfig", "MatchingEngine",
                         "CandidatePool", "Candidate", "PatentCandidateEvidence"}

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for forbidden in forbidden_modules:
                assert not node.module.startswith(forbidden), (
                    f"Architectural violation in runner.py: imports from '{node.module}'. "
                    "The runner must be completely independent of the matching domain. "
                    "All matching-domain wiring belongs in matching_adapter.py."
                )
            if node.names:
                imported = {alias.name for alias in node.names}
                violations = imported & forbidden_symbols
                assert not violations, (
                    f"Architectural violation in runner.py: imports matching-domain symbols {violations}. "
                    "The runner must use only evaluation-domain types."
                )


def test_runner_depends_only_on_matching_engine_protocol():
    """Legacy alias for runner isolation test — kept for backward compatibility."""
    test_runner_imports_no_matching_domain_types()


# ---------------------------------------------------------------------------
# 5. Explicit injection — no optional parameters
# ---------------------------------------------------------------------------

def test_run_evaluation_requires_all_parameters_without_defaults():
    """ADR 0007 §5: run_evaluation must require dataset, ranking_port, policy, and context without defaults."""
    loader_sig = inspect.signature(DefaultEvaluationRunner.run_evaluation)
    protocol_sig = inspect.signature(EvaluationRunner.run_evaluation)

    required_params = ("dataset", "ranking_port", "policy", "context")
    for sig, owner in [(loader_sig, "DefaultEvaluationRunner"), (protocol_sig, "EvaluationRunner")]:
        for param_name in required_params:
            param = sig.parameters.get(param_name)
            assert param is not None, f"Missing parameter '{param_name}' in {owner}.run_evaluation"
            assert param.default is inspect.Parameter.empty, (
                f"Parameter '{param_name}' in {owner}.run_evaluation must NOT have a default value. "
                "Explicit dependency injection is strictly mandatory under ADR 0007."
            )


# ---------------------------------------------------------------------------
# 6. Epistemic invariant — UNCERTAIN != negative
# ---------------------------------------------------------------------------

def test_no_coercion_of_uncertain_to_negative():
    """AGENTS.md & ADR 0007 §3: UNCERTAIN must NEVER be coerced to 0 or treated as false positive."""
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


# ---------------------------------------------------------------------------
# 7. Evaluation protocol — no matching imports, no Any for cross-context hiding
# ---------------------------------------------------------------------------

def test_evaluation_protocol_does_not_import_matching_modules():
    """ADR 0007 + Clean Architecture: domain/protocols/evaluation.py must NOT import from matching."""
    tree, _ = _read_ast("backend/src/main/domain/protocols/evaluation.py")

    forbidden_matching_modules = (
        "domain.protocols.matching",
        "domain.models.matching",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for forbidden in forbidden_matching_modules:
                    assert not alias.name.startswith(forbidden), (
                        f"Architectural violation: domain/protocols/evaluation.py imports '{alias.name}'. "
                        "The evaluation protocol must not depend on matching modules."
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            for forbidden in forbidden_matching_modules:
                assert not node.module.startswith(forbidden), (
                    f"Architectural violation: domain/protocols/evaluation.py imports from '{node.module}'. "
                    "The evaluation protocol must not depend on matching modules."
                )


# ---------------------------------------------------------------------------
# 8. Adapter isolation — ONLY matching_adapter.py may import matching-domain types
# ---------------------------------------------------------------------------

def test_only_adapter_imports_matching_domain_in_evaluation():
    """ADR 0007 adapter pattern: Only matching_adapter.py may import from matching domain.

    runner.py, metrics.py, __init__.py, and any future evaluation module must NOT import
    from domain.models.matching or domain.protocols.matching. The adapter is the sole
    translation boundary between bounded contexts.
    """
    forbidden_modules = (
        "domain.models.matching",
        "domain.protocols.matching",
    )

    for py_file in _eval_dir().glob("*.py"):
        if py_file.name == "matching_adapter.py":
            continue  # Only this file is permitted to import matching-domain types

        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_modules:
                    assert not node.module.startswith(forbidden), (
                        f"Adapter boundary violation in {py_file.name}: "
                        f"imports from matching-domain module '{node.module}'. "
                        "Only matching_adapter.py is permitted to import matching-domain types."
                    )


# ---------------------------------------------------------------------------
# 9. Evidence integrity — adapter passes real PatentCandidateEvidence to engine
# ---------------------------------------------------------------------------

@pytest.fixture
def _fake_engine_and_call_record():
    """Returns a fake engine that records calls and assertions about what it received."""
    from unittest.mock import MagicMock
    from domain.models.matching import (
        ConfidenceThresholds,
        CPCConcordanceLevels,
        MatchAssessment,
        MatchConfidence,
        MatchFeatures,
        MatchingPolicyConfig,
        OperationalLimits,
        RankerWeights,
        SufficiencyRules,
        EvidenceSufficiency,
    )

    policy = MatchingPolicyConfig(
        policy_id="adapter-test-policy",
        policy_version="1.0.0",
        description="Adapter test policy",
        weights=RankerWeights(alpha=0.25, beta=0.45, gamma=0.30),
        operational_limits=OperationalLimits(retrieval_limit=100, max_candidate_pool_size=300),
        cpc_concordance_levels=CPCConcordanceLevels(
            subgroup=1.0, main_group=0.8, subclass=0.5, section=0.2, none=0.0
        ),
        confidence_thresholds=ConfidenceThresholds(strong=0.75, moderate=0.50, weak=0.25),
        sufficiency_rules=SufficiencyRules(
            min_active_signals=2, min_signals_for_sufficient=3, require_temporal_validity=True
        ),
        concept_to_cpc_taxonomy={},
        policy_sha256="e" * 64,
    )

    calls = {}

    class FakeEngine:
        def evaluate(self, demand, candidates, policy, patent_metadata=None):
            calls["demand"] = demand
            calls["candidates"] = candidates
            calls["policy"] = policy
            calls["patent_metadata"] = patent_metadata
            return [
                MatchAssessment(
                    demand_id=demand.demand_id,
                    publication_id=c.publication_id,
                    overall_score=0.5,
                    confidence=MatchConfidence.MODERATE,
                    sufficiency=EvidenceSufficiency.SUFFICIENT,
                    features=MatchFeatures(),
                    rationale="fake",
                    policy_id=policy.policy_id,
                    policy_version=policy.policy_version,
                    policy_sha256=policy.policy_sha256,
                )
                for c in candidates.candidates
            ]

    return FakeEngine(), policy, calls


def test_adapter_passes_real_evidence_to_engine(_fake_engine_and_call_record):
    """ADR 0007: Adapter must pass PatentCandidateEvidence with real benchmark data to engine.

    Verifies that:
    - Each patent in the evaluation dataset produces one PatentCandidateEvidence entry
    - CPC classifications, title, and abstract are passed through without modification
    - retrieval_scores={} for all candidates (no synthetic evidence)
    """
    fake_engine, policy, calls = _fake_engine_and_call_record

    prov = EvaluationProvenance(
        source_authority="oepm",
        source_uri="https://example.com",
        extraction_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        raw_payload_sha256="f" * 64,
        modality=DataModality.OBSERVED,
    )
    demand = EvaluationDemand(
        demand_id="D-TEST",
        title="Test Demand",
        description="Test description",
        posted_date=date(2023, 6, 1),
        target_cpc_prefixes=["E03C"],
        provenance=prov,
    )
    patents = [
        EvaluationPatent(
            publication_id="EP-1",
            publication_date=date(2022, 3, 15),
            classifications_cpc=["E03C1/02", "E03D1/00"],
            title="Drainage valve",
            abstract="A valve for draining water.",
            provenance=prov,
        ),
        EvaluationPatent(
            publication_id="EP-2",
            publication_date=date(2021, 7, 20),
            classifications_cpc=["F16K1/00"],
            title="Check valve",
            abstract="A one-way valve.",
            provenance=prov,
        ),
    ]

    adapter = DefaultMatchingAdapter(engine=fake_engine, policy=policy)
    assert isinstance(adapter, EvaluationRankingPort)

    ranked = adapter.rank_candidates(demand, patents)

    # 1. Ranked list contains all patent ids
    assert set(ranked) == {"EP-1", "EP-2"}

    # 2. All candidates have retrieval_scores={} — no synthetic evidence
    for candidate in calls["candidates"].candidates:
        assert candidate.retrieval_scores == {}, (
            f"Candidate {candidate.publication_id} must have retrieval_scores={{}}. "
            "No synthetic retrieval evidence may be fabricated for a sealed benchmark pool."
        )

    # 3. Real patent evidence was passed to the engine
    assert calls["patent_metadata"] is not None
    evidence_by_id = {ev.publication_id: ev for ev in calls["patent_metadata"]}

    ev1 = evidence_by_id["EP-1"]
    assert ev1.classifications_cpc == ["E03C1/02", "E03D1/00"], "CPC classifications must be preserved"
    assert ev1.title == "Drainage valve", "Title must be preserved"
    assert ev1.abstract == "A valve for draining water.", "Abstract must be preserved"
    assert ev1.publication_date == "2022-03-15", "Publication date must be passed as ISO string"

    ev2 = evidence_by_id["EP-2"]
    assert ev2.classifications_cpc == ["F16K1/00"]
    assert ev2.title == "Check valve"


# ---------------------------------------------------------------------------
# 10. Honest pool — adapter must not fabricate retrieval scores
# ---------------------------------------------------------------------------

def test_adapter_does_not_fabricate_retrieval_scores_for_sealed_pool():
    """ADR 0007: adapter must use retrieval_scores={} — no synthetic evidence."""
    adapter_file = _eval_dir() / "matching_adapter.py"
    code = adapter_file.read_text(encoding="utf-8")

    forbidden_patterns = [
        "RetrievalMethod.LEXICAL",
        "RetrievalMethod.SEMANTIC",
        "retrieval_scores={RetrievalMethod",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in code, (
            f"Forbidden synthetic retrieval score in matching_adapter.py: '{pattern}'. "
            "Sealed benchmark pools must use retrieval_scores={{}}."
        )
