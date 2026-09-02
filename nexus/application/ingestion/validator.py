"""Patent validation rules and schema enforcement."""

from datetime import datetime
from nexus.domain.models.patent import PatentDocument


class ValidationError(Exception):
    """Raised when a patent document or batch violates domain validation rules."""


class PatentValidator:
    """Validator enforcing integrity and quality constraints on patent documents."""

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
        date_fields = [
            ("filing_date", doc.filing_date),
            ("publication_date", doc.publication_date),
            ("priority_date", doc.priority_date),
        ]
        for field_name, date_val in date_fields:
            if date_val is not None:
                if not isinstance(date_val, str):
                    raise ValidationError(
                        f"Invalid date format for {field_name}: {date_val}. Expected YYYY-MM-DD"
                    )
                try:
                    parsed = datetime.strptime(date_val, "%Y-%m-%d")
                    # Ensure strict canonical format (e.g. correct padding and valid calendar dates)
                    if parsed.strftime("%Y-%m-%d") != date_val:
                        raise ValueError()
                except ValueError:
                    raise ValidationError(
                        f"Invalid date format for {field_name}: {date_val}. Expected YYYY-MM-DD"
                    )

        # 3. Citation count checks
        if doc.forward_citation_count is not None and doc.forward_citation_count < 0:
            raise ValidationError("forward_citation_count cannot be negative")

        if doc.backward_citation_count is not None and doc.backward_citation_count < 0:
            raise ValidationError("backward_citation_count cannot be negative")

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
