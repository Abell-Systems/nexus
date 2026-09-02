"""Patent source adapters."""

from infrastructure.sources.patent.oepm_raw_source import OepmRawSource
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient

__all__ = ["OepmRawSource", "EpoOpsClient"]
