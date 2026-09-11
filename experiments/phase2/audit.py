"""Phase-2 Corpus Expansion Audit Verification Script (ADR 0032).

Verifies end-to-end cryptographic, partition, and content invariants for the
Phase-2 demand corpus expansion towards N >= 60 independent observations.
Operates 100% offline with zero network connectivity.

Invariants verified:
1. Cryptographic sidecars match: verifies that .sha256 sidecars for
   candidates_raw.manifest.json, candidates_mapped.json, candidates_accepted.json,
   candidates_rejected.json match computed hashes on disk.
2. Partition equation:
   candidates_mapped == candidates_accepted + candidates_rejected
   candidates_accepted ∩ candidates_rejected == ∅
   (verified by demand_id set operations).
3. Accepted candidate invariants:
   - 100% of accepted records have non-null publication_date.
   - 100% of accepted records have publication_date within temporal window [2020-01-01, 2025-12-31].
   - 100% of accepted records have canonical_word_count >= 25.
   - 100% of accepted records have has_articulated_technical_problem is True and
     non-empty technical_problem_evidence_text.
   - 0% of accepted records have rejection reasons.
4. Rejected candidate invariants:
   - 100% of rejected records have at least one rejection reason from CandidateRejectionReason.
   - Records with UNVERIFIABLE_PUBLICATION_DATE have publication_date is None.
   - Records with OUT_OF_TEMPORAL_WINDOW have verified publication_date outside [2020-01-01, 2025-12-31].
5. Descriptive stratification metrics:
   - Summary table: Total raw, total mapped, total mapping errors, total accepted, total rejected.
   - Stratum distribution (spain vs international_european) for accepted candidates.
   - Source distribution (innoget vs een_pod).
   - Breakdown of rejection reasons.
6. Exit code: 0 if all invariants pass, 1 if any invariant fails.
"""

import argparse
import hashlib
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.corpus.expansion_policy_validator import (  # noqa: E402
    load_corpus_expansion_policy,
)
from domain.models.corpus_expansion import (  # noqa: E402
    CandidateRejectionReason,
    CorpusExpansionPolicy,
    calculate_canonical_word_count,
)

logger = logging.getLogger("experiments.phase2.audit")

DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "policies" / "data" / "corpus_expansion_policy_v1.json"

SEALED_ARTIFACTS = (
    "candidates_raw.manifest.json",
    "candidates_mapped.json",
    "candidates_accepted.json",
    "candidates_rejected.json",
)


@dataclass(frozen=True)
class AuditResult:
    """Immutable outcome of the Phase-2 corpus expansion audit."""

    is_valid: bool
    errors: tuple[str, ...]
    summary_metrics: dict[str, int]
    stratum_distribution: dict[str, int]
    source_distribution: dict[str, dict[str, int]]
    rejection_breakdown: dict[str, int]
    report: str


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_sidecar_path(experiments_dir: Path, filename: str) -> Path | None:
    """Find the companion .sha256 sidecar file for a given artifact filename."""
    candidate_paths = [
        (experiments_dir / filename).with_suffix(".sha256"),
        experiments_dir / f"{filename}.sha256",
    ]
    for p in candidate_paths:
        if p.is_file():
            return p
    return None


def extract_publication_date(record: dict[str, Any]) -> date | None:
    """Extract publication date from record or nested evidence/candidate object."""
    pub_val = record.get("publication_date")
    if pub_val is None and "publication_date_evidence" in record:
        p_ev = record["publication_date_evidence"]
        if isinstance(p_ev, dict):
            pub_val = p_ev.get("publication_date")

    if pub_val is None and "candidate" in record:
        cand = record["candidate"]
        if isinstance(cand, dict):
            pub_val = cand.get("publication_date")
            if pub_val is None and "publication_date_evidence" in cand:
                p_ev = cand["publication_date_evidence"]
                if isinstance(p_ev, dict):
                    pub_val = p_ev.get("publication_date")

    if pub_val is None:
        return None
    if isinstance(pub_val, date):
        return pub_val
    if isinstance(pub_val, str):
        return date.fromisoformat(pub_val)
    return None


