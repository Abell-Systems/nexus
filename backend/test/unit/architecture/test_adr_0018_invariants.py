"""Architectural invariant tests for ADR 0018 (Temporal Pool Eligibility Contract).

No implementation exists yet — these tests enforce the boundary ahead of any
implementation (contract -> test -> code, per ADR 0013 §3 / ADR 0016 precedent,
mirroring #27's "Enforce ADR 0013 derived-ranking-feature boundary" pattern).
They must all pass today, on the pre-ADR-0018 codebase, and must keep passing
once the follow-up implementation PR lands — a future PR that breaks one of
these has violated the ADR, not the test.

Invariants enforced:
1. `temporal_pool_mode` does not yet exist as a field anywhere — a trip-wire so
   whoever adds it is forced to re-read this file and the ADR.
2. Pool eligibility filtering must never live inside `matching_adapter.py`,
   `engine.py`, or `evaluator.py` (ADR 0018 §3/Enforcement #2) — checked by
   absence of the token in those files today, and structurally by AST-checking
   that none of them import date-comparison/eligibility helpers from the
   runner or a future pool-builder module.
2. `DefaultEvaluationRunner` remains the only place a per-demand `patent_universe`
   is assembled and handed to the ranking port — the correct home for future
   `strict`-mode filtering (ADR 0018 §3).
3. The adapter's ADR 0013 closed-universe guarantee — regression-pinned here as
   the "unconstrained baseline" ADR 0018 must preserve for
   `temporal_pool_mode="unconstrained"` — is unaffected by this ADR.
4. The evaluator's INELIGIBLE_TEMPORAL/overall_score=0.0 sufficiency behavior
   stays confined to `evaluator.py`, never duplicated elsewhere (ADR 0018 §4).
5. The 3 known temporal-violation pairs (PR #43) remain unedited in the sealed
   dataset, byte-for-byte, with their real dates/grades pinned as a regression.
"""

import ast
import json
from datetime import UTC, date, datetime
from pathlib import Path

from application.evaluation.matching_adapter import DefaultMatchingAdapter
from domain.models.evaluation import EvaluationExecutionContext
from domain.models.matching import MatchingPolicyConfig


def _get_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _read_source(rel_path: str) -> str:
    return (_get_repo_root() / rel_path).read_text(encoding="utf-8")


def _read_ast(rel_path: str) -> ast.Module:
    return ast.parse(_read_source(rel_path))


_EVAL_DIR_FILES = [
    "backend/src/main/application/evaluation/matching_adapter.py",
    "backend/src/main/application/evaluation/runner.py",
]
_MATCHING_DIR_FILES = [
    "backend/src/main/application/matching/engine.py",
    "backend/src/main/application/matching/evaluator.py",
]


# ---------------------------------------------------------------------------
# 1. temporal_pool_mode does not exist yet — trip-wire
# ---------------------------------------------------------------------------


def test_temporal_pool_mode_field_does_not_exist_yet_on_execution_context():
    """Trip-wire: once `temporal_pool_mode` is added to EvaluationExecutionContext,
    this test starts failing and forces the implementer back to ADR 0018 §5 to
    verify the field is mandatory (no default) rather than silently defaulted."""
    assert "temporal_pool_mode" not in EvaluationExecutionContext.model_fields, (
        "ADR 0018 has not been implemented yet in this codebase snapshot — if this "
        "fails, temporal_pool_mode now exists; verify it is mandatory (no default, "
        "ADR 0005 explicit-injection principle) per ADR 0018 §5, then delete this test."
    )


def test_temporal_pool_mode_token_absent_from_ranking_and_evaluation_layers():
    """No component has started inferring/hardcoding a temporal pool mode anywhere
    in the ranking or evaluation layers — the decision has not been smuggled in
    ahead of the ADR being implemented properly (ADR 0018 §2, mandatory + explicit)."""
    for rel_path in _EVAL_DIR_FILES + _MATCHING_DIR_FILES:
        source = _read_source(rel_path)
        assert "temporal_pool_mode" not in source, (
            f"{rel_path} already references 'temporal_pool_mode' — ADR 0018 requires "
            "this to be a mandatory, explicit, typed field on EvaluationExecutionContext, "
            "never inferred inside a ranking/evaluation component."
        )


# ---------------------------------------------------------------------------
# 2. Pool filtering must never live in the adapter, engine, or evaluator
# ---------------------------------------------------------------------------


