# experiments/phase2/sample_dense_exclusive_stratified.py
"""#104 dense-exclusive stratified sample, step 1: manifest generation.

Per docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md.
Reads the frozen dense-retrieval results verbatim (no re-retrieval), verifies
the population/strata counts and source hash the design was frozen against,
computes the pre-registered demand allocation, draws the seeded sample, and
writes a manifest -- this script does not decide any sampling parameter, it
only consumes what the spec already committed.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dense_exclusive_sampling import (  # noqa: E402
    SAMPLING_SEED,
    largest_remainder_allocation,
    select_stratified_sample,
)

EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256 = (
    "f9ddde0756830f07f88020efa562471ef3bedbe3b9785891e2bde0da1c469d60"
)

EXPECTED_STRATUM_A_ALLOCATION = {
    "122428-2024": 3, "146289-2024": 3, "158024-2024": 3, "221305-2025": 3,
    "273005-2025": 2, "410719-2024": 2, "588217-2024": 2, "642378-2025": 2,
    "654218-2024": 2, "794374-2025": 2, "820594-2025": 2,
}

EXPECTED_STRATUM_B_ALLOCATION = {
    "104441-2025": 3, "137639-2024": 3, "140590-2024": 2, "200095-2024": 2,
    "22543-2024": 2, "264820-2024": 2, "268550-2024": 2, "277089-2025": 2,
    "315512-2025": 2, "368294-2025": 2, "380300-2024": 2, "42938-2024": 2,
    "454027-2024": 2, "498443-2025": 2, "566290-2025": 2, "584867-2024": 2,
    "696940-2025": 2, "814207-2025": 2, "89204-2025": 2,
}

DECISION_RULE = {
    "p0": 14 / 108,
    "p1": 0.25,
    "alpha_one_sided": 0.05,
    "target_power": 0.80,
    "n": 66,
    "critical_c": 14,
    "actual_alpha": 0.0415,
    "achieved_power": 0.8013,
}


def generate(dense_results_path: Path, out_path: Path) -> dict[str, Any]:
    raw_bytes = dense_results_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256 != EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256:
        raise ValueError(
            f"Source file hash mismatch: expected {EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256}, "
            f"got {actual_sha256}. This script must BLOCK rather than sample against data "
            "the design spec was not frozen against."
        )
    dense = json.loads(raw_bytes.decode("utf-8"))

    sizes_a: dict[str, int] = {}
    sizes_b: dict[str, int] = {}
    pool_a: dict[str, list[str]] = {}
    pool_b: dict[str, list[str]] = {}
    for demand_id, v in dense["per_demand"].items():
        unscored = [
            c["publication_id"]
            for c in v["candidates"]
            if c["provenance"] == "dense_exclusive_new_unscored"
        ]
        if v["was_bm25_zero_pool"]:
            sizes_a[demand_id] = len(unscored)
            pool_a[demand_id] = unscored
        else:
            sizes_b[demand_id] = len(unscored)
            pool_b[demand_id] = unscored

    if len(sizes_a) != 11:
        raise ValueError(f"Expected 11 Stratum A demands, found {len(sizes_a)}")
    if len(sizes_b) != 19:
        raise ValueError(f"Expected 19 Stratum B demands, found {len(sizes_b)}")
    if sum(sizes_a.values()) != 220:
        raise ValueError(f"Expected Stratum A total 220, found {sum(sizes_a.values())}")
    if sum(sizes_b.values()) != 333:
        raise ValueError(f"Expected Stratum B total 333, found {sum(sizes_b.values())}")

    allocation_a = largest_remainder_allocation(26, sizes_a)
    allocation_b = largest_remainder_allocation(40, sizes_b)
    if allocation_a != EXPECTED_STRATUM_A_ALLOCATION:
        raise ValueError(
            f"Stratum A allocation drift from pre-registered table: {allocation_a} != "
            f"{EXPECTED_STRATUM_A_ALLOCATION}"
        )
    if allocation_b != EXPECTED_STRATUM_B_ALLOCATION:
        raise ValueError(
            f"Stratum B allocation drift from pre-registered table: {allocation_b} != "
            f"{EXPECTED_STRATUM_B_ALLOCATION}"
        )

    combined_allocation = {**allocation_a, **allocation_b}
    combined_pool = {**pool_a, **pool_b}
    selected = select_stratified_sample(combined_pool, combined_allocation, seed=SAMPLING_SEED)

    total_selected = sum(len(v) for v in selected.values())
    if total_selected != 66:
        raise ValueError(f"Expected 66 total selected pairs, got {total_selected}")

    stratum_by_demand = {**{d: "A" for d in sizes_a}, **{d: "B" for d in sizes_b}}
    selected_rows = [
        {"demand_id": demand_id, "publication_id": publication_id, "stratum": stratum_by_demand[demand_id]}
        for demand_id in sorted(selected)
        for publication_id in selected[demand_id]
    ]

    out = {
        "dataset_id": "nexus-phase2-ted-dense-exclusive-stratified-sample-v1",
        "purpose": "DUAL_ANNOTATION_POOL -- #104 dense-exclusive stratified sample, "
                   "docs/superpowers/specs/2026-09-23-dense-exclusive-stratified-sample-design.md",
        "source_dense_retrieval_results_path": str(dense_results_path.relative_to(REPO_ROOT)),
        "source_dense_retrieval_results_sha256": actual_sha256,
        "sampling_seed": SAMPLING_SEED,
        "n_total": total_selected,
        "n_stratum_a": sum(allocation_a.values()),
        "n_stratum_b": sum(allocation_b.values()),
        "stratum_a_allocation": allocation_a,
        "stratum_b_allocation": allocation_b,
        "decision_rule": DECISION_RULE,
        "selected": selected_rows,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(f"Wrote {total_selected} selected pairs ({out['n_stratum_a']} A / {out['n_stratum_b']} B) to {out_path}")
    return out


def main() -> int:
    generate(
        dense_results_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_retrieval_results.json",
        out_path=REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_stratified_sample_manifest.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
