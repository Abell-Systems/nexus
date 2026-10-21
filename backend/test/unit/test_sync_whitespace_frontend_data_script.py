import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / "frontend" / "src" / "main" / "infrastructure" / "data"
PUBLIC = REPO_ROOT / "frontend" / "public" / "data"


def _script():
    spec = importlib.util.spec_from_file_location(
        "sync_whitespace_frontend_data", REPO_ROOT / "scripts" / "sync_whitespace_frontend_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shouldProduceExactlyTheCommittedCopiesAndManifestWhenSyncing(tmp_path):
    manifest = _script().sync(tmp_path / "bundled", tmp_path / "public")
    for served, committed in (("bundled", DATA), ("on_demand", PUBLIC)):
        entries = {e["file"] for e in manifest["files"] if e["served"] == served}
        produced = {p.name for p in (tmp_path / ("bundled" if served == "bundled" else "public")).glob("*.json")}
        assert entries == produced - {"provenance.json"}
        for name in entries:
            assert (tmp_path / ("bundled" if served == "bundled" else "public") / name).read_bytes() == (
                committed / name
            ).read_bytes(), name


def test_shouldKeepTheLargePairsResultOutOfTheBundledDataWhenSyncing(tmp_path):
    manifest = _script().sync(tmp_path / "bundled", tmp_path / "public")
    assert not (tmp_path / "bundled" / "oepm-subclass-pairs-results.json").exists()
    assert (tmp_path / "public" / "oepm-subclass-pairs-results.json").exists()
    assert {e["served"] for e in manifest["files"]} == {"bundled", "on_demand"}
