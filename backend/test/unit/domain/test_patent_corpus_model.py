"""Unit tests for PatentCorpus/PatentCorpusItem (ADR 0020 §5)."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from domain.models.evaluation import DataModality, EvaluationProvenance, PatentCorpus, PatentCorpusItem


def _provenance() -> EvaluationProvenance:
    return EvaluationProvenance(
        source_authority="European Patent Office (EPO OPS 3.2)",
        source_uri="https://ops.epo.org",
        extraction_timestamp=datetime.now(UTC),
        raw_payload_sha256="a" * 64,
        modality=DataModality.OBSERVED,
    )


def _item(pub_id: str, country: str = "US") -> PatentCorpusItem:
    return PatentCorpusItem(
        publication_id=pub_id,
        country_code=country,
        kind_code="B2",
        title="A widget",
        abstract="A widget that does things.",
        publication_date="2020-01-01",
        classifications_cpc=["B65D1/00"],
        provenance=_provenance(),
    )


def test_patent_corpus_item_is_frozen():
    item = _item("US1234567B2")
    with pytest.raises(ValidationError):
        item.title = "changed"  # type: ignore[misc]


def test_patent_corpus_rejects_duplicate_publication_ids():
    with pytest.raises(ValidationError, match="Duplicate publication_id"):
        PatentCorpus(
            dataset_id="nexus-patent-corpus-p-v1",
            schema_version="1.0.0",
            dataset_version="1.0.0",
            description="test",
            patents=[_item("US1234567B2"), _item("US1234567B2")],
        )


def test_patent_corpus_accepts_multi_jurisdiction_items():
    corpus = PatentCorpus(
        dataset_id="nexus-patent-corpus-p-v1",
        schema_version="1.0.0",
        dataset_version="1.0.0",
        description="test",
        patents=[_item("US1234567B2", "US"), _item("JP1234567B2", "JP")],
    )
    assert {p.country_code for p in corpus.patents} == {"US", "JP"}
