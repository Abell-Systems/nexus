"""Unit tests for the #102 TED multidimensional independence audit script."""

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_audit_ted = importlib.import_module("experiments.phase2.audit_ted_independence")
extract_cpv_code = _audit_ted.extract_cpv_code
_concentration_report = _audit_ted._concentration_report
_multi_member_groups = _audit_ted._multi_member_groups


def test_extract_cpv_code_finds_main_classification():
    html = (
        '<span class="label" data-labels-key="field|name|BT-262-Procedure">Main classification</span>'
        '<span class="data">cpv</span><span class="data">77230000</span>'
        '<span class="data" data-labels-key="code|name|cpv.77230000">Services incidental to forestry</span>'
    )
    assert extract_cpv_code(html) == "77230000"


def test_extract_cpv_code_missing_returns_none():
    assert extract_cpv_code("<html><body>No classification here</body></html>") is None


def test_extract_cpv_code_takes_first_in_document_order():
    """The buyer's own main classification (section 2) precedes any lot-level
    classification (section 5) -- document order, not the last match."""
    html = (
        'data-labels-key="code|name|cpv.72000000">IT services'
        '...later in the document...'
        'data-labels-key="code|name|cpv.72500000">IT services related'
    )
    assert extract_cpv_code(html) == "72000000"


def test_concentration_report_computes_shares_and_flags_warnings():
    labels = ["77", "77", "77", "77", "72", "99"]  # 4/6 = 0.667 for "77"; others 1/6 each
    report = _concentration_report(labels, threshold=0.35)

    assert report["total"] == 6
    assert report["distribution"] == {"77": 4, "72": 1, "99": 1}
    assert report["shares"]["77"] == pytest.approx(4 / 6)
    assert report["concentration_warnings"] == ["77"]


def test_concentration_report_no_warning_when_evenly_distributed():
    labels = ["a", "b", "c"]
    report = _concentration_report(labels, threshold=0.35)
    assert report["concentration_warnings"] == []


def test_concentration_report_empty_input():
    report = _concentration_report([], threshold=0.35)
    assert report["total"] == 0
    assert report["distribution"] == {}
    assert report["concentration_warnings"] == []


def test_multi_member_groups_excludes_singletons():
    independent_ids = ["A1", "B1", "C1"]
    pseudoreplicate_ids = ["A2", "A3"]
    org_group_by_id = {
        "A1": "Org A", "A2": "Org A", "A3": "Org A",
        "B1": "Org B",
        "C1": None,
    }
    groups = _multi_member_groups(independent_ids, pseudoreplicate_ids, org_group_by_id)
    assert groups == {"Org A": ["A1", "A2", "A3"]}
