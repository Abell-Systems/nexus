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
from application.evaluation.runner import DefaultEvaluationRunner, validate_temporal_pool_mode_consistency
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
    policy_sha256, and the complete EvaluationExecutionContext as native
    fields. It does NOT carry the frozen model-configuration manifest's own
    hash (ADR 0012's config_sha256, which pins M0's BM25 k1/b) — that is a
    separate provenance-controlled document, so it is added explicitly here.
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


def _build_comparative_provenance(
    report_m0: EvaluationRunReport,
    report_m1: EvaluationRunReport,
    model_config_sha256: str,
) -> dict:
    """Machine-checkable P_shared linkage for the comparative artifact (code review, PR #51).

    ComparativeRunReport only carries study_protocol_id/sha256 and the two run_ids —
    a consumer would otherwise have to dereference both individual run reports to
    confirm this was actually a like-for-like comparison (same dataset, policy,
    engine commit, temporal_pool_mode). This asserts that identity explicitly
    rather than merely assuming it, and surfaces it directly on the comparative
    artifact so it never needs re-deriving.
    """
    shared_fields = [
        ("dataset_id", report_m0.dataset_id, report_m1.dataset_id),
        ("dataset_sha256", report_m0.dataset_sha256, report_m1.dataset_sha256),
        ("policy_id", report_m0.policy_id, report_m1.policy_id),
        ("policy_sha256", report_m0.policy_sha256, report_m1.policy_sha256),
        ("engine_commit_hash", report_m0.context.engine_commit_hash, report_m1.context.engine_commit_hash),
        ("temporal_pool_mode", report_m0.context.temporal_pool_mode, report_m1.context.temporal_pool_mode),
        ("execution_timestamp", report_m0.context.execution_timestamp, report_m1.context.execution_timestamp),
    ]
    for name, v0, v1 in shared_fields:
        if v0 != v1:
            raise ValueError(
                f"M0 and M1 run reports disagree on '{name}' ({v0!r} vs {v1!r}) — "
                "this comparative artifact requires a like-for-like P_shared run, "
                "not two independently-configured evaluations."
            )

    return {
        "dataset_id": report_m0.dataset_id,
        "dataset_sha256": report_m0.dataset_sha256,
        "policy_id": report_m0.policy_id,
        "policy_sha256": report_m0.policy_sha256,
        "model_config_sha256": model_config_sha256,
        "engine_commit_hash": report_m0.context.engine_commit_hash,
        # Match pydantic's own JSON datetime format ("Z" suffix) exactly, so this
        # string is byte-comparable with EvaluationExecutionContext's serialized form.
        "execution_timestamp": report_m0.context.execution_timestamp.isoformat().replace("+00:00", "Z"),
        "temporal_pool_mode": report_m0.context.temporal_pool_mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the first M0 vs M1 pilot comparison (PR-E)")
    parser.add_argument("--dataset", type=Path, default=repo_root / "experiments" / "shared" / "dataset_pilot_benchmark.json")
    parser.add_argument("--checksum", type=Path, default=repo_root / "experiments" / "shared" / "dataset_pilot_benchmark.sha256")
    parser.add_argument("--manifest", type=Path, default=repo_root / "experiments" / "shared" / "dataset_pilot_benchmark.manifest.json")
    parser.add_argument("--policy", type=Path, default=repo_root / "config" / "policies" / "matching" / "default_matching_policy.json")
    parser.add_argument("--model-config", type=Path, dest="model_config", default=repo_root / "config" / "evaluations" / "model_configurations_m0_m6.json")
    parser.add_argument("--embeddings", type=Path, default=repo_root / "experiments" / "shared" / "embeddings_pilot_benchmark.json")
    parser.add_argument("--protocol", type=Path, default=repo_root / "config" / "evaluations" / "comparisons_m0_vs_m1_pilot.json")
    parser.add_argument("--output-dir", type=Path, dest="output_dir", default=repo_root / "data" / "experiments")
    parser.add_argument("--environment", type=str, default="local_benchmark")
    parser.add_argument("--engine-commit", type=str, dest="engine_commit", default=None)
    parser.add_argument(
        "--temporal-pool-mode",
        type=str,
        choices=["strict", "unconstrained"],
        required=True,
        dest="temporal_pool_mode",
        help=(
            "ADR 0018: mandatory, no default. The historical PR-E result (#45, "
            "data/experiments/m0_vs_m1_comparative_report.json) was produced before "
            "this contract existed, under what ADR 0018 retroactively identifies as "
            "the contaminated unconstrained+require_temporal_validity=True condition — "
            "that artifact is frozen, historical, and NOT reproduced bit-for-bit by "
            "this flag. A live run must declare a contract-valid combination: 'strict' "
            "works with the current default policy as-is; 'unconstrained' requires a "
            "policy with require_temporal_validity=false or this script fails fast."
        ),
    )
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

    # ADR 0018 §2: fail fast on the one invalid temporal_pool_mode/policy
    # combination before either run executes.
    validate_temporal_pool_mode_consistency(
        temporal_pool_mode=args.temporal_pool_mode,
        require_temporal_validity=policy.sufficiency_rules.require_temporal_validity,
    )

    commit_hash = _resolve_commit_hash(args.engine_commit, repo_root)
    # Same context instance for both runs: same commit, same timestamp, same
    # environment — the P_shared the two runs must share to be comparable.
    context = EvaluationExecutionContext(
        engine_name="DefaultMatchingEngine",
        engine_version="0.2.0",
        engine_commit_hash=commit_hash,
        execution_timestamp=datetime.now(UTC),
        environment=args.environment,
        temporal_pool_mode=args.temporal_pool_mode,
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
    comparative_dict = serialize_comparative_report(comparative)
    comparative_dict["provenance"] = _build_comparative_provenance(
        report_m0, report_m1, model_config.config_sha256
    )
    (args.output_dir / "m0_vs_m1_comparative_report.json").write_text(
        json.dumps(comparative_dict, indent=2), encoding="utf-8"
    )
    print(f"\nArtifacts written to: {args.output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
