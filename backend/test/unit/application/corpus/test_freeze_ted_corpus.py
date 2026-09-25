"""Unit tests for the #103 TED corpus freeze + Dev/Test split script."""

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_freeze = importlib.import_module("experiments.phase2.freeze_ted_corpus")
freeze_ted_corpus = _freeze.freeze_ted_corpus


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _accepted_demand(demand_id: str, organization_raw: str) -> dict:
    return {
        "demand_id": demand_id,
        "source_id": "ted",
        "organization_raw": organization_raw,
        "geographic_stratum": "international_european",
    }


def _write_raw_notice(raw_dir: Path, demand_id: str, cpv: str) -> None:
    html = f'<span data-labels-key="code|name|cpv.{cpv}">label</span>'
    (raw_dir / "ted").mkdir(parents=True, exist_ok=True)
    (raw_dir / "ted" / f"{demand_id}.html").write_text(html, encoding="utf-8")


def test_freeze_refuses_when_gate_did_not_pass(tmp_path: Path) -> None:
    accepted_path = tmp_path / "accepted.json"
    audit_path = tmp_path / "audit.json"
    _write_json(accepted_path, [_accepted_demand("1-2026", "Org A")])
    _write_json(
        audit_path,
        {
            "organization_axis": {"independent": ["1-2026"], "pseudoreplicate": [], "unknown": []},
            "n_power": {"value": 1, "gate_threshold": 60, "gate_result": "STOP"},
        },
    )

    with pytest.raises(ValueError, match="Refusing to freeze"):
        freeze_ted_corpus(
            accepted_path=accepted_path,
            independence_audit_path=audit_path,
            raw_dir=tmp_path / "raw",
            out_dir=tmp_path / "out",
        )


def test_freeze_excludes_pseudoreplicates_and_splits_without_org_overlap(tmp_path: Path) -> None:
    accepted_path = tmp_path / "accepted.json"
    audit_path = tmp_path / "audit.json"
    raw_dir = tmp_path / "raw"
    out_dir = tmp_path / "out"

    # 6 independent demands from 6 distinct orgs, plus 2 pseudoreplicates of org "Org A"
    # that must never enter the partition universe.
    demands = [_accepted_demand(f"{i}-2026", f"Org {chr(65 + i)}") for i in range(6)]
    demands.append(_accepted_demand("6-2026", "Org A"))  # pseudoreplicate of Org A
    _write_json(accepted_path, demands)
    for i, d in enumerate(demands):
        _write_raw_notice(raw_dir, d["demand_id"], cpv=f"7200000{i % 2}")

    _write_json(
        audit_path,
        {
            "organization_axis": {
                "independent": [f"{i}-2026" for i in range(6)],
                "pseudoreplicate": ["6-2026"],
                "unknown": [],
            },
            "n_power": {"value": 6, "gate_threshold": 60, "gate_result": "PASS"},
        },
    )

    manifest = freeze_ted_corpus(
        accepted_path=accepted_path,
        independence_audit_path=audit_path,
        raw_dir=raw_dir,
        out_dir=out_dir,
    )

    assert manifest["n_power"] == 6
    assert manifest["dev_count"] + manifest["test_count"] == 6
    assert manifest["organization_overlap"] == []
    assert manifest["pseudoreplicate_count_excluded"] == 1

    corpus = json.loads((out_dir / "ted_independent_corpus_v1.json").read_text(encoding="utf-8"))
    corpus_ids = {d["demand_id"] for d in corpus["demands"]}
    assert "6-2026" not in corpus_ids
    assert corpus_ids == {f"{i}-2026" for i in range(6)}

    split = json.loads((out_dir / "ted_devtest_split_v1.json").read_text(encoding="utf-8"))
    assert set(split["dev"]) | set(split["test"]) == corpus_ids
    assert set(split["dev"]) & set(split["test"]) == set()

    # Sealed artifacts carry sha256 sidecars
    for name in ("ted_independent_corpus_v1.json", "ted_devtest_split_v1.json", "ted_freeze_manifest_v1.json"):
        assert (out_dir / name).exists()
        assert (out_dir / Path(name).with_suffix(".sha256")).exists()
