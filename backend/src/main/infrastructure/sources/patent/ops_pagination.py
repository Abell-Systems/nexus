"""Enumerability-safe pagination over EpoOpsClient.fetch_batches.

Per ADR 0020 §4 (and the explicit implementation-time requirement it does not yet
codify in text): eligible_available_records must be the FULL universe satisfying the
inclusion contract, never a fetch that was silently truncated by an API/pagination
limit. This module either enumerates the true universe completely -- verified against
EPO OPS's own `total-result-count` -- or raises, so a truncated fetch can never
silently become "the" corpus.
"""

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import Protocol

from domain.protocols.sources import RawPayload


class _PaginatedPatentSource(Protocol):
    def fetch_batches(
        self, cql_query: str = "", range_start: int = 1, range_end: int = 25
    ) -> Iterator[RawPayload]: ...


def parse_total_result_count(xml_bytes: bytes) -> int | None:
    """Extract ops:biblio-search's total-result-count attribute, namespace-agnostic."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    for elem in root.iter():
        tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag_local == "biblio-search" and "total-result-count" in elem.attrib:
            try:
                return int(elem.attrib["total-result-count"])
            except ValueError:
                return None
    return None


def fetch_all_ops_batches(
    client: _PaginatedPatentSource,
    cql_query: str,
    page_size: int = 100,
    max_records: int = 60000,
) -> list[RawPayload]:
    """Page through `client.fetch_batches` until EPO OPS's own total-result-count is
    fully covered, and return the complete, verified list of batches. Raises
    RuntimeError instead of returning anything if the total count is missing,
    changes mid-run, or exceeds `max_records` before completion.

    Deliberately NOT a generator: every batch is verified and buffered internally
    as it arrives, and only handed to the caller via `return` once the full universe
    has been confirmed covered. A generator's `yield` would expose each batch to the
    caller before the run as a whole (not just that one page) had been verified
    complete -- a caller consuming it lazily could observe and act on data from a
    fetch that later turns out to be truncated or corrupt. Buffer-then-return closes
    that gap: this function either returns the complete verified list, or raises
    before returning anything at all.
    """
    range_start = 1
    known_total: int | None = None
    batches: list[RawPayload] = []

    while True:
        range_end = range_start + page_size - 1
        batch = next(iter(client.fetch_batches(cql_query=cql_query, range_start=range_start, range_end=range_end)))

        page_total = parse_total_result_count(batch.payload_bytes)
        if page_total is None:
            try:
                ET.fromstring(batch.payload_bytes)
                cause = "the response parsed but has no ops:biblio-search total-result-count attribute"
            except ET.ParseError as e:
                cause = f"the response XML failed to parse ({e})"
            raise RuntimeError(
                f"EPO OPS response for range {range_start}-{range_end} is missing "
                f"total-result-count ({cause}); cannot verify complete enumeration of the "
                "eligible universe (ADR 0020 §4 enumerability requirement)."
            )
        batches.append(batch)
        if known_total is None:
            known_total = page_total
        elif page_total != known_total:
            raise RuntimeError(
                f"EPO OPS total-result-count changed mid-pagination ({known_total} -> "
                f"{page_total}); the universe is not stable, cannot guarantee complete "
                "enumeration."
            )

        if range_end >= known_total:
            return batches
        if range_end >= max_records:
            raise RuntimeError(
                f"EPO OPS pagination reached max_records={max_records} before covering "
                f"total_result_count={known_total} for query {cql_query!r}. Raise "
                "max_records or narrow the query -- do not silently accept a truncated fetch."
            )
        range_start = range_end + 1


def peek_total_result_count(client: _PaginatedPatentSource, cql_query: str) -> int:
    """Fetch page 1 only of `cql_query` and return its declared total-result-count,
    without paginating further. Used to decide partition eligibility (PR-E0.1 contract
    §5.3) before committing to a full fetch_all_ops_batches run. Raises RuntimeError
    with the same diagnostic style as fetch_all_ops_batches if total-result-count is
    missing or unparseable.
    """
    batch = next(iter(client.fetch_batches(cql_query=cql_query, range_start=1, range_end=1)))
    total = parse_total_result_count(batch.payload_bytes)
    if total is None:
        raise RuntimeError(
            f"EPO OPS response for query {cql_query!r} is missing total-result-count; "
            "cannot determine partition eligibility (PR-E0.1 contract §5.3)."
        )
    return total
