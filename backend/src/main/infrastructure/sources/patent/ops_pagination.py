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
) -> Iterator[RawPayload]:
    """Page through `client.fetch_batches` until EPO OPS's own total-result-count is
    fully covered. Raises RuntimeError instead of returning a partial set if the total
    count is missing, changes mid-run, or exceeds `max_records` before completion.
    """
    range_start = 1
    known_total: int | None = None

    while True:
        range_end = range_start + page_size - 1
        batch = next(iter(client.fetch_batches(cql_query=cql_query, range_start=range_start, range_end=range_end)))
        yield batch

        page_total = parse_total_result_count(batch.payload_bytes)
        if page_total is None:
            raise RuntimeError(
                f"EPO OPS response for range {range_start}-{range_end} is missing "
                "total-result-count; cannot verify complete enumeration of the eligible "
                "universe (ADR 0020 §4 enumerability requirement)."
            )
        if known_total is None:
            known_total = page_total
        elif page_total != known_total:
            raise RuntimeError(
                f"EPO OPS total-result-count changed mid-pagination ({known_total} -> "
                f"{page_total}); the universe is not stable, cannot guarantee complete "
                "enumeration."
            )

        if range_end >= known_total:
            return
        if range_end >= max_records:
            raise RuntimeError(
                f"EPO OPS pagination reached max_records={max_records} before covering "
                f"total_result_count={known_total} for query {cql_query!r}. Raise "
                "max_records or narrow the query -- do not silently accept a truncated fetch."
            )
        range_start = range_end + 1
