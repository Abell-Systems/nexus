import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dense_exclusive_sampling import simple_random_sample


def _population(n: int) -> list[tuple[str, str]]:
    return [(f"D{i:03d}", f"P{i:03d}") for i in range(n)]


def test_simple_random_sample_returns_exactly_n_items():
    population = _population(553)
    sample = simple_random_sample(population, n=66, seed=104)
    assert len(sample) == 66


def test_simple_random_sample_has_no_duplicates():
    population = _population(553)
    sample = simple_random_sample(population, n=66, seed=104)
    assert len(sample) == len(set(sample))


def test_simple_random_sample_only_draws_from_population():
    population = _population(553)
    sample = simple_random_sample(population, n=66, seed=104)
    assert set(sample).issubset(set(population))


def test_simple_random_sample_is_deterministic_across_runs():
    population = _population(553)
    first = simple_random_sample(population, n=66, seed=104)
    second = simple_random_sample(population, n=66, seed=104)
    assert first == second


def test_simple_random_sample_is_order_independent():
    """Drawing from the same logical population in a different insertion
    order must produce the same sample -- the function must sort before
    sampling, not trust caller ordering."""
    population = _population(553)
    reversed_population = list(reversed(population))
    from_forward = simple_random_sample(population, n=66, seed=104)
    from_reversed = simple_random_sample(reversed_population, n=66, seed=104)
    assert from_forward == from_reversed


def test_simple_random_sample_raises_when_n_exceeds_population():
    population = _population(10)
    with pytest.raises(ValueError):
        simple_random_sample(population, n=66, seed=104)


def test_simple_random_sample_different_seeds_differ():
    population = _population(553)
    a = simple_random_sample(population, n=66, seed=104)
    b = simple_random_sample(population, n=66, seed=999)
    assert a != b