def format_audit_report(
    summary_metrics: dict[str, int],
    stratum_distribution: dict[str, int],
    source_distribution: dict[str, dict[str, int]],
    rejection_breakdown: dict[str, int],
    errors: Sequence[str],
) -> str:
    """Format audit summary metrics, distributions, and results as a readable report."""
    lines: list[str] = [
        "=" * 80,
        "Phase-2 Corpus Expansion Audit Verification Report (ADR 0032)",
        "=" * 80,
        "",
        "1. Summary Metrics:",
        "-" * 80,
        f"  Total Raw Candidates:       {summary_metrics.get('total_raw', 0):>6}",
        f"  Total Mapped Candidates:    {summary_metrics.get('total_mapped', 0):>6}",
        f"  Total Mapping Errors:       {summary_metrics.get('total_mapping_errors', 0):>6}",
        f"  Total Accepted Candidates:  {summary_metrics.get('total_accepted', 0):>6}",
        f"  Total Rejected Candidates:  {summary_metrics.get('total_rejected', 0):>6}",
        "",
        "2. Stratum Distribution (Accepted Candidates):",
        "-" * 80,
    ]

    if stratum_distribution:
        for stratum, count in sorted(stratum_distribution.items()):
            lines.append(f"  {stratum:<30} {count:>6}")
    else:
        lines.append("  (No accepted candidates)")

    lines.extend(
        [
            "",
            "3. Source Distribution (Accepted / Mapped / Raw / Rejected):",
            "-" * 80,
        ]
    )

    if source_distribution:
        for src, counts in sorted(source_distribution.items()):
            lines.append(
                f"  {src:<20} {counts.get('accepted', 0):>4} accepted / "
                f"{counts.get('mapped', 0):>4} mapped / "
                f"{counts.get('raw', 0):>4} raw / "
                f"{counts.get('rejected', 0):>4} rejected"
            )
    else:
        lines.append("  (No sources recorded)")

    lines.extend(
        [
            "",
            "4. Rejection Reason Breakdown:",
            "-" * 80,
        ]
    )

    if rejection_breakdown:
        for reason, count in sorted(rejection_breakdown.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"  {reason:<35} {count:>6}")
    else:
        lines.append("  (No rejection reasons recorded)")

    lines.extend(
        [
            "",
            "=" * 80,
        ]
    )

    if not errors:
        lines.append("AUDIT RESULT: PASSED (All cryptographic, partition, and field invariants verified)")
    else:
        lines.append(f"AUDIT RESULT: FAILED ({len(errors)} invariant violations detected)")
        lines.append("-" * 80)
        for i, err in enumerate(errors, 1):
            lines.append(f"  [{i}] {err}")

    lines.append("=" * 80)
    return "\n".join(lines)


