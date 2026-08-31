"""Builds a compact, token-budgeted text summary of one selected cluster.

Deterministic and credential-free, same spirit as clustering.py. Keeps the
Inventor/Adversarial agents from having to replay the full patent landscape
(20+ raw records, citations, similar-patent lookups) on every LLM call —
they get just enough evidence to write a defensible claim.
"""

from .schemas import DemandSignal, PatentCluster, PatentRecord

_ABSTRACT_CHARS = 220  # ponytail: fixed truncation, raise if inventor claims read thin


def build_cluster_context(
    cluster: PatentCluster,
    records: list[PatentRecord],
    demand_signals: list[DemandSignal],
) -> str:
    """Compact context for one cluster: label, score, its representative patents
    (already the top-3 by citation_count from clustering.py), and any matching
    demand signals. Target: well under 1K tokens."""
    by_pub = {r.publication_number: r for r in records}
    lines = [
        f"Cluster {cluster.cluster_id} — {cluster.label}",
        f"white_space_score={cluster.white_space_score} is_white_space={cluster.is_white_space} "
        f"patent_count={cluster.patent_count}",
        "Representative patents:",
    ]
    for pub_number in cluster.representative_patents:
        record = by_pub.get(pub_number)
        if record is None:
            continue
        abstract = record.abstract[:_ABSTRACT_CHARS]
        lines.append(
            f"- {record.publication_number} ({record.publication_date}) \"{record.title}\": {abstract}"
        )

    matching_demand = [d for d in demand_signals if d.cpc_prefix and d.cpc_prefix in cluster.cluster_id]
    if matching_demand:
        lines.append("Demand signals:")
        for signal in matching_demand[:3]:
            lines.append(f"- [{signal.source}] {signal.title}: {signal.description[:_ABSTRACT_CHARS]}")

    return "\n".join(lines)
