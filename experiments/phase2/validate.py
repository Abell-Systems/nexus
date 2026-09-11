"""Deterministic Offline Validation Pipeline & Dataset Sealer (ADR 0032).

This module implements the offline parsing, policy validation, and dataset sealing
for Phase-2 demand corpus expansion towards N >= 60 independent observations.
Operates 100% offline with zero network connectivity.
"""

import argparse
import hashlib
import json
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.corpus.expansion_policy_validator import (  # noqa: E402
    load_corpus_expansion_policy,
    validate_demand_candidate,
)
from application.corpus.mappers import (  # noqa: E402
    EenPodCandidateMapper,
    InnogetCandidateMapper,
    MappingError,
)
from domain.models.corpus_expansion import (  # noqa: E402
    CandidateRejectionReason,
    CorpusExpansionPolicy,
    DemandCandidateContractRecord,
    calculate_canonical_word_count,
)

logger = logging.getLogger("experiments.phase2.validate")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "policies" / "data" / "corpus_expansion_policy_v1.json"


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_sealed_json(target_path: Path, data: Any, write_sidecar: bool = True) -> str:
    """Write JSON with deterministic formatting (indent=2, sort_keys=True) and generate .sha256 sidecar.

    Sidecar format strictly follows: '<hash>  <basename>\\n'.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()

    if write_sidecar:
        sidecar_path = target_path.with_suffix(".sha256")
        sidecar_content = f"{sha256_hex}  {target_path.name}\n"
        sidecar_path.write_text(sidecar_content, encoding="utf-8")

    return sha256_hex


def extract_trigger_evidence(
    candidate: DemandCandidateContractRecord,
    reasons: Sequence[CandidateRejectionReason],
    policy: CorpusExpansionPolicy,
) -> dict[str, Any]:
    """Extract structured evidence associated with each triggered rejection reason."""
    evidence: dict[str, Any] = {}
    for reason in reasons:
        if reason == CandidateRejectionReason.UNVERIFIABLE_PUBLICATION_DATE:
            evidence[reason.value] = {
                "publication_date_evidence": candidate.publication_date_evidence.model_dump(mode="json"),
            }
        elif reason == CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW:
            evidence[reason.value] = {
                "max_publication_date": str(policy.temporal_window.max_publication_date),
                "min_publication_date": str(policy.temporal_window.min_publication_date),
                "publication_date": str(candidate.publication_date) if candidate.publication_date else None,
                "publication_date_evidence": candidate.publication_date_evidence.model_dump(mode="json"),
            }
        elif reason == CandidateRejectionReason.CONTENT_TOO_SHORT:
            word_count = calculate_canonical_word_count(candidate.description_text)
            evidence[reason.value] = {
                "min_word_count": policy.content_requirements.min_word_count,
                "observed_word_count": word_count,
                "text_snippet": candidate.description_text[:120],
            }
        elif reason == CandidateRejectionReason.NO_TECHNICAL_PROBLEM:
            evidence[reason.value] = {
                "has_articulated_technical_problem": candidate.has_articulated_technical_problem,
                "technical_problem_evidence_text": candidate.technical_problem_evidence_text,
            }
        elif reason == CandidateRejectionReason.UNAUTHORIZED_SOURCE:
            evidence[reason.value] = {
                "permitted_sources": [s.source_id for s in policy.sources],
                "source_id": candidate.source_id,
            }
        elif reason == CandidateRejectionReason.INCOMPATIBLE_CONSTRUCT:
            evidence[reason.value] = {
                "source_construct": candidate.source_construct,
                "source_id": candidate.source_id,
            }
        elif reason == CandidateRejectionReason.UNAUTHORIZED_GEOGRAPHIC_STRATUM:
            evidence[reason.value] = {
                "geographic_stratum": candidate.geographic_stratum,
                "permitted_strata": [s.stratum_id for s in policy.geographic_strata],
            }
        elif reason == CandidateRejectionReason.CONFIDENTIALITY_REDACTED:
            evidence[reason.value] = {
                "has_confidentiality_redaction": candidate.has_confidentiality_redaction,
            }
        elif reason == CandidateRejectionReason.ACCESS_NOT_PUBLIC:
            evidence[reason.value] = {
                "is_publicly_accessible": candidate.is_publicly_accessible,
            }
    return evidence


def discover_raw_payloads(raw_dir: Path) -> list[tuple[Path, Path | None]]:
    """Discover raw candidate payloads and their matching .meta.json sidecars."""
    discovered: list[tuple[Path, Path | None]] = []

    if not raw_dir.exists():
        return discovered

    # Collect all candidate files recursively
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        # Skip metadata, hashes, manifests, hidden files
        if (
            path.name.startswith(".")
            or path.name.endswith(".meta.json")
            or path.name.endswith(".sha256")
            or path.name.endswith(".manifest.json")
            or path.name.endswith(".tmp")
        ):
            continue

        # Check for companion .meta.json
        stem_meta = path.parent / f"{path.stem}.meta.json"
        alt_meta = path.parent / f"{path.name.rsplit('.', 1)[0]}.meta.json"

        meta_path: Path | None = None
        if stem_meta.is_file():
            meta_path = stem_meta
        elif alt_meta.is_file():
            meta_path = alt_meta

        discovered.append((path, meta_path))

    return sorted(discovered, key=lambda pair: str(pair[0]))


def infer_source_id(payload_path: Path, demand_id: str, meta: dict[str, Any]) -> str:
    """Infer source_id from metadata, directory structure, or demand_id prefix."""
    if meta.get("source_id"):
        return str(meta["source_id"]).strip().lower()

    parent_name = payload_path.parent.name.lower()
    if parent_name in ("een_pod", "een", "lombardia"):
        return "een_pod"
    if parent_name in ("innoget", "challenges"):
        return "innoget"

    demand_upper = demand_id.upper()
    if demand_upper.startswith("TR") or demand_upper.startswith("LOMBARDIA"):
        return "een_pod"
    if demand_upper.startswith("INNOGET"):
        return "innoget"

    return "een_pod"


def run_offline_validation(
    raw_dir: Path,
    out_dir: Path,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    """Execute the deterministic offline validation and sealing pipeline (ADR 0032).

    Steps:
    1. Resolve and verify CorpusExpansionPolicy and its cryptographic sidecar.
    2. Discover raw payload files and companion .meta.json in raw_dir.
    3. Construct candidates_raw.manifest.json registry.
    4. Map each raw payload using EenPodCandidateMapper or InnogetCandidateMapper.
    5. Capture MappingError instances into mapping_errors.json.
    6. Seal mapped candidates into candidates_mapped.json + candidates_mapped.sha256.
    7. Deterministically validate candidates with validate_demand_candidate(c, policy).
    8. Partition into accepted and rejected candidate pools.
    9. Emit candidates_accepted.json + .sha256 and candidates_rejected.json + .sha256.
    10. Emit acquisition_run.manifest.json.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Resolve and verify policy
    p_path = policy_path or DEFAULT_POLICY_PATH
    if not p_path.is_file() and not p_path.is_absolute():
        p_path = (REPO_ROOT / p_path).resolve()
    if not p_path.is_file():
        raise FileNotFoundError(f"Corpus expansion policy file not found: {p_path}")

    h_path = p_path.with_suffix(".sha256")
    if not h_path.is_file():
        raise FileNotFoundError(f"Corpus expansion policy hash sidecar not found: {h_path}")

    policy = load_corpus_expansion_policy(policy_path=p_path, hash_path=h_path)
    policy_hash = h_path.read_text(encoding="utf-8").strip().split()[0]

    # 2. Discover raw payloads
    raw_pairs = discover_raw_payloads(raw_dir)

    candidates_raw_manifest: list[dict[str, Any]] = []
    mapped_candidates: list[DemandCandidateContractRecord] = []
    mapping_errors: list[dict[str, Any]] = []

    # 3 & 4. Process each raw payload
    for payload_path, meta_path in raw_pairs:
        raw_bytes = payload_path.read_bytes()
        actual_hash = hashlib.sha256(raw_bytes).hexdigest()

        meta: dict[str, Any] = {}
        if meta_path and meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to parse metadata sidecar %s: %s", meta_path, exc)

        demand_id = meta.get("demand_id") or payload_path.stem
        source_id = infer_source_id(payload_path, demand_id, meta)
        meta["demand_id"] = demand_id
        meta["source_id"] = source_id
        if "raw_payload_sha256" not in meta:
            meta["raw_payload_sha256"] = actual_hash

        try:
            rel_file_path = str(payload_path.relative_to(raw_dir))
        except ValueError:
            rel_file_path = payload_path.name

        candidates_raw_manifest.append(
            {
                "acquisition_timestamp": meta.get("acquisition_timestamp", ""),
                "demand_id": demand_id,
                "file_name": payload_path.name,
                "file_path": rel_file_path,
                "raw_payload_sha256": actual_hash,
                "source_id": source_id,
                "source_uri": meta.get("source_uri", ""),
            }
        )

        try:
            if source_id in ("een_pod", "een", "lombardia"):
                candidate = EenPodCandidateMapper.map_payload(raw_bytes, metadata=meta)
            elif source_id == "innoget":
                candidate = InnogetCandidateMapper.map_payload(raw_bytes, metadata=meta)
            else:
                raise MappingError(f"Unsupported source_id '{source_id}' for {payload_path}")

            mapped_candidates.append(candidate)

        except MappingError as exc:
            mapping_errors.append(
                {
                    "demand_id": demand_id,
                    "error_message": str(exc),
                    "error_type": "MappingError",
                    "file_path": rel_file_path,
                    "source_id": source_id,
                }
            )
        except Exception as exc:
            mapping_errors.append(
                {
                    "demand_id": demand_id,
                    "error_message": f"Unexpected error: {exc}",
                    "error_type": type(exc).__name__,
                    "file_path": rel_file_path,
                    "source_id": source_id,
                }
            )

    # 5. Deterministic sorting for mapped datasets
    candidates_raw_manifest.sort(key=lambda r: str(r["demand_id"]))
    mapped_candidates.sort(key=lambda c: c.demand_id)
    mapping_errors.sort(key=lambda e: (str(e.get("demand_id") or ""), str(e.get("file_path") or "")))

    # 6. Policy validation and partitioning
    accepted_candidates: list[DemandCandidateContractRecord] = []
    rejected_records: list[dict[str, Any]] = []

    for candidate in mapped_candidates:
        val_result = validate_demand_candidate(candidate, policy)
        if len(val_result.rejection_reasons) == 0:
            accepted_candidates.append(candidate)
        else:
            evidence = extract_trigger_evidence(candidate, val_result.rejection_reasons, policy)
            candidate_dump = candidate.model_dump(mode="json")
            rejected_entry = {
                **candidate_dump,
                "candidate": candidate_dump,
                "rejection_reasons": [r.value for r in val_result.rejection_reasons],
                "trigger_evidence": evidence,
            }
            rejected_records.append(rejected_entry)

    accepted_candidates.sort(key=lambda c: c.demand_id)
    rejected_records.sort(key=lambda r: str(r["demand_id"]))

    mapped_records = [c.model_dump(mode="json") for c in mapped_candidates]
    accepted_records = [c.model_dump(mode="json") for c in accepted_candidates]

    # 7. Write and cryptographically seal outputs
    hash_raw = write_sealed_json(
        out_dir / "candidates_raw.manifest.json",
        candidates_raw_manifest,
        write_sidecar=True,
    )
    hash_mapped = write_sealed_json(
        out_dir / "candidates_mapped.json",
        mapped_records,
        write_sidecar=True,
    )
    hash_accepted = write_sealed_json(
        out_dir / "candidates_accepted.json",
        accepted_records,
        write_sidecar=True,
    )
    hash_rejected = write_sealed_json(
        out_dir / "candidates_rejected.json",
        rejected_records,
        write_sidecar=True,
    )
    write_sealed_json(
        out_dir / "mapping_errors.json",
        mapping_errors,
        write_sidecar=False,
    )

    # 8. Compute breakdown statistics for acquisition run manifest
    rejection_counts: dict[str, int] = {}
    for r in rejected_records:
        for reason in r["rejection_reasons"]:
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

    source_breakdown: dict[str, dict[str, int]] = {}
    for r in candidates_raw_manifest:
        src = r["source_id"]
        source_breakdown.setdefault(src, {"accepted": 0, "mapped": 0, "raw": 0, "rejected": 0})
        source_breakdown[src]["raw"] += 1

    for c in mapped_candidates:
        src = c.source_id
        source_breakdown.setdefault(src, {"accepted": 0, "mapped": 0, "raw": 0, "rejected": 0})
        source_breakdown[src]["mapped"] += 1

    for a in accepted_candidates:
        src = a.source_id
        source_breakdown.setdefault(src, {"accepted": 0, "mapped": 0, "raw": 0, "rejected": 0})
        source_breakdown[src]["accepted"] += 1

    for rej in rejected_records:
        src = rej["source_id"]
        source_breakdown.setdefault(src, {"accepted": 0, "mapped": 0, "raw": 0, "rejected": 0})
        source_breakdown[src]["rejected"] += 1

    stratum_breakdown: dict[str, int] = {}
    for a in accepted_candidates:
        strat = a.geographic_stratum
        stratum_breakdown[strat] = stratum_breakdown.get(strat, 0) + 1

    run_manifest: dict[str, Any] = {
        "artifact_hashes": {
            "candidates_accepted.json": hash_accepted,
            "candidates_mapped.json": hash_mapped,
            "candidates_raw.manifest.json": hash_raw,
            "candidates_rejected.json": hash_rejected,
        },
        "counts": {
            "total_accepted": len(accepted_records),
            "total_mapped": len(mapped_records),
            "total_mapping_errors": len(mapping_errors),
            "total_raw": len(candidates_raw_manifest),
            "total_rejected": len(rejected_records),
        },
        "execution_timestamp": datetime.now(UTC).isoformat(),
        "manifest_version": "1.0.0",
        "pipeline_version": "phase2_offline_validator_v1",
        "policy_sha256": policy_hash,
        "policy_version": policy.policy_version,
        "rejection_breakdown": rejection_counts,
        "source_breakdown": source_breakdown,
        "stratum_breakdown": stratum_breakdown,
    }

    write_sealed_json(
        out_dir / "acquisition_run.manifest.json",
        run_manifest,
        write_sidecar=False,
    )

    logger.info(
        "Offline validation complete: raw=%d, mapped=%d, accepted=%d, rejected=%d, mapping_errors=%d",
        len(candidates_raw_manifest),
        len(mapped_records),
        len(accepted_records),
        len(rejected_records),
        len(mapping_errors),
    )

    return run_manifest


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for offline validation runner."""
    parser = argparse.ArgumentParser(
        description="Deterministic offline validation pipeline and dataset sealer (ADR 0032)."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/phase2_candidates"),
        help="Path to directory containing raw acquired payloads and .meta.json sidecars.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/experiments/phase2"),
        help="Path to output directory for sealed datasets, manifests, and sidecars.",
    )
    parser.add_argument(
        "--policy-path",
        type=Path,
        default=None,
        help="Path to frozen corpus expansion policy JSON file (optional).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for offline validation runner."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        run_offline_validation(
            raw_dir=args.raw_dir,
            out_dir=args.out_dir,
            policy_path=args.policy_path,
        )
        return 0
    except Exception as exc:
        logger.exception("Offline validation pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
