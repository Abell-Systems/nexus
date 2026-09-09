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


class ClusterPatentsIndependentRegressionOracleTest:
    """Golden-value regression test (PR #74 review, Bloqueante 3): expected values
    below are hand-derived from compute_white_space_metrics's formula independently
    of calling compute_cluster_landscape/cluster_patents — not by comparing the
    refactored function against itself or against another helper in this module.

    Single patent, single cluster, no demand signals. ref_year=2026 (default),
    horizon_years=20 (default):
      n_i=1, n_max=1 -> density = 1/1 = 1.0
      age = 2026-2016 = 10 -> recency = max(0, min(1, 1 - 10/20)) = 0.5
      citation_traction: age=10>3 -> tau_p = citation_count/age = 5/10 = 0.5;
        traction = min(1, max(0, 0.5/5.0)) = 0.1; citation_coverage = 1/1 = 1.0
      demand_intensity = 0.0 (no demand signals)
      white_space_score = 0.40*(1-1.0) + 0.20*0.5 + 0.15*0.1 + 0.25*0.0
                         = 0 + 0.10 + 0.015 + 0 = 0.115
      is_white_space = 0.115 >= 0.50 -> False
      quadrant: demand_intensity(0.0) < 0.5 and density(1.0) >= 0.4
                -> "Quadrant IV (Over-patented / Low Market Pull)"
      mean_age_years = 10.0
    """

    def _oracle_patent(self) -> PatentRecord:
        return _patent(
            publication_number="ORACLE-0001",
            title="Oracle test patent",
            filing_date="2016-01-01",
            cpc_codes=["H01M10/0562"],
            citation_count=5,
            backward_citation_count=None,
        )

    def test_cluster_patents_should_match_hand_derived_expected_cluster(self) -> None:
        clusters = cluster_patents([self._oracle_patent()], demand_signals=[], domain="solid_state_battery")

        assert len(clusters) == 1
        cluster = clusters[0]
        assert cluster.cluster_id == "H01M"
        assert cluster.label == "Solid State Battery - H01M"
        assert cluster.representative_patents == ["ORACLE-0001"]
        assert cluster.patent_count == 1
        assert cluster.white_space_score == 0.115
        assert cluster.is_white_space is False

    def test_compute_cluster_landscape_should_match_hand_derived_expected_metrics(self) -> None:
        results = compute_cluster_landscape([self._oracle_patent()], demand_signals=[], domain="solid_state_battery")

        assert len(results) == 1
        _cluster, metrics = results[0]
        assert metrics["density"] == 1.0
        assert metrics["recency"] == 0.5
        assert metrics["citation_traction"] == 0.1
        assert metrics["citation_coverage"] == 1.0
        assert metrics["demand_intensity"] == 0.0
        assert metrics["white_space_score"] == 0.115
        assert metrics["is_white_space"] is False
        assert metrics["quadrant"] == "Quadrant IV (Over-patented / Low Market Pull)"
        assert metrics["mean_age_years"] == 10.0


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
