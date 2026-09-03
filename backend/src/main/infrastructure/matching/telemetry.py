import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from domain.models.matching import MatchingResult
from domain.protocols.matching import MatchingTelemetrySink


class FileSystemMatchingTelemetrySink(MatchingTelemetrySink):
    """Persists matching runs to immutable JSON/JSONL artifacts.

    Produces:
    data/experiments/<run_id>/
        ├── metadata.json       (Provenance, configuration, hashes, versions)
        ├── result.json         (Canonical versioned contract for machine & UI consumers)
        ├── candidates.jsonl    (P_shared candidates with multi-signal provenance)
        └── rankings.jsonl      (Full ranked outputs per strategy with score components)
    """

    def __init__(self, base_dir: Path | str = "data/experiments") -> None:
        self.base_dir = Path(base_dir)

    def record_run(
        self,
        result: MatchingResult,
        metadata: dict[str, Any],
        patent_evidence: dict[str, dict[str, Any]] | None = None,
    ) -> str:
        timestamp_str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        unique_suffix = uuid.uuid4().hex[:8]
        run_id = metadata.get("run_id") or f"{timestamp_str}_{result.demand_id}_{unique_suffix}"

        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # 1. Enrich Metadata
        full_metadata: dict[str, Any] = {
            "schema_version": "1.0",
            "run_id": run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "demand_id": result.demand_id,
            "pool_size": len(result.pool.candidates),
            "strategies": list(result.rankings.keys()),
            **metadata,
        }

        # 2. Canonical Result Contract (Unified for Machine and UI consumption)
        canonical_rankings: dict[str, list[dict[str, Any]]] = {}
        for strategy, ranked_list in result.rankings.items():
            canonical_rankings[strategy] = []
            for item in ranked_list:
                evidence = (patent_evidence or {}).get(item.publication_id, {})
                canonical_rankings[strategy].append({
                    "publication_id": item.publication_id,
                    "rank": item.rank,
                    "score": item.score,
                    "signals": item.components,
                    "evidence": {
                        "title": evidence.get("title", ""),
                        "abstract": evidence.get("abstract", ""),
                        "publication_date": evidence.get("publication_date", ""),
                        "cpc_codes": evidence.get("cpc_codes", []),
                    },
                })

        canonical_result: dict[str, Any] = {
            "schema_version": "1.0",
            "run_id": run_id,
            "demand_id": result.demand_id,
            "status": "completed",
            "shared_pool_size": len(result.pool.candidates),
            "rankings": canonical_rankings,
            "metadata": full_metadata,
        }

        # Write result.json and calculate its sha256
        result_json_path = run_dir / "result.json"
        result_bytes = json.dumps(canonical_result, indent=2, ensure_ascii=False).encode("utf-8")
        result_json_path.write_bytes(result_bytes)
        full_metadata["result_sha256"] = hashlib.sha256(result_bytes).hexdigest()

        # Write metadata.json
        metadata_json_path = run_dir / "metadata.json"
        metadata_json_path.write_text(json.dumps(full_metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        # 3. Write candidates.jsonl (P_shared)
        candidates_jsonl_path = run_dir / "candidates.jsonl"
        with candidates_jsonl_path.open("w", encoding="utf-8") as f:
            for cand in result.pool.candidates:
                line_data: dict[str, Any] = {
                    "demand_id": result.demand_id,
                    "publication_id": cand.publication_id,
                    "retrieval_scores": {k.value if hasattr(k, "value") else str(k): v for k, v in cand.retrieval_scores.items()},
                }
                f.write(json.dumps(line_data, ensure_ascii=False) + "\n")

        # 4. Write rankings.jsonl
        rankings_jsonl_path = run_dir / "rankings.jsonl"
        with rankings_jsonl_path.open("w", encoding="utf-8") as f:
            for strategy, ranked_list in result.rankings.items():
                for item in ranked_list:
                    rank_line_data: dict[str, Any] = {
                        "strategy": strategy,
                        "publication_id": item.publication_id,
                        "rank": item.rank,
                        "score": item.score,
                        "components": item.components,
                    }
                    f.write(json.dumps(rank_line_data, ensure_ascii=False) + "\n")

        return run_id
