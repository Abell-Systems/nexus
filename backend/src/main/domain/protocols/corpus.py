"""Domain protocol for TED construct-eligibility text classification, per
docs/superpowers/specs/2026-09-23-ted-construct-validity-classifier-design.md."""

from typing import Protocol, runtime_checkable

from domain.models.corpus_expansion import TechnicalProblemClassification


@runtime_checkable
class TechnicalProblemClassifierProtocol(Protocol):
    """Classifies whether a candidate's description text articulates a genuine
    technical problem (spec SS3), a generic procurement/scope description, or is
    empty/insufficient."""

    def classify(self, description_text: str) -> TechnicalProblemClassification:
        ...  # pragma: no cover
