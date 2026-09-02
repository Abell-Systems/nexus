"""Source adapters for external authorities (Patent and Demand)."""

from nexus.infrastructure.sources.patent.oepm_raw_source import OepmRawSource
from nexus.infrastructure.sources.patent.epo_ops_client import EpoOpsClient

__all__ = ["OepmRawSource", "EpoOpsClient"]
