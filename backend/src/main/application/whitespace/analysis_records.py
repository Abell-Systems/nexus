"""Records reduced to what the white-space descriptive analyses need (characterization §4.2 and §7).

Derived values are computed here from the adapter's raw observations and nowhere else.
"""

from collections.abc import Iterable
from datetime import date
from typing import NamedTuple

from application.whitespace.corpus_report import kind_group
from domain.models.whitespace import PatentPublication, RejectedRecord


class AnalysisRecord(NamedTuple):
    doc_id: str
    published: date
    group: str
    filing_year: int | None
    subclasses: tuple[str, ...]
    kind: str = ""

    @property
    def is_ep_translation(self) -> bool:
        return self.group == "ep_translation"


def filing_year(publication: PatentPublication) -> int | None:
    """Year of the earliest readable date among the priority dates and the application date.

    A priority claim whose date could not be read is ignored here (it is not in ``priority_dates``), so the
    year comes from the other readable dates; ``None`` only if there is no readable date at all.
    """
    dates = [*publication.priority_dates, *([publication.application_date] if publication.application_date else [])]
    return min(dates).year if dates else None


def to_analysis_records(outcomes: Iterable[PatentPublication | RejectedRecord]) -> list[AnalysisRecord]:
    """Every read publication, in source order; rejected records are not part of the analysis."""
    return [
        AnalysisRecord(
            doc_id=item.doc_id,
            published=item.publication_date,
            group=kind_group(item.kind),
            filing_year=filing_year(item),
            subclasses=tuple(sorted({entry.subclass_symbol for entry in item.ipc_entries})),
            kind=item.kind,
        )
        for item in outcomes
        if isinstance(item, PatentPublication)
    ]


def distinct_publications(records: Iterable[AnalysisRecord]) -> list[AnalysisRecord]:
    """First occurrence of each (identifier, publication date): the 'distinct document' of the analyses (ADR 0036 P4)."""
    seen: set[tuple[str, date]] = set()
    kept: list[AnalysisRecord] = []
    for record in records:
        key = (record.doc_id, record.published)
        if key not in seen:
            seen.add(key)
            kept.append(record)
    return kept
