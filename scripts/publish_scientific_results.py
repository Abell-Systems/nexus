#!/usr/bin/env python3
"""Publishes a real scientific_results.json snapshot from an actual Head A landscape
execution (ADR 0025).

Runs the same real, deterministic pipeline `GET /api/landscape` uses
(`get_patents_datasource()` / `get_demand_datasource()` -> `compute_cluster_landscape`,
`application.landscape.clustering`/`metrics`) directly — no LLM/ADK invocation, no
Gemini call, no network access. This script does NOT synthesize candidate inventions,
adversarial verdicts, or scorecards: those come from Head A's inventor/adversarial/
governor ADK agent graph, which requires a live Gemini call this environment has no
credentials configured for (see the module-level note in PR history — MODEL_KEY is
unset). Publishing them here would mean either making a live LLM call from a
publication script (a live-backend/API coupling this script must not have) or
fabricating output, and both are excluded. Only the landscape/clustering sub-pipeline
of Head A is real and reproducible without an LLM, so that is exactly, and only, what
this script publishes.

Track is always `discovery` (Head A). `dataset_id`/`dataset_version`/`policy_id`/
`policy_version`/`policy_sha256`/`engine_commit` are deliberately left unset on the
published `ScientificResultsExecution`: Head A has no durable, versioned dataset or
policy identity today (ADR 0017 §7), and inventing one would misrepresent this
execution as reproducible/versioned when it is not. The contract (PR #71) already
treats these fields as optional for exactly this reason.

The default patents/demand datasources this script uses
(`infrastructure.sources.bigquery_patents.get_patents_datasource()`,
`infrastructure.sources.demand_sources.get_demand_datasource()`) are, in this
environment, the same fixture-backed `MockPatentsDataSource`/`MockDemandDataSource`
Nexus's own `GET /api/landscape` endpoint falls back to by default — not live
BigQuery. `datasource_status()` below reports exactly which implementation ran, and
this script prints it, so that fact is never hidden.

Publishing is exclusively via `infrastructure.storage.scientific_results_publisher.
publish_scientific_results` (PR #73) — this script performs no other write to disk.
"""

import argparse
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Ensure backend/src/main is in python path (mirrors scripts/run_scientific_evaluation.py)
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "backend" / "src" / "main"))

from application.landscape.clustering import compute_cluster_landscape  # noqa: E402
from domain.models.scientific_results import (  # noqa: E402
    DiscoveryLandscapeRecord,
    ScientificResultsDocument,
    ScientificResultsExecution,
    TechnologyClusterObservation,
    Track,
)
from infrastructure.sources.bigquery_patents import get_patents_datasource  # noqa: E402
from infrastructure.sources.demand_sources import get_demand_datasource  # noqa: E402
from infrastructure.storage.scientific_results_publisher import publish_scientific_results  # noqa: E402

SCHEMA_VERSION = "0.1.0"


def datasource_status(patents_datasource: Any, demand_datasource: Any) -> dict[str, Any]:
    """Reports which concrete datasource implementations actually ran — never hidden."""
    return {
        "patents_datasource": (
            patents_datasource.get_status() if hasattr(patents_datasource, "get_status") else type(patents_datasource).__name__
        ),
        "demand_datasource": type(demand_datasource).__name__,
    }


def run_landscape_execution(
    domain: str,
    query: str,
    max_patents: int,
    execution_id: str,
    created_at: datetime,
) -> tuple[ScientificResultsExecution, DiscoveryLandscapeRecord, dict[str, Any]]:
    """Runs the real Head A landscape sub-pipeline once and wraps its output.

    No scientific computation happens here beyond what `compute_cluster_landscape`
    (application.landscape.clustering, already real, already tested) itself performs —
    this function only calls the same real datasources the live API uses and shapes
    their real output into the scientific-results contract.
    """
    patents_datasource = get_patents_datasource()
    demand_datasource = get_demand_datasource()

    patents = patents_datasource.search_patents(query=query, domain=domain, limit=max_patents)
    demands = demand_datasource.search_demand(query=query, domain=domain)

    execution = ScientificResultsExecution(
        execution_id=execution_id,
        track=Track.DISCOVERY,
        domain=domain,
        query=query,
        created_at=created_at,
        # dataset_id/dataset_version/policy_*/engine_commit intentionally omitted —
        # see module docstring. Not fabricated.
    )

    cluster_observations = tuple(
        TechnologyClusterObservation(
            cluster=cluster,
            density=metrics["density"],
            recency=metrics["recency"],
            citation_traction=metrics["citation_traction"],
            citation_coverage=metrics["citation_coverage"],
            demand_intensity=metrics["demand_intensity"],
            quadrant=metrics["quadrant"],
            mean_age_years=metrics["mean_age_years"],
        )
        for cluster, metrics in compute_cluster_landscape(patents=patents, demand_signals=demands, domain=domain)
    )

    landscape = DiscoveryLandscapeRecord(
        execution_id=execution_id,
        query=query,
        clusters=cluster_observations,
    )

    return execution, landscape, datasource_status(patents_datasource, demand_datasource)


def build_document(
    domain: str,
    query: str,
    max_patents: int,
    generated_at: datetime,
    execution_id: str | None = None,
) -> tuple[ScientificResultsDocument, dict[str, Any]]:
    resolved_execution_id = execution_id or uuid.uuid4().hex
    execution, landscape, status = run_landscape_execution(
        domain=domain,
        query=query,
        max_patents=max_patents,
        execution_id=resolved_execution_id,
        created_at=generated_at,
    )
    document = ScientificResultsDocument(
        schema_version=SCHEMA_VERSION,
        generated_at=generated_at,
        executions=(execution,),
        landscapes=(landscape,),
    )
    return document, status


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a real scientific_results.json Head A landscape snapshot")
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument("--output", type=Path, default=None, help="Target path (default: <repo-root>/scientific_results.json)")
    parser.add_argument("--domain", type=str, default="solid_state_battery")
    parser.add_argument("--query", type=str, default="solid electrolyte")
    parser.add_argument("--max-patents", type=int, default=20)
    parser.add_argument("--execution-id", type=str, default=None, help="Override the generated execution_id")
    parser.add_argument("--no-write", action="store_true", help="Build and validate only, do not publish")
    args = parser.parse_args()

    resolved_repo_root = args.repo_root.resolve()
    target = args.output or (resolved_repo_root / "scientific_results.json")
    generated_at = datetime.now(UTC)

    document, status = build_document(
        domain=args.domain,
        query=args.query,
        max_patents=args.max_patents,
        generated_at=generated_at,
        execution_id=args.execution_id,
    )

    print(f"Datasource status: {status}")
    print(f"Execution: {document.executions[0].execution_id} (track={document.executions[0].track})")
    print(f"Clusters: {len(document.landscapes[0].clusters)}")

    if not args.no_write:
        published_path = publish_scientific_results(document, target)
        rel = published_path.relative_to(resolved_repo_root) if published_path.is_relative_to(resolved_repo_root) else published_path
        print(f"Published: {rel}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
