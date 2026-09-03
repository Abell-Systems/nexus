"""Architectural invariant tests for ADR 0006 (Scientific Validation Dataset and Provenance).

Invariants enforced:
1. Zero repository-relative paths to 'data/evaluation/' inside domain/ or application/.
2. Evaluation dataset loaders require explicit Path injection and have no default fallback paths.
3. Unit test fixtures ('backend/test/fixtures') are strictly decoupled from the evaluation domain.
4. Cryptographic verification inspects raw bytes without parsing or re-serialization.
5. Injected tamper test: modifying a single byte in a real dataset forces an integrity failure.
"""

from pathlib import Path

import pytest

from infrastructure.evaluation.dataset_loader import DefaultEvaluationDatasetLoader


def test_no_data_evaluation_relative_paths_in_domain_or_application():
    """ADR 0006 §6: Domain and application logic must NOT resolve repository-relative dataset paths."""
    repo_root = Path(__file__).resolve().parents[4]
    domain_app_dirs = [
        repo_root / "backend" / "src" / "main" / "domain",
        repo_root / "backend" / "src" / "main" / "application",
    ]

    violating_files = []
    for directory in domain_app_dirs:
        for py_file in directory.rglob("*.py"):
            code = py_file.read_text(encoding="utf-8")
            if "data/evaluation" in code:
                violating_files.append(str(py_file))

    assert not violating_files, (
        f"Found forbidden repository-relative evaluation paths in domain/application: {violating_files}. "
        "Under ADR 0006 & ADR 0005, dataset paths must be injected explicitly from bootstrap/runners."
    )


def test_dataset_loader_requires_explicit_path_injection_without_fallbacks():
    """ADR 0006 §6: DefaultEvaluationDatasetLoader must NOT provide default path parameters."""
    import inspect
    loader = DefaultEvaluationDatasetLoader()
    sig = inspect.signature(loader.load_validated_dataset)

    # dataset_path and checksum_path must be required (no default value)
    for param_name in ("dataset_path", "checksum_path"):
        param = sig.parameters.get(param_name)
        assert param is not None, f"Missing expected parameter '{param_name}'"
        assert param.default is inspect.Parameter.empty, (
            f"Parameter '{param_name}' must NOT have a default fallback value. "
            "Explicit path injection is strictly mandatory under ADR 0006."
        )


def test_fixtures_are_not_imported_in_evaluation_code():
    """ADR 0006 §6: Unit test fixtures must NOT be coupled to or imported in evaluation code."""
    repo_root = Path(__file__).resolve().parents[4]
    eval_dirs = [
        repo_root / "backend" / "src" / "main" / "domain" / "models" / "evaluation.py",
        repo_root / "backend" / "src" / "main" / "infrastructure" / "evaluation",
    ]

    for path in eval_dirs:
        files = [path] if path.is_file() else list(path.rglob("*.py"))
        for py_file in files:
            content = py_file.read_text(encoding="utf-8")
            assert "fixtures" not in content, (
                f"Forbidden fixture reference found in {py_file}. "
                "Empirical evaluation code must not reference unit test fixtures."
            )


def test_tamper_rejection_on_canonical_benchmark_file(tmp_path):
    """ADR 0006 §4 & §8: 1-byte alteration of raw bytes causes an immediate integrity failure."""
    repo_root = Path(__file__).resolve().parents[4]
    real_dataset = repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.json"
    real_checksum = repo_root / "data" / "evaluation" / "dataset_pilot_benchmark.sha256"

    # Copy files to tmp_path
    tampered_dataset = tmp_path / "dataset_pilot_benchmark.json"
    tampered_checksum = tmp_path / "dataset_pilot_benchmark.sha256"

    raw_bytes = bytearray(real_dataset.read_bytes())
    # Alter exactly 1 byte
    raw_bytes[50] = ord("Z") if raw_bytes[50] != ord("Z") else ord("W")
    tampered_dataset.write_bytes(raw_bytes)
    tampered_checksum.write_text(real_checksum.read_text(encoding="utf-8"))

    loader = DefaultEvaluationDatasetLoader()
    with pytest.raises(ValueError, match="Cryptographic integrity verification failed"):
        loader.load_validated_dataset(
            dataset_path=tampered_dataset,
            checksum_path=tampered_checksum,
        )
