"""Landscape clustering: groups a patent list into technology clusters and scores
each one for white-space potential.

v0 heuristic, deliberately credential-free: groups by CPC-code prefix and scores
white-space potential from density, recency and citation velocity. This avoids
requiring embeddings (which would need a Gemini API key or a downloaded local
model) so the pipeline is fully exercisable before GEMINI_API_KEY exists.

Upgrade path (tracked in docs/roadmap.md): once a real Gemini API key is
available, replace the CPC-prefix grouping with embedding-based clustering
(e.g. Gemini embeddings + HDBSCAN/KMeans) for finer-grained, non-taxonomy-bound
clusters. The output contract (PatentCluster) does not need to change.
"""

from collections import defaultdict
from datetime import date

from .schemas import DemandSignal, PatentCluster, PatentRecord

_CPC_LABELS = {
    "H01M": "Batteries & fuel cells",
    "C01B": "Non-metallic elements/compounds",
    "B01J": "Catalysts & chemical processes",
    "H01L": "Semiconductor devices",
    "C08L": "Polymer compositions",
    "G01N": "Materials investigation/analysis",
    "A61K": "Pharmaceutical preparations",
}


def _cpc_prefix(cpc_code: str) -> str:
    return cpc_code[:4] if cpc_code else "UNKNOWN"


def _primary_prefix(record: PatentRecord) -> str:
    if not record.cpc_codes:
        return "UNKNOWN"
    return _cpc_prefix(record.cpc_codes[0])


def _filing_year(record: PatentRecord, current_year: int) -> int:
    """Filing year, or the current year (age 1) for malformed dates from real sources."""
    try:
        return int(record.filing_date[:4])
    except ValueError:
        return current_year


def cluster_patents(
    patents: list[PatentRecord],
    demand_signals: list[DemandSignal] | None = None,
    current_year: int | None = None,
    white_space_threshold: float = 0.5,
) -> list[PatentCluster]:
    """Group patents by primary CPC prefix and score each group for white-space potential.

    Score combines four signals, each normalized to [0, 1]:
    - low density (few patents relative to the largest cluster) -> more white-space
    - recency (average filing year close to current_year) -> more white-space
    - citation velocity (citations per year since filing) -> active research interest,
      which keeps a low-density cluster from just being an abandoned dead end
    - demand (open technology-need signals whose cpc_prefix matches the cluster) ->
      market pull, which keeps a low-density cluster from being white-space nobody wants
    """
    if not patents:
        return []

    year = current_year or date.today().year

    groups: dict[str, list[PatentRecord]] = defaultdict(list)
    for record in patents:
        groups[_primary_prefix(record)].append(record)

    max_count = max(len(records) for records in groups.values())

    demand_counts: dict[str, int] = defaultdict(int)
    for signal in demand_signals or []:
        if signal.cpc_prefix:
            demand_counts[signal.cpc_prefix] += 1
    max_demand = max(demand_counts.values(), default=0)

    clusters: list[PatentCluster] = []
    for prefix, records in groups.items():
        count = len(records)
        density_norm = count / max_count

        ages = [max(1, year - _filing_year(r, year)) for r in records]
        avg_age = sum(ages) / len(ages)
        recency_norm = max(0.0, min(1.0, 1 - (avg_age / 20)))

        velocities = [r.citation_count / age for r, age in zip(records, ages)]
        avg_velocity = sum(velocities) / len(velocities)
        velocity_norm = max(0.0, min(1.0, avg_velocity / 10))

        demand_norm = (demand_counts[prefix] / max_demand) if max_demand else 0.0

        white_space_score = round(
            0.4 * (1 - density_norm)
            + 0.2 * recency_norm
            + 0.15 * velocity_norm
            + 0.25 * demand_norm,
            3,
        )

        representative = sorted(records, key=lambda r: r.citation_count, reverse=True)[:3]

        clusters.append(
            PatentCluster(
                cluster_id=f"cluster-{prefix}",
                label=_CPC_LABELS.get(prefix, f"CPC {prefix}"),
                representative_patents=[r.publication_number for r in representative],
                patent_count=count,
                white_space_score=white_space_score,
                is_white_space=white_space_score >= white_space_threshold,
            )
        )

    clusters.sort(key=lambda c: c.white_space_score, reverse=True)
    return clusters


def patents_for_demand_signal(
    signal: DemandSignal, domain: str, max_results: int = 20
) -> list[PatentRecord]:
    """Find patents related to one demand signal (e.g. an Innoget technology call).

    Searches patents by the signal's title, then narrows to the same CPC prefix
    when that yields any hits (falls back to the unfiltered search otherwise —
    the demand source's CPC classification is a heuristic, not exact).
    """
    from .bigquery_patents import get_patents_datasource

    records = get_patents_datasource().search_patents(signal.title, domain, max_results)
    if signal.cpc_prefix:
        matched = [r for r in records if _primary_prefix(r) == signal.cpc_prefix]
        if matched:
            return matched
    return records


def cluster_patents_tool(query: str, domain: str, max_results: int = 20) -> list[dict]:
    """Search patents for a domain and cluster them into white-space vs. saturated areas.

    Args:
        query: Free-text search terms (e.g. "solid electrolyte interphase").
        domain: The locked demo technology domain (see docs/roadmap.md).
        max_results: How many patents to pull before clustering.

    Returns:
        A list of clusters, each with a label, patent_count, white_space_score,
        is_white_space flag, and representative_patents (publication_numbers).
    """
    from .bigquery_patents import get_patents_datasource
    from .demand_sources import get_demand_datasource

    records = get_patents_datasource().search_patents(query, domain, max_results)
    demand_signals = get_demand_datasource().search_demand(query, domain)
    clusters = cluster_patents(records, demand_signals)
    return [c.model_dump() for c in clusters]
