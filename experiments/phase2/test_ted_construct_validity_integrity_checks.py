"""Unit tests for the sha256 integrity checks in the TED construct-validity
classifier's phase2 scripts -- verifies each script refuses to run against
upstream data that has drifted from what a manifest/LLM-run file recorded,
rather than silently proceeding. Lives here, not under backend/test, per
ADR 0026 (backend/test never references the experiments/ tree)."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PHASE2_DIR = Path(__file__).resolve().parent


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run_llm = _load_module(
    "run_ted_construct_validity_llm_classification",
    PHASE2_DIR / "run_ted_construct_validity_llm_classification.py",
)
evaluate_gate = _load_module(
    "evaluate_ted_construct_validity_gate",
    PHASE2_DIR / "evaluate_ted_construct_validity_gate.py",
)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_generate_llm_classification_rejects_drifted_mapped_candidates(tmp_path):
    mapped_path = tmp_path / "candidates_mapped.json"
    mapped_path.write_text(json.dumps([{"demand_id": "x", "description_text": "d", "language_code": "en"}]))

    manifest_path = tmp_path / "manifest.json"
    _write_json(manifest_path, {"all_ids": ["x"], "source_mapped_candidates_sha256": "0" * 64})

    with pytest.raises(ValueError, match="candidates_mapped.json has changed"):
        run_llm.generate(manifest_path, mapped_path, tmp_path / "out.json")


def test_evaluate_gate_rejects_llm_file_from_a_different_manifest(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_data = {"all_ids": ["a"], "boundary_ids": []}
    _write_json(manifest_path, manifest_data)

    valentin_csv = tmp_path / "valentin.csv"
    lydia_csv = tmp_path / "lydia.csv"
    for p in (valentin_csv, lydia_csv):
        p.write_text("demand_id,description_text,language_code,judgment\na,d,en,TECHNICAL_PROBLEM\n")

    llm_path = tmp_path / "llm.json"
    _write_json(llm_path, {"source_manifest_sha256": "0" * 64, "classifications": {"a": "TECHNICAL_PROBLEM"}})

    with pytest.raises(ValueError, match="different manifest"):
        evaluate_gate.evaluate(
            manifest_path=manifest_path,
            valentin_csv=valentin_csv,
            lydia_csv=lydia_csv,
            llm_path=llm_path,
            adjudication_path=tmp_path / "adjudication.json",
            out_path=tmp_path / "out.json",
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
