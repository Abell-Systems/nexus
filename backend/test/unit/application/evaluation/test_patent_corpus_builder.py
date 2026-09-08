"""Unit tests for deterministic sha256(publication_id)-order selection (ADR 0020 §3, §4)."""

import hashlib

import pytest

from application.evaluation.patent_corpus_builder import (
    PatentCorpusConstructionError,
    select_frozen_patents,
)
from domain.models.patent import PatentDocument


def _doc(pub_id: str) -> PatentDocument:
    return PatentDocument(
        publication_id=pub_id,
        country_code=pub_id[:2],
        doc_number=pub_id[2:],
        kind_code="B2",
        title=f"Title {pub_id}",
        abstract=f"Abstract for {pub_id}.",
    )


def test_selection_is_sorted_by_sha256_of_publication_id():
    docs = [_doc("US1"), _doc("US2"), _doc("US3")]
    selected = select_frozen_patents(docs, target_n=3, minimum_acceptable_n=1)

    expected_order = sorted(docs, key=lambda d: hashlib.sha256(d.publication_id.encode()).hexdigest())
    assert [d.publication_id for d in selected] == [d.publication_id for d in expected_order]


def test_selection_caps_at_target_n():
    docs = [_doc(f"US{i}") for i in range(10)]
    selected = select_frozen_patents(docs, target_n=4, minimum_acceptable_n=1)
    assert len(selected) == 4


def test_selection_takes_all_when_below_target():
    docs = [_doc(f"US{i}") for i in range(3)]
    selected = select_frozen_patents(docs, target_n=100, minimum_acceptable_n=1)
    assert len(selected) == 3


def test_selection_raises_below_floor():
    docs = [_doc(f"US{i}") for i in range(3)]
    with pytest.raises(PatentCorpusConstructionError, match="eligible_available_records"):
        select_frozen_patents(docs, target_n=100, minimum_acceptable_n=5)


def test_selection_is_reproducible_across_calls():
    docs = [_doc(f"US{i}") for i in range(20)]
    first = select_frozen_patents(docs, target_n=10, minimum_acceptable_n=1)
    second = select_frozen_patents(list(reversed(docs)), target_n=10, minimum_acceptable_n=1)
    assert [d.publication_id for d in first] == [d.publication_id for d in second]


def test_selection_keeps_last_occurrence_when_same_publication_id_has_different_content():
    """select_frozen_patents does its own dict-based dedup keyed on publication_id.

    This is a general-purpose function, not exclusively fed from a single
    PatentValidator run -- callers upstream (e.g. two disagreeing sources, or a
    data-quality bug) can hand it two PatentDocuments sharing a publication_id
    but differing in content. The dict comprehension's last-wins semantics
    silently pick the document that appears LATER in the input list and drop
    the earlier one, with no warning or error. That behavior is deliberate and
    kept as-is (per ADR 0020 task brief) -- this test makes it explicit and
    pins it down instead of leaving it an accidental side effect of a dict
    comprehension.
    """
    first_seen = _doc("US1")
    first_seen.title = "First title"
    last_seen = _doc("US1")
    last_seen.title = "Last title"

    selected = select_frozen_patents(
        [first_seen, last_seen], target_n=10, minimum_acceptable_n=1
    )

    assert len(selected) == 1
    assert selected[0].title == "Last title"
