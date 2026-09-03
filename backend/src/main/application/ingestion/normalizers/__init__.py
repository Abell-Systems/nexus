"""Patent normalizers module."""

from application.ingestion.normalizers.base import PatentNormalizerProtocol
from application.ingestion.normalizers.oepm_normalizer import OepmNormalizer

__all__ = [
    "PatentNormalizerProtocol",
    "OepmNormalizer",
]
