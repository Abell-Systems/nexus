"""#103 Freeze: seals the TED-independent corpus and its organization-aware Dev/Test
split (ADR 0029, ADR 0030), gated on #102's TED independence audit passing N_power>=60.

Partition universe is INDEPENDENT + UNKNOWN only (PSEUDOREPLICATE demands are
excluded per `organization_aware_split`'s own contract). The TED pool's UNKNOWN
count is 0 (organization_raw is a mandatory structured field on every TED notice,
ADR 0034), so the universe here is exactly the 65 INDEPENDENT demands.

Stratification key is each demand's CPV division (2-digit), the same structural
sector label #102 already computed -- descriptive concentration reporting and
Dev/Test stratification reuse the same non-inferred signal, nothing new is
introduced here.

100% offline, zero network connectivity.
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from application.evaluation.organization_aware_split import organization_aware_split  # noqa: E402
from domain.models.annotation import DemandIndependenceStatus  # noqa: E402
from experiments.phase2.audit_ted_independence import extract_cpv_code  # noqa: E402

logger = logging.getLogger("experiments.phase2.freeze_ted_corpus")

DEV_FRACTION = 0.5
BASE_SEED = 42
MISSING_STRATUM = "_NO_CPV"


def compute_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_sealed_json(target_path: Path, data: Any) -> str:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    target_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    sidecar_path = target_path.with_suffix(".sha256")
    sidecar_path.write_text(f"{sha256_hex}  {target_path.name}\n", encoding="utf-8")
    return sha256_hex


def freeze_ted_corpus(
    accepted_path: Path,
    independence_audit_path: Path,
    raw_dir: Path,
    out_dir: Path,
) -> dict[str, Any]:
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    audit = json.loads(independence_audit_path.read_text(encoding="utf-8"))

    if audit["n_power"]["gate_result"] != "PASS":
        raise ValueError(
            f"Refusing to freeze: independence audit gate is {audit['n_power']['gate_result']}, "
            f"N_power={audit['n_power']['value']} < {audit['n_power']['gate_threshold']}"
        )

    org_axis = audit["organization_axis"]
    status_by_id: dict[str, DemandIndependenceStatus] = {}
    for demand_id in org_axis["independent"]:
        status_by_id[demand_id] = DemandIndependenceStatus.INDEPENDENT
    for demand_id in org_axis["pseudoreplicate"]:
        status_by_id[demand_id] = DemandIndependenceStatus.PSEUDOREPLICATE
    for demand_id in org_axis["unknown"]:
        status_by_id[demand_id] = DemandIndependenceStatus.UNKNOWN

    accepted_by_id = {d["demand_id"]: d for d in accepted}

    # Partition universe: INDEPENDENT + UNKNOWN only (organization_aware_split
    # forbids PSEUDOREPLICATE in its input universe).
    universe_ids = sorted(org_axis["independent"] + org_axis["unknown"])
    universe = [accepted_by_id[demand_id] for demand_id in universe_ids]

    def _cpv_stratum(demand: dict[str, Any]) -> str:
        raw_path = raw_dir / "ted" / f"{demand['demand_id']}.html"
        if not raw_path.is_file():
            return MISSING_STRATUM
        cpv = extract_cpv_code(raw_path.read_text(encoding="utf-8"))
        return cpv[:2] if cpv else MISSING_STRATUM

    result = organization_aware_split(
        items=universe,
        item_id=lambda d: d["demand_id"],
        org_key=lambda d: d.get("organization_raw"),
        status_key=lambda d: status_by_id[d["demand_id"]],
        stratum_key=_cpv_stratum,
        dev_fraction=DEV_FRACTION,
        base_seed=BASE_SEED,
        unknown_policy="dev_only",
    )

    dev_ids = sorted(result.dev.demand_ids)
    test_ids = sorted(result.test.demand_ids)

    dev_orgs = {accepted_by_id[d]["organization_raw"] for d in dev_ids if status_by_id[d] == DemandIndependenceStatus.INDEPENDENT}
    test_orgs = {accepted_by_id[d]["organization_raw"] for d in test_ids if status_by_id[d] == DemandIndependenceStatus.INDEPENDENT}
    org_overlap = dev_orgs & test_orgs
    if org_overlap:
        raise ValueError(f"Cross-partition organization overlap detected: {org_overlap}")

    frozen_corpus = {
        "dataset_id": "nexus-phase2-ted-independent-corpus-v1",
        "source": "ted",
        "n_power": len(universe_ids),
        "independence_audit_sha256": compute_file_sha256(independence_audit_path),
        "demands": [accepted_by_id[demand_id] for demand_id in universe_ids],
    }
    corpus_sha = write_sealed_json(out_dir / "ted_independent_corpus_v1.json", frozen_corpus)

    split_dataset = {
        "dataset_id": "nexus-phase2-ted-devtest-split-v1",
        "dev": dev_ids,
        "test": test_ids,
    }
    split_sha = write_sealed_json(out_dir / "ted_devtest_split_v1.json", split_dataset)

    manifest = {
        "manifest_id": "nexus-phase2-ted-freeze-v1",
        "execution_timestamp": datetime.now(UTC).isoformat(),
        "corpus_sha256": corpus_sha,
        "split_sha256": split_sha,
        "n_power": len(universe_ids),
        "independent_count": result.independent_count,
        "unknown_count": result.unknown_count,
        "pseudoreplicate_count_excluded": len(org_axis["pseudoreplicate"]),
        "dev_count": len(dev_ids),
        "test_count": len(test_ids),
        "per_stratum_counts": {c.stratum: {"dev": c.dev, "test": c.test} for c in result.per_stratum_counts},
        "organization_isolation": "exact",
        "organization_overlap": sorted(org_overlap),
        "dev_fraction": DEV_FRACTION,
        "base_seed": BASE_SEED,
        "unknown_split_policy": "dev_only",
        "stratification_key": "cpv_division",
        "not_combined_with": "data/experiments/phase2_v3 (EEN/POD, 76 accepted, all organization_raw=UNKNOWN, N_power contribution=0) -- kept as a separate, distinctly-labeled dataset, never merged into this N as if 65+76 were 141 independent observations",
    }
    write_sealed_json(out_dir / "ted_freeze_manifest_v1.json", manifest)

    logger.info(
        "Frozen: N_power=%d, dev=%d, test=%d, org_overlap=%s",
        len(universe_ids), len(dev_ids), len(test_ids), bool(org_overlap),
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="#103 freeze TED-independent corpus + Dev/Test split.")
    parser.add_argument("--accepted-path", type=Path, default=Path("data/experiments/phase2_v4/candidates_accepted.json"))
    parser.add_argument("--independence-audit-path", type=Path, default=Path("data/experiments/phase2_v4/ted_independence_audit.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/phase2_candidates_ted"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/experiments/phase2_v4"))
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    freeze_ted_corpus(
        accepted_path=args.accepted_path,
        independence_audit_path=args.independence_audit_path,
        raw_dir=args.raw_dir,
        out_dir=args.out_dir,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
