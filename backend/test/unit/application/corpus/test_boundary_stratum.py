import pytest

from application.corpus.boundary_stratum import build_control_sample, is_boundary_case


def test_is_boundary_case_true_within_tolerance():
    assert is_boundary_case(word_count=20, min_word_count=25, tolerance=10) is True
    assert is_boundary_case(word_count=35, min_word_count=25, tolerance=10) is True
    assert is_boundary_case(word_count=15, min_word_count=25, tolerance=10) is True


def test_is_boundary_case_false_outside_tolerance():
    assert is_boundary_case(word_count=14, min_word_count=25, tolerance=10) is False
    assert is_boundary_case(word_count=36, min_word_count=25, tolerance=10) is False


def test_build_control_sample_includes_full_boundary_stratum():
    candidates = [
        {"demand_id": "b1", "word_count": 20, "status": "accepted", "language_code": "en"},
        {"demand_id": "b2", "word_count": 30, "status": "rejected", "language_code": "de"},
    ] + [
        {"demand_id": f"r{i}", "word_count": 100, "status": "accepted", "language_code": "en"}
        for i in range(10)
    ]
    sample = build_control_sample(candidates, min_word_count=25, target_size=5, seed=1)
    assert set(sample.boundary_ids) == {"b1", "b2"}
    assert len(sample.fill_ids) == 3
    assert len(set(sample.all_ids)) == 5


def test_build_control_sample_raises_when_target_smaller_than_boundary():
    candidates = [
        {"demand_id": "b1", "word_count": 20, "status": "accepted", "language_code": "en"},
        {"demand_id": "b2", "word_count": 30, "status": "rejected", "language_code": "de"},
    ]
    with pytest.raises(ValueError):
        build_control_sample(candidates, min_word_count=25, target_size=1, seed=1)


def test_build_control_sample_is_deterministic_regardless_of_input_order():
    candidates = [
        {
            "demand_id": f"r{i}",
            "word_count": 100,
            "status": "accepted" if i % 2 == 0 else "rejected",
            "language_code": "en" if i % 3 else "de",
        }
        for i in range(20)
    ]
    s1 = build_control_sample(candidates, min_word_count=25, target_size=10, seed=7)
    s2 = build_control_sample(list(reversed(candidates)), min_word_count=25, target_size=10, seed=7)
    assert s1 == s2


def test_build_control_sample_raises_when_not_enough_candidates():
    candidates = [
        {"demand_id": "r1", "word_count": 100, "status": "accepted", "language_code": "en"},
    ]
    with pytest.raises(ValueError):
        build_control_sample(candidates, min_word_count=25, target_size=5, seed=1)
