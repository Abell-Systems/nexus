#!/usr/bin/env python3
"""A priori power analysis for the Phase 2 primary hypothesis test (H1).

Protocol: docs/empirical-study-protocol.md §3.2 (Reproducible A Priori Power
Analysis Procedure). Determines the minimum demand sample size |D| for which
a paired two-sided Wilcoxon signed-rank test on nDCG@10 differences
(hybrid vs. best single-signal baseline) reaches 80% power at alpha=0.05.

This is a pre-registration artifact: the output JSON must be frozen and
committed *before* any Phase 2 test-split result is inspected. Re-running
this script with the same arguments and seed reproduces byte-identical
numeric output (RNG is seeded once per effect size).

Simulation design (protocol-mandated parameters, see §3.2):
- Paired differences Delta = nDCG@10_hybrid - nDCG@10_best_single are modeled
  as a zero-inflated continuous distribution bounded in [-1, 1]: a point mass
  at 0 (tied metric outcomes) mixed with a symmetric Beta(a, a) shape mapped
  onto [-1, 1], shifted by a location parameter and clipped to the bound.
- The location parameter is solved by bisection so the simulated sample's
  median/IQR ratio matches the target standardized effect size theta. The
  shape parameter `a` and tie rate are fixed, literature-informed assumptions
  (documented below) rather than fitted — Phase 1's n=3 pilot demands are far
  too few to estimate a stable dispersion, and the protocol (§3.1) forbids
  using Phase 1 to ground Phase 2 statistical claims.
- Power at each candidate N is the fraction of B Monte Carlo trials where a
  paired Wilcoxon signed-rank test (scipy, zero_method="wilcox", which drops
  exact ties — the standard treatment of the modeled zero-inflation) rejects
  H0 at alpha.

# ponytail: tie_rate=0.10 and Beta shape a=2.5 are documented a priori
# assumptions, not fitted from data (none exists yet at adequate scale).
# Revisit once Phase 2 development-split data is available for a sensitivity
# re-run — this script accepts --tie-rate / --shape for that purpose.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

DEFAULT_EFFECT_SIZES = (0.2, 0.5, 0.8)  # conventional small/medium/large bands


def _sample_deltas(
    n: int,
    loc: float,
    rng: np.random.Generator,
    shape: float,
    tie_rate: float,
) -> np.ndarray:
    """Draws n paired nDCG@10 differences from the zero-inflated bounded model."""
    beta = rng.beta(shape, shape, size=n)
    deltas = np.clip(2.0 * (beta - 0.5) + loc, -1.0, 1.0)
    deltas[rng.random(n) < tie_rate] = 0.0
    return deltas


def _realized_theta(
    loc: float, rng: np.random.Generator, shape: float, tie_rate: float, calib_size: int = 200_000
) -> float:
    """Standardized effect size (median/IQR) realized by a given location shift."""
    sample = _sample_deltas(calib_size, loc, rng, shape, tie_rate)
    q75, q25 = np.percentile(sample, [75, 25])
    iqr = q75 - q25
    return 0.0 if iqr == 0 else float(np.median(sample) / iqr)


def _calibrate_location(
    target_theta: float, rng: np.random.Generator, shape: float, tie_rate: float, tolerance: float = 1e-3
) -> float:
    """Bisection search for the location shift realizing the target standardized effect size.

    theta=0 is handled directly as loc=0: the tie atom at 0 makes the mixture's
    median "sticky" near loc=0 (median reads exactly 0 for a whole range of small
    shifts before jumping), so bisecting to a *measured* zero can land on a
    positive, asymmetric loc that inflates Type I error under the null. Only
    loc=0 is exactly symmetric.
    """
    if abs(target_theta) < 1e-12:
        return 0.0
    lo, hi = 0.0, 1.0
    mid = 0.0
    for _ in range(40):
        mid = (lo + hi) / 2
        realized = _realized_theta(mid, rng, shape, tie_rate)
        if abs(realized - target_theta) < tolerance:
            break
        if realized < target_theta:
            lo = mid
        else:
            hi = mid
    return mid


def _power_at_n(
    n: int, loc: float, rng: np.random.Generator, shape: float, tie_rate: float, alpha: float, iterations: int
) -> float:
    """Monte Carlo power estimate: fraction of B trials rejecting H0 at n paired demands."""
    rejects = 0
    for _ in range(iterations):
        deltas = _sample_deltas(n, loc, rng, shape, tie_rate)
        if not np.any(deltas != 0.0):
            continue  # all ties: Wilcoxon undefined, correctly counts as a non-rejection
        _, p_value = wilcoxon(deltas, alternative="two-sided", zero_method="wilcox")
        if p_value < alpha:
            rejects += 1
    return rejects / iterations


def run_power_analysis(
    effect_sizes: tuple[float, ...],
    alpha: float,
    target_power: float,
    n_min: int,
    n_max: int,
    step: int,
    iterations: int,
    tie_rate: float,
    shape: float,
    seed: int,
) -> dict:
    """Runs the full pre-registered grid search and returns the artifact dict."""
    results = []
    for theta in effect_sizes:
        rng = np.random.default_rng(seed)
        loc = _calibrate_location(theta, rng, shape, tie_rate)
        power_curve: dict[int, float] = {}
        n_star: int | None = None
        for n in range(n_min, n_max + 1, step):
            power = _power_at_n(n, loc, rng, shape, tie_rate, alpha, iterations)
            power_curve[n] = power
            if n_star is None and power >= target_power:
                n_star = n
        results.append(
            {
                "target_theta": theta,
                "calibrated_location": loc,
                "power_curve": power_curve,
                "n_min": n_star,
            }
        )
    return {
        "protocol_reference": "docs/empirical-study-protocol.md §3.2",
        "test": "paired two-sided Wilcoxon signed-rank test",
        "alpha": alpha,
        "target_power": target_power,
        "iterations_per_point": iterations,
        "candidate_grid": {"n_min": n_min, "n_max": n_max, "step": step},
        "assumptions": {"tie_rate": tie_rate, "beta_shape": shape},
        "seed": seed,
        "results": results,
    }


def _self_check() -> None:
    """Sanity check: under the null (theta=0), rejection rate must track alpha."""
    rng = np.random.default_rng(7)
    loc = _calibrate_location(0.0, rng, shape=2.5, tie_rate=0.10)
    power = _power_at_n(n=60, loc=loc, rng=rng, shape=2.5, tie_rate=0.10, alpha=0.05, iterations=2000)
    assert power < 0.12, f"Type I error inflated under null: observed {power:.3f}, expected ~0.05"

    # Power must not decrease as N grows, for a fixed non-null effect.
    rng = np.random.default_rng(7)
    loc = _calibrate_location(0.5, rng, shape=2.5, tie_rate=0.10)
    power_small_n = _power_at_n(n=15, loc=loc, rng=rng, shape=2.5, tie_rate=0.10, alpha=0.05, iterations=2000)
    power_large_n = _power_at_n(n=80, loc=loc, rng=rng, shape=2.5, tie_rate=0.10, alpha=0.05, iterations=2000)
    assert power_large_n >= power_small_n, "Power did not increase with sample size"
    print("Self-check passed: null calibration and power monotonicity hold.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--power", type=float, default=0.80, help="Target statistical power (1 - beta).")
    parser.add_argument("--n-min", type=int, default=15)
    parser.add_argument("--n-max", type=int, default=100)
    parser.add_argument("--step", type=int, default=5, help="Grid step over |D|. Use 1 for the literal protocol grid (slow: ~15 min).")
    parser.add_argument("--iterations", type=int, default=10_000, help="Monte Carlo trials per grid point (protocol: B=10,000).")
    parser.add_argument(
        "--effect-sizes",
        type=str,
        default=",".join(str(t) for t in DEFAULT_EFFECT_SIZES),
        help="Comma-separated standardized effect sizes (median/IQR) to pre-register power for.",
    )
    parser.add_argument("--tie-rate", type=float, default=0.10)
    parser.add_argument("--shape", type=float, default=2.5, help="Beta(shape, shape) dispersion parameter.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("data/experiments/power_analysis_wilcoxon.json"))
    parser.add_argument("--self-check", action="store_true", help="Run the sanity self-check and exit.")
    args = parser.parse_args()

    if args.self_check:
        _self_check()
        return 0

    effect_sizes = tuple(float(t) for t in args.effect_sizes.split(","))

    print("Running pre-registered a priori power analysis (Wilcoxon signed-rank, paired)...")
    print(f"  alpha={args.alpha}  target_power={args.power}  B={args.iterations}  grid=[{args.n_min},{args.n_max}] step={args.step}")
    start = time.time()
    artifact = run_power_analysis(
        effect_sizes=effect_sizes,
        alpha=args.alpha,
        target_power=args.power,
        n_min=args.n_min,
        n_max=args.n_max,
        step=args.step,
        iterations=args.iterations,
        tie_rate=args.tie_rate,
        shape=args.shape,
        seed=args.seed,
    )
    elapsed = time.time() - start

    print("=" * 80)
    for result in artifact["results"]:
        n_min = result["n_min"]
        theta = result["target_theta"]
        label = f"N_min={n_min}" if n_min is not None else f"NOT REACHED within [{args.n_min},{args.n_max}]"
        print(f"  theta={theta:.2f}  ->  {label}")
    print(f"Elapsed: {elapsed:.1f}s")
    print("=" * 80)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Pre-registration artifact written to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
