# experiments/phase2/sample_dense_exclusive_srs.py
"""Dense-exclusive sample, SRS redesign: manifest generation.

Per docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md.
Reads the frozen dense-retrieval results verbatim (no re-retrieval),
verifies the population/strata counts the design was frozen against, draws
a pure simple random sample (no allocation step), and writes a manifest --
this script does not decide any sampling parameter, it only consumes what
the spec already committed.

Supersedes experiments/phase2/sample_dense_exclusive_stratified.py
(deleted -- its stratum-proportional + equal-per-demand allocation is the
mechanism this redesign replaces).
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dense_exclusive_sampling import SAMPLING_SEED, simple_random_sample  # noqa: E402

EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256 = (
    "f9ddde0756830f07f88020efa562471ef3bedbe3b9785891e2bde0da1c469d60"
)

SAMPLE_SIZE = 66
POPULATION_SIZE = 553
EXPECTED_INCLUSION_PROBABILITY = SAMPLE_SIZE / POPULATION_SIZE

DECISION_RULE = {
    "p0": 14 / 108,
    "p1": 0.25,
    "alpha_one_sided": 0.05,
    "target_power": 0.80,
    "n": 66,
    "critical_c": 14,
    "actual_alpha": 0.0415,
    "achieved_power": 0.8013,
    "caveat": (
        "actual_alpha/achieved_power are the pre-specified design-stage operating "
        "characteristics for the exact one-sided binomial test, not a claim that the "
        "66 SRS-without-replacement draws are literally independent Bernoulli trials "
        "-- see design spec SS8 for the finite-population dependence disclosure."
    ),
}


def generate(dense_results_path: Path, out_path: Path) -> dict[str, Any]:
    raw_bytes = dense_results_path.read_bytes()
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    dense = json.loads(raw_bytes.decode("utf-8"))

    stratum_by_demand: dict[str, str] = {}
    population: list[tuple[str, str]] = []
    n_stratum_a_demands = 0
    n_stratum_b_demands = 0
    for demand_id, v in dense["per_demand"].items():
        unscored = [
            c["publication_id"]
            for c in v["candidates"]
            if c["provenance"] == "dense_exclusive_new_unscored"
        ]
        stratum = "A" if v["was_bm25_zero_pool"] else "B"
        stratum_by_demand[demand_id] = stratum
        if stratum == "A":
            n_stratum_a_demands += 1
        else:
            n_stratum_b_demands += 1
        for publication_id in unscored:
            population.append((demand_id, publication_id))

    if len(population) != len(set(population)):
        raise ValueError(
            "Population contains duplicate (demand_id, publication_id) identities -- "
            "refusing to sample from a population with duplicate entries, which could "
            "let random.sample draw the same logical pair twice."
        )

    n_stratum_a_population = sum(1 for d, _ in population if stratum_by_demand[d] == "A")
    n_stratum_b_population = sum(1 for d, _ in population if stratum_by_demand[d] == "B")

    if n_stratum_a_demands != 11:
        raise ValueError(f"Expected 11 Stratum A demands, found {n_stratum_a_demands}")
    if n_stratum_b_demands != 19:
        raise ValueError(f"Expected 19 Stratum B demands, found {n_stratum_b_demands}")
    if n_stratum_a_population != 220:
        raise ValueError(f"Expected Stratum A population 220, found {n_stratum_a_population}")
    if n_stratum_b_population != 333:
        raise ValueError(f"Expected Stratum B population 333, found {n_stratum_b_population}")
    if len(population) != POPULATION_SIZE:
        raise ValueError(f"Expected total population {POPULATION_SIZE}, found {len(population)}")

    sample = simple_random_sample(population, n=SAMPLE_SIZE, seed=SAMPLING_SEED)

    selected_rows = [
        {
            "demand_id": demand_id,
            "publication_id": publication_id,
            "stratum": stratum_by_demand[demand_id],
            "inclusion_probability": EXPECTED_INCLUSION_PROBABILITY,
        }
        for demand_id, publication_id in sorted(sample)
    ]

    out = {
        "dataset_id": "nexus-phase2-ted-dense-exclusive-srs-sample-v1",
        "purpose": (
            "DUAL_ANNOTATION_POOL -- #104/#113 dense-exclusive SRS sample, "
            "docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md"
        ),
        "source_dense_retrieval_results_path": str(dense_results_path.resolve().relative_to(REPO_ROOT))
        if dense_results_path.resolve().is_relative_to(REPO_ROOT)
        else str(dense_results_path),
        "source_dense_retrieval_results_sha256": actual_sha256,
        "sampling_seed": SAMPLING_SEED,
        "population_size": len(population),
        "sample_size": len(sample),
        "inclusion_probability": EXPECTED_INCLUSION_PROBABILITY,
        "n_stratum_a_population": n_stratum_a_population,
        "n_stratum_b_population": n_stratum_b_population,
        "n_stratum_a_sampled": sum(1 for r in selected_rows if r["stratum"] == "A"),
        "n_stratum_b_sampled": sum(1 for r in selected_rows if r["stratum"] == "B"),
        "decision_rule": DECISION_RULE,
        "selected": selected_rows,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    print(
        f"Wrote {len(sample)} SRS-selected pairs "
        f"({out['n_stratum_a_sampled']} A / {out['n_stratum_b_sampled']} B, diagnostic split) "
        f"to {out_path}"
    )
    return out


def main() -> int:
    dense_results_path = REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_at_scale_dense_retrieval_results.json"
    actual_sha256 = hashlib.sha256(dense_results_path.read_bytes()).hexdigest()
    if actual_sha256 != EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256:
        raise ValueError(
            f"Source file hash mismatch: expected {EXPECTED_DENSE_RETRIEVAL_RESULTS_SHA256}, "
            f"got {actual_sha256}. This script must BLOCK rather than sample against data "
            "the design spec was not frozen against."
        )
    generate(
        dense_results_path=dense_results_path,
        out_path=REPO_ROOT / "data" / "annotations" / "ted_dense_exclusive_srs_sample_manifest.json",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
