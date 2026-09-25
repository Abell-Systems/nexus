from domain.models.corpus_expansion import TechnicalProblemClassification
from domain.protocols.corpus import TechnicalProblemClassifierProtocol


def test_technical_problem_classifier_protocol_accepts_conforming_implementation():
    class FakeClassifier:
        def classify(self, description_text: str) -> TechnicalProblemClassification:
            return TechnicalProblemClassification.EMPTY_INSUFFICIENT

    assert isinstance(FakeClassifier(), TechnicalProblemClassifierProtocol)


def test_technical_problem_classifier_protocol_rejects_non_conforming_object():
    class NotAClassifier:
        pass

    assert not isinstance(NotAClassifier(), TechnicalProblemClassifierProtocol)
