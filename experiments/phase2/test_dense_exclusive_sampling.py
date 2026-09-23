import pytest

from dense_exclusive_sampling import largest_remainder_allocation, select_stratified_sample

STRATUM_A_SIZES = {d: 20 for d in [
    "122428-2024", "146289-2024", "158024-2024", "221305-2025", "273005-2025",
    "410719-2024", "588217-2024", "642378-2025", "654218-2024", "794374-2025",
    "820594-2025",
]}

STRATUM_A_EXPECTED = {
    "122428-2024": 3, "146289-2024": 3, "158024-2024": 3, "221305-2025": 3,
    "273005-2025": 2, "410719-2024": 2, "588217-2024": 2, "642378-2025": 2,
    "654218-2024": 2, "794374-2025": 2, "820594-2025": 2,
}

STRATUM_B_SIZES = {
    "104441-2025": 19, "137639-2024": 20, "140590-2024": 16, "200095-2024": 20,
    "22543-2024": 19, "264820-2024": 19, "268550-2024": 18, "277089-2025": 17,
    "315512-2025": 19, "368294-2025": 19, "380300-2024": 20, "42938-2024": 20,
    "454027-2024": 10, "498443-2025": 20, "566290-2025": 16, "584867-2024": 20,
    "696940-2025": 19, "814207-2025": 13, "89204-2025": 9,
}

STRATUM_B_EXPECTED = {
    "104441-2025": 3, "137639-2024": 3, "140590-2024": 2, "200095-2024": 2,
    "22543-2024": 2, "264820-2024": 2, "268550-2024": 2, "277089-2025": 2,
    "315512-2025": 2, "368294-2025": 2, "380300-2024": 2, "42938-2024": 2,
    "454027-2024": 2, "498443-2025": 2, "566290-2025": 2, "584867-2024": 2,
    "696940-2025": 2, "814207-2025": 2, "89204-2025": 2,
}


def test_largest_remainder_allocation_matches_stratum_a_table():
    assert largest_remainder_allocation(26, STRATUM_A_SIZES) == STRATUM_A_EXPECTED


def test_largest_remainder_allocation_matches_stratum_b_table():
    assert largest_remainder_allocation(40, STRATUM_B_SIZES) == STRATUM_B_EXPECTED


def test_largest_remainder_allocation_sums_to_total_n():
    alloc = largest_remainder_allocation(26, STRATUM_A_SIZES)
    assert sum(alloc.values()) == 26


def test_largest_remainder_allocation_raises_when_total_exceeds_capacity():
    with pytest.raises(ValueError):
        largest_remainder_allocation(1000, STRATUM_A_SIZES)


def test_largest_remainder_allocation_raises_when_allocation_exceeds_one_demand_size():
    tiny = {"a": 1, "b": 100}
    with pytest.raises(ValueError):
        largest_remainder_allocation(3, tiny)


def test_select_stratified_sample_respects_allocation_counts():
    candidates = {d: [f"{d}-p{i}" for i in range(20)] for d in STRATUM_A_SIZES}
    selected = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    for demand_id, k in STRATUM_A_EXPECTED.items():
        assert len(selected[demand_id]) == k


def test_select_stratified_sample_never_selects_duplicate_within_demand():
    candidates = {d: [f"{d}-p{i}" for i in range(20)] for d in STRATUM_A_SIZES}
    selected = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    for demand_id, picks in selected.items():
        assert len(picks) == len(set(picks))


def test_select_stratified_sample_is_deterministic_across_runs():
    candidates = {d: [f"{d}-p{i}" for i in range(20)] for d in STRATUM_A_SIZES}
    first = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    second = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    assert first == second


def test_select_stratified_sample_only_picks_from_given_pool():
    candidates = {d: [f"{d}-p{i}" for i in range(20)] for d in STRATUM_A_SIZES}
    selected = select_stratified_sample(candidates, STRATUM_A_EXPECTED, seed=104)
    for demand_id, picks in selected.items():
        assert set(picks).issubset(set(candidates[demand_id]))
