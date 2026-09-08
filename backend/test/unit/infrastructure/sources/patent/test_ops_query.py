"""Unit tests for the OPS CQL query builder (ADR 0020 §2, §3)."""

import pytest

from infrastructure.sources.patent.ops_query import build_patent_corpus_cql


def test_build_query_encodes_all_jurisdictions_and_window():
    query = build_patent_corpus_cql(
        jurisdictions=["EP", "US", "JP", "CN", "KR", "WO"],
        min_publication_year=2016,
        max_publication_year=2026,
    )
    assert 'pn=EP or pn=US or pn=JP or pn=CN or pn=KR or pn=WO' in query
    assert "pd within \"20160101 20261231\"" in query


def test_build_query_is_deterministic():
    args = dict(jurisdictions=["EP", "US"], min_publication_year=2020, max_publication_year=2021)
    assert build_patent_corpus_cql(**args) == build_patent_corpus_cql(**args)


def test_build_query_rejects_empty_jurisdictions():
    with pytest.raises(ValueError, match="jurisdictions"):
        build_patent_corpus_cql(jurisdictions=[], min_publication_year=2016, max_publication_year=2026)


def test_build_query_rejects_inverted_window():
    with pytest.raises(ValueError, match="min_publication_year"):
        build_patent_corpus_cql(jurisdictions=["EP"], min_publication_year=2026, max_publication_year=2016)
