"""Patent validation rules, deduplication tracking, and schema enforcement."""

from datetime import datetime

from domain.models.ingestion import (
    NormalizationResult,
    QuarantinedRecord,
    QuarantineReason,
    RecordDisposition,
)
from domain.models.patent import PatentDocument


class ValidationError(Exception):
    """Raised when a patent document or batch violates domain validation rules."""


class PatentValidator:
    """Validator enforcing integrity, deduplication, and quality constraints on patent documents."""

    def __init__(self) -> None:
        self._seen_publication_ids: set[str] = set()

    def reset_deduplication(self) -> None:
        """Reset internal deduplication state across pipeline runs."""
        self._seen_publication_ids.clear()

    def is_duplicate(self, publication_id: str) -> bool:
        """Check if publication_id has already been processed and track it."""
        if not publication_id or not publication_id.strip():
            return False
        clean_id = publication_id.strip()
        if clean_id in self._seen_publication_ids:
            return True
        self._seen_publication_ids.add(clean_id)
        return False

    def validate_normalization_result(
        self, result: NormalizationResult
    ) -> NormalizationResult:
        """Validate and classify a NormalizationResult enforcing deduplication and critical constraints.

        If a document is INCLUDED but its publication_id has already been processed,
        it is re-classified as DUPLICATE.
        """
        if result.disposition == RecordDisposition.INCLUDED and result.document is not None:
            # 1. Check publication_id deduplication
            if self.is_duplicate(result.document.publication_id):
                return NormalizationResult(
                    disposition=RecordDisposition.DUPLICATE,
                    document=result.document,
                    observations=result.observations,
                )

            # 2. Strict document validation
            try:
                self.validate_document(result.document)
            except ValidationError as e:
                # Quarantines invalid document
                return NormalizationResult(
                    disposition=RecordDisposition.QUARANTINED,
                    quarantined=QuarantinedRecord(
                        raw_identifier=result.document.publication_id,
                        reason=QuarantineReason.UNVERIFIABLE_METADATA,
                        error_message=f"Validation failed: {e}",
                        raw_snippet=f"publication_id={result.document.publication_id}",
                        detected_at=datetime.now(),
                        source_uri="",
                    ),
                    observations=result.observations,
                )

        return result

    def _validate_date(self, date_val: str | None, field_name: str) -> None:
        if date_val is None:
            return
        if not isinstance(date_val, str):
            raise ValidationError(
                f"Invalid date format for {field_name}: {date_val}. Expected YYYY-MM-DD"
            )
        try:
            parsed = datetime.strptime(date_val, "%Y-%m-%d")
            if parsed.strftime("%Y-%m-%d") != date_val:
                raise ValueError()
        except ValueError:
            raise ValidationError(
                f"Invalid date format for {field_name}: {date_val}. Expected YYYY-MM-DD"
            ) from None

    def _validate_citations(self, doc: PatentDocument) -> None:
        if doc.forward_citation_count is not None and doc.forward_citation_count < 0:
            raise ValidationError("forward_citation_count cannot be negative")
        if doc.backward_citation_count is not None and doc.backward_citation_count < 0:
            raise ValidationError("backward_citation_count cannot be negative")

    def validate_document(self, doc: PatentDocument) -> bool:
        """Validate a single PatentDocument instance.

        Raises:
            ValidationError: If any validation rule fails.

        Returns:
            bool: True if validation succeeds.
        """
        # 1. Publication ID must be non-empty and non-whitespace
        if not doc.publication_id or not doc.publication_id.strip():
            raise ValidationError("publication_id cannot be empty")

        # 2. Date format and calendar validity checks (YYYY-MM-DD)
        self._validate_date(doc.filing_date, "filing_date")
        self._validate_date(doc.publication_date, "publication_date")
        self._validate_date(doc.priority_date, "priority_date")

        # 3. Citation count checks
        self._validate_citations(doc)

        return True

    def validate_batch(self, documents: list[PatentDocument]) -> list[PatentDocument]:
        """Validate a batch of PatentDocument instances.

        Raises:
            ValidationError: If any document in the batch fails validation.

        Returns:
            list[PatentDocument]: The validated batch.
        """
        for doc in documents:
            self.validate_document(doc)
        return documents
