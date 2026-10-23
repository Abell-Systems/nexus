"""Run with `pytest experiments/wpi-demand-patent-matching/checks/check_restricted_separation.py` (ADR 0026: experiment
evidence lives under experiments/, not in backend/test; the CI does not run it).

Guards for the separation of the original demand corpus (third-party text) from the public tree.

D1 of ADR 0037 gate 5: docs/data-acquisition/third-party-files-d1-inventory.md.
"""

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

EXPERIMENT = Path(__file__).resolve().parent.parent
REPO_ROOT = EXPERIMENT.parents[1]
SYNTHETIC_DATA = EXPERIMENT / "synthetic" / "data"
FINGERPRINTS = json.loads((Path(__file__).parent / "third_party_text_fingerprints.json").read_text(encoding="utf-8"))
SCANNED = (
    EXPERIMENT,
    REPO_ROOT / "scripts",
    REPO_ROOT / "experiments" / "operational-dense-probe",
    REPO_ROOT / "docs" / "validation",
    REPO_ROOT / "docs" / "phase2-demand-construct-eligibility-audit-protocol.md",
    REPO_ROOT / "data" / "annotations",
    REPO_ROOT / "data" / "experiments",
    REPO_ROOT / "backend" / "test" / "fixtures",
    REPO_ROOT / "backend" / "test" / "unit" / "application" / "ingestion",
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(script: Path, data_dir: str, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "WPI_DATA_DIR": data_dir}
    return subprocess.run([sys.executable, str(script), *args], env=env, capture_output=True, text=True)


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\\", "").lower()).strip()


def test_should_find_no_original_demand_text_in_the_scanned_tree() -> None:
    """Tracked files only. Compares the hash of every window with the hashes of the first 60 normalised characters of
    each original description and recorded quote, and of the first 25 of each Innoget title (no text is stored)."""
    checks = (
        (FINGERPRINTS["window"], set(FINGERPRINTS["sha256_of_first_window"])),
        (FINGERPRINTS["title_window"], set(FINGERPRINTS["sha256_of_first_title_window"])),
    )
    found = []
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", *(str(r.relative_to(REPO_ROOT)) for r in SCANNED)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\0")
    for name in filter(None, tracked):
        path = REPO_ROOT / name
        if not path.is_file() or path.suffix in {".pyc", ".parquet", ".pdf"}:
            continue
        text = _normalise(path.read_text(encoding="utf-8", errors="ignore"))
        if any(
            hashlib.sha256(text[i : i + window].encode()).hexdigest() in known
            for window, known in checks
            for i in range(len(text) - window + 1)
        ):
            found.append(name)
    assert not found, f"original third-party demand text found in: {found}"


@pytest.mark.parametrize(
    "script",
    [
        EXPERIMENT / "checks" / "check_sector_assignments.py",
        EXPERIMENT / "checks" / "generate_construct_eligibility_audit.py",
        REPO_ROOT / "scripts" / "extract_operational_texts.py",
    ],
)
def test_should_stop_with_an_explicit_message_when_the_original_corpus_is_missing(script: Path, tmp_path: Path) -> None:
    result = _run(script, str(tmp_path))
    assert result.returncode != 0
    assert "Original demand corpus not available" in result.stderr
    assert "RETIRED_FILES.json" in result.stderr


def test_should_not_build_a_snapshot_when_the_original_corpus_is_missing(tmp_path: Path) -> None:
    out = tmp_path / "demands.json"
    result = _run(REPO_ROOT / "scripts" / "build_demands_snapshot.py", str(tmp_path), "--out", str(out))
    assert result.returncode != 0
    assert "Original demand corpus not available" in result.stderr
    assert not out.exists()


def test_should_pass_the_generic_conformance_check_on_the_synthetic_corpus() -> None:
    result = _run(EXPERIMENT / "checks" / "check_demand_corpus.py", str(SYNTHETIC_DATA))
    assert result.returncode == 0, result.stderr
    assert "SYNTHETIC-A-" in result.stdout


def test_should_mark_every_synthetic_record_as_synthetic() -> None:
    corpus = json.loads((SYNTHETIC_DATA / "dataset_phase2_demand_corpus_n39.json").read_text(encoding="utf-8"))
    assert {d["provenance"]["modality"] for d in corpus["demands"]} == {"synthetic_control"}
    assert {d["provenance"]["source_authority"] for d in corpus["demands"]} == {"synthetic"}
    assert len(corpus["demands"]) == 39


def test_should_keep_the_synthetic_files_equal_to_what_the_generator_writes() -> None:
    generator = _load(EXPERIMENT / "synthetic" / "generate_synthetic_corpus.py", "generate_synthetic_corpus")
    data, manifest = generator.build()
    assert (SYNTHETIC_DATA / "dataset_phase2_demand_corpus_n39.json").read_bytes() == data
    assert json.loads((SYNTHETIC_DATA / "dataset_phase2_demand_corpus_n39.manifest.json").read_text()) == manifest


def test_should_record_the_hashes_of_the_retired_files_and_match_their_committed_sidecars() -> None:
    record = json.loads((EXPERIMENT / "data" / "RETIRED_FILES.json").read_text(encoding="utf-8"))
    assert len(record["files"]) == 6
    for row in record["files"]:
        assert re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
        assert row["matches_committed_sidecar"] is True
