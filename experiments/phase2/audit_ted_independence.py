"""#102 Multidimensional Demand-Independence Audit for TED (ADR 0034/ADR 0035).

Runs organization independence (ADR 0029's unmodified `derive_independence_groups`)
plus a descriptive, structural-only sector/technology-family concentration report
over the TED-accepted candidate pool, and seals the result.

Sector and technology-family use each notice's own CPV (Common Procurement
Vocabulary) classification -- an observed, structured field on the source record
itself (BT-262-Procedure), never text-similarity or embedding-based inference.
Per ADR 0031 SS2.4, concentration is reported and flagged, never used to
auto-exclude a valid observation.

Duplicate-industrial-problem is explicitly NOT evaluated here: no structural,
non-inferred signal for it exists in this source's raw evidence (ADR 0029 SS3.2
rejects text/embedding similarity for the same circularity reason). Recorded as
an open, disclosed limitation of this closure, not silently assumed resolved.

100% offline, zero network connectivity, operating only on already-sealed
candidates_accepted.json and the already-acquired raw payloads.
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.annotation.demand_independence import derive_independence_groups  # noqa: E402
from domain.models.annotation import DemandIndependenceStatus, DemandOrganizationObservation  # noqa: E402

logger = logging.getLogger("experiments.phase2.audit_ted_independence")

_CPV_RE = re.compile(r"code\|name\|cpv\.(\d{8})")
CONCENTRATION_WARNING_THRESHOLD = 0.35


def compute_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_sealed_json(target_path: Path, data: Any) -> str:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    sidecar_path = target_path.with_suffix(".sha256")
    sidecar_path.write_text(f"{sha256_hex}  {target_path.name}\n", encoding="utf-8")
    return sha256_hex


def extract_cpv_code(raw_html: str) -> str | None:
    """First CPV code in document order is the notice's main classification
    (BT-262-Procedure), which precedes any lot-level or place-of-performance
    classification later in the document -- a document-order rule, matching
    the same pattern already used for buyer country in `ted_mapper.py`."""
    m = _CPV_RE.search(raw_html)
    return m.group(1) if m else None


def _concentration_report(labels: list[str], threshold: float) -> dict[str, Any]:
    total = len(labels)
    counts = Counter(labels)
    shares = {k: v / total for k, v in counts.items()} if total else {}
    warnings = [k for k, share in shares.items() if share > threshold]
    return {
        "total": total,
        "distribution": dict(counts),
        "shares": shares,
        "concentration_warnings": warnings,
        "threshold": threshold,
    }


def _multi_member_groups(
    independent_ids: list[str],
    pseudoreplicate_ids: list[str],
    org_group_by_id: dict[str, str | None],
) -> dict[str, list[str]]:
    """Every organization group with more than one member (one INDEPENDENT
    representative plus its PSEUDOREPLICATE siblings), keyed by organization name."""
    members_by_org: dict[str, list[str]] = {}
    for demand_id in independent_ids + pseudoreplicate_ids:
        org = org_group_by_id.get(demand_id)
        if org is None:
            continue
        members_by_org.setdefault(org, []).append(demand_id)
    return {org: sorted(ids) for org, ids in members_by_org.items() if len(ids) > 1}


def run_ted_independence_audit(
    accepted_path: Path,
    raw_dir: Path,
    non_identifying_values: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))

    # 1. Organization independence -- ADR 0029, unmodified.
    observations = [
        DemandOrganizationObservation(demand_id=d["demand_id"], requesting_organization=d.get("organization_raw"))
        for d in accepted
    ]
    org_entries = derive_independence_groups(observations, non_identifying_values)
    org_status_by_id = {e.demand_id: e.status for e in org_entries}
    org_group_by_id = {e.demand_id: e.independence_group_id for e in org_entries}

    independent_ids = [d["demand_id"] for d in accepted if org_status_by_id[d["demand_id"]] == DemandIndependenceStatus.INDEPENDENT]
    pseudoreplicate_ids = [
        d["demand_id"] for d in accepted if org_status_by_id[d["demand_id"]] == DemandIndependenceStatus.PSEUDOREPLICATE
    ]
    unknown_ids = [d["demand_id"] for d in accepted if org_status_by_id[d["demand_id"]] == DemandIndependenceStatus.UNKNOWN]

    # 2. Sector / technology-family -- structural CPV classification, over the
    # INDEPENDENT set only (the set that actually determines N_power).
    cpv_by_id: dict[str, str | None] = {}
    for d in accepted:
        if d["demand_id"] not in independent_ids:
            continue
        raw_path = raw_dir / "ted" / f"{d['demand_id']}.html"
        cpv_by_id[d["demand_id"]] = extract_cpv_code(raw_path.read_text(encoding="utf-8")) if raw_path.is_file() else None

    missing_cpv = [k for k, v in cpv_by_id.items() if v is None]
    sector_labels = [v[:2] for v in cpv_by_id.values() if v]  # CPV division (2-digit)
    family_labels = [v for v in cpv_by_id.values() if v]  # full 8-digit CPV code

    sector_report = _concentration_report(sector_labels, CONCENTRATION_WARNING_THRESHOLD)
    family_report = _concentration_report(family_labels, CONCENTRATION_WARNING_THRESHOLD)

    # Sector/family are descriptive and reported per ADR 0031 SS2.4 -- they never
    # auto-exclude a valid observation, so N_power is unaffected by this step.
    n_power = len(independent_ids)

    result: dict[str, Any] = {
        "audit_version": "ted_independence_audit_v1",
        "execution_timestamp": datetime.now(UTC).isoformat(),
        "source_dataset": accepted_path.name,
        "source_dataset_sha256": compute_file_sha256(accepted_path),
        "organization_axis": {
            "total_accepted": len(accepted),
            "independent": sorted(independent_ids),
            "pseudoreplicate": sorted(pseudoreplicate_ids),
            "unknown": sorted(unknown_ids),
            "counts": {
                "INDEPENDENT": len(independent_ids),
                "PSEUDOREPLICATE": len(pseudoreplicate_ids),
                "UNKNOWN": len(unknown_ids),
            },
            "multi_member_groups": _multi_member_groups(independent_ids, pseudoreplicate_ids, org_group_by_id),
        },
        "sector_axis": {
            "method": "CPV division (first 2 digits of BT-262-Procedure main classification), structural/observed only, never text-similarity or embedding inference",
            "evaluated_over": "INDEPENDENT set only (N={})".format(len(independent_ids)),
            "missing_cpv": sorted(missing_cpv),
            "report": sector_report,
            "excludes_observations": False,
        },
        "technology_family_axis": {
            "method": "Full 8-digit CPV code (BT-262-Procedure main classification), structural/observed only, never text-similarity or embedding inference",
            "evaluated_over": "INDEPENDENT set only (N={})".format(len(independent_ids)),
            "missing_cpv": sorted(missing_cpv),
            "report": family_report,
            "excludes_observations": False,
        },
        "duplicate_industrial_problem_axis": {
            "status": "NOT_EVALUATED",
            "reason": (
                "No structural, non-inferred signal for duplicate industrial-problem "
                "detection exists in TED's raw evidence. Text-similarity or embedding-"
                "based deduplication is explicitly rejected (ADR 0029 SS3.2's circularity "
                "reasoning applies identically here) rather than approximated. This is a "
                "disclosed, open limitation of this closure, not an assumption that no "
                "duplicates exist."
            ),
        },
        "n_power": {
            "value": n_power,
            "definition": "count(INDEPENDENT) after organization axis; sector/family are descriptive per ADR 0031 SS2.4 and do not reduce this value; duplicate-industrial-problem is not evaluated and also does not reduce this value",
            "gate_threshold": 60,
            "gate_result": "PASS" if n_power >= 60 else "STOP",
        },
    }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="#102 TED demand-independence audit (organization + sector/family concentration).")
    parser.add_argument("--accepted-path", type=Path, default=Path("data/experiments/phase2_v4/candidates_accepted.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/phase2_candidates_ted"))
    parser.add_argument("--out-path", type=Path, default=Path("data/experiments/phase2_v4/ted_independence_audit.json"))
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    result = run_ted_independence_audit(accepted_path=args.accepted_path, raw_dir=args.raw_dir)
    write_sealed_json(args.out_path, result)

    logger.info(
        "TED independence audit complete: N_power=%d, gate=%s",
        result["n_power"]["value"],
        result["n_power"]["gate_result"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
