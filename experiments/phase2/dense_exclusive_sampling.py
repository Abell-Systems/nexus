"""Pure sampling logic for the pre-registered dense-exclusive sample
(docs/superpowers/specs/2026-09-25-dense-exclusive-srs-redesign.md).

No I/O here -- this module only implements the redesign's SS4 selection
procedure. The scripts that call it are responsible for reading the frozen
source data and writing output.

Supersedes the stratum-proportional + equal-per-demand allocation this
module used to hold (`largest_remainder_allocation`, the old
`select_stratified_sample`) -- deleted, not deprecated, per the redesign
spec SS2: pure SRS needs no allocation step at all.
"""

import random

SAMPLING_SEED = 104
BLIND_EXPORT_SEED = 42


def simple_random_sample(
    population: list[tuple[str, str]], n: int, seed: int
) -> list[tuple[str, str]]:
    """Uniform random draw of n items without replacement from population,
    deterministic given seed. Population is sorted before any RNG call, so
    the result is identical regardless of the caller's input ordering --
    required for bit-for-bit reproducibility. Raises ValueError (from the
    underlying random.Random.sample call) if n exceeds len(population).
    """
    rng = random.Random(seed)
    sorted_population = sorted(population)
    return rng.sample(sorted_population, n)
