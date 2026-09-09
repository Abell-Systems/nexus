from application.landscape.clustering import cluster_patents, compute_cluster_landscape
from domain.models.demand import DemandSignal
from domain.models.runtime_schemas import PatentRecord


def _patent(**overrides) -> PatentRecord:
    defaults = {
        "publication_number": "US-11223001-B2",
        "title": "Solid state battery with sulfide solid electrolyte",
        "abstract": "A solid state battery.",
        "filing_date": "2020-03-15",
        "cpc_codes": ["H01M10/0562"],
        "citation_count": 8,
        "backward_citation_count": 12,
    }
    defaults.update(overrides)
    return PatentRecord(**defaults)


def _demand(**overrides) -> DemandSignal:
    defaults = {
        "demand_id": "dem-1",
        "title": "Solid electrolyte demand",
        "description": "Challenge description",
        "classified_cpc_prefixes": ["H01M"],
    }
    defaults.update(overrides)
    return DemandSignal(**defaults)


class ComputeClusterLandscapeTest:
    def test_should_return_empty_when_no_patents(self) -> None:
        assert compute_cluster_landscape([]) == []

    def test_should_pair_each_cluster_with_its_full_metrics_dict(self) -> None:
        results = compute_cluster_landscape([_patent()], demand_signals=[_demand()], domain="solid_state_battery")

        assert len(results) == 1
        cluster, metrics = results[0]
        assert cluster.cluster_id == "H01M"
        assert cluster.white_space_score == metrics["white_space_score"]
        assert cluster.is_white_space == metrics["is_white_space"]
        # Fields cluster_patents() discards must be present in the paired metrics dict.
        for key in ("density", "recency", "citation_traction", "citation_coverage", "demand_intensity", "quadrant", "mean_age_years"):
            assert key in metrics

    def test_should_produce_deterministic_output_for_the_same_input(self) -> None:
        patents = [_patent()]
        demands = [_demand()]

        first = compute_cluster_landscape(patents, demand_signals=demands, domain="solid_state_battery")
        second = compute_cluster_landscape(patents, demand_signals=demands, domain="solid_state_battery")

        assert first == second


class ClusterPatentsBackwardCompatibilityTest:
    """cluster_patents() now delegates to compute_cluster_landscape(); its own
    output must remain byte-for-byte identical to before the refactor."""

    def test_should_return_same_patent_clusters_as_compute_cluster_landscape(self) -> None:
        patents = [_patent()]
        demands = [_demand()]

        clusters = cluster_patents(patents, demand_signals=demands, domain="solid_state_battery")
        paired = compute_cluster_landscape(patents, demand_signals=demands, domain="solid_state_battery")

        assert clusters == [cluster for cluster, _metrics in paired]

    def test_should_return_empty_list_when_no_patents(self) -> None:
        assert cluster_patents([]) == []