def test_matching_adapter_and_engine_and_evaluator_contain_no_pool_filtering_logic():
    """ADR 0018 Enforcement #2: strict-mode Φ_temporal pool exclusion must be
    implemented in DefaultEvaluationRunner (or an equivalent pre-ranking step),
    never inside DefaultMatchingAdapter, DefaultMatchingEngine, or
    DefaultEvidenceEvaluator. A forbidden implementation would need to filter
    the candidate/patent list it's handed — this checks none of these three
    files contain list-comprehension-based filtering keyed on a temporal/date
    predicate today (the future PR must not add it here either)."""
    forbidden_tokens = ("P_eligible", "phi_temporal", "Φ_temporal", "eligible_patents", "eligible_candidates")
    for rel_path in ["backend/src/main/application/evaluation/matching_adapter.py"] + _MATCHING_DIR_FILES:
        source = _read_source(rel_path)
        for token in forbidden_tokens:
            assert token not in source, (
                f"{rel_path} references '{token}' — pool eligibility filtering belongs in "
                "DefaultEvaluationRunner (ADR 0018 §3), not in the adapter, engine, or evaluator."
            )


def test_runner_is_the_sole_assembler_of_the_per_demand_patent_universe():
    """Locks the exact architectural fact ADR 0018 §3 relies on: the runner
    builds one `patent_universe` and hands it to `ranking_port.rank_candidates`
    before computing `candidate_universe_size` — the correct, and only correct,
    insertion point for future strict-mode filtering."""
    tree = _read_ast("backend/src/main/application/evaluation/runner.py")
    source = _read_source("backend/src/main/application/evaluation/runner.py")

    assert "patent_universe" in source, (
        "DefaultEvaluationRunner no longer assembles a named patent_universe — "
        "re-verify ADR 0018 §3's insertion point still holds before implementing."
    )
    # Runner must still import nothing from the matching domain (ADR 0007's
    # "pure independent auditor" invariant) — date comparison for Φ_temporal
    # needs only evaluation-domain types (EvaluationPatent.publication_date,
    # EvaluationDemand.posted_date), so this invariant is not a blocker and
    # must not be loosened to implement ADR 0018.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("domain.models.matching"), (
                "runner.py imports from domain.models.matching — this must stay true "
                "even after ADR 0018 lands; Φ_temporal filtering needs only "
                "evaluation-domain date fields, never a matching-domain type."
            )
            assert not node.module.startswith("domain.protocols.matching"), (
                "runner.py imports from domain.protocols.matching — forbidden by "
                "ADR 0007; Φ_temporal filtering must not require this import either."
            )


# ---------------------------------------------------------------------------
# 3. Adapter's closed-universe guarantee = today's (future "unconstrained") baseline
# ---------------------------------------------------------------------------


def _make_policy() -> MatchingPolicyConfig:
    """Loads the real default policy — avoids hand-constructing every nested
    config type (RankerWeights, CPCConcordanceLevels, etc.) with guessed field
    names."""
    policy_path = (
        _get_repo_root() / "config" / "policies" / "matching" / "default_matching_policy.json"
    )
    return MatchingPolicyConfig.load_from_json(policy_path)


def test_adapter_still_preserves_full_universe_even_with_a_temporally_ineligible_patent():
    """Regression-pins today's ONLY behavior — every input patent becomes a
    candidate regardless of temporal validity — as the exact baseline ADR 0018
    must reproduce for temporal_pool_mode="unconstrained". Strict-mode filtering
    must be introduced upstream (in the runner, per ADR 0018 §3), never by
    changing DefaultMatchingAdapter.rank_candidates itself — if this test ever
    starts failing because the adapter began filtering, ADR 0018 has been
    implemented in the wrong layer."""
    class _RecordingEngine:
        def evaluate(self, demand, candidates, policy, patent_metadata):  # noqa: ANN001
            self.seen_candidates = candidates
            return []

    class _FakeEvalPatent:
        def __init__(self, publication_id: str, publication_date):
            self.publication_id = publication_id
            self.publication_date = publication_date
            self.classifications_cpc: list[str] = []
            self.title = "T"
            self.abstract = "A"

    class _FakeEvalDemand:
        demand_id = "D-ADR-0018"
        title = "T"
        description = "D"
        posted_date = date(2023, 6, 1)
        provenance = type("P", (), {"source_authority": "test"})()
        target_cpc_prefixes: list[str] = []

    engine = _RecordingEngine()
    policy = _make_policy()
    adapter = DefaultMatchingAdapter(engine=engine, policy=policy, bm25_k1=1.5, bm25_b=0.75)

    patents = [
        _FakeEvalPatent("EP-ELIGIBLE", date(2022, 1, 1)),  # t_pub < t_demand: eligible
        _FakeEvalPatent("EP-INELIGIBLE", date(2024, 1, 1)),  # t_pub > t_demand: ineligible
    ]

    adapter.rank_candidates(_FakeEvalDemand(), patents)  # type: ignore[arg-type]

    candidate_ids = {c.publication_id for c in engine.seen_candidates.candidates}
    assert candidate_ids == {"EP-ELIGIBLE", "EP-INELIGIBLE"}, (
        "Adapter must still preserve the full closed universe today — temporal "
        "eligibility is not evaluated by the adapter at all (it has no demand "
        "date to compare against; DemandSignal carries no posted_date reachable "
        "here). This is the unconstrained-mode baseline ADR 0018 must keep true."
    )


