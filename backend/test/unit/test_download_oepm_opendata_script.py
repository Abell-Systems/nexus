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
