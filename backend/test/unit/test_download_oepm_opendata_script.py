import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG = "https://sede.oepm.gob.es/eSede/datos/es/catalogo/catalogo-patentes-y-modelos-de-utilidad/"


def _script():
    spec = importlib.util.spec_from_file_location(
        "download_oepm_opendata", REPO_ROOT / "scripts" / "download_oepm_opendata.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_shouldKeepOnlyDistinctZipPathsWhenListingLinks():
    hrefs = [
        f"{CATALOG}../descargar.jsp?u=INVENCIONES/resumenes_example.zip",
        f"{CATALOG}../descargar.jsp?u=INVENCIONES/resumenes_example.zip",
        f"{CATALOG}../descargar.jsp?u=INVENCIONES/BIBLIO/2020/BIBLIO_2020.zip",
        f"{CATALOG}../descargar.jsp?u=INVENCIONES/AuthorityFile_V2_2.xsd",
        "https://sede.oepm.gob.es/eSede/datos/es/catalogo/otra-pagina/",
        "https://evil.example/descargar.jsp?u=INVENCIONES/robado.zip",
        "http://sede.oepm.gob.es/descargar.jsp?u=INVENCIONES/inseguro.zip",
    ]
    assert _script().zip_paths(hrefs) == [
        "INVENCIONES/BIBLIO/2020/BIBLIO_2020.zip",
        "INVENCIONES/resumenes_example.zip",
    ]


REJECTED = [
    "https://evil.example/",
    "https://sede.oepm.gob.es.evil.example/x",
    "https://evil.example/https://sede.oepm.gob.es/",
    "https://sede.oepm.gob.es@evil.example/",
    "https://user:pass@sede.oepm.gob.es/",
    "https://sede.oepm.gob.es:8443/",
    "https://sede.oepm.gob.es:notaport/",
    "http://sede.oepm.gob.es/",
    "//sede.oepm.gob.es/",
    "sede.oepm.gob.es/",
    "",
]


@pytest.mark.parametrize("url", REJECTED)
def test_shouldNotRecogniseAUrlThatIsNotOnTheSedeHostWhenCheckingOrigin(url):
    assert not _script().is_sede_url(url)


def test_shouldRecogniseSedePagesWhenCheckingOrigin():
    script = _script()
    assert script.is_sede_url(CATALOG) and script.is_sede_url("https://sede.oepm.gob.es:443/x")


@pytest.mark.parametrize("page", REJECTED)
def test_shouldRejectAPageOutsideTheSedeBeforeReadingCredentialsOrImportingPlaywright(monkeypatch, capsys, page):
    monkeypatch.setattr(sys, "argv", ["download_oepm_opendata.py", "--page", page, "--list"])
    monkeypatch.delenv("OEPM_USER", raising=False)
    monkeypatch.delenv("OEPM_PWD", raising=False)
    monkeypatch.setitem(sys.modules, "playwright", None)  # an import would raise, as on a machine without it
    with pytest.raises(SystemExit) as stopped:
        _script().main()
    assert stopped.value.code == 2
    assert "--page must be an https page of sede.oepm.gob.es" in capsys.readouterr().err


def test_shouldNotNeedPlaywrightToImportTheScript():
    assert "playwright" not in vars(_script())


class _FakePage:
    """Stands in for a Playwright page: login succeeds, and navigating to `redirect_to` lands there instead."""

    def __init__(self, redirect_to: str | None, hrefs: list[str]):
        self.url, self._redirect_to, self._hrefs = "", redirect_to, hrefs

    def goto(self, url):
        self.url = self._redirect_to if self._redirect_to and url == CATALOG else url

    def get_by_label(self, _):
        return self

    def get_by_role(self, *_, **__):
        return self

    def fill(self, _):
        pass

    def click(self):
        pass

    def wait_for_load_state(self, _):
        pass

    def content(self):
        return ""

    def eval_on_selector_all(self, *_):
        return self._hrefs


def _fake_playwright(monkeypatch, page):
    class _Browser:
        def new_context(self, **_):
            return type("Context", (), {"new_page": lambda self: page})()

        def close(self):
            pass

    class _Playwright:
        chromium = type("Chromium", (), {"launch": lambda self: _Browser()})()

    class _Manager:
        def __enter__(self):
            return _Playwright()

        def __exit__(self, *_):
            return False

    module = type(sys)("playwright.sync_api")
    module.sync_playwright = lambda: _Manager()
    monkeypatch.setitem(sys.modules, "playwright", type(sys)("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", module)


def _run(monkeypatch, page):
    monkeypatch.setattr(sys, "argv", ["download_oepm_opendata.py", "--page", CATALOG, "--list"])
    monkeypatch.setenv("OEPM_USER", "user@example.test")
    monkeypatch.setenv("OEPM_PWD", "not-a-real-password")
    _fake_playwright(monkeypatch, page)
    return _script().main()


def test_shouldAbortWhenThePageRedirectsOutsideTheSedeAfterNavigating(monkeypatch):
    hrefs = ["https://evil.example/descargar.jsp?u=INVENCIONES/robado.zip"]
    with pytest.raises(SystemExit) as stopped:
        _run(monkeypatch, _FakePage("https://evil.example/", hrefs))
    assert "redirected outside sede.oepm.gob.es" in str(stopped.value)


def test_shouldListTheSedeZipsWhenThePageDoesNotRedirect(monkeypatch, capsys):
    hrefs = [f"{CATALOG}../descargar.jsp?u=INVENCIONES/cpc_example.zip"]
    assert _run(monkeypatch, _FakePage(None, hrefs)) == 0
    assert capsys.readouterr().out.strip() == "INVENCIONES/cpc_example.zip"
