"""JSON-safe serialization for ComparativeRunReport (PR-E).

ComparativeRunReport.results[].wilcoxon / .bootstrap_ci are typed as plain
"object" in the domain model (they wrap pre-existing frozen dataclasses from
application.evaluation.statistics.types, PR #22) because pydantic does not own
those types. This module converts the full report to a plain, JSON-dumpable
dict for artifact output — an infrastructure/output concern, not a domain rule.
"""

import dataclasses
from typing import Any, cast

from application.evaluation.statistics.types import BootstrapCIResult, WilcoxonResult
from domain.models.evaluation import ComparativeRunReport


def serialize_comparative_report(report: ComparativeRunReport) -> dict[str, Any]:
    """Converts a ComparativeRunReport into a plain, JSON-dumpable dict."""
    return {
        "study_protocol_id": report.study_protocol_id,
        "study_protocol_sha256": report.study_protocol_sha256,
        "study_status": report.study_status,
        "run_ids": dict(report.run_ids),
        "results": [
            {
                "hypothesis_id": r.hypothesis_id,
                "baseline": r.baseline,
                "treatment": r.treatment,
                "metric": r.metric,
                "scope": r.scope,
                "wilcoxon": dataclasses.asdict(cast(WilcoxonResult, r.wilcoxon)),
                "bootstrap_ci": dataclasses.asdict(cast(BootstrapCIResult, r.bootstrap_ci)),
                "adjusted_q_value": r.adjusted_q_value,
                "rejected": r.rejected,
                "n_paired": r.n_paired,
                "excluded_demand_ids": list(r.excluded_demand_ids),
            }
            for r in report.results
        ],
    }
