import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _script():
    spec = importlib.util.spec_from_file_location(
        "build_whitespace_briefing", REPO_ROOT / "scripts" / "build_whitespace_briefing.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build(tmp_path, monkeypatch) -> str:
    out = tmp_path / "briefing.html"
    monkeypatch.setattr(sys, "argv", ["build_whitespace_briefing.py", "--out", str(out)])
    assert _script().main() == 0
    return out.read_text(encoding="utf-8")


def test_shouldFillEveryPlaceholderWithVersionedFiguresWhenBuildingTheBriefing(tmp_path, monkeypatch):
    html = _build(tmp_path, monkeypatch)
    assert "{{" not in html
    assert "774,552" in html and "25,849" in html


def test_shouldStaySelfContainedAndFreeOfRankingsWhenBuildingTheBriefing(tmp_path, monkeypatch):
    html = _build(tmp_path, monkeypatch)
    assert "<script" not in html and "http://" not in html and "https://" not in html
    assert "no es una oportunidad" in html.lower() or "no son oportunidades" in html.lower()
    assert "prometedor" in html.lower()  # named only to say that none is shown


def test_shouldRegenerateExactlyTheCommittedPageWhenBuildingFromTheVersionedResults(tmp_path, monkeypatch):
    committed = (REPO_ROOT / "docs" / "whitespace" / "briefing-lydia.html").read_text(encoding="utf-8")
    assert _build(tmp_path, monkeypatch) == committed


def test_shouldUseOneColourScaleForBothMapsWhenBuildingTheBriefing(tmp_path, monkeypatch):
    html = _build(tmp_path, monkeypatch)
    assert "común a ambos mapas" in html
    assert html.count('class="heat"') == 2
