"""Patent normalizers module."""

from nexus.application.ingestion.normalizers.base import PatentNormalizerProtocol
from nexus.application.ingestion.normalizers.oepm_normalizer import OepmNormalizer

__all__ = [
    "PatentNormalizerProtocol",
    "OepmNormalizer",
]
