"""Assert-based self-check for the Minesoft extraction contract validator.

No pytest -- run directly: python3 experiments/article/test_extraction_contract.py
Matches this repo's experiments/ convention (standalone check scripts, no test framework).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "checks"))

from validate_extraction_contract import (  # noqa: E402
    FAIL,
    LEGACY_UNVERIFIABLE,
    NOT_APPLICABLE,
    PASS,
    evaluate_count_reconciliation,
    evaluate_future_run,
    evaluate_legacy_compound,
    evaluate_pagination_completeness,
    evaluate_pagination_mode,
    evaluate_query_documented_legacy,
    evaluate_raw_source_archive,
    evaluate_row_provenance,
)


def test_count_reconciliation_uncapped_pass():
    finding = evaluate_count_reconciliation(
        rows_extracted=2613, unique_ids=2613, total_hits_reported=2613,
        capped=False, extraction_cap=None,
    )
    assert finding.invariant == "count_reconciliation"
    assert finding.verdict == PASS


def test_count_reconciliation_uncapped_fail_brentuximab_shaped():
    # Shape of the historical Brentuximab bug: 2,612 rows saved against a declared 2,613 total.
    finding = evaluate_count_reconciliation(
        rows_extracted=2612, unique_ids=2612, total_hits_reported=2613,
        capped=False, extraction_cap=None,
    )
    assert finding.verdict == FAIL
    assert "2612" in finding.detail and "2613" in finding.detail


def test_count_reconciliation_capped_binding():
    # total_hits_reported (19075) >= extraction_cap (1000) -> cap_binding True, expects exactly 1000.
    finding = evaluate_count_reconciliation(
        rows_extracted=1000, unique_ids=1000, total_hits_reported=19075,
        capped=True, extraction_cap=1000,
    )
    assert finding.verdict == PASS
    assert "cap_binding=True" in finding.detail


def test_count_reconciliation_capped_not_binding():
    # total_hits_reported (731) < extraction_cap (1000) -> cap never binds, full population expected.
    finding = evaluate_count_reconciliation(
        rows_extracted=731, unique_ids=731, total_hits_reported=731,
        capped=True, extraction_cap=1000,
    )
    assert finding.verdict == PASS
    assert "cap_binding=False" in finding.detail


def test_count_reconciliation_capped_binding_rejects_partial_rows():
    # This is exactly the case the design review flagged: 731 rows against a 1000 cap with
    # total_hits_reported >= cap must FAIL, not be accepted as "<= cap".
    finding = evaluate_count_reconciliation(
        rows_extracted=731, unique_ids=731, total_hits_reported=19075,
        capped=True, extraction_cap=1000,
    )
    assert finding.verdict == FAIL


def test_count_reconciliation_capped_requires_declared_cap():
    finding = evaluate_count_reconciliation(
        rows_extracted=1000, unique_ids=1000, total_hits_reported=19075,
        capped=True, extraction_cap=None,
    )
    assert finding.verdict == FAIL
    assert "not declared" in finding.detail


def test_pagination_completeness_uncapped_pass():
    # 2613 hits at page_size=50 -> ceil(2613/50) = 53 pages.
    finding = evaluate_pagination_completeness(
        pages_extracted=53, total_hits_reported=2613, page_size=50, capped=False,
    )
    assert finding.verdict == PASS


def test_pagination_completeness_uncapped_fail():
    finding = evaluate_pagination_completeness(
        pages_extracted=52, total_hits_reported=2613, page_size=50, capped=False,
    )
    assert finding.verdict == FAIL


def test_pagination_completeness_capped_not_applicable():
    finding = evaluate_pagination_completeness(
        pages_extracted=20, total_hits_reported=19075, page_size=50, capped=True,
    )
    assert finding.verdict == NOT_APPLICABLE


def test_pagination_mode_pass():
    finding = evaluate_pagination_mode("sequential_single_run")
    assert finding.verdict == PASS


def test_pagination_mode_fail():
    finding = evaluate_pagination_mode("multi_session_resumable")
    assert finding.verdict == FAIL


def _sample_pages():
    return [
        {"page_number": 0, "raw_response_path": "raw/page_0.json", "content_sha256": "abc123"},
        {"page_number": 1, "raw_response_path": "raw/page_1.json", "content_sha256": "def456"},
    ]


def _sample_rows(run_id="run-1"):
    return [
        {"publication_id": "US-1-A1", "extraction_run_id": run_id, "page_number": 0, "row_index": 0},
        {"publication_id": "US-2-A1", "extraction_run_id": run_id, "page_number": 1, "row_index": 1},
    ]


def test_raw_source_archive_pass_structural():
    finding = evaluate_raw_source_archive(_sample_pages())
    assert finding.verdict == PASS


def test_raw_source_archive_fail_missing_field():
    pages = [{"page_number": 0, "raw_response_path": None, "content_sha256": None}]
    finding = evaluate_raw_source_archive(pages)
    assert finding.verdict == FAIL


def test_raw_source_archive_fail_no_pages():
    finding = evaluate_raw_source_archive([])
    assert finding.verdict == FAIL


def test_raw_source_archive_fail_hash_mismatch():
    finding = evaluate_raw_source_archive(_sample_pages(), computed_hashes={0: "abc123", 1: "WRONG"})
    assert finding.verdict == FAIL
    assert "page(s): [1]" in finding.detail


def test_raw_source_archive_pass_hash_match():
    finding = evaluate_raw_source_archive(_sample_pages(), computed_hashes={0: "abc123", 1: "def456"})
    assert finding.verdict == PASS


def test_row_provenance_pass():
    finding = evaluate_row_provenance(_sample_rows(), _sample_pages(), extraction_run_id="run-1")
    assert finding.verdict == PASS


def test_row_provenance_fail_wrong_run_id():
    finding = evaluate_row_provenance(_sample_rows(run_id="other-run"), _sample_pages(), extraction_run_id="run-1")
    assert finding.verdict == FAIL


def test_row_provenance_fail_dangling_page_pointer():
    rows = [{"publication_id": "US-1-A1", "extraction_run_id": "run-1", "page_number": 99, "row_index": 0}]
    finding = evaluate_row_provenance(rows, _sample_pages(), extraction_run_id="run-1")
    assert finding.verdict == FAIL


def test_evaluate_future_run_all_pass():
    run = {
        "extraction_run_id": "run-1",
        "compound": "Test_compound",
        "capped": False,
        "extraction_cap": None,
        "total_hits_reported": 2,
        "page_size": 1,
        "pagination_mode": "sequential_single_run",
        "pages": _sample_pages(),
        "rows": _sample_rows(),
    }
    findings = evaluate_future_run(run, computed_hashes={0: "abc123", 1: "def456"})
    invariants = {f.invariant: f.verdict for f in findings}
    assert invariants == {
        "raw_source_archive": PASS,
        "count_reconciliation": PASS,
        "pagination_completeness": PASS,
        "pagination_mode": PASS,
        "row_provenance": PASS,
    }


def test_query_documented_legacy_pass():
    readme = "## Per-compound counts\n\n| 01 | Brentuximab vedotin | 2,613 |"
    finding = evaluate_query_documented_legacy("Brentuximab vedotin", readme)
    assert finding.verdict == PASS


def test_query_documented_legacy_fail():
    readme = "## Per-compound counts\n\n| 01 | Trabectedin | 1,890 |"
    finding = evaluate_query_documented_legacy("Brentuximab vedotin", readme)
    assert finding.verdict == FAIL


def test_evaluate_legacy_compound_brentuximab_shaped():
    rows = [{"publication_id": f"US-{i}-A1"} for i in range(2613)]
    readme = "Brentuximab vedotin appears here"
    findings = evaluate_legacy_compound(
        "Brentuximab vedotin", rows, capped=False, total_hits_reported=2613, readme_text=readme,
    )
    by_invariant = {f.invariant: f.verdict for f in findings}
    assert by_invariant["count_reconciliation"] == PASS
    assert by_invariant["raw_source_archive"] == LEGACY_UNVERIFIABLE
    assert by_invariant["pagination_completeness"] == LEGACY_UNVERIFIABLE
    assert by_invariant["pagination_mode"] == LEGACY_UNVERIFIABLE
    assert by_invariant["query_documented_human_readable"] == PASS
    assert by_invariant["query_documented_machine_readable"] == LEGACY_UNVERIFIABLE


def test_evaluate_legacy_compound_capped_cytarabine_shaped():
    rows = [{"publication_id": f"US-{i}-A1"} for i in range(1000)]
    readme = "Cytarabine cap: only the first 1,000 results"
    findings = evaluate_legacy_compound(
        "Cytarabine", rows, capped=True, total_hits_reported=19075, readme_text=readme,
    )
    by_invariant = {f.invariant: f.verdict for f in findings}
    assert by_invariant["count_reconciliation"] == PASS
    count_finding = next(f for f in findings if f.invariant == "count_reconciliation")
    assert "inferred" in count_finding.detail


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"\n{len(tests)} test(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
