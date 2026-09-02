#!/usr/bin/env python3
"""Run the empirical experiment: Spanish Innoget Demand vs. Spanish ES Patents.

Executes deterministic quantitative alignment & white-space metrics with cryptographic
dataset verification, and triggers multi-agent candidate synthesis via Groq API.
"""

import os
import sys
import json
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.patent_agent.tools.innoget_datasource import InnogetDemandDataSource
from backend.patent_agent.tools.duckdb_patents import DuckDbPatentsDataSource
from backend.patent_agent.tools.metrics import compute_white_space_metrics, ExecutionMode
from backend.patent_agent.groq_client import GroqLlmClient
from backend.patent_agent.synthesis_engine import InventionSynthesisEngine
from backend.patent_agent.tools.schemas import InventionCandidate, AdversarialVerdict, ScoreCard


def verify_dataset_manifest(
    manifest_path: str = "data/snapshots/patents_es_manifest.json"
) -> dict:
    """Verify cryptographic hash and provenance of the frozen patent dataset."""
    p_man = Path(manifest_path)
    if not p_man.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}. Run scripts/ingest_oepm_ops.py first.")

    with open(p_man, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    parquet_file = Path(manifest["provenance"]["parquet_file"])
    if not parquet_file.exists():
        raise FileNotFoundError(f"Underlying parquet dataset missing at {parquet_file}")

    # Compute SHA-256
    hasher = hashlib.sha256()
    with open(parquet_file, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    actual_hash = hasher.hexdigest()

    expected_hash = manifest.get("sha256_hash", "")
    if actual_hash != expected_hash:
        raise ValueError(
            f"Dataset integrity mismatch!\nExpected SHA-256: {expected_hash}\nActual SHA-256:   {actual_hash}"
        )

    return manifest


def run_experiment(
    mode: ExecutionMode = ExecutionMode.EMPIRICAL,
    db_path: str = "data/snapshots/patents_es_snapshot.duckdb",
    manifest_path: str = "data/snapshots/patents_es_manifest.json",
    output_dir: str = "data/experiments/latest",
    dry_run_llm: bool = False,
):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Dataset Verification & Ingestion
    if mode == ExecutionMode.EMPIRICAL:
        manifest = verify_dataset_manifest(manifest_path)
        dataset_status = f"EMPIRICAL (VERIFIED - SHA256: {manifest['sha256_hash'][:12]}...)"
    else:
        manifest = {"sha256_hash": "unverified-fixture-run", "total_records": "N/A"}
        dataset_status = f"{mode.upper()} (SYNTHETIC / TEST FIXTURE - NOT FOR PUBLICATION)"

    demand_ds = InnogetDemandDataSource()
    spanish_demands = demand_ds.get_spanish_demands()
    patent_ds = DuckDbPatentsDataSource(db_path=db_path)

    # Group demands by mapped CPC subclass prefix
    cpc_demands: dict[str, list] = {}
    for d in spanish_demands:
        cpc_demands.setdefault(d.cpc_prefix, []).append(d)

    all_clusters = sorted(list(set(
        list(cpc_demands.keys()) + ["C11D", "E03C", "G05B", "C22C", "H01M", "C08L"]
    )))

    # Fetch domestic patents across all clusters without premature selection bias
    cluster_patents: dict[str, list] = {}
    for c in all_clusters:
        cluster_patents[c] = patent_ds.search_patents(c, limit=1000)

    max_patents = max(len(p) for p in cluster_patents.values()) if cluster_patents else 1
    max_demands = max(len(d) for d in cpc_demands.values()) if cpc_demands else 1

    # 2. Compute Deterministic Quantitative Metrics (Zero LLM Dependency)
    metrics_list = []
    for c in all_clusters:
        pats = cluster_patents.get(c, [])
        dems = cpc_demands.get(c, [])
        m = compute_white_space_metrics(
            cluster_id=c,
            patents=pats,
            demand_signals=dems,
            max_patents=max_patents,
            max_demands=max_demands,
            ref_year=2026,
        )
        metrics_list.append(m)

    # 3. Export Alignment Matrix CSV
    csv_file = out / "demand_patent_alignment_matrix.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics_list[0].keys()))
        writer.writeheader()
        writer.writerows(metrics_list)

    # 4. Multi-Agent Candidate Synthesis & Adversarial Prior-Art Defense (Groq Layer)
    case_studies = []
    white_space_clusters = [m for m in metrics_list if m["is_white_space"]]

    has_groq_key = bool(os.getenv("GROQ_API_KEY")) and os.getenv("GROQ_API_KEY") != "mock_key"
    can_run_live_llm = (not dry_run_llm) and has_groq_key

    if can_run_live_llm:
        try:
            client = GroqLlmClient()
            engine = InventionSynthesisEngine(client=client)
            synthesis_status = "EMPIRICAL (LIVE GROQ SYNTHESIS & ADVERSARIAL VERDICT)"
        except Exception as e:
            engine = None
            synthesis_status = f"DRY-RUN (GROQ CLIENT ERROR: {e})"
    else:
        engine = None
        synthesis_status = "SYNTHETIC DRY-RUN (AWAITING LIVE GROQ API KEY)"

    # Prioritize top white-space clusters (or default clusters if none pass threshold)
    target_clusters = white_space_clusters if white_space_clusters else metrics_list[:2]

    for m in target_clusters[:2]:
        c_id = m["cluster_id"]
        dems = cpc_demands.get(c_id, [])
        pats = cluster_patents.get(c_id, [])
        primary_demand = dems[0] if dems else spanish_demands[0]
        ref_pub = pats[0].publication_number if pats else "ES-2849102-B2"

        if not engine:
            # Deterministic structural mock strictly labeled
            cand = InventionCandidate(
                id=f"INV-{c_id}-001-SYNTHETIC",
                cluster_id=c_id,
                title=f"[DRY-RUN] Candidate Invention for {c_id}",
                description="Cold-water active surfactant system with biocompatible microencapsulation.",
                novelty_claim="Activation temperature window under 20C with zero phosphorus release.",
            )
            verd = AdversarialVerdict(
                verdict="survives",
                rationale=f"Differentiates from cited domestic prior art {ref_pub} in room temperature kinetic activation.",
                cited_patents=[ref_pub],
            )
            score = ScoreCard(
                novelty=0.88,
                prior_art_risk=0.80,
                differentiation=0.85,
                evidence=0.92,
                supporting_evidence=[ref_pub],
            )
        else:
            cand, verd, score = engine.run_loop(c_id, primary_demand, pats)

        case_studies.append({
            "cluster_id": c_id,
            "evidence_tier": "empirical" if engine else "synthetic_dry_run",
            "demand": primary_demand.model_dump(),
            "candidate": cand.model_dump(),
            "verdict": verd.model_dump(),
            "scorecard": score.model_dump(),
        })

    # 5. Metadata and Markdown Publication Summary
    meta = {
        "timestamp": datetime.now().isoformat(),
        "execution_mode": mode.value,
        "dataset_status": dataset_status,
        "synthesis_status": synthesis_status,
        "dataset_sha256": manifest.get("sha256_hash"),
        "total_spanish_demands": len(spanish_demands),
        "total_clusters_analyzed": len(all_clusters),
        "white_space_clusters_found": len(white_space_clusters),
        "database_path": db_path,
    }
    with open(out / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    with open(out / "case_studies.json", "w", encoding="utf-8") as f:
        json.dump(case_studies, f, indent=2)

    # Render LaTeX/Markdown Table
    banner = (
        f"> **[SCIENTIFIC EVIDENCE AUDIT TRAIL]**\n"
        f"> - **Dataset Status:** `{dataset_status}`\n"
        f"> - **Synthesis Engine:** `{synthesis_status}`\n"
        f"> - **Dataset SHA-256:** `{manifest.get('sha256_hash')}`\n"
    )

    md_summary = [
        "# Empirical Results: Spanish Innoget Demand vs. Spanish ES Patents\n",
        banner,
        f"**Generated:** {meta['timestamp']} | **Execution Mode:** `{mode.value}`\n",
        "| Cluster (CPC) | Patents ($n_i$) | Demands ($m_i$) | Density ($d_i$) | Recency ($r_i$) | Traction ($T_i$) | Demand ($q_i$) | White Space ($W_i$) | Quadrant |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for m in metrics_list:
        md_summary.append(
            f"| `{m['cluster_id']}` | {m['patent_count']} | {m['demand_count']} | {m['density']:.2f} | {m['recency']:.2f} | {m['citation_traction']:.2f} | {m['demand_intensity']:.2f} | **{m['white_space_score']:.2f}** | {m['quadrant']} |"
        )

    md_summary.append("\n## Multi-Agent Qualitative Case Studies\n")
    for cs in case_studies:
        md_summary.append(
            f"### Case Study: Cluster `{cs['cluster_id']}` ({cs['evidence_tier'].upper()})\n"
            f"- **Industrial Demand:** {cs['demand']['title']}\n"
            f"- **Synthesized Invention:** **{cs['candidate']['title']}**\n"
            f"- **Claimed Novelty:** {cs['candidate']['novelty_claim']}\n"
            f"- **Adversarial Verdict:** `{cs['verdict']['verdict'].upper()}` — *{cs['verdict']['rationale']}*\n"
            f"- **Cited Prior Art:** `{', '.join(cs['verdict']['cited_patents'])}`\n"
            f"- **ScoreCard:** Novelty: `{cs['scorecard']['novelty']:.2f}`, Risk: `{cs['scorecard']['prior_art_risk']:.2f}`, Evidence: `{cs['scorecard']['evidence']:.2f}`\n"
        )

    md_text = "\n".join(md_summary)
    with open(out / "paper_results_summary.md", "w", encoding="utf-8") as f:
        f.write(md_text)

    print(md_text)
    return metrics_list, case_studies


if __name__ == "__main__":
    run_experiment(mode=ExecutionMode.EMPIRICAL)