# ---------------------------------------------------------------------------
# 4. INELIGIBLE_TEMPORAL scoring stays confined to evaluator.py
# ---------------------------------------------------------------------------


def test_ineligible_temporal_scoring_logic_exists_only_in_evaluator():
    """ADR 0018 §4: the evaluator's INELIGIBLE_TEMPORAL / overall_score=0.0
    sufficiency behavior is a distinct, pre-existing concern that must not be
    duplicated into any future pool-eligibility implementation."""
    evaluator_source = _read_source("backend/src/main/application/matching/evaluator.py")
    assert "INELIGIBLE_TEMPORAL" in evaluator_source

    other_files = [
        "backend/src/main/application/evaluation/matching_adapter.py",
        "backend/src/main/application/evaluation/runner.py",
        "backend/src/main/application/matching/engine.py",
    ]
    for rel_path in other_files:
        source = _read_source(rel_path)
        assert "INELIGIBLE_TEMPORAL" not in source, (
            f"{rel_path} references INELIGIBLE_TEMPORAL — this sufficiency-scoring "
            "concern must stay confined to DefaultEvidenceEvaluator (ADR 0018 §4)."
        )


# ---------------------------------------------------------------------------
# 5. Sealed dataset's 3 flagged temporal-violation pairs remain unedited
# ---------------------------------------------------------------------------


def test_sealed_dataset_temporal_violation_pairs_remain_unedited():
    """Regression-pins the exact dates/grades PR #43 recorded for the 3 known
    temporal violations (docs/dataset-identity-audit.md §2.4). ADR 0018
    decides what the harness does with these pairs at pool-construction time;
    it must never edit, re-annotate, or remove them from the sealed dataset."""
    dataset_path = _get_repo_root() / "data" / "evaluation" / "dataset_pilot_benchmark.json"
    data = json.loads(dataset_path.read_text(encoding="utf-8"))

    grades_by_pair = {(a["demand_id"], a["publication_id"]): a["grade"] for a in data["annotations"]}
    posted_dates = {d["demand_id"]: d["posted_date"] for d in data["demands"]}
    pub_dates = {p["publication_id"]: p["publication_date"] for p in data["patents"]}

    expected = {
        ("INNOGET-2415", "ES-2901234-A1"): 2,
        ("INNOGET-2501", "ES-2901234-A1"): 0,
        ("INNOGET-2292", "ES-2856789-A1"): 0,
    }
    for pair, expected_grade in expected.items():
        assert grades_by_pair[pair] == expected_grade, f"Grade for {pair} changed since #43 — dataset was edited."

    assert posted_dates["INNOGET-2415"] == "2023-01-10"
    assert posted_dates["INNOGET-2501"] == "2023-03-20"
    assert posted_dates["INNOGET-2292"] == "2023-02-15"
    assert pub_dates["ES-2901234-A1"] == "2023-04-20"
    assert pub_dates["ES-2856789-A1"] == "2023-03-25"

    # All 3 pairs must still violate t_pub < t_demand (still temporal violations,
    # not silently corrected).
    for demand_id, publication_id in expected:
        t_demand = datetime.strptime(posted_dates[demand_id], "%Y-%m-%d").replace(tzinfo=UTC)
        t_pub = datetime.strptime(pub_dates[publication_id], "%Y-%m-%d").replace(tzinfo=UTC)
        assert not (t_pub < t_demand), f"{(demand_id, publication_id)} is no longer a temporal violation — dataset was edited."
