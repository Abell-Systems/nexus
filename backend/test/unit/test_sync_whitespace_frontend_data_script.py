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


def _root_with_topic(tmp_path, names):
    root = tmp_path / "root"
    (root / "docs" / "whitespace").mkdir(parents=True)
    for name in names:
        (root / "docs" / name if "/" in name else root / "docs" / "whitespace" / name).parent.mkdir(exist_ok=True)
        (root / "docs" / name if "/" in name else root / "docs" / "whitespace" / name).write_text('{"synthetic": true}\n', encoding="utf-8")
    return root


def _sync_without_the_fixed_sources(script, tmp_path, root):
    script.SOURCES, script.ON_DEMAND_SOURCES = [], []
    return script.sync(tmp_path / "bundled", tmp_path / "public", root)


def test_shouldSkipATopicResultThatDoesNotExistYet(tmp_path):
    manifest = _sync_without_the_fixed_sources(_script(), tmp_path, _root_with_topic(tmp_path, []))
    assert manifest["files"] == []
    assert list((tmp_path / "public").glob("topic-map-*")) == []


def test_shouldCopyATopicResultWithItsHashWhenItExists(tmp_path):
    import hashlib

    root = _root_with_topic(tmp_path, ["topic-map-batteries.json", "topic-map.json", "other-topic-map-x.json"])
    manifest = _sync_without_the_fixed_sources(_script(), tmp_path, root)
    (entry,) = manifest["files"]
    copy = tmp_path / "public" / "topic-map-batteries.json"
    assert entry["file"] == "topic-map-batteries.json"
    assert entry["served"] == "on_demand"
    assert entry["producedBy"] == "scripts/report_topic_map.py"
    assert "pullRequest" not in entry
    assert entry["bytes"] == len(copy.read_bytes())
    assert entry["sha256"] == hashlib.sha256(copy.read_bytes()).hexdigest()
    assert not (tmp_path / "public" / "topic-map.json").exists()


def test_shouldOnlyDiscoverTopicResultsDirectlyUnderDocsWhitespace(tmp_path):
    # Closed: topic-map-looking files elsewhere under docs/ or nested below docs/whitespace/ are never copied or listed.
    root = _root_with_topic(
        tmp_path, ["topic-map-ok.json", "other/topic-map-x.json", "whitespace/sub/topic-map-y.json"]
    )
    manifest = _sync_without_the_fixed_sources(_script(), tmp_path, root)
    assert [e["file"] for e in manifest["files"]] == ["topic-map-ok.json"]
    assert [p.name for p in (tmp_path / "public").glob("*.json")] == ["topic-map-ok.json"]
