#!/usr/bin/env python3
"""CLI Bootstrap for Scientific Evaluation under ADR 0006 and ADR 0007.

Invariants:
- CLI bootstrap handles all filesystem, argument resolution, and environment discovery.
- EvaluationRunner executes in-memory without filesystem access.
- Mandatory explicit paths for dataset, checksum, manifest, and matching policy.
- Zero tuning or multi-policy search: executes a single sealed evaluation run.
- Prints honest, unedited scientific report and optionally writes JSON artifact.
- Git provenance is mandatory: either auto-discovered or explicitly provided via --engine-commit.
  Fallback placeholder hashes (e.g. "0000000") are strictly prohibited.
"""

import argparse
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Ensure backend/src/main is in python path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "backend" / "src" / "main"))

from application.evaluation.matching_adapter import DefaultMatchingAdapter
from application.evaluation.runner import DefaultEvaluationRunner
from application.matching.engine import DefaultMatchingEngine
from domain.models.evaluation import (
    EvaluationExecutionContext,
    FrozenEmbeddingArtifact,
    ModelConfigurationManifest,
)
from domain.models.matching import MatchingPolicyConfig
from infrastructure.evaluation.dataset_loader import DefaultEvaluationDatasetLoader

_COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _get_git_commit(cwd: Path) -> str | None:
    """Discovers current git commit hash in the CLI bootstrap layer.

    Returns the full commit hash on success, or None if git is unavailable.
    """
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return res.stdout.strip()
    except Exception:
        return None


def _resolve_commit_hash(engine_commit_arg: str | None, cwd: Path) -> str:
    """Resolves the engine commit hash for provenance stamping.

    Priority:
    1. --engine-commit argument (validated strictly against hex regex).
    2. Auto-discovery via git rev-parse HEAD.

    Raises:
        ValueError: if --engine-commit is provided but fails hex validation.
        RuntimeError: if git discovery fails and --engine-commit is absent.
    """
    if engine_commit_arg is not None:
        if not _COMMIT_HASH_RE.match(engine_commit_arg):
            raise ValueError(
                f"Invalid --engine-commit '{engine_commit_arg}': "
                f"must be 7-40 hexadecimal characters (same contract as EvaluationExecutionContext)."
            )
        return engine_commit_arg

    discovered = _get_git_commit(cwd)
    if discovered is None:
        raise RuntimeError(
            "Unable to discover git commit hash: 'git rev-parse HEAD' failed. "
            "Either run inside a git repository or pass --engine-commit <hash> explicitly. "
            "Placeholder hashes are prohibited — provenance must be exact."
        )
    return discovered


