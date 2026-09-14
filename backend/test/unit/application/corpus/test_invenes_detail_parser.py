"""Unit tests for the INVENES detail-page parser (ADR 0035 SS11.3) against the
three real fetched fixtures in data/raw/oepm_invenes_sample/."""

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Dynamic import, not a static import statement, per ADR 0026's
# reference-boundary check (backend/test/unit/architecture/test_adr_0026_invariants.py),
# matching test_harvesters.py's established precedent for testing this tree's code.
_invenes_parser_module = importlib.import_module("experiments.oepm.invenes_detail_parser")
parse_invenes_detail = _invenes_parser_module.parse_invenes_detail

FIXTURE_DIR = REPO_ROOT / "data" / "raw" / "oepm_invenes_sample"


def _load(referencia: str) -> bytes:
    path = FIXTURE_DIR / f"detalle_{referencia.split('=')[-1]}.html"
    return path.read_bytes()


def test_parses_real_national_patent_record():
    html = (FIXTURE_DIR / "detalle_P201430605.html").read_bytes()
    parsed = parse_invenes_detail(html, referencia="P201430605")
    assert parsed is not None
    assert parsed.kind_code == "A1"
    assert parsed.item["publication_id"] == "ES2549395A1"
    assert parsed.item["application_number"] == "P201430605"
    assert parsed.item["filing_date"] == "2014-04-24"
    assert parsed.item["publication_date"] == "2015-10-27"
    assert "suciedad" in parsed.item["title"].lower()
    assert "sensor" in parsed.item["abstract"].lower()
    assert parsed.item["assignees"] == ["FUNDACIÓN TEKNIKER"]
    assert "G01N21/94" in parsed.item["classifications_ipc"]
    assert "F24S40/20" in parsed.item["classifications_cpc"]


def test_parses_real_utility_model_record():
    html = (FIXTURE_DIR / "detalle_U202130129.html").read_bytes()
    parsed = parse_invenes_detail(html, referencia="U202130129")
    assert parsed is not None
    assert parsed.kind_code == "U"
    assert parsed.item["publication_id"] == "ES1265150U"
    # Real, disclosed finding: utility models on this public route frequently
    # have no "Resumen" (abstract) field -- not a parser bug.
    assert parsed.item["abstract"] == ""


def test_parses_real_ep_es_t3_record():
    html = (FIXTURE_DIR / "detalle_E14275070.html").read_bytes()
    parsed = parse_invenes_detail(html, referencia="E14275070")
    assert parsed is not None
    assert parsed.kind_code == "T3"
    assert parsed.item["publication_id"] == "ES2878119T3"
    assert parsed.item["assignees"] == ["Regal Beloit America, Inc."]


def test_returns_none_for_unrecognizable_page():
    assert parse_invenes_detail(b"<html><body>not a patent record</body></html>", referencia="X") is None
