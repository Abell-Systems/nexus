"""Deterministic CPC Mapper for technology call records.

Re-exports from canonical cpc_taxonomy module to ensure single source of truth.
"""

from .cpc_taxonomy import map_cpc_prefix, map_demand_to_cpc, get_cpc_description

__all__ = ["map_cpc_prefix", "map_demand_to_cpc", "get_cpc_description"]
