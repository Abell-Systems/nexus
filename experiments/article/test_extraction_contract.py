"""Assert-based self-check for the Minesoft extraction contract validator.

No pytest -- run directly: python3 experiments/article/test_extraction_contract.py
Matches this repo's experiments/ convention (standalone check scripts, no test framework).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "checks"))

from validate_extraction_contract import (  # noqa: E402
    FAIL,
    PASS,
    evaluate_count_reconciliation,
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


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"\n{len(tests)} test(s) passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
