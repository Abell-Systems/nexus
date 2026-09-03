#!/usr/bin/env python3
"""Run the empirical experiment: Spanish Innoget Demand vs. Spanish ES Patents.

Executes deterministic quantitative alignment & white-space metrics with cryptographic
dataset verification, sensitivity analysis, and optional multi-agent candidate synthesis.
"""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Ensure backend/src/main is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_SRC = REPO_ROOT / "backend" / "src" / "main"
for p in (REPO_ROOT, BACKEND_SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from application.landscape.cpc_taxonomy import CPC_TAXONOMY_DICTIONARY
from application.landscape.metrics import ExecutionMode, compute_white_space_metrics
from application.synthesis.synthesis_engine import SynthesisEngine as InventionSynthesisEngine
from domain.models.runtime_schemas import AdversarialVerdict, InventionCandidate, ScoreCard
from infrastructure.llm.groq_client import GroqClient as GroqLlmClient
from infrastructure.sources.demand_sources import InnogetDemandDataSource
from infrastructure.sources.duckdb_patents import DuckDbPatentsDataSource


def get_git_commit() -> str:
    """Retrieve current git HEAD commit hash."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
        return res.stdout.strip() if res.returncode == 0 else "unknown-commit"
    except Exception:
        return "unknown-commit"


def verify_dataset_manifest(
    manifest_path: str = "data/snapshots/patents_es_manifest.json"
) -> dict:
    """Verify cryptographic hash and provenance of the frozen patent dataset."""
    p_man = Path(manifest_path)
    if not p_man.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}. Run scripts/ingest_oepm_ops.py first.")

    with open(p_man, encoding="utf-8") as f:
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


def audit_demand_cpc_mappings(spanish_demands: list) -> list[dict[str, Any]]:
    """Generate record-level audit trail for demand-to-CPC taxonomy classification."""
    audit_trail = []
    for d in spanish_demands:
        entry = CPC_TAXONOMY_DICTIONARY.get(d.cpc_prefix)
        matched_kws = []
        text = f"{d.title} {d.description}".lower()
        if entry:
            for kw in entry.keywords:
                if kw.lower() in text:
                    matched_kws.append(kw)
        
        audit_trail.append({
            "demand_id": d.id,
            "title": d.title,
            "mapped_cpc_prefix": d.cpc_prefix,
            "cpc_subclass_name": entry.subclass if entry else "General / Uncategorized",
            "matched_keywords": matched_kws,
            "mapping_rule": "Deterministic regex and keyword taxonomy concordance",
            "confidence": 1.0 if matched_kws else 0.85,
            "source_call_url": d.url
        })
    return audit_trail


def compute_sensitivity_analysis(metrics_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Perform mathematical sensitivity analysis of W_i across 5 distinct weighting regimes."""
    regimes = {
        "Baseline (0.40, 0.20, 0.15, 0.25)": (0.40, 0.20, 0.15, 0.25),
        "Demand-Heavy (0.30, 0.15, 0.15, 0.40)": (0.30, 0.15, 0.15, 0.40),
        "IP-Heavy (0.50, 0.20, 0.20, 0.10)": (0.50, 0.20, 0.20, 0.10),
        "Traction-Heavy (0.30, 0.20, 0.30, 0.20)": (0.30, 0.20, 0.30, 0.20),
        "Equal-Weights (0.25, 0.25, 0.25, 0.25)": (0.25, 0.25, 0.25, 0.25),
    }

    sensitivity_rows = []
    for m in metrics_list:
        row = {"cluster_id": m["cluster_id"]}
        density_term = 1.0 - m["density"]
        recency = m["recency"]
        traction = m["citation_traction"]
        demand_intensity = m["demand_intensity"]

        for regime_name, (wd, wr, wt, wq) in regimes.items():
            w_score = round(wd * density_term + wr * recency + wt * traction + wq * demand_intensity, 4)
            row[regime_name] = w_score

        sensitivity_rows.append(row)
    return sensitivity_rows


def run_experiment(
    mode: ExecutionMode = ExecutionMode.EMPIRICAL,
    db_path: str = "data/snapshots/patents_es_snapshot.duckdb",
    manifest_path: str = "data/snapshots/patents_es_manifest.json",
    output_dir: str = "data/experiments/latest",
    no_llm: bool = False,
    dry_run_llm: bool = False,
):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    git_commit = get_git_commit()

    # 1. Dataset Verification & Ingestion Source-of-Truth
    if mode == ExecutionMode.EMPIRICAL:
        manifest = verify_dataset_manifest(manifest_path)
        parquet_file = manifest["provenance"]["parquet_file"]
        patent_ds = DuckDbPatentsDataSource.from_parquet(parquet_file)
        dataset_status = f"EMPIRICAL (VERIFIED - SHA256: {manifest['sha256_hash'][:12]}...)"
    else:
        manifest = {"sha256_hash": "unverified-fixture-run", "total_records": "N/A"}
        patent_ds = DuckDbPatentsDataSource(db_path=db_path)
        dataset_status = f"{mode.upper()} (SYNTHETIC / TEST FIXTURE - NOT FOR PUBLICATION)"

    demand_ds = InnogetDemandDataSource()
    spanish_demands = demand_ds.get_spanish_demands()

    # Group demands by mapped CPC subclass prefix
    cpc_demands: dict[str, list] = {}
    for d in spanish_demands:
        cpc_demands.setdefault(d.cpc_prefix, []).append(d)

    # Export demand-to-CPC mapping audit trail
    cpc_audit = audit_demand_cpc_mappings(spanish_demands)
    with open(out / "demand_cpc_mapping_audit.json", "w", encoding="utf-8") as f:
        json.dump(cpc_audit, f, indent=2, ensure_ascii=False)

    # Predefined analytical evaluation set aligned with domestic industrial sectors
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

    # 4. Sensitivity Analysis across Weighting Regimes
    sensitivity_rows = compute_sensitivity_analysis(metrics_list)
    sens_csv = out / "sensitivity_analysis.csv"
    with open(sens_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(sensitivity_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sensitivity_rows)

    # 5. Metadata and Quantitative Report Export
    case_studies = []
    has_groq_key = bool(os.getenv("GROQ_API_KEY")) and os.getenv("GROQ_API_KEY") != "mock_key"
    can_run_live_llm = (not no_llm) and (not dry_run_llm) and has_groq_key

    if no_llm:
        engine = None
        synthesis_status = "NOT REQUESTED / NO LLM MODE ACTIVE"
    elif can_run_live_llm:
        try:
            client = GroqLlmClient()
            engine = InventionSynthesisEngine(client=client)
            synthesis_status = "EMPIRICAL (LIVE GROQ SYNTHESIS & ADVERSARIAL VERDICT)"
        except Exception as e:
            engine = None
            synthesis_status = f"SKIPPED ({e})"
    else:
        engine = None
        synthesis_status = "SYNTHETIC DRY-RUN (AWAITING LIVE GROQ API KEY)"

    meta = {
        "timestamp": datetime.now().isoformat(),
        "git_commit": git_commit,
        "execution_mode": mode.value,
        "dataset_status": dataset_status,
        "synthesis_status": synthesis_status,
        "dataset_sha256": manifest.get("sha256_hash"),
        "raw_source_sha256": manifest.get("raw_source_sha256"),
        "total_spanish_demands": len(spanish_demands),
        "total_clusters_analyzed": len(all_clusters),
        "white_space_formula_weights": {
            "w_density": 0.40,
            "w_recency": 0.20,
            "w_traction": 0.15,
            "w_demand": 0.25
        },
        "quadrant_thresholds": {
            "white_space_score_threshold": 0.50,
            "unmet_opportunity_density_ceiling": 0.40,
            "high_demand_threshold": 0.50
        },
        "dataset_source": "Verified Parquet Snapshot (In-Memory)" if mode == ExecutionMode.EMPIRICAL else db_path,
    }
    with open(out / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # Render LaTeX/Markdown Table
    banner = (
        f"> **[SCIENTIFIC EVIDENCE AUDIT TRAIL]**\n"
        f"> - **Git Commit:** `{git_commit}`\n"
        f"> - **Dataset Status:** `{dataset_status}`\n"
        f"> - **Synthesis Engine:** `{synthesis_status}`\n"
        f"> - **Dataset SHA-256:** `{manifest.get('sha256_hash')}`\n"
        f"> - **Raw Source SHA-256:** `{manifest.get('raw_source_sha256')}`\n"
    )

    md_summary = [
        "# Empirical Quantitative Results: Spanish Innoget Demand vs. Spanish ES Patents\n",
        banner,
        f"**Generated:** {meta['timestamp']} | **Execution Mode:** `{mode.value}`\n",
        "## 1. Demand-to-Patent Alignment & White-Space Matrix\n",
        "| Cluster (CPC) | Patents ($n_i$) | Demands ($m_i$) | Density ($d_i$) | Recency ($r_i$) | Traction ($T_i$) | Coverage ($C_i$) | Demand ($q_i$) | White Space ($W_i$) | Quadrant |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for m in metrics_list:
        md_summary.append(
            f"| `{m['cluster_id']}` | {m['patent_count']} | {m['demand_count']} | {m['density']:.2f} | {m['recency']:.2f} | {m['citation_traction']:.2f} | {m['citation_coverage']:.2f} | {m['demand_intensity']:.2f} | **{m['white_space_score']:.2f}** | {m['quadrant']} |"
        )

    md_summary.append("\n*Note: Clusters C11D, E03C, G05B, C22C, H01M, C08L represent a predefined analytical evaluation set for cross-sector comparison.*\n")

    md_summary.append("\n## 2. Sensitivity Analysis (Weight Perturbation Regimes)\n")
    md_summary.append("| Cluster | Baseline (0.40, 0.20, 0.15, 0.25) | Demand-Heavy | IP-Heavy | Traction-Heavy | Equal-Weights |")
    md_summary.append("|---|---|---|---|---|---|")
    for s in sensitivity_rows:
        md_summary.append(
            f"| `{s['cluster_id']}` | **{s['Baseline (0.40, 0.20, 0.15, 0.25)']:.2f}** | {s['Demand-Heavy (0.30, 0.15, 0.15, 0.40)']:.2f} | {s['IP-Heavy (0.50, 0.20, 0.20, 0.10)']:.2f} | {s['Traction-Heavy (0.30, 0.20, 0.30, 0.20)']:.2f} | {s['Equal-Weights (0.25, 0.25, 0.25, 0.25)']:.2f} |"
        )

    md_text = "\n".join(md_summary)
    with open(out / "empirical_results_summary.md", "w", encoding="utf-8") as f:
        f.write(md_text)

    # Keep paper_results_summary.md as alias for backwards compatibility
    with open(out / "paper_results_summary.md", "w", encoding="utf-8") as f:
        f.write(md_text)

    print(md_text)

    # 6. Multi-Agent Synthesis Layer (Dry-Run / Live Groq)
    if not no_llm:
        eligible_clusters = [
            m for m in metrics_list
            if len(cpc_demands.get(m["cluster_id"], [])) > 0 and len(cluster_patents.get(m["cluster_id"], [])) > 0
        ]
        eligible_clusters.sort(key=lambda x: -x["white_space_score"])

        for m in eligible_clusters[:2]:
            c_id = m["cluster_id"]
            dems = cpc_demands[c_id]
            pats = cluster_patents[c_id]
            primary_demand = dems[0]
            ref_pub = pats[0].publication_number

            if not engine:
                cand = InventionCandidate(
                    id=f"INV-{c_id}-001-SYNTHETIC",
                    cluster_id=c_id,
                    title=f"[DRY-RUN] Candidate Invention for {c_id}",
                    description=f"Tailored technological solution addressing {primary_demand.title[:60]}.",
                    novelty_claim=f"Novel differentiating implementation relative to domestic prior art {ref_pub}.",
                )
                verd = AdversarialVerdict(
                    verdict="survives",
                    rationale=f"Differentiates from cited domestic prior art {ref_pub} in core technical execution.",
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

        with open(out / "case_studies.json", "w", encoding="utf-8") as f:
            json.dump(case_studies, f, indent=2)

    return metrics_list, case_studies


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Spanish paper empirical experiment.")
    parser.add_argument("--mode", choices=["empirical", "pilot", "fixture"], default="empirical",
                        help="Execution mode (default: empirical).")
    parser.add_argument("--no-llm", action="store_true", default=False,
                        help="Execute purely quantitative metrics without LLM synthesis.")
    parser.add_argument("--output-dir", default="data/experiments/latest",
                        help="Output directory for experimental artifacts.")
    args = parser.parse_args()

    run_experiment(
        mode=ExecutionMode(args.mode),
        output_dir=args.output_dir,
        no_llm=args.no_llm
    )
