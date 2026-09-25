import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sample_dense_exclusive_srs import EXPECTED_INCLUSION_PROBABILITY, generate


def _make_dense_results(tmp_path: Path) -> Path:
    """Builds a synthetic dense-retrieval-results fixture matching the real
    file's shape: 11 Stratum A demands (was_bm25_zero_pool=True, 20
    dense_exclusive_new_unscored candidates each = 220), 19 Stratum B
    demands (was_bm25_zero_pool=False, varying counts summing to 333).
    Total 553, matching the real frozen population's invariants."""
    per_demand = {}
    for i in range(11):
        demand_id = f"A{i:03d}-2024"
        candidates = [
            {"publication_id": f"{demand_id}-pub{j}", "provenance": "dense_exclusive_new_unscored"}
            for j in range(20)
        ]
        # One already-scored candidate per demand, must be filtered out by provenance.
        candidates.append({"publication_id": f"{demand_id}-scored", "provenance": "bm25_gold_scored"})
        per_demand[demand_id] = {"was_bm25_zero_pool": True, "candidates": candidates}

    # 19 Stratum B demands, sizes summing to 333 (17 x 17 = 289, + 2 x 22 = 44 -> 333).
    b_sizes = [17] * 17 + [22, 22]
    assert sum(b_sizes) == 333
    for i, size in enumerate(b_sizes):
        demand_id = f"B{i:03d}-2024"
        candidates = [
            {"publication_id": f"{demand_id}-pub{j}", "provenance": "dense_exclusive_new_unscored"}
            for j in range(size)
        ]
        per_demand[demand_id] = {"was_bm25_zero_pool": False, "candidates": candidates}

    dense_results_path = tmp_path / "dense_results.json"
    dense_results_path.write_text(json.dumps({"per_demand": per_demand}), encoding="utf-8")
    return dense_results_path


def test_generate_selects_exactly_66_pairs(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    assert len(out["selected"]) == 66
    assert out["sample_size"] == 66


def test_generate_selected_pairs_have_no_duplicates(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    ids = [(row["demand_id"], row["publication_id"]) for row in out["selected"]]
    assert len(ids) == len(set(ids))


def test_generate_every_selected_pair_exists_in_population(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    dense = json.loads(dense_results_path.read_text(encoding="utf-8"))
    population_ids = set()
    for demand_id, v in dense["per_demand"].items():
        for c in v["candidates"]:
            if c["provenance"] == "dense_exclusive_new_unscored":
                population_ids.add((demand_id, c["publication_id"]))

    out = generate(dense_results_path, tmp_path / "manifest.json")
    for row in out["selected"]:
        assert (row["demand_id"], row["publication_id"]) in population_ids


def test_generate_excludes_already_scored_candidates(tmp_path):
    """The one 'bm25_gold_scored' candidate injected per Stratum A demand in
    the fixture must never appear in the population or the sample -- proves
    the provenance filter is applied, not just population size checked."""
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    for row in out["selected"]:
        assert not row["publication_id"].endswith("-scored")


def test_generate_is_deterministic_with_same_seed_and_population(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    first = generate(dense_results_path, tmp_path / "manifest1.json")
    second = generate(dense_results_path, tmp_path / "manifest2.json")
    assert first["selected"] == second["selected"]


def test_generate_records_correct_inclusion_probability_per_pair(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    assert out["inclusion_probability"] == EXPECTED_INCLUSION_PROBABILITY
    for row in out["selected"]:
        assert row["inclusion_probability"] == EXPECTED_INCLUSION_PROBABILITY


def test_generate_tags_each_selected_pair_with_correct_stratum(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    for row in out["selected"]:
        if row["demand_id"].startswith("A"):
            assert row["stratum"] == "A"
        else:
            assert row["stratum"] == "B"


def test_generate_reports_population_stratum_totals(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out = generate(dense_results_path, tmp_path / "manifest.json")
    assert out["population_size"] == 553
    assert out["n_stratum_a_population"] == 220
    assert out["n_stratum_b_population"] == 333


def test_generate_raises_on_wrong_stratum_a_demand_count(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    dense = json.loads(dense_results_path.read_text(encoding="utf-8"))
    # Flip one Stratum A demand to Stratum B, breaking the 11/19 invariant.
    first_a_key = next(k for k in dense["per_demand"] if k.startswith("A"))
    dense["per_demand"][first_a_key]["was_bm25_zero_pool"] = False
    dense_results_path.write_text(json.dumps(dense), encoding="utf-8")

    with pytest.raises(ValueError, match="Stratum A"):
        generate(dense_results_path, tmp_path / "manifest.json")


def test_generate_raises_on_duplicate_population_identity(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    dense = json.loads(dense_results_path.read_text(encoding="utf-8"))
    first_a_key = next(k for k in dense["per_demand"] if k.startswith("A"))
    # Duplicate the first candidate's publication_id within the same demand.
    dupe = dict(dense["per_demand"][first_a_key]["candidates"][0])
    dense["per_demand"][first_a_key]["candidates"].append(dupe)
    dense_results_path.write_text(json.dumps(dense), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        generate(dense_results_path, tmp_path / "manifest.json")


def test_generate_writes_manifest_file_and_sha256_sidecar(tmp_path):
    dense_results_path = _make_dense_results(tmp_path)
    out_path = tmp_path / "manifest.json"
    generate(dense_results_path, out_path)
    assert out_path.is_file()
    assert out_path.with_suffix(".sha256").is_file()

    import hashlib
    written_bytes = out_path.read_bytes()
    sidecar = out_path.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(written_bytes).hexdigest() == sidecar


def test_generate_does_not_write_any_annotation_file(tmp_path):
    """This script's job stops at the manifest -- no CSV or blind-export
    artifact must be created as a side effect."""
    dense_results_path = _make_dense_results(tmp_path)
    generate(dense_results_path, tmp_path / "manifest.json")
    csv_files = list(tmp_path.glob("*.csv"))
    assert csv_files == []
