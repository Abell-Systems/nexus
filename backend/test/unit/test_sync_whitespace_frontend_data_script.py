import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / "frontend" / "src" / "main" / "infrastructure" / "data"


def _script():
    spec = importlib.util.spec_from_file_location(
        "sync_whitespace_frontend_data", REPO_ROOT / "scripts" / "sync_whitespace_frontend_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shouldProduceExactlyTheCommittedCopiesAndManifestWhenSyncing(tmp_path):
    manifest = _script().sync(tmp_path)
    assert {entry["file"] for entry in manifest["files"]} == {p.name for p in tmp_path.glob("*.json")} - {
        "provenance.json"
    }
    for produced in tmp_path.glob("*.json"):
        assert produced.read_bytes() == (DATA / produced.name).read_bytes(), produced.name
