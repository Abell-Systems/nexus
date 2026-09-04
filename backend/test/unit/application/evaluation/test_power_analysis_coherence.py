"""Tests verifying coherence with the pre-registered frozen power analysis artifact and architecture invariants."""

import importlib
import json
import pkgutil
from pathlib import Path

import application.evaluation.statistics as stats_pkg


def test_frozen_power_analysis_artifact_coherence():
    """Verify that empirical benchmark sizing aligns strictly with the pre-registered power analysis.

    Under docs/empirical-study-protocol.md §3.2 and data/experiments/power_analysis_wilcoxon.json:
    - Target standardized effect theta = 0.20 requires minimum N = 60 demands.
    - Medium-large effect theta >= 0.50 requires minimum N = 15 demands (the protocol grid floor).
    - Alpha = 0.05, Target Power = 0.80, B = 10,000 iterations per grid point.
    """
    artifact_path = Path("data/experiments/power_analysis_wilcoxon.json")
    assert artifact_path.exists(), f"Pre-registered artifact missing at {artifact_path}"

    with open(artifact_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["alpha"] == 0.05
    assert data["target_power"] == 0.80
    assert data["test"] == "paired two-sided Wilcoxon signed-rank test"
    assert data["iterations_per_point"] == 10_000
    assert data["seed"] == 42

    results_by_theta = {r["target_theta"]: r for r in data["results"]}

    # theta = 0.20 -> N = 60
    assert 0.2 in results_by_theta
    r_small = results_by_theta[0.2]
    assert r_small["n_min"] == 60
    assert r_small["power_curve"]["60"] >= 0.80

    # theta >= 0.50 -> N = 15 floor
    assert 0.5 in results_by_theta
    r_med = results_by_theta[0.5]
    assert r_med["n_min"] == 15
    assert r_med["power_curve"]["15"] >= 0.80

    assert 0.8 in results_by_theta
    r_large = results_by_theta[0.8]
    assert r_large["n_min"] == 15
    assert r_large["power_curve"]["15"] >= 0.80

    # Macro trend: for theta = 0.2, power at N=100 is higher than power at N=15
    p_15 = r_small["power_curve"]["15"]
    p_100 = r_small["power_curve"]["100"]
    assert p_100 > p_15, f"Expected macro power increase from N=15 ({p_15}) to N=100 ({p_100})"


def test_statistics_layer_has_zero_external_provider_or_matching_imports():
    """Verify ADR 0010 architectural isolation: statistics imports neither matching nor providers."""
    forbidden_prefixes = (
        "domain.models.matching",
        "domain.protocols.matching",
        "application.matching",
        "infrastructure",
        "google",
        "openai",
        "anthropic",
        "groq",
        "litellm",
        "langgraph",
        "llama_index",
    )

    package_path = Path(stats_pkg.__file__).parent
    modules_to_inspect = []

    for _, modname, _ in pkgutil.iter_modules([str(package_path)]):
        full_name = f"application.evaluation.statistics.{modname}"
        modules_to_inspect.append(importlib.import_module(full_name))

    for mod in modules_to_inspect:
        for attr_name, attr_val in vars(mod).items():
            if hasattr(attr_val, "__module__") and attr_val.__module__:
                mod_origin = attr_val.__module__
                for forbidden in forbidden_prefixes:
                    assert not mod_origin.startswith(forbidden), (
                        f"Module {mod.__name__} violates architectural isolation by referencing "
                        f"{attr_name} from {mod_origin}"
                    )
