# PR-E: First Empirical M0 vs M1 Comparison — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the first reproducible, pre-registered M0 (lexical+CPC) vs M1 (lexical+semantic+CPC, ADR 0016 fusion) comparison over the sealed 45-pair benchmark, with nDCG@10 as the primary endpoint, Recall@5 and MRR as secondary/pre-registered endpoints, and a sealed `ComparativeRunReport` artifact carrying full provenance.

**Architecture:** No changes to `domain/`, `application/matching/`, or `MetricSet` (closed in #44). This PR adds one new pre-registered `StudyProtocol` JSON (scoped to M0-vs-M1 only, does not touch the sealed `comparisons_m0_m6.json` M0–M6 family), one small JSON-serialization helper for `ComparativeRunReport` (the existing model embeds two plain dataclasses that pydantic cannot serialize losslessly to JSON), and one new CLI script that runs M0 and M1 under exactly the same `EvaluationExecutionContext` (same dataset, same policy, same commit, same timestamp — the shared `P_shared`) and feeds both `EvaluationRunReport`s into the existing `evaluate_study_protocol`.

**Tech Stack:** Python 3.12, pydantic v2, pytest. Reuses `DefaultEvaluationRunner`, `DefaultMatchingAdapter`, `DefaultMatchingEngine`, `evaluate_study_protocol` — all already implemented and unchanged by this plan.

**Spec:** This plan implements the user's PR-E spec from the conversation (2026-09-07): run M0 vs M1 over the sealed 45 pairs, nDCG@10 primary, Recall@5 secondary (per the user's explicit decision to not reopen `MetricSet` for `recall_at_10`), MRR secondary/pre-registered without reinterpretation, explicit denominators/exclusions (already in `EvaluationRunReport.macro_denominators` and `HypothesisTestResult.excluded_demand_ids`/`n_paired` per #44), a reproducible artifact with hashes/provenance, no weight/protocol retrofitting, `study_status: PILOT`, and the 3 known temporal violations from #43 left untouched (the runner already scores them `INELIGIBLE_TEMPORAL` / `overall_score=0.0` — no dataset edit happens in this PR).

## Global Constraints

- Do not modify `backend/src/main/domain/models/evaluation.py` (`MetricSet`, `StudyProtocol`, `HypothesisTestResult`, `ComparativeRunReport` stay exactly as `#44` left them).
- Do not modify `config/evaluations/comparisons_m0_m6.json` or its test (`test_study_protocol.py`) — the M0-vs-M1 protocol is a **new, separate** pre-registered file.
- Do not modify `application/matching/evaluator.py`, `application/evaluation/matching_adapter.py`, `application/evaluation/comparative.py`, or any policy weight — this PR only orchestrates two existing evaluation runs and feeds them through the existing comparative harness.
- Do not touch `data/evaluation/dataset_pilot_benchmark.json` or its sidecars (sealed, per #43) — the 3 temporal-violation pairs stay in the dataset, scored `INELIGIBLE_TEMPORAL` by the existing runner, exactly as #43 recorded.
- No new third-party dependency. Only `stdlib` + already-installed `pydantic`/`pytest`.
- Every commit in this repo credits `Lydia Bares <lydiabares@gmail.com>` as co-author (see `/home/valentin/code/nexus/CLAUDE.md`).

---

## Task 1: Pre-register the M0-vs-M1 pilot study protocol

**Files:**
- Create: `config/evaluations/comparisons_m0_vs_m1_pilot.json`
- Test: `backend/test/unit/application/evaluation/test_m0_vs_m1_pilot_protocol.py`

**Interfaces:**
- Consumes: `domain.models.evaluation.StudyProtocol` (existing, unchanged) — the test round-trips the JSON through `StudyProtocol.model_validate`.
- Produces: the sealed protocol file, loaded by Task 3's script via `StudyProtocol.model_validate(json.loads(path.read_text()))`.

- [ ] **Step 1: Generate the pre-registered protocol JSON from a script — never hand-type the hash**

The `protocol_sha256` must be computed from the actual serialized payload, not copied by hand. Run this one-off generation script so the hash is always derived from the real file content, using the exact same canonicalization `test_study_protocol_sha256_integrity` (the M0–M6 family's own test) already uses — `json.dumps(payload, sort_keys=True, indent=2)` over every field except `protocol_sha256` itself:

```bash
cd /home/valentin/code/nexus && python3 - <<'PYEOF'
import json
import hashlib
from pathlib import Path

payload = {
    "study_id": "NEXUS-M0-VS-M1-PILOT",
    "study_version": "1.0.0",
    "description": (
        "Pre-registered comparative inferential evaluation protocol for the first "
        "M0 (lexical+CPC) vs M1 (lexical+semantic+CPC, ADR 0016 fusion) pilot "
        "comparison over the sealed 45-pair benchmark."
    ),
    "alpha": 0.05,
    "multiple_testing_method": "benjamini_hochberg",
    "bootstrap_iterations": 10000,
    "bootstrap_confidence_level": 0.95,
    "seed": 42,
    "models": {
        "M0": "Lexical BM25 + CPC concordance baseline (no semantic artifact wired)",
        "M1": "Lexical + semantic (frozen embedding, ADR 0014) + CPC, fused per ADR 0016",
    },
    "hypotheses": [
        {
            "id": "H01_M0_VS_M1_NDCG10",
            "baseline": "M0",
            "treatment": "M1",
            "metric": "ndcg_at_10",
            "scope": "strict",
            "alternative": "greater",
            "description": (
                "Primary endpoint (PR #44): wiring the frozen M1 semantic embedding "
                "improves nDCG@10 over the lexical+CPC baseline."
            ),
        },
        {
            "id": "H02_M0_VS_M1_RECALL5",
            "baseline": "M0",
            "treatment": "M1",
            "metric": "recall_at_5",
            "scope": "strict",
            "alternative": "greater",
            "description": "Secondary endpoint: M1 improves Recall@5 over the lexical+CPC baseline.",
        },
        {
            "id": "H03_M0_VS_M1_MRR",
            "baseline": "M0",
            "treatment": "M1",
            "metric": "mrr",
            "scope": "strict",
            "alternative": "greater",
            "description": (
                "Secondary, pre-registered endpoint (mirrors H01_M1_vs_M0_MRR in "
                "config/evaluations/comparisons_m0_m6.json, not reinterpreted): M1 "
                "improves strict MRR over the lexical+CPC baseline."
            ),
        },
    ],
}

canonical = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
payload["protocol_sha256"] = hashlib.sha256(canonical).hexdigest()

out_path = Path("config/evaluations/comparisons_m0_vs_m1_pilot.json")
out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {out_path} with protocol_sha256={payload['protocol_sha256']}")
PYEOF
```

Expected output: `Wrote config/evaluations/comparisons_m0_vs_m1_pilot.json with protocol_sha256=<64 hex chars>`. Inspect the file afterward (`cat config/evaluations/comparisons_m0_vs_m1_pilot.json`) — Step 4's test independently recomputes this same hash from the file and is the actual authority on correctness, not this script.

- [ ] **Step 2: Write the failing test**

Create `backend/test/unit/application/evaluation/test_m0_vs_m1_pilot_protocol.py`:

```python
"""Tests for the pre-registered M0-vs-M1 pilot study protocol (PR-E).

Invariants verified:
- config/evaluations/comparisons_m0_vs_m1_pilot.json exists and parses.
- Exactly 3 pre-registered hypotheses: nDCG@10 (primary), Recall@5 (secondary),
  MRR (secondary, pre-registered, not reinterpreted from the M0-M6 family).
- protocol_sha256 matches the exact content digest excluding self-reference.
- The file round-trips through domain.models.evaluation.StudyProtocol.
- This file is independent of config/evaluations/comparisons_m0_m6.json — neither
  file references or mutates the other.
"""

import hashlib
import json
from pathlib import Path

import pytest

from domain.models.evaluation import StudyProtocol


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def get_protocol_path() -> Path:
    return get_repo_root() / "config" / "evaluations" / "comparisons_m0_vs_m1_pilot.json"


def test_m0_vs_m1_pilot_protocol_file_exists_and_parses():
    protocol_path = get_protocol_path()
    assert protocol_path.is_file(), f"Pre-registered M0-vs-M1 protocol missing at {protocol_path}"

    data = json.loads(protocol_path.read_text(encoding="utf-8"))

    assert data["study_id"] == "NEXUS-M0-VS-M1-PILOT"
    assert data["study_version"] == "1.0.0"
    assert data["alpha"] == 0.05
    assert data["multiple_testing_method"] == "benjamini_hochberg"
    assert data["bootstrap_iterations"] == 10000
    assert data["bootstrap_confidence_level"] == 0.95
    assert data["seed"] == 42

    hypotheses = data["hypotheses"]
    assert len(hypotheses) == 3, "Expected exactly 3 pre-registered hypotheses for the M0-vs-M1 pilot"

    expected_ids = ["H01_M0_VS_M1_NDCG10", "H02_M0_VS_M1_RECALL5", "H03_M0_VS_M1_MRR"]
    assert [h["id"] for h in hypotheses] == expected_ids

    expected_metrics = {
        "H01_M0_VS_M1_NDCG10": "ndcg_at_10",
        "H02_M0_VS_M1_RECALL5": "recall_at_5",
        "H03_M0_VS_M1_MRR": "mrr",
    }
    for h in hypotheses:
        assert h["baseline"] == "M0"
        assert h["treatment"] == "M1"
        assert h["metric"] == expected_metrics[h["id"]]
        assert h["scope"] == "strict"
        assert h["alternative"] == "greater"


def test_m0_vs_m1_pilot_protocol_sha256_integrity():
    data = json.loads(get_protocol_path().read_text(encoding="utf-8"))
    declared_sha = data["protocol_sha256"]
    assert len(declared_sha) == 64

    payload = {k: v for k, v in data.items() if k != "protocol_sha256"}
    canonical_bytes = json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")
    computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

    assert declared_sha == computed_sha, f"Protocol digest mismatch: {declared_sha} vs {computed_sha}"


def test_m0_vs_m1_pilot_protocol_round_trips_through_domain_model():
    data = json.loads(get_protocol_path().read_text(encoding="utf-8"))
    protocol = StudyProtocol.model_validate(data)

    assert protocol.study_id == "NEXUS-M0-VS-M1-PILOT"
    assert len(protocol.hypotheses) == 3
    assert protocol.hypotheses[0].metric == "ndcg_at_10"
    assert protocol.hypotheses[0].alternative == "greater"


def test_m0_vs_m1_pilot_protocol_is_independent_of_m0_m6_family():
    m0_m6_path = get_repo_root() / "config" / "evaluations" / "comparisons_m0_m6.json"
    m0_m6_data = json.loads(m0_m6_path.read_text(encoding="utf-8"))
    pilot_data = json.loads(get_protocol_path().read_text(encoding="utf-8"))

    assert m0_m6_data["study_id"] != pilot_data["study_id"]
    m0_m6_ids = {h["id"] for h in m0_m6_data["hypotheses"]}
    pilot_ids = {h["id"] for h in pilot_data["hypotheses"]}
    assert m0_m6_ids.isdisjoint(pilot_ids), "Hypothesis IDs must not collide between the two protocols"
```

- [ ] **Step 3: Run test to verify it fails only if the file is missing**

Run: `cd /home/valentin/code/nexus && pytest backend/test/unit/application/evaluation/test_m0_vs_m1_pilot_protocol.py -v`
Expected (before Step 1's file exists): `FAIL` with `AssertionError: Pre-registered M0-vs-M1 protocol missing at ...`. If you already created the JSON in Step 1, this instead should already `PASS` — run it now to confirm the hash and content are exactly right before moving on.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/valentin/code/nexus && pytest backend/test/unit/application/evaluation/test_m0_vs_m1_pilot_protocol.py -v`
Expected: `4 passed`.

- [ ] **Step 5: Commit**

```bash
git add config/evaluations/comparisons_m0_vs_m1_pilot.json backend/test/unit/application/evaluation/test_m0_vs_m1_pilot_protocol.py
git commit -m "$(cat <<'EOF'
Pre-register M0-vs-M1 pilot study protocol (PR-E, doc/config-only)

nDCG@10 primary, Recall@5 secondary, MRR secondary/pre-registered
(mirrors comparisons_m0_m6.json's H01 without touching that sealed
file). Registered before any M0/M1 comparative result exists.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

## Task 2: JSON-safe serialization for `ComparativeRunReport`

**Files:**
- Create: `backend/src/main/infrastructure/evaluation/comparative_report_serializer.py`
- Test: `backend/test/unit/infrastructure/test_comparative_report_serializer.py`

**Interfaces:**
- Consumes: `domain.models.evaluation.ComparativeRunReport`, `domain.models.evaluation.HypothesisTestResult` (existing, unchanged); `application.evaluation.statistics.types.WilcoxonResult`, `BootstrapCIResult` (existing plain frozen dataclasses).
- Produces: `serialize_comparative_report(report: ComparativeRunReport) -> dict` — a plain JSON-serializable dict. Task 3's script imports and calls this.

Pydantic's `ComparativeRunReport.model_dump_json()` cannot losslessly serialize `HypothesisTestResult.wilcoxon`/`.bootstrap_ci` — both are typed `"object"` with `arbitrary_types_allowed=True` because they're plain `@dataclass(frozen=True)` types (`application/evaluation/statistics/types.py`), not pydantic models. This infrastructure-layer helper (it belongs in `infrastructure/` per this repo's Clean Architecture split: it's a serialization/output concern, not a domain rule) converts them via `dataclasses.asdict` explicitly.

- [ ] **Step 1: Write the failing test**

Create `backend/test/unit/infrastructure/test_comparative_report_serializer.py`:

```python
"""Tests for JSON-safe serialization of ComparativeRunReport (PR-E)."""

import json

from application.evaluation.statistics.types import BootstrapCIResult, WilcoxonResult
from domain.models.evaluation import ComparativeRunReport, HypothesisTestResult
from infrastructure.evaluation.comparative_report_serializer import serialize_comparative_report


def _make_report() -> ComparativeRunReport:
    wilcoxon = WilcoxonResult(statistic=0.0, p_value=0.125, n_pairs=3, n_nonzero=2, alternative="greater")
    bootstrap = BootstrapCIResult(
        estimate=0.15, ci_lower=-0.05, ci_upper=0.35, n_bootstrap=10000, confidence_level=0.95, seed=42
    )
    result = HypothesisTestResult(
        hypothesis_id="H01_M0_VS_M1_NDCG10",
        baseline="M0",
        treatment="M1",
        metric="ndcg_at_10",
        scope="strict",
        wilcoxon=wilcoxon,
        bootstrap_ci=bootstrap,
        adjusted_q_value=0.25,
        rejected=False,
        n_paired=3,
        excluded_demand_ids=[],
    )
    return ComparativeRunReport(
        study_protocol_id="NEXUS-M0-VS-M1-PILOT",
        study_protocol_sha256="5c4687e7a88ab86426799f06f03864d6eb1bca3b657289e6ce270f5373240de8",
        study_status="PILOT",
        run_ids={"M0": "run-m0-abc", "M1": "run-m1-def"},
        results=[result],
    )


def test_serialize_comparative_report_is_json_dumpable():
    report = _make_report()
    serialized = serialize_comparative_report(report)
    dumped = json.dumps(serialized)  # raises if anything isn't JSON-safe
    reloaded = json.loads(dumped)
    assert reloaded["study_protocol_id"] == "NEXUS-M0-VS-M1-PILOT"


def test_serialize_comparative_report_preserves_wilcoxon_and_bootstrap_fields():
    report = _make_report()
    serialized = serialize_comparative_report(report)
    result = serialized["results"][0]

    assert result["hypothesis_id"] == "H01_M0_VS_M1_NDCG10"
    assert result["wilcoxon"] == {
        "statistic": 0.0,
        "p_value": 0.125,
        "n_pairs": 3,
        "n_nonzero": 2,
        "alternative": "greater",
    }
    assert result["bootstrap_ci"] == {
        "estimate": 0.15,
        "ci_lower": -0.05,
        "ci_upper": 0.35,
        "n_bootstrap": 10000,
        "confidence_level": 0.95,
        "seed": 42,
    }
    assert result["n_paired"] == 3
    assert result["excluded_demand_ids"] == []


def test_serialize_comparative_report_top_level_fields():
    report = _make_report()
    serialized = serialize_comparative_report(report)

    assert serialized["study_status"] == "PILOT"
    assert serialized["run_ids"] == {"M0": "run-m0-abc", "M1": "run-m1-def"}
    assert len(serialized["results"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/valentin/code/nexus/backend && PYTHONPATH=src/main pytest ../backend/test/unit/infrastructure/test_comparative_report_serializer.py -v`
Expected: `FAIL` with `ModuleNotFoundError: No module named 'infrastructure.evaluation.comparative_report_serializer'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/src/main/infrastructure/evaluation/comparative_report_serializer.py`:

```python
"""JSON-safe serialization for ComparativeRunReport (PR-E).

ComparativeRunReport.results[].wilcoxon / .bootstrap_ci are typed as plain
"object" in the domain model (they wrap pre-existing frozen dataclasses from
application.evaluation.statistics.types, PR #22) because pydantic does not own
those types. This module converts the full report to a plain, JSON-dumpable
dict for artifact output — an infrastructure/output concern, not a domain rule.
"""

import dataclasses
from typing import Any

from domain.models.evaluation import ComparativeRunReport


def serialize_comparative_report(report: ComparativeRunReport) -> dict[str, Any]:
    """Converts a ComparativeRunReport into a plain, JSON-dumpable dict."""
    return {
        "study_protocol_id": report.study_protocol_id,
        "study_protocol_sha256": report.study_protocol_sha256,
        "study_status": report.study_status,
        "run_ids": dict(report.run_ids),
        "results": [
            {
                "hypothesis_id": r.hypothesis_id,
                "baseline": r.baseline,
                "treatment": r.treatment,
                "metric": r.metric,
                "scope": r.scope,
                "wilcoxon": dataclasses.asdict(r.wilcoxon),
                "bootstrap_ci": dataclasses.asdict(r.bootstrap_ci),
                "adjusted_q_value": r.adjusted_q_value,
                "rejected": r.rejected,
                "n_paired": r.n_paired,
                "excluded_demand_ids": list(r.excluded_demand_ids),
            }
            for r in report.results
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/valentin/code/nexus/backend && PYTHONPATH=src/main pytest ../backend/test/unit/infrastructure/test_comparative_report_serializer.py -v`
Expected: `3 passed`.

- [ ] **Step 5: Run ruff and mypy on the new file**

Run: `cd /home/valentin/code/nexus && ruff check backend/src/main/infrastructure/evaluation/comparative_report_serializer.py backend/test/unit/infrastructure/test_comparative_report_serializer.py && mypy backend/src/main --ignore-missing-imports`
Expected: `All checks passed!` and `Success: no issues found in ... source files`.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/infrastructure/evaluation/comparative_report_serializer.py backend/test/unit/infrastructure/test_comparative_report_serializer.py
git commit -m "$(cat <<'EOF'
Add JSON-safe serializer for ComparativeRunReport (PR-E)

ComparativeRunReport embeds plain dataclasses (WilcoxonResult,
BootstrapCIResult) pydantic cannot serialize losslessly. Needed before
the M0-vs-M1 comparison script can write a machine-readable artifact.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

## Task 3: CLI script — run M0 and M1 under the same `P_shared` and compare

**Files:**
- Create: `scripts/run_m0_vs_m1_comparison.py`
- Test: covered by Task 4's e2e test (this script is a CLI entrypoint; per this repo's convention, `run_scientific_evaluation.py` also has no standalone unit test — it's exercised end-to-end).

**Interfaces:**
- Consumes: `DefaultEvaluationDatasetLoader.load_validated_dataset` (existing), `MatchingPolicyConfig.load_from_json` (existing), `ModelConfigurationManifest.load_from_json`/`.verify_source_policy` (existing), `FrozenEmbeddingArtifact.load_from_json`/`.verify_source_dataset` (existing), `DefaultMatchingAdapter.__init__(engine, policy, *, bm25_k1, bm25_b, semantic_artifact=None)` (existing), `DefaultEvaluationRunner.run_evaluation(dataset, ranking_port, policy, context) -> EvaluationRunReport` (existing), `evaluate_study_protocol(runs, protocol, study_status) -> ComparativeRunReport` (existing), `serialize_comparative_report` (Task 2), `StudyProtocol` (existing).
- Produces: three JSON files under `--output-dir` (default `data/experiments/`): `m0_run_report.json`, `m1_run_report.json`, `m0_vs_m1_comparative_report.json`.

- [ ] **Step 1: Write the script**

Create `scripts/run_m0_vs_m1_comparison.py`:

```python
#!/usr/bin/env python3
"""CLI: First empirical M0 vs M1 comparison (PR-E) under ADR 0007/0011/0016.

Runs M0 (lexical BM25 + CPC, no semantic artifact) and M1 (lexical + semantic
frozen embedding + CPC, ADR 0016 fusion) over the SAME sealed dataset, policy,
engine commit, and execution timestamp (P_shared), then feeds both
EvaluationRunReports into the pre-registered M0-vs-M1 pilot protocol
(config/evaluations/comparisons_m0_vs_m1_pilot.json) via the existing
evaluate_study_protocol harness (ADR 0011).

Invariants:
- Zero weight tuning, zero protocol retrofitting: both runs use the same
  MatchingPolicyConfig and the same frozen model configuration manifest.
- The 3 known temporal-violation pairs (PR #43) are NOT corrected here: the
  sealed dataset is loaded as-is; the runner already scores them
  INELIGIBLE_TEMPORAL / overall_score=0.0, exactly as #43 recorded.
- study_status is always "PILOT" — this script cannot produce a "FINAL" result.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "backend" / "src" / "main"))

from application.evaluation.comparative import evaluate_study_protocol
from application.evaluation.matching_adapter import DefaultMatchingAdapter
from application.evaluation.runner import DefaultEvaluationRunner
from application.matching.engine import DefaultMatchingEngine
from domain.models.evaluation import (
    EvaluationExecutionContext,
    EvaluationRunReport,
    FrozenEmbeddingArtifact,
    ModelConfigurationManifest,
    StudyProtocol,
)
from domain.models.matching import MatchingPolicyConfig
from infrastructure.evaluation.comparative_report_serializer import serialize_comparative_report
from infrastructure.evaluation.dataset_loader import DefaultEvaluationDatasetLoader

_COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _get_git_commit(cwd: Path) -> str | None:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, check=True, capture_output=True, text=True
        )
        return res.stdout.strip()
    except Exception:
        return None


def _resolve_commit_hash(engine_commit_arg: str | None, cwd: Path) -> str:
    if engine_commit_arg is not None:
        if not _COMMIT_HASH_RE.match(engine_commit_arg):
            raise ValueError(f"Invalid --engine-commit '{engine_commit_arg}': must be 7-40 hex chars.")
        return engine_commit_arg
    discovered = _get_git_commit(cwd)
    if discovered is None:
        raise RuntimeError(
            "Unable to discover git commit hash: 'git rev-parse HEAD' failed. "
            "Pass --engine-commit explicitly. Placeholder hashes are prohibited."
        )
    return discovered


def _run_report_artifact(
    report: EvaluationRunReport,
    semantic_artifact: FrozenEmbeddingArtifact | None,
    model_config_sha256: str,
) -> dict:
    """Assembles the individual run artifact with FULL provenance.

    EvaluationRunReport.model_dump_json() already carries dataset_sha256,
    policy_sha256, and the complete EvaluationExecutionContext (engine_name,
    engine_version, engine_commit_hash, execution_timestamp, environment) as
    native fields (verified directly against domain/models/evaluation.py
    during planning — do not assume, re-check if that model ever changes).
    It does NOT carry the frozen model-configuration manifest's own hash
    (ADR 0012's config_sha256, which is what pins M0's BM25 k1/b) — that is
    a separate provenance-controlled document from a different loader, so it
    is added explicitly here rather than silently left out of the artifact.
    """
    report_dict = json.loads(report.model_dump_json(indent=2))
    report_dict["study_status"] = "PILOT"
    report_dict["study_protocol_id"] = "NEXUS-M0-VS-M1-PILOT"
    report_dict["model_config_sha256"] = model_config_sha256
    report_dict["embedding_provenance"] = (
        None
        if semantic_artifact is None
        else {
            "artifact_id": semantic_artifact.artifact_id,
            "artifact_sha256": semantic_artifact.artifact_sha256,
            "dataset_sha256": semantic_artifact.dataset_sha256,
            "model_name": semantic_artifact.model_name,
            "model_revision": semantic_artifact.model_revision,
            "embedding_dimension": semantic_artifact.embedding_dimension,
            "generation_device": semantic_artifact.generation_device,
        }
    )
    return report_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the first M0 vs M1 pilot comparison (PR-E)")
    parser.add_argument("--dataset", type=Path, default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.json")
    parser.add_argument("--checksum", type=Path, default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.sha256")
    parser.add_argument("--manifest", type=Path, default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.manifest.json")
    parser.add_argument("--policy", type=Path, default=repo_root / "config" / "policies" / "matching" / "default_matching_policy.json")
    parser.add_argument("--model-config", type=Path, dest="model_config", default=repo_root / "config" / "evaluations" / "model_configurations_m0_m6.json")
    parser.add_argument("--embeddings", type=Path, default=repo_root / "data" / "evaluation" / "embeddings_pilot_benchmark.json")
    parser.add_argument("--protocol", type=Path, default=repo_root / "config" / "evaluations" / "comparisons_m0_vs_m1_pilot.json")
    parser.add_argument("--output-dir", type=Path, dest="output_dir", default=repo_root / "data" / "experiments")
    parser.add_argument("--environment", type=str, default="local_benchmark")
    parser.add_argument("--engine-commit", type=str, dest="engine_commit", default=None)
    args = parser.parse_args()

    print("================================================================================")
    print("Nexus PR-E — First Empirical M0 vs M1 Comparison (ADR 0011 / ADR 0016)")
    print("================================================================================")

    loader = DefaultEvaluationDatasetLoader()
    validated_dataset = loader.load_validated_dataset(
        dataset_path=args.dataset, checksum_path=args.checksum, manifest_path=args.manifest
    )
    print(f"Dataset verified:   {validated_dataset.dataset.dataset_id} (SHA: {validated_dataset.manifest.content_sha256[:12]}...)")

    policy = MatchingPolicyConfig.load_from_json(args.policy)
    print(f"Policy verified:    {policy.policy_id} v{policy.policy_version}")

    model_config = ModelConfigurationManifest.load_from_json(args.model_config)
    model_config.verify_source_policy(policy)
    m0_config = next(m for m in model_config.models if m.model_id == "M0")
    if m0_config.weights is None:
        raise ValueError(f"Model configuration manifest '{args.model_config}' declares no weights for M0.")
    bm25_k1 = m0_config.weights["k1"]
    bm25_b = m0_config.weights["b"]
    print(f"Model config verified: M0 k1={bm25_k1}, b={bm25_b}")

    semantic_artifact = FrozenEmbeddingArtifact.load_from_json(args.embeddings)
    semantic_artifact.verify_source_dataset(validated_dataset)
    print(f"Embeddings verified: {semantic_artifact.artifact_id} ({semantic_artifact.model_name})")

    commit_hash = _resolve_commit_hash(args.engine_commit, repo_root)
    # Same context instance for both runs: same commit, same timestamp, same
    # environment — the P_shared the two runs must share to be comparable.
    context = EvaluationExecutionContext(
        engine_name="DefaultMatchingEngine",
        engine_version="0.2.0",
        engine_commit_hash=commit_hash,
        execution_timestamp=datetime.now(UTC),
        environment=args.environment,
    )
    print(f"Execution Context:  Engine commit {commit_hash[:7]} at {context.execution_timestamp.isoformat()}")

    engine = DefaultMatchingEngine()
    runner = DefaultEvaluationRunner()

    print("\nRunning M0 (lexical + CPC, no semantic artifact)...")
    adapter_m0 = DefaultMatchingAdapter(engine=engine, policy=policy, bm25_k1=bm25_k1, bm25_b=bm25_b, semantic_artifact=None)
    report_m0 = runner.run_evaluation(dataset=validated_dataset, ranking_port=adapter_m0, policy=policy, context=context)
    print(f"  M0 run_id: {report_m0.run_id}")

    print("Running M1 (lexical + semantic + CPC, ADR 0016 fusion)...")
    adapter_m1 = DefaultMatchingAdapter(engine=engine, policy=policy, bm25_k1=bm25_k1, bm25_b=bm25_b, semantic_artifact=semantic_artifact)
    report_m1 = runner.run_evaluation(dataset=validated_dataset, ranking_port=adapter_m1, policy=policy, context=context)
    print(f"  M1 run_id: {report_m1.run_id}")

    protocol = StudyProtocol.model_validate(json.loads(args.protocol.read_text(encoding="utf-8")))
    print(f"\nProtocol loaded:    {protocol.study_id} v{protocol.study_version} ({len(protocol.hypotheses)} hypotheses)")

    comparative = evaluate_study_protocol(runs={"M0": report_m0, "M1": report_m1}, protocol=protocol, study_status="PILOT")

    print("\n================================================================================")
    print(f"COMPARATIVE REPORT — study_status={comparative.study_status}")
    print("================================================================================")
    for r in comparative.results:
        print(
            f"{r.hypothesis_id:<28} metric={r.metric:<12} n_paired={r.n_paired} "
            f"excluded={r.excluded_demand_ids} p={r.wilcoxon.p_value:.4f} "
            f"q={r.adjusted_q_value:.4f} rejected={r.rejected} "
            f"bootstrap_ci=[{r.bootstrap_ci.ci_lower:.4f}, {r.bootstrap_ci.ci_upper:.4f}]"
        )
    print("================================================================================")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "m0_run_report.json").write_text(
        json.dumps(_run_report_artifact(report_m0, None, model_config.config_sha256), indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "m1_run_report.json").write_text(
        json.dumps(_run_report_artifact(report_m1, semantic_artifact, model_config.config_sha256), indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "m0_vs_m1_comparative_report.json").write_text(
        json.dumps(serialize_comparative_report(comparative), indent=2), encoding="utf-8"
    )
    print(f"\nArtifacts written to: {args.output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Make it executable and run it once manually to sanity-check**

Run: `cd /home/valentin/code/nexus && python3 scripts/run_m0_vs_m1_comparison.py --output-dir /tmp/pr-e-manual-check`
Expected: exit code 0, printed comparative table with 3 rows (`H01_M0_VS_M1_NDCG10`, `H02_M0_VS_M1_RECALL5`, `H03_M0_VS_M1_MRR`), and three JSON files created under `/tmp/pr-e-manual-check/`. If any loader raises (e.g. hash mismatch), fix the invoked paths — do not touch the loaders themselves.

- [ ] **Step 3: Ruff and mypy**

Run: `cd /home/valentin/code/nexus && ruff check scripts/run_m0_vs_m1_comparison.py --fix && mypy backend/src/main --ignore-missing-imports`
Expected: `All checks passed!` / no new mypy errors. (mypy is configured against `backend/src/main`, not `scripts/`, matching the existing CI job for `run_scientific_evaluation.py`.)

- [ ] **Step 4: Commit**

```bash
git add scripts/run_m0_vs_m1_comparison.py
git commit -m "$(cat <<'EOF'
Add CLI for the first M0 vs M1 pilot comparison (PR-E)

Runs M0 and M1 under the same EvaluationExecutionContext (P_shared:
same dataset, policy, commit, timestamp) and feeds both reports into
the pre-registered comparisons_m0_vs_m1_pilot.json protocol via the
existing evaluate_study_protocol harness. No weight or protocol
changes; the 3 known temporal violations (#43) are left untouched.

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

## Task 4: End-to-end test over the real sealed benchmark

**Files:**
- Create: `backend/test/e2e/test_m0_vs_m1_comparison_cli.py`

**Interfaces:**
- Consumes: `scripts/run_m0_vs_m1_comparison.py` (Task 3) via `subprocess`, following the existing convention in `backend/test/e2e/test_ingest_use_case.py`.
- Produces: nothing consumed downstream — this is the terminal verification gate for PR-E.

- [ ] **Step 1: Write the failing test**

Create `backend/test/e2e/test_m0_vs_m1_comparison_cli.py`:

```python
"""E2E test for the M0 vs M1 pilot comparison CLI (PR-E).

Runs the real script against the real sealed dataset, real frozen M1 artifact,
and real pre-registered protocol — no mocks, no synthetic fixtures. Verifies
the acceptance bar this PR closes: a reproducible M0-vs-M1 comparative result
with explicit denominators/exclusions and full provenance.
"""

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "scripts" / "run_m0_vs_m1_comparison.py"


def _run_cli(output_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--output-dir", str(output_dir)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_m0_vs_m1_comparison_cli_exits_zero_and_writes_artifacts(tmp_path: Path):
    output_dir = tmp_path / "run_a"
    result = _run_cli(output_dir)

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert (output_dir / "m0_run_report.json").is_file()
    assert (output_dir / "m1_run_report.json").is_file()
    assert (output_dir / "m0_vs_m1_comparative_report.json").is_file()


def test_m0_vs_m1_comparative_report_has_three_pre_registered_hypotheses(tmp_path: Path):
    output_dir = tmp_path / "run_a"
    _run_cli(output_dir)

    comparative = json.loads((output_dir / "m0_vs_m1_comparative_report.json").read_text())

    assert comparative["study_protocol_id"] == "NEXUS-M0-VS-M1-PILOT"
    assert comparative["study_status"] == "PILOT"
    assert set(comparative["run_ids"].keys()) == {"M0", "M1"}

    ids = [r["hypothesis_id"] for r in comparative["results"]]
    assert ids == ["H01_M0_VS_M1_NDCG10", "H02_M0_VS_M1_RECALL5", "H03_M0_VS_M1_MRR"]

    for r in comparative["results"]:
        assert r["n_paired"] + len(r["excluded_demand_ids"]) == 3  # 3 sealed demands
        assert "wilcoxon" in r and "p_value" in r["wilcoxon"]
        assert "bootstrap_ci" in r and "ci_lower" in r["bootstrap_ci"]


def test_m0_run_report_has_no_embedding_provenance_m1_does(tmp_path: Path):
    output_dir = tmp_path / "run_a"
    _run_cli(output_dir)

    m0 = json.loads((output_dir / "m0_run_report.json").read_text())
    m1 = json.loads((output_dir / "m1_run_report.json").read_text())

    assert m0["embedding_provenance"] is None
    assert m1["embedding_provenance"] is not None
    assert m1["embedding_provenance"]["artifact_id"]


def test_m0_vs_m1_comparison_cli_is_deterministic_across_runs(tmp_path: Path):
    """Clean-clone reproducibility gate (ADR 0007 style), with an EXPLICIT boundary:

    MUST be identical across independent runs (scientific result + accounting):
    dataset/policy/model-config hashes, macro metrics, paired-observation
    accounting (n_paired, excluded_demand_ids), and every statistical outcome
    (Wilcoxon p-value, BH-adjusted q-value, rejection decision).

    MUST NOT be compared for equality (execution identity, not a result):
    run_id and created_at. These are asserted to *differ* below, precisely to
    make the boundary intentional rather than an oversight — this test would
    otherwise pass by accident if a future edit made those fields deterministic
    too, silently hiding that each execution is meant to be a distinct run.
    """
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"
    _run_cli(dir_a)
    _run_cli(dir_b)

    comp_a = json.loads((dir_a / "m0_vs_m1_comparative_report.json").read_text())
    comp_b = json.loads((dir_b / "m0_vs_m1_comparative_report.json").read_text())

    for ra, rb in zip(comp_a["results"], comp_b["results"], strict=True):
        assert ra["hypothesis_id"] == rb["hypothesis_id"]
        assert ra["n_paired"] == rb["n_paired"]
        assert ra["excluded_demand_ids"] == rb["excluded_demand_ids"]
        assert ra["wilcoxon"]["p_value"] == rb["wilcoxon"]["p_value"]
        assert ra["adjusted_q_value"] == rb["adjusted_q_value"]
        assert ra["rejected"] == rb["rejected"]

    m0_a = json.loads((dir_a / "m0_run_report.json").read_text())
    m0_b = json.loads((dir_b / "m0_run_report.json").read_text())
    assert m0_a["dataset_sha256"] == m0_b["dataset_sha256"]
    assert m0_a["policy_sha256"] == m0_b["policy_sha256"]
    assert m0_a["model_config_sha256"] == m0_b["model_config_sha256"]
    assert m0_a["macro_strict"] == m0_b["macro_strict"]
    assert m0_a["macro_broad"] == m0_b["macro_broad"]
    assert m0_a["macro_denominators"] == m0_b["macro_denominators"]

    # Execution identity is NOT a scientific result: it is expected to differ,
    # and this test documents that expectation instead of silently ignoring it.
    assert m0_a["run_id"] != m0_b["run_id"]
    assert m0_a["created_at"] != m0_b["created_at"]
```

- [ ] **Step 2: Run test to verify it fails before Task 3 exists**

Run: `cd /home/valentin/code/nexus && pytest backend/test/e2e/test_m0_vs_m1_comparison_cli.py -v`
Expected (if run before Task 3's script exists): `FAIL` — script not found / nonzero exit. If Task 3 is already done, this should already pass — run it now to confirm.

- [ ] **Step 3: Run test to verify it passes**

Run: `cd /home/valentin/code/nexus && pytest backend/test/e2e/test_m0_vs_m1_comparison_cli.py -v`
Expected: `4 passed`. If `test_m0_vs_m1_comparative_report_has_three_pre_registered_hypotheses` fails on the `n_paired + excluded == 3` assertion, check whether a hypothesis has 0 valid pairs — `evaluate_study_protocol` raises `ValueError` in that case (by design, per its docstring: "Cannot test on zero pairs"), which would show up as a nonzero exit code in Step 1's assertions instead; if that happens, it is a genuine finding to report, not a test to weaken.

- [ ] **Step 4: Run the full backend suite from repo root**

Run: `cd /home/valentin/code/nexus && pytest backend/test`
Expected: all tests pass, including the pre-existing 413 plus this plan's new ones.

- [ ] **Step 5: Commit**

```bash
git add backend/test/e2e/test_m0_vs_m1_comparison_cli.py
git commit -m "$(cat <<'EOF'
Add e2e reproducibility test for the M0 vs M1 comparison CLI (PR-E)

Runs the real CLI against the real sealed dataset/artifact/protocol
(no mocks). Verifies exit code, artifact shape, embedding provenance
presence/absence, and clean-clone determinism across two independent
runs (ADR 0007-style reproducibility gate).

Co-Authored-By: Lydia Bares <lydiabares@gmail.com>
EOF
)"
```

---

## Task 5: Capture the real result and open the PR

This task has no pre-written numeric content — the whole point of PR-E is that nobody has seen this result yet. Do not draft any prose claiming an outcome before this task actually runs the script.

- [ ] **Step 1: Run the real comparison and capture output**

Run: `cd /home/valentin/code/nexus && python3 scripts/run_m0_vs_m1_comparison.py --output-dir data/experiments --environment local_benchmark | tee /tmp/pr-e-run-output.txt`

- [ ] **Step 2: Decide whether to commit the artifacts**

`data/experiments/m0_run_report.json`, `m1_run_report.json`, `m0_vs_m1_comparative_report.json` are generated artifacts, not sealed inputs — check with the user whether committing them (as the PR's evidence) or leaving them CI-generated is preferred before `git add`ing `data/experiments/`.

- [ ] **Step 3: Push the branch and open the PR**

Follow this repo's existing PR convention (see `git log` for prior PR titles/format, e.g. `#41`–`#44`). Title suggestion: `PR-E: First empirical M0 vs M1 comparison (nDCG@10 primary)`. In the PR body, quote the actual printed table from Step 1 verbatim — never restate it from memory or round trip through a paraphrase.

State this explicitly in the PR body (no code change requested for this — it is a documentation/reporting clarification the user raised before approving execution): **the sealed benchmark is 45 demand–patent pairs but only 3 independent demand queries** (3 demands × 15 patents/demand). `evaluate_study_protocol` performs paired inference at the **demand** level, not the pair level — hence `n_paired` in the comparative artifact tops out at 3, not 45. This is why the e2e test in Task 4 asserts `n_paired + len(excluded_demand_ids) == 3`. State plainly in the PR: *"45 demand–patent pairs / 3 demand queries; the unit of statistical inference is the demand, not the pair."* This avoids a future reader mistaking `n=3` for an experiment failure — it is the correct, intended unit of analysis for this pilot's design.

- [ ] **Step 4: After merge — refresh `docs/roadmap.md`**

Only after this PR is merged (per the user's explicit ordering: experiment first, roadmap refresh after), update `docs/roadmap.md` §2 ("Where things stand") and §3 (PR sequence table) to reflect: ADR 0016 implemented (not "Proposed"), PR-B/C/D/44 done, and this PR's actual `study_status: PILOT` result. This is intentionally a separate, later task — not part of this plan.

---

## Self-Review Notes

- **Spec coverage:** sealed dataset (Task 3 loads it unmodified) ✓; same `P_shared` for M0/M1 (Task 3, one `context` instance) ✓; per-demand results (existing `demand_reports`, printed and serialized as-is) ✓; nDCG@10 primary (`H01`, Task 1) ✓; Recall@5 secondary (`H02`, per the user's explicit decision) ✓; MRR secondary/pre-registered, not reinterpreted (`H03` mirrors the M0-M6 family's `H01_M1_vs_M0_MRR` wording) ✓; explicit denominators/exclusions (`macro_denominators`, `n_paired`, `excluded_demand_ids` — all pre-existing #44 fields, surfaced as-is) ✓; paired contrast M0 vs M1 (`evaluate_study_protocol`, unchanged) ✓; artifact with hashes/provenance (Task 3's three JSON files) ✓; no weight/protocol retrofitting (Global Constraints) ✓; `study_status: PILOT` (hardcoded in Task 3) ✓; temporal violations untouched (Global Constraints + docstring) ✓.
- **Placeholder scan:** none found — every step has runnable code or an exact shell command.
- **Type consistency:** `serialize_comparative_report` (Task 2) is imported by name in Task 3's script exactly as defined; `StudyProtocol`, `EvaluationRunReport`, `FrozenEmbeddingArtifact`, `ModelConfigurationManifest`, `MatchingPolicyConfig`, `DefaultMatchingAdapter`, `DefaultEvaluationRunner`, `DefaultMatchingEngine`, `evaluate_study_protocol` are all used with their real, already-verified signatures from the codebase (confirmed by reading `matching_adapter.py`, `comparative.py`, `run_scientific_evaluation.py`, and `evaluation.py` directly before writing this plan) — none invented.

### Preflight verification (three corrections applied before execution)

1. **`protocol_sha256` is never hand-typed.** Task 1 Step 1 now generates the JSON via a script that computes the hash from the actual serialized payload; Task 1's test independently recomputes it from the written file and is the real authority. No hash appears anywhere in this plan as a literal to trust on faith.
2. **`EvaluationRunReport` provenance completeness verified directly against `domain/models/evaluation.py` (lines 277–306):** it natively carries `dataset_sha256`, `policy_sha256`, and the full `EvaluationExecutionContext` (`engine_name`, `engine_version`, `engine_commit_hash`, `execution_timestamp`, `environment` — confirmed by dumping a real instance). It does **not** carry the frozen model-configuration manifest's own hash (`ModelConfigurationManifest.config_sha256`, ADR 0012 — confirmed absent from the field list). Task 3 was corrected to add `model_config_sha256` explicitly to both run artifacts so the "full provenance" claim is actually true, not assumed.
3. **Temporal-violation behavior verified against the real runner, not assumed from #43's doc:** `DefaultMatchingEngine.evaluate` (`application/matching/engine.py`) sorts `assessments.sort(key=lambda a: (-a.overall_score, a.publication_id))`, and `DefaultEvidenceEvaluator.evaluate_candidate` sets `overall_score = 0.0` / `sufficiency = INELIGIBLE_TEMPORAL` whenever `features.temporal_valid` is `False`. `features.temporal_valid` is computed in `application/matching/feature_extractor.py` from the demand/publication date delta, gated on `policy.sufficiency_rules.require_temporal_validity` — confirmed `true` in the actual `config/policies/matching/default_matching_policy.json` this script loads. So the 3 known temporal-violation pairs are confirmed, against the real code path this plan invokes, to sink to the bottom of the ranking with `overall_score=0.0`, exactly as #43 described and without any dataset edit.
4. **Task 4's determinism test boundary made explicit, not implicit:** it already excluded `run_id`/timestamp from equality checks before this correction; it now additionally asserts `model_config_sha256` equality (closing gap #2) and asserts `run_id`/`created_at` *differ* between the two runs — turning "we didn't check execution identity" into "we deliberately assert execution identity is not a scientific result."
