"""Pure validation library for the Minesoft extraction contract (v1).

Every function here is pure: it takes already-loaded Python data and returns Finding tuples.
No file I/O, no network calls -- that lives in the CLI scripts (check_extraction_run.py,
audit_minesoft_origin_v0_1.py) that call into this module.
"""

from collections import namedtuple

CONTRACT_VERSION = "extraction_contract_v1"

PASS = "PASS"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"
LEGACY_UNVERIFIABLE = "LEGACY_UNVERIFIABLE"

Finding = namedtuple("Finding", ["invariant", "verdict", "detail"])


def evaluate_count_reconciliation(
    rows_extracted: int,
    unique_ids: int,
    total_hits_reported: int,
    capped: bool,
    extraction_cap: int | None,
) -> Finding:
    """Dataset unit is (compound, publication_id); uniqueness is scoped per compound.

    Uncapped: rows_extracted and unique_ids must both equal total_hits_reported exactly.
    Capped: extraction_cap must be declared; the expected count is min(total_hits_reported,
    extraction_cap), and cap_binding records which bound actually applied.
    """
    if not capped:
        if rows_extracted == total_hits_reported and unique_ids == rows_extracted:
            return Finding(
                "count_reconciliation", PASS,
                f"rows_extracted={rows_extracted}, total_hits_reported={total_hits_reported}, "
                f"unique={unique_ids}",
            )
        return Finding(
            "count_reconciliation", FAIL,
            f"rows_extracted={rows_extracted}, unique={unique_ids} do not both equal "
            f"total_hits_reported={total_hits_reported} for an uncapped run",
        )

    if extraction_cap is None:
        return Finding("count_reconciliation", FAIL, "capped=True but extraction_cap was not declared")

    cap_binding = total_hits_reported >= extraction_cap
    expected = extraction_cap if cap_binding else total_hits_reported
    if rows_extracted == expected and unique_ids == rows_extracted:
        return Finding(
            "count_reconciliation", PASS,
            f"rows_extracted={rows_extracted}, expected={expected}, cap_binding={cap_binding}",
        )
    return Finding(
        "count_reconciliation", FAIL,
        f"rows_extracted={rows_extracted}, unique={unique_ids} do not both equal expected={expected} "
        f"(cap_binding={cap_binding})",
    )
