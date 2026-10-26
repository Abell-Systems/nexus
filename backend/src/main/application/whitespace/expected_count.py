"""Expected co-classifications under independence within publication years (ADR 0038 E3; vertical 3 contract, section 3).

For a pair of subclasses (i, j): E(i, j) = sum over observed years y of n_i(y) * n_j(y) / N(y), where n_i(y) is the number of
documents first published in y that carry i (the unit of the study, O4: the publication identifier, the union of the
subclasses of its earliest date) and N(y) the number of documents first published in y. A year with no document (2010) is
skipped, never counted as zero. This is a descriptive reference under independence. It is not the study's null model (no
degree-preserving randomisation), not a score, not a baseline and not F1, and nothing here predicts anything.
"""

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping

from application.whitespace.analysis_records import AnalysisRecord
from application.whitespace.base_rates import active_subclass_sets, activity_counts
from application.whitespace.subclass_pairs import subclass_pairs


def documents_per_year(records: Iterable[AnalysisRecord]) -> dict[int, int]:
    """N(y): the documents (identifiers) whose earliest publication date falls in y."""
    earliest: dict[str, int] = {}
    for record in records:
        year = record.published.year
        if record.doc_id not in earliest or year < earliest[record.doc_id]:
            earliest[record.doc_id] = year
    return dict(Counter(earliest.values()))


def expected_count(a: Mapping[int, int], b: Mapping[int, int], totals: Mapping[int, int]) -> float:
    """The formula of E3 over the years in which documents exist (``totals``); a missing count in a year is 0 documents."""
    return sum(a.get(year, 0) * b.get(year, 0) / total for year, total in totals.items() if total > 0)


def unobserved_pairs_expected(
    records: Iterable[AnalysisRecord], origin: int, min_documents: int = 20
) -> Iterator[tuple[str, str, float]]:
    """Every pair of two active subclasses at ``origin`` that no single source record states, with its expected count."""
    records = [r for r in records if r.published.year <= origin]
    active = sorted(active_subclass_sets(records, [origin], min_documents=min_documents, copy_policy="union")[origin])
    observed = set(subclass_pairs(records, origin, min_documents)["pairs"])
    counts = activity_counts(records, "union")
    totals = documents_per_year(records)
    for index, a in enumerate(active):
        for b in active[index + 1 :]:
            if f"{a}|{b}" not in observed:
                yield a, b, expected_count(counts[a], counts[b], totals)
