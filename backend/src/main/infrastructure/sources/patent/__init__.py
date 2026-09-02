"""Patent source adapters."""

from infrastructure.sources.patent.epo_ops_client import EpoOpsClient
from infrastructure.sources.patent.oepm_raw_source import OepmRawSource

__all__ = ["OepmRawSource", "EpoOpsClient"]
