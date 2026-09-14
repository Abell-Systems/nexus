"""INVENES population adequacy probe (pre-registered:
docs/phase2-invenes-population-adequacy-probe-preregistration.md).

Single, capped, predefined acquisition attempt answering: can a deliberate
acquisition strategy (specific multi-word technical queries, not the generic
terms that hurt coverage_characterization.py's yield) sustain the inclusion
rate needed to reach N>=60?

Deviation from pre-registration, decided before any inclusion outcome was
observed for these referencias: the "see first latest publications" toggle
proved unreliable to script (intermittent 504s on resubmit); dropped. Sampling
reverted to "first 4 non-PCT referencias per query, in the order INVENES
returns them" (still fully deterministic, no manual curation).

Independent of and disjoint from both prior batches (build_oepm_corpus.py's
smoke-test batch, coverage_characterization.py's generic-query batch).
"""

import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.oepm.invenes_detail_parser import parse_invenes_detail  # noqa: E402
from experiments.oepm.invenes_harvester import SOURCE_ID, InvenesHarvester  # noqa: E402

logger = logging.getLogger("experiments.oepm.population_adequacy_probe")

# Real "Number of results" INVENES reported per query (2026-09-14), and the
# first 4 non-PCT referencias returned, in order -- fixed before any
# classification outcome was observed.
REFERENCIA_BY_QUERY: dict[str, tuple[int, list[str]]] = {
    "sistema de refrigeracion por absorcion": (9959, ["P0191788", "P0552363", "P0401163", "U9500720"]),
    "dispositivo de monitorizacion de constantes vitales": (321, ["E03015537", "P201230951", "P201231201", "E06124382"]),
    "metodo de reciclaje de baterias de litio": (186, ["P201100237", "E20153991", "E20202581", "U202530397"]),
    "estructura modular de vivienda prefabricada": (94, ["P9002089", "P200600531", "P0526310", "U9302606"]),
    "sistema de purificacion de aire mediante fotocatalisis": (82, ["E05016942", "E90201172", "P200931134", "P201500772"]),
    "algoritmo de deteccion de fraude en transacciones": (120, ["E99303407", "E99303404", "E94201452", "E96118760"]),
    "revestimiento anticorrosivo para estructuras metalicas": (99, ["U9401743", "P0481547", "E89101632", "P0522864"]),
    "sistema de riego automatizado por goteo": (83, ["P200401444", "U9302107", "P200700618", "E88106685"]),
    "dispositivo de asistencia para movilidad reducida": (464, ["U200502811", "P201200383", "P201331371", "P201831035"]),
    "metodo de fabricacion aditiva de piezas metalicas": (242, ["E10153412", "P201430439", "E11000350", "P202130841"]),
}

ALLOWED_KIND_CODES = frozenset({"A1", "A2", "B1", "B2", "U"})


def _decision(included: int, attempted_planned: int, harvested: int) -> str:
    if harvested < attempted_planned:
        return "OPERATIONALLY_CONSTRAINED_UNRESOLVED"
    rate = included / attempted_planned
    if included >= 8:
        return f"SCENARIO_A_SIGNAL (yield {rate:.1%} >= 20% threshold)"
    if included < 4:
        return f"SCENARIO_B_SIGNAL (yield {rate:.1%} < 10% threshold)"
    return f"INCONCLUSIVE (yield {rate:.1%}, between 10-20% thresholds)"


def run_probe(
    referencia_by_query: dict[str, tuple[int, list[str]]] = REFERENCIA_BY_QUERY,
    out_path: Path = REPO_ROOT / "data" / "experiments" / "oepm_v1" / "invenes_population_adequacy_probe.json",
    skip_harvest: bool = False,
    delay_seconds: float = 1.0,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    raw_dir = REPO_ROOT / "data" / "raw" / "oepm_invenes_probe_sample"
    all_referencias = [r for _, refs in referencia_by_query.values() for r in refs]
    referencia_query = {r: q for q, (_, refs) in referencia_by_query.items() for r in refs}

    if not skip_harvest:
        harvester = InvenesHarvester(delay_seconds=delay_seconds, timeout_seconds=timeout_seconds)
        harvester.harvest(all_referencias, out_dir=raw_dir)
        if harvester.acquisition_errors:
            (raw_dir.parent / "probe_harvest_errors.json").write_text(
                json.dumps(harvester.acquisition_errors, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

    dispositions = Counter()
    per_query_included = Counter()
    per_query_harvested = Counter()
    records: list[dict[str, Any]] = []

    for referencia in all_referencias:
        html_path = raw_dir / SOURCE_ID / f"{referencia}.html"
        query = referencia_query[referencia]
        if not html_path.exists():
            dispositions["not_harvested"] += 1
            continue
        per_query_harvested[query] += 1

        parsed = parse_invenes_detail(html_path.read_bytes(), referencia=referencia)
        if parsed is None:
            dispositions["quarantined_unparseable"] += 1
            continue

        item = parsed.item
        has_text = bool(item["title"].strip()) and bool(item["abstract"].strip())
        if parsed.kind_code not in ALLOWED_KIND_CODES:
            disposition = "excluded_kind_code"
        elif not has_text:
            disposition = "excluded_missing_text"
        else:
            disposition = "included"

        dispositions[disposition] += 1
        if disposition == "included":
            per_query_included[query] += 1

        records.append({
            "referencia": referencia, "query": query, "publication_id": item["publication_id"],
            "kind_code": parsed.kind_code, "disposition": disposition,
        })

    total_attempted = len(all_referencias)
    total_harvested = total_attempted - dispositions["not_harvested"]
    included = dispositions["included"]

    report = {
        "purpose": "Pre-registered population adequacy probe -- docs/phase2-invenes-population-adequacy-probe-preregistration.md",
        "deviation_from_preregistration": (
            "'See first latest publications' toggle proved unreliable to script (intermittent 504s); "
            "dropped before observing any classification outcome. Sampling rule (first 4 non-PCT per "
            "query, as returned) otherwise unchanged."
        ),
        "queries": {
            q: {
                "invenes_reported_total_results": total,
                "attempted": len(refs),
                "harvested": per_query_harvested[q],
                "included": per_query_included[q],
            }
            for q, (total, refs) in referencia_by_query.items()
        },
        "totals": {
            "attempted": total_attempted,
            "harvested": total_harvested,
            "dispositions": dict(dispositions),
            "yield_of_attempted": round(included / total_attempted, 3) if total_attempted else None,
        },
        "decision": _decision(included, total_attempted, total_harvested),
        "decision_rule_reference": "docs/phase2-invenes-population-adequacy-probe-preregistration.md SS4",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    out_path.with_name("invenes_population_adequacy_probe_records.json").write_text(
        json.dumps(records, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    logger.info("Probe report: %s", json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_probe()
