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
    ]
    assert _script().zip_paths(hrefs) == [
        "INVENCIONES/BIBLIO/2020/BIBLIO_2020.zip",
        "INVENCIONES/resumenes_example.zip",
    ]


@pytest.mark.parametrize(
    "page", ["https://evil.example/", "https://sede.oepm.gob.es.evil.example/x", "http://sede.oepm.gob.es/"]
)
def test_shouldRejectAPageOutsideTheSedeWhenParsingArguments(monkeypatch, capsys, page):
    monkeypatch.setattr(sys, "argv", ["download_oepm_opendata.py", "--page", page, "--list"])
    with pytest.raises(SystemExit) as stopped:
        _script().main()
    assert stopped.value.code == 2
    assert "--page must be a page of" in capsys.readouterr().err


def test_shouldNotNeedPlaywrightToImportTheScript():
    assert "playwright" not in vars(_script())
