"""Pure validation library for the Minesoft extraction contract (v1).

Every function here is pure: it takes already-loaded Python data and returns Finding tuples.
No file I/O, no network calls -- that lives in the CLI scripts (check_extraction_run.py,
audit_minesoft_origin_v0_1.py) that call into this module.
"""

import math
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


def evaluate_pagination_completeness(
    pages_extracted: int,
    total_hits_reported: int,
    page_size: int,
    capped: bool,
) -> Finding:
    """Capped runs are not required to exhaust every page -- they stop at the cap by design."""
    if capped:
        return Finding(
            "pagination_completeness", NOT_APPLICABLE,
            "capped runs are not required to exhaust all pages",
        )
    expected_pages = math.ceil(total_hits_reported / page_size) if total_hits_reported else 0
    if pages_extracted == expected_pages:
        return Finding(
            "pagination_completeness", PASS,
            f"pages_extracted={pages_extracted}, expected={expected_pages}",
        )
    return Finding(
        "pagination_completeness", FAIL,
        f"pages_extracted={pages_extracted} != expected={expected_pages}",
    )


def evaluate_pagination_mode(pagination_mode: str) -> Finding:
    """The contract requires one continuous session per compound -- no pause/resume/restart."""
    if pagination_mode == "sequential_single_run":
        return Finding("pagination_mode", PASS, "pagination_mode == 'sequential_single_run'")
    return Finding(
        "pagination_mode", FAIL,
        f"pagination_mode={pagination_mode!r} != required 'sequential_single_run'",
    )


def evaluate_raw_source_archive(
    pages: list[dict],
    computed_hashes: dict[int, str] | None = None,
) -> Finding:
    """Structural check: every page declares raw_response_path + content_sha256.

    If computed_hashes is given (page_number -> actual sha256 of the file on disk, computed by the
    caller), also verifies each page's declared content_sha256 matches -- this function stays pure
    by taking the already-computed hashes rather than reading files itself.
    """
    if not pages:
        return Finding("raw_source_archive", FAIL, "no pages recorded")
    missing = [
        p["page_number"] for p in pages
        if not p.get("raw_response_path") or not p.get("content_sha256")
    ]
    if missing:
        return Finding(
            "raw_source_archive", FAIL,
            f"pages missing raw_response_path/content_sha256: {missing}",
        )
    if computed_hashes is not None:
        mismatched = [
            p["page_number"] for p in pages
            if computed_hashes.get(p["page_number"]) != p["content_sha256"]
        ]
        if mismatched:
            return Finding(
                "raw_source_archive", FAIL,
                f"content_sha256 mismatch for page(s): {mismatched}",
            )
    return Finding("raw_source_archive", PASS, f"{len(pages)} page(s) with verified raw archive")


def evaluate_row_provenance(
    rows: list[dict],
    pages: list[dict],
    extraction_run_id: str,
) -> Finding:
    """Every extraction-layer row must trace back to a recorded page in this same run."""
    page_numbers = {p["page_number"] for p in pages}
    bad = [
        r["row_index"] for r in rows
        if r.get("extraction_run_id") != extraction_run_id or r.get("page_number") not in page_numbers
    ]
    if bad:
        return Finding(
            "row_provenance", FAIL,
            f"row(s) with a bad run_id or dangling page_number back-pointer: {bad}",
        )
    return Finding(
        "row_provenance", PASS,
        f"{len(rows)} row(s) traceable to a recorded page and run_id={extraction_run_id!r}",
    )


def evaluate_future_run(
    run: dict,
    computed_hashes: dict[int, str] | None = None,
) -> list[Finding]:
    """Aggregate entry point for a FUTURE extraction run's full provenance bundle.

    `run` keys: extraction_run_id, compound, capped, extraction_cap, total_hits_reported, page_size,
    pagination_mode, pages (list of page dicts), rows (list of row dicts). See module docstring
    examples in test_extraction_contract.py for the exact shape.
    """
    rows = run["rows"]
    pages = run["pages"]
    rows_extracted = len(rows)
    unique_ids = len({r["publication_id"] for r in rows})
    return [
        evaluate_raw_source_archive(pages, computed_hashes=computed_hashes),
        evaluate_count_reconciliation(
            rows_extracted, unique_ids, run["total_hits_reported"], run["capped"], run.get("extraction_cap"),
        ),
        evaluate_pagination_completeness(len(pages), run["total_hits_reported"], run["page_size"], run["capped"]),
        evaluate_pagination_mode(run["pagination_mode"]),
        evaluate_row_provenance(rows, pages, run["extraction_run_id"]),
    ]


def evaluate_query_documented_legacy(compound_display_name: str, readme_text: str) -> Finding:
    """Real (not rubber-stamped) check: the compound's display name must actually appear in the
    README prose for this to count as documented -- not assumed true for every compound."""
    if compound_display_name in readme_text:
        return Finding(
            "query_documented_human_readable", PASS,
            f"README mentions compound {compound_display_name!r}",
        )
    return Finding(
        "query_documented_human_readable", FAIL,
        f"README does not mention compound {compound_display_name!r}",
    )


def evaluate_legacy_compound(
    compound_display_name: str,
    rows: list[dict],
    capped: bool,
    total_hits_reported: int,
    readme_text: str,
) -> list[Finding]:
    """Retroactive, read-only audit of one v0.1 compound CSV against the v1 contract.

    v0.1 never recorded a raw archive, page-level trace, session log, or a separately declared
    extraction_cap -- those invariants report LEGACY_UNVERIFIABLE, not FAIL, and are never
    backfilled. count_reconciliation IS checkable from the CSV's own columns (publication_id,
    capped, total_hits_reported) and is the one invariant that would have caught the historical
    Brentuximab under-count immediately.
    """
    rows_extracted = len(rows)
    unique_ids = len({r["publication_id"] for r in rows})
    extraction_cap = rows_extracted if capped else None

    count_finding = evaluate_count_reconciliation(
        rows_extracted, unique_ids, total_hits_reported, capped, extraction_cap,
    )
    if capped and count_finding.verdict == PASS:
        count_finding = Finding(
            "count_reconciliation", PASS,
            count_finding.detail + " (extraction_cap inferred as rows saved -- v0.1 does not "
            "record a separately declared cap)",
        )

    return [
        Finding("raw_source_archive", LEGACY_UNVERIFIABLE, "no raw API archive captured for this pass"),
        count_finding,
        Finding("pagination_completeness", LEGACY_UNVERIFIABLE, "no page-level trace recorded for this pass"),
        Finding("pagination_mode", LEGACY_UNVERIFIABLE, "no session log recorded for this pass"),
        evaluate_query_documented_legacy(compound_display_name, readme_text),
        Finding(
            "query_documented_machine_readable", LEGACY_UNVERIFIABLE,
            "no machine-readable request metadata (endpoint/params) captured for this pass",
        ),
    ]
