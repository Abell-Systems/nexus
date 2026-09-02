import pytest
from domain.models.patent import PatentDocument
from application.ingestion.validator import PatentValidator, ValidationError


def test_validator_rejects_missing_publication_id():
    validator = PatentValidator()
    doc = PatentDocument(
        publication_id="",
        country_code="ES",
        doc_number="",
        kind_code="B2",
        title="Valid Title",
        abstract="Valid Abstract",
    )
    with pytest.raises(ValidationError, match="publication_id cannot be empty"):
        validator.validate_document(doc)


def test_validator_rejects_whitespace_publication_id():
    validator = PatentValidator()
    doc = PatentDocument(
        publication_id="   ",
        country_code="ES",
        doc_number="2849102",
        kind_code="B2",
        title="Valid Title",
        abstract="Valid Abstract",
    )
    with pytest.raises(ValidationError, match="publication_id cannot be empty"):
        validator.validate_document(doc)


def test_validator_checks_date_format_valid():
    validator = PatentValidator()
    doc = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        filing_date="2020-05-10",
        publication_date="2021-05-10",
        priority_date="2019-12-01",
    )
    assert validator.validate_document(doc) is True


def test_validator_allows_none_dates():
    validator = PatentValidator()
    doc = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        filing_date=None,
        publication_date=None,
        priority_date=None,
    )
    assert validator.validate_document(doc) is True


def test_validator_rejects_invalid_date_formats():
    validator = PatentValidator()

    # Slashes instead of dashes
    doc1 = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        publication_date="2021/05/10",
    )
    with pytest.raises(ValidationError, match="Invalid date format for publication_date"):
        validator.validate_document(doc1)

    # DD-MM-YYYY format
    doc2 = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        filing_date="10-05-2021",
    )
    with pytest.raises(ValidationError, match="Invalid date format for filing_date"):
        validator.validate_document(doc2)

    # Invalid calendar day (e.g. Feb 31)
    doc3 = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        priority_date="2021-02-31",
    )
    with pytest.raises(ValidationError, match="Invalid date format for priority_date"):
        validator.validate_document(doc3)


def test_validator_leap_year_handling():
    validator = PatentValidator()

    # Valid leap day
    doc_leap_valid = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        filing_date="2020-02-29",
    )
    assert validator.validate_document(doc_leap_valid) is True

    # Invalid non-leap year Feb 29
    doc_leap_invalid = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        filing_date="2021-02-29",
    )
    with pytest.raises(ValidationError, match="Invalid date format for filing_date"):
        validator.validate_document(doc_leap_invalid)


def test_validator_rejects_negative_citations():
    validator = PatentValidator()
    doc1 = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        forward_citation_count=-1,
    )
    with pytest.raises(ValidationError, match="forward_citation_count cannot be negative"):
        validator.validate_document(doc1)

    doc2 = PatentDocument(
        publication_id="ES-001-A1",
        country_code="ES",
        doc_number="001",
        kind_code="A1",
        title="Valid Title",
        abstract="Valid Abstract",
        backward_citation_count=-3,
    )
    with pytest.raises(ValidationError, match="backward_citation_count cannot be negative"):
        validator.validate_document(doc2)


def test_validator_validate_batch_success():
    validator = PatentValidator()
    docs = [
        PatentDocument(
            publication_id=f"ES-{i:03d}-A1",
            country_code="ES",
            doc_number=f"{i:03d}",
            kind_code="A1",
            title=f"Valid Title {i}",
            abstract=f"Valid Abstract {i}",
            publication_date="2021-05-10",
        )
        for i in range(5)
    ]
    result = validator.validate_batch(docs)
    assert len(result) == 5
    assert result == docs


def test_validator_validate_batch_empty():
    validator = PatentValidator()
    assert validator.validate_batch([]) == []


def test_validator_validate_batch_fails_on_invalid_doc():
    validator = PatentValidator()
    docs = [
        PatentDocument(
            publication_id="ES-001-A1",
            country_code="ES",
            doc_number="001",
            kind_code="A1",
            title="Valid Title",
            abstract="Valid Abstract",
        ),
        PatentDocument(
            publication_id="",
            country_code="ES",
            doc_number="002",
            kind_code="A1",
            title="Valid Title",
            abstract="Valid Abstract",
        ),
    ]
    with pytest.raises(ValidationError, match="publication_id cannot be empty"):
        validator.validate_batch(docs)