def main() -> int:
    parser = argparse.ArgumentParser(description="Run scientific matching evaluation benchmark")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.json",
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument(
        "--checksum",
        type=Path,
        default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.sha256",
        help="Path to dataset .sha256 file",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.manifest.json",
        help="Path to dataset .manifest.json file",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=repo_root / "config" / "policies" / "matching" / "default_matching_policy.json",
        help="Path to matching policy JSON",
    )
    parser.add_argument(
        "--model-config",
        type=Path,
        default=repo_root / "config" / "evaluations" / "model_configurations_m0_m6.json",
        dest="model_config",
        help="Path to frozen model configuration manifest JSON (ADR 0012)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to save serialized EvaluationRunReport JSON",
    )
    parser.add_argument(
        "--embeddings",
        type=Path,
        default=None,
        help=(
            "Optional path to the frozen M1 embedding artifact JSON (ADR 0014). "
            "When omitted the run is M0-only (lexical + CPC); when supplied the artifact "
            "is hash-verified, source-dataset-verified against the loaded dataset, and wired "
            "into the adapter as raw-cosine semantic scores. Nothing is ever generated or "
            "modified in place — the artifact file is read-only input."
        ),
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="local_benchmark",
        help="Execution environment tag (e.g. ci, local_benchmark)",
    )
    parser.add_argument(
        "--engine-commit",
        type=str,
        default=None,
        dest="engine_commit",
        help=(
            "Explicit engine git commit hash (7-40 hex chars). "
            "Use when running outside a git repo or to pin a specific commit for reproducibility. "
            "If omitted, auto-discovered from 'git rev-parse HEAD'. "
            "Placeholder hashes are prohibited — evaluation will fail fast if provenance cannot be resolved."
        ),
    )

    args = parser.parse_args()

    print("================================================================================")
    print("Nexus Matching Engine — Scientific Evaluation Benchmark (ADR 0006 / ADR 0007)")
    print("================================================================================")
    print(f"Loading dataset from:  {args.dataset}")
    print(f"Verifying checksum:    {args.checksum}")
    print(f"Verifying manifest:    {args.manifest}")
    print(f"Loading policy from:   {args.policy}")

    # 1. Load and cryptographically verify dataset
    loader = DefaultEvaluationDatasetLoader()
    validated_dataset = loader.load_validated_dataset(
        dataset_path=args.dataset,
        checksum_path=args.checksum,
        manifest_path=args.manifest,
    )
    print(f"✓ Dataset verified:    {validated_dataset.dataset.dataset_id} (SHA: {validated_dataset.manifest.content_sha256[:12]}...)")
    print(f"  Demands: {len(validated_dataset.dataset.demands)}, "
          f"Patents: {len(validated_dataset.dataset.patents)}, "
          f"Annotations: {len(validated_dataset.dataset.annotations)}")

    # 2. Load matching policy
    policy = MatchingPolicyConfig.load_from_json(args.policy)
    print(f"✓ Policy verified:     {policy.policy_id} v{policy.policy_version} (SHA: {policy.policy_sha256[:12]}...)")

    # 2b. Load frozen model configuration manifest and verify it still matches the policy in
    # use (ADR 0012 §5) — the manifest, not any implementation default, controls M0's BM25
    # parameters (ADR 0013 enforcement: see matching_adapter.py's mandatory constructor args).
    model_config = ModelConfigurationManifest.load_from_json(args.model_config)
    model_config.verify_source_policy(policy)
    m0_config = next(m for m in model_config.models if m.model_id == "M0")
    if m0_config.weights is None:
        raise ValueError(
            f"Model configuration manifest '{args.model_config}' declares no weights for M0 — "
            "BM25 k1/b must be recorded there before evaluation can run."
        )
    bm25_k1 = m0_config.weights["k1"]
    bm25_b = m0_config.weights["b"]
    print(f"✓ Model config verified: M0 k1={bm25_k1}, b={bm25_b} (SHA: {model_config.config_sha256[:12]}...)")

    # 3. Resolve exact commit hash for provenance — fails fast if unavailable (ADR 0007 §5)
    commit_hash = _resolve_commit_hash(args.engine_commit, repo_root)
    context = EvaluationExecutionContext(
        engine_name="DefaultMatchingEngine",
        engine_version="0.2.0",
        engine_commit_hash=commit_hash,
        execution_timestamp=datetime.now(UTC),
        environment=args.environment,
    )
    print(f"✓ Execution Context:   Engine commit {commit_hash[:7]} at {context.execution_timestamp.isoformat()}")

    # 4. Instantiate engine and adapter in CLI layer (the appropriate place for concrete wiring)
    # DefaultMatchingAdapter is the single adapter between evaluation-domain and matching-domain types.
    # Optional M1 wiring (ADR 0014): the artifact is loaded, hash-verified, and bound to the
    # already-validated dataset here — never inside the runner, never generated, never edited.
    semantic_artifact: FrozenEmbeddingArtifact | None = None
    if args.embeddings is not None:
        semantic_artifact = FrozenEmbeddingArtifact.load_from_json(args.embeddings)
        semantic_artifact.verify_source_dataset(validated_dataset)
        print(
            f"✓ Embeddings wired:  {semantic_artifact.artifact_id} "
            f"({semantic_artifact.model_name}@{semantic_artifact.model_revision[:12]}, "
            f"dim={semantic_artifact.embedding_dimension}, "
            f"SHA: {semantic_artifact.artifact_sha256[:12]}...)"
        )
    else:
        print("○ Embeddings:        M0-only mode (no semantic artifact supplied)")
    engine = DefaultMatchingEngine()
    ranking_port = DefaultMatchingAdapter(
        engine=engine,
        policy=policy,
        bm25_k1=bm25_k1,
        bm25_b=bm25_b,
        semantic_artifact=semantic_artifact,
    )

    # 5. Execute evaluation via in-memory runner
    # The runner receives only the EvaluationRankingPort — it never sees CandidatePool or MatchingPolicyConfig.
    runner = DefaultEvaluationRunner()
    print("\nRunning evaluation across closed candidate universe...")
    report = runner.run_evaluation(
        dataset=validated_dataset,
        ranking_port=ranking_port,
        policy=policy,
        context=context,
    )

    # 6. Display Honest Scientific Report
    def _fmt(value: float | None) -> str:
        return f"{value:.2f}" if value is not None else "n/a"

    print("\n================================================================================")
    print(f"EVALUATION REPORT: {report.run_id}")
    print("================================================================================")
    print(f"Dataset SHA-256:       {report.dataset_sha256}")
    print(f"Policy SHA-256:        {report.policy_sha256}")
    print(f"Engine Commit:         {report.context.engine_commit_hash}")
    print(f"Uncertainty Rate:      {report.uncertainty_rate:.2%}")
    print("--------------------------------------------------------------------------------")
    print(f"{'Demand ID':<16} {'Cand':<5} {'Judged':<7} {'P@1 (S)':<8} {'P@3 (S)':<8} {'R@3 (S)':<8} {'MRR (S)':<8} {'nDCG@5':<8} {'nDCG@10':<8}")
    print("--------------------------------------------------------------------------------")

    for d_rep in report.demand_reports:
        s = d_rep.strict_metrics
        print(
            f"{d_rep.demand_id:<16} "
            f"{d_rep.candidate_count:<5} "
            f"{d_rep.judged_count:<7} "
            f"{s.precision_at_1:<8.2f} "
            f"{s.precision_at_3:<8.2f} "
            f"{_fmt(s.recall_at_3):<8} "
            f"{s.mrr:<8.2f} "
            f"{_fmt(s.ndcg_at_5):<8} "
            f"{_fmt(s.ndcg_at_10):<8}"
        )

    print("--------------------------------------------------------------------------------")
    ms = report.macro_strict
    mb = report.macro_broad
    n_demands = len(report.demand_reports)
    print("MACRO-AVERAGES (undefined per-demand values excluded, never imputed):")
    print(
        "  Valid queries: nDCG@10 over "
        f"{report.macro_denominators.get('strict.ndcg_at_10', 0)}/{n_demands} demands (strict), "
        f"{report.macro_denominators.get('broad.ndcg_at_10', 0)}/{n_demands} (broad)"
    )
    print("  Strict Alignment (Grade 3):")
    print(f"    Precision: P@1 = {ms.precision_at_1:.2f}, P@3 = {ms.precision_at_3:.2f}, P@5 = {ms.precision_at_5:.2f}")
    print(f"    Recall:    R@1 = {_fmt(ms.recall_at_1)}, R@3 = {_fmt(ms.recall_at_3)}, R@5 = {_fmt(ms.recall_at_5)}")
    print(
        f"    Ranking:   MRR = {ms.mrr:.2f}, MRR@5 = {ms.mrr_at_5:.2f}, "
        f"nDCG@5 = {_fmt(ms.ndcg_at_5)}, nDCG@10 = {_fmt(ms.ndcg_at_10)}"
    )
    print(f"    Coverage:  Judged@1 = {ms.judged_at_1:.2f}, Judged@3 = {ms.judged_at_3:.2f}, Judged@5 = {ms.judged_at_5:.2f}")
    print("  Broad Alignment (Grades 2 & 3):")
    print(f"    Precision: P@1 = {mb.precision_at_1:.2f}, P@3 = {mb.precision_at_3:.2f}, P@5 = {mb.precision_at_5:.2f}")
    print(f"    Recall:    R@1 = {_fmt(mb.recall_at_1)}, R@3 = {_fmt(mb.recall_at_3)}, R@5 = {_fmt(mb.recall_at_5)}")
    print(
        f"    Ranking:   MRR = {mb.mrr:.2f}, MRR@5 = {mb.mrr_at_5:.2f}, "
        f"nDCG@5 = {_fmt(mb.ndcg_at_5)}, nDCG@10 = {_fmt(mb.ndcg_at_10)}"
    )
    print("================================================================================")

    if args.output is not None:
        import json as _json
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report_dict = _json.loads(report.model_dump_json(indent=2))
        # ADR 0011: every output must declare study_status and reference the study protocol
        report_dict["study_status"] = "PILOT"
        report_dict["study_protocol_id"] = "NEXUS-PHASE2-ABLATION-M0-M6"
        # M1 provenance: which frozen artifact (if any) fed the semantic scores
        if semantic_artifact is not None:
            report_dict["embedding_provenance"] = {
                "artifact_id": semantic_artifact.artifact_id,
                "artifact_sha256": semantic_artifact.artifact_sha256,
                "dataset_sha256": semantic_artifact.dataset_sha256,
                "model_name": semantic_artifact.model_name,
                "model_revision": semantic_artifact.model_revision,
                "embedding_dimension": semantic_artifact.embedding_dimension,
                "generation_device": semantic_artifact.generation_device,
            }
        else:
            report_dict["embedding_provenance"] = None
        args.output.write_text(_json.dumps(report_dict, indent=2), encoding="utf-8")
        print(f"Report JSON saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
