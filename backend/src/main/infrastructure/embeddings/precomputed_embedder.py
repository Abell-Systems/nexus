from collections.abc import Mapping, Sequence


class UnknownEmbeddingTextError(KeyError):
    """No frozen vector exists for this text. The runtime never falls back to a live model."""


class PrecomputedEmbedder:
    """Looks up frozen demand vectors by their exact text. Structurally satisfies TextEmbedder."""

    def __init__(self, vectors_by_text: Mapping[str, Sequence[float]]) -> None:
        if not vectors_by_text:
            raise ValueError("PrecomputedEmbedder requires at least one vector")
        self._vectors = {text: [float(x) for x in vector] for text, vector in vectors_by_text.items()}

    def embed(self, text: str) -> list[float]:
        try:
            return list(self._vectors[text])
        except KeyError as err:
            raise UnknownEmbeddingTextError(f"No frozen embedding for text starting {text[:60]!r}") from err
