"""Patent validation rules and schema enforcement."""

from datetime import datetime

from domain.models.patent import PatentDocument


class ValidationError(Exception):
    """Raised when a patent document or batch violates domain validation rules."""


class PatentValidator:
    """Validator enforcing integrity and quality constraints on patent documents."""

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