def run_phase2_audit(
    experiments_dir: Path,
    raw_dir: Path,
    policy_path: Path | None = None,
) -> AuditResult:
    """Execute full audit of Phase-2 corpus expansion artifacts and invariants."""
    errors: list[str] = []

    # 1. Resolve and load policy (fail-fast per ADR 0005 and Section 3)
    p_path = policy_path or DEFAULT_POLICY_PATH
    if not p_path.is_file() and not p_path.is_absolute():
        p_path = (REPO_ROOT / p_path).resolve()
    if not p_path.is_file():
        raise FileNotFoundError(f"Corpus expansion policy file not found: {p_path}")

    h_path = p_path.with_suffix(".sha256")
    if not h_path.is_file():
        raise FileNotFoundError(f"Corpus expansion policy hash sidecar not found: {h_path}")

    policy: CorpusExpansionPolicy = load_corpus_expansion_policy(policy_path=p_path, hash_path=h_path)
    min_date = policy.temporal_window.min_publication_date
    max_date = policy.temporal_window.max_publication_date
    min_word_count = policy.content_requirements.min_word_count

    # 2. Invariant 1: Cryptographic sidecars match
    for filename in SEALED_ARTIFACTS:
        target_file = experiments_dir / filename
        if not target_file.is_file():
            errors.append(f"Missing required artifact file: {filename}")
            continue

        sidecar_file = find_sidecar_path(experiments_dir, filename)
        if not sidecar_file or not sidecar_file.is_file():
            errors.append(f"Missing required cryptographic sidecar for artifact: {filename}")
            continue

        actual_hash = compute_sha256(target_file)
        sidecar_text = sidecar_file.read_text(encoding="utf-8").strip()
        parts = sidecar_text.split()
        if not parts:
            errors.append(f"Empty cryptographic sidecar file: {sidecar_file.name}")
            continue

        expected_hash = parts[0]
        if actual_hash.lower() != expected_hash.lower():
            errors.append(f"Cryptographic hash mismatch for {filename}: expected {expected_hash}, got {actual_hash}")

    # 3. Load artifact payloads
    def _load_json_list(filename: str) -> list[dict[str, Any]]:
        target_file = experiments_dir / filename
        if not target_file.is_file():
            return []
        try:
            data = json.loads(target_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            errors.append(f"Expected JSON list in {filename}, got {type(data).__name__}")
            return []
        except Exception as exc:
            errors.append(f"Failed to parse JSON file {filename}: {exc}")
            return []

    raw_manifest = _load_json_list("candidates_raw.manifest.json")
    mapped = _load_json_list("candidates_mapped.json")
    accepted = _load_json_list("candidates_accepted.json")
    rejected = _load_json_list("candidates_rejected.json")

    mapping_errors_file = experiments_dir / "mapping_errors.json"
    mapping_errors: list[dict[str, Any]] = []
    if mapping_errors_file.is_file():
        try:
            loaded_errors = json.loads(mapping_errors_file.read_text(encoding="utf-8"))
            if isinstance(loaded_errors, list):
                mapping_errors = loaded_errors
        except Exception as exc:
            errors.append(f"Failed to parse mapping_errors.json: {exc}")

    # 4. Invariant 2: Partition equation & disjointness
    ids_mapped = [r.get("demand_id", "") for r in mapped]
    ids_accepted = [r.get("demand_id", "") for r in accepted]
    ids_rejected = [r.get("demand_id", "") for r in rejected]

    if len(set(ids_mapped)) != len(ids_mapped):
        errors.append("Partition violation: duplicate demand_ids found in candidates_mapped.json")
    if len(set(ids_accepted)) != len(ids_accepted):
        errors.append("Partition violation: duplicate demand_ids found in candidates_accepted.json")
    if len(set(ids_rejected)) != len(ids_rejected):
        errors.append("Partition violation: duplicate demand_ids found in candidates_rejected.json")

    set_mapped = set(ids_mapped)
    set_accepted = set(ids_accepted)
    set_rejected = set(ids_rejected)

    # Disjointness: accepted ∩ rejected == ∅
    overlap = set_accepted & set_rejected
    if overlap:
        errors.append(f"Partition violation: overlap between accepted and rejected candidates: {sorted(overlap)}")

    # Equation: mapped == accepted + rejected
    missing_from_partition = set_mapped - (set_accepted | set_rejected)
    if missing_from_partition:
        errors.append(
            f"Partition violation: mapped candidates missing from accepted/rejected: {sorted(missing_from_partition)}"
        )

    extra_in_partition = (set_accepted | set_rejected) - set_mapped
    if extra_in_partition:
        errors.append(
            f"Partition violation: candidates in accepted/rejected not found in mapped: {sorted(extra_in_partition)}"
        )

    if len(mapped) != len(accepted) + len(rejected):
        errors.append(
            f"Partition equation count mismatch: mapped ({len(mapped)}) != "
            f"accepted ({len(accepted)}) + rejected ({len(rejected)})"
        )

    # 5. Invariant 3: Accepted candidate invariants
    for r in accepted:
        demand_id = r.get("demand_id", "<unknown>")

        pub_date = extract_publication_date(r)
        if pub_date is None:
            errors.append(f"Accepted candidate '{demand_id}' has null publication_date")
        else:
            if pub_date < min_date or pub_date > max_date:
                errors.append(
                    f"Accepted candidate '{demand_id}' has publication_date {pub_date} "
                    f"outside temporal window [{min_date}, {max_date}]"
                )

        desc_text = str(r.get("description_text") or "")
        word_count = calculate_canonical_word_count(desc_text)
        if word_count < min_word_count:
            errors.append(f"Accepted candidate '{demand_id}' has canonical word count {word_count} < {min_word_count}")

        has_problem = r.get("has_articulated_technical_problem")
        if not has_problem:
            errors.append(f"Accepted candidate '{demand_id}' has has_articulated_technical_problem=False")

        problem_evidence = str(r.get("technical_problem_evidence_text") or "").strip()
        if not problem_evidence:
            errors.append(f"Accepted candidate '{demand_id}' has empty technical_problem_evidence_text")

        rejection_reasons = r.get("rejection_reasons")
        if rejection_reasons:
            errors.append(f"Accepted candidate '{demand_id}' contains non-empty rejection_reasons: {rejection_reasons}")

    # 6. Invariant 4: Rejected candidate invariants
    valid_reasons = {e.value for e in CandidateRejectionReason}
    for r in rejected:
        demand_id = r.get("demand_id", "<unknown>")
        reasons = r.get("rejection_reasons", [])
        if not reasons:
            errors.append(f"Rejected candidate '{demand_id}' has no rejection reasons")
            continue

        for reason in reasons:
            if reason not in valid_reasons:
                errors.append(f"Rejected candidate '{demand_id}' has invalid rejection reason: '{reason}'")

        pub_date = extract_publication_date(r)

        if CandidateRejectionReason.UNVERIFIABLE_PUBLICATION_DATE.value in reasons and pub_date is not None:
            errors.append(
                f"Rejected candidate '{demand_id}' has UNVERIFIABLE_PUBLICATION_DATE "
                f"but publication_date is not None: {pub_date}"
            )

        if CandidateRejectionReason.OUT_OF_TEMPORAL_WINDOW.value in reasons:
            if pub_date is None:
                errors.append(
                    f"Rejected candidate '{demand_id}' has OUT_OF_TEMPORAL_WINDOW but publication_date is None"
                )
            elif min_date <= pub_date <= max_date:
                errors.append(
                    f"Rejected candidate '{demand_id}' has OUT_OF_TEMPORAL_WINDOW but publication_date "
                    f"{pub_date} is inside temporal window [{min_date}, {max_date}]"
                )

    # 7. Descriptive stratification metrics
    summary_metrics: dict[str, int] = {
        "total_accepted": len(accepted),
        "total_mapped": len(mapped),
        "total_mapping_errors": len(mapping_errors),
        "total_raw": len(raw_manifest),
        "total_rejected": len(rejected),
    }

    stratum_distribution: dict[str, int] = {}
    for r in accepted:
        s = str(r.get("geographic_stratum") or "unknown")
        stratum_distribution[s] = stratum_distribution.get(s, 0) + 1

    source_distribution: dict[str, dict[str, int]] = {}
    for r in raw_manifest:
        src = str(r.get("source_id") or "unknown")
        source_distribution.setdefault(src, {"accepted": 0, "mapped": 0, "raw": 0, "rejected": 0})
        source_distribution[src]["raw"] += 1

    for r in mapped:
        src = str(r.get("source_id") or "unknown")
        source_distribution.setdefault(src, {"accepted": 0, "mapped": 0, "raw": 0, "rejected": 0})
        source_distribution[src]["mapped"] += 1

    for r in accepted:
        src = str(r.get("source_id") or "unknown")
        source_distribution.setdefault(src, {"accepted": 0, "mapped": 0, "raw": 0, "rejected": 0})
        source_distribution[src]["accepted"] += 1

    for r in rejected:
        src = str(r.get("source_id") or "unknown")
        source_distribution.setdefault(src, {"accepted": 0, "mapped": 0, "raw": 0, "rejected": 0})
        source_distribution[src]["rejected"] += 1

    rejection_breakdown: dict[str, int] = {}
    for r in rejected:
        for reason in r.get("rejection_reasons", []):
            reason_str = str(reason)
            rejection_breakdown[reason_str] = rejection_breakdown.get(reason_str, 0) + 1

    # 8. Report and result packaging
    report = format_audit_report(
        summary_metrics=summary_metrics,
        stratum_distribution=stratum_distribution,
        source_distribution=source_distribution,
        rejection_breakdown=rejection_breakdown,
        errors=errors,
    )

    return AuditResult(
        is_valid=len(errors) == 0,
        errors=tuple(errors),
        summary_metrics=summary_metrics,
        stratum_distribution=stratum_distribution,
        source_distribution=source_distribution,
        rejection_breakdown=rejection_breakdown,
        report=report,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for audit script."""
    parser = argparse.ArgumentParser(description="Phase-2 Corpus Expansion Audit Verification Script (ADR 0032).")
    parser.add_argument(
        "--experiments-dir",
        type=Path,
        default=Path("data/experiments/phase2"),
        help="Path to directory containing sealed Phase-2 experiment datasets and sidecars.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/phase2_candidates"),
        help="Path to directory containing raw candidate payloads and .meta.json sidecars.",
    )
    parser.add_argument(
        "--policy-path",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="Path to corpus expansion policy JSON file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for audit verification."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_phase2_audit(
            experiments_dir=args.experiments_dir,
            raw_dir=args.raw_dir,
            policy_path=args.policy_path,
        )
        print(result.report)
        return 0 if result.is_valid else 1
    except Exception as exc:
        logger.exception("Audit verification execution failed: %s", exc)
        print(f"\nFATAL AUDIT ERROR: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
