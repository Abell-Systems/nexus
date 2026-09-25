"""ADR 0035: INVENES coverage/scalability characterization -- NOT a corpus
build, NOT #104 input. Answers one question before any further scale-up:

    Can INVENES alone provide a large enough, complete enough corpus for the
    study, or does it have a practical ceiling?

Uses a DIFFERENT, deliberately generic query set (materials/chemistry/
mechanical/textile/food/optics/energy -- domain-diverse, not chosen for TED
topical overlap) than build_oepm_corpus.py's smoke-test batch, to avoid
smuggling a scientific-sample selection under a characterization label.
Measures: temporal distribution, abstract-presence rate (overall and by
publication-era), kind-code distribution, exact duplicates, IPC/CPC
distribution, applicant distribution, INCLUDED/EXCLUDED/QUARANTINED rates,
per-query yield, and reports each query's own total-results count (INVENES's
"Number of results") as the accessible-population signal.
"""

import json
import logging
import re
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

logger = logging.getLogger("experiments.oepm.coverage_characterization")

# Deliberately domain-diverse (not TED-topic-aligned) and NOT the smoke-test
# query set (experiments/oepm/build_oepm_corpus.py's REFERENCIAS) -- real
# "Number of results" counts captured from a live INVENES search on 2026-09-14.
# One query ("envase alimentario") used INVENES's "see first latest
# publications" toggle to counteract the other queries' default
# oldest-first-ish ranking and get temporal spread.
QUERY_TOTAL_RESULTS: dict[str, int] = {
    "aleacion metalica": 21119,
    "composicion farmaceutica": 70791,
    "maquina agricola": 4883,
    "tejido textil": 18870,
    "motor combustion": 33289,
    "envase alimentario (latest first)": 2118,
    "sensor optico": 23374,
    "bateria recargable": 7801,
}

# Referencias from page 1 of each query above, PCT (not-yet-nationalized)
# excluded, and deduplicated against build_oepm_corpus.py's own smoke-test
# batch so this characterization sample is fully disjoint from it.
REFERENCIA_BY_QUERY: dict[str, list[str]] = {
    "aleacion metalica": [
        "P0360287", "P0535348", "P0359291", "P0398884", "P0174790", "P0178738",
        "P0269237", "P0521039", "P0552833", "P0304204", "P0255316", "U200401863",
        "P0264723", "P0264015", "P0220334", "U200800251", "P0478003", "P0479819",
        "U0197398", "P0097035",
    ],
    "composicion farmaceutica": [
        "P0360470", "P0496711", "P0520364", "P0544172", "P200600571", "P8801445",
        "P0444194", "P0335022", "P0551844", "P0247237", "P0514308", "P0520177",
        "P202030879", "E17202117",
    ],
    "maquina agricola": [
        "U8800282", "P0401521", "P0375433", "U9400888", "P0275048", "P0449935",
        "P0436475", "P0430624", "P0287275", "P0431743", "P0253966", "U200400256",
        "P0249335", "P0475667", "P0482526", "U0117985", "P0537660", "P0541497",
        "P200601852",
    ],
    "tejido textil": [
        "P0360276", "P0360644", "U8901266", "P0360987", "U8702604", "P0402011",
        "U0221950", "P0396118", "P0179079", "P0335406", "U9402802", "P0337786",
        "P0381890", "P0280564", "U200500100", "U0010053", "U200401738", "U0259992",
        "P0098394", "P0099685",
    ],
    "motor combustion": [
        "P0420857", "P0416574", "P0533078", "P0402846", "P0538344", "P200501644",
        "P0526980", "P0398890", "P0396813", "P0545909", "P0279544", "U0229837",
        "P0281540", "P0376614", "P0380926", "U200500766", "P0547524", "P0261861",
        "P0554678", "U0022149",
    ],
    "envase alimentario (latest first)": [
        "U202530004", "E24220875", "U202532498", "U202630034", "U202531791",
        "U202531853", "E23162548", "P202530058", "E24175348", "E16166075",
        "P202630302", "E17166814",
    ],
    "sensor optico": [
        "P0525275", "P0525168", "P8903955", "P0520099", "P9002761", "U0295271",
        "P9702227", "P201531938", "P201730488", "U201800317", "E12000170",
        "E15195550", "E17203897", "U202032658", "E19167805",
    ],
    "bateria recargable": [
        "P0359270", "P0425515", "P0450284", "P0447684", "P0553289", "P0382389",
        "U0265344", "U200900105", "U200602003", "P200301173", "P200703195",
        "P201430191", "P201630778", "U201730750", "U202132125",
    ],
}

ALLOWED_KIND_CODES = frozenset({"A1", "A2", "B1", "B2", "U"})
_OLD_APP_NUMBER_RE = re.compile(r"^[A-Z](\d{7,8})$")  # pre-2000-style: e.g. P0360287
_NEW_APP_NUMBER_RE = re.compile(r"^[A-Z](\d{6})(\d{5})$")  # post-2000-style: e.g. P201430830


def _era_from_referencia(referencia: str) -> str:
    """Coarse era bucket from the referencia's own numbering convention (not
    from publication_date, which is often absent for excluded records --
    this lets excluded records still contribute to the temporal picture)."""
    if referencia.startswith(("P19", "P20", "U19", "U20")) and len(referencia) >= 6 and referencia[1:5].isdigit():
        year = int(referencia[1:5])
        if 1900 <= year <= 2100:
            return f"{(year // 5) * 5}s"
    return "pre-2000 (legacy numbering)"


def characterize(
    referencia_by_query: dict[str, list[str]] = REFERENCIA_BY_QUERY,
    query_total_results: dict[str, int] = QUERY_TOTAL_RESULTS,
    out_path: Path = REPO_ROOT / "data" / "experiments" / "oepm_v1" / "invenes_coverage_characterization.json",
    skip_harvest: bool = False,
    harvest_timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    raw_dir = REPO_ROOT / "data" / "raw" / "oepm_invenes_coverage_sample"
    all_referencias = [r for refs in referencia_by_query.values() for r in refs]

    if not skip_harvest:
        harvester = InvenesHarvester(delay_seconds=1.0, timeout_seconds=harvest_timeout_seconds)
        harvester.harvest(all_referencias, out_dir=raw_dir)
        if harvester.acquisition_errors:
            (raw_dir.parent / "coverage_harvest_errors.json").write_text(
                json.dumps(harvester.acquisition_errors, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

    referencia_query: dict[str, str] = {}
    for query, refs in referencia_by_query.items():
        for r in refs:
            referencia_query[r] = query

    records: list[dict[str, Any]] = []
    dispositions = Counter()
    per_query_included = Counter()
    per_query_attempted = Counter()

    for referencia in all_referencias:
        per_query_attempted[referencia_query[referencia]] += 1
        # save_raw_payload nests under out_dir/source_id unless out_dir's own
        # name already equals source_id (not the case here, unlike
        # build_oepm_corpus.py's raw_harvest_dir).
        html_path = raw_dir / SOURCE_ID / f"{referencia}.html"
        if not html_path.exists():
            dispositions["not_harvested"] += 1
            continue

        parsed = parse_invenes_detail(html_path.read_bytes(), referencia=referencia)
        if parsed is None:
            dispositions["quarantined_unparseable"] += 1
            continue

        item = parsed.item
        has_abstract = bool(item["abstract"].strip())
        has_title = bool(item["title"].strip())
        disposition = "included"
        if parsed.kind_code not in ALLOWED_KIND_CODES:
            disposition = "excluded_kind_code"
        elif not has_title or not has_abstract:
            disposition = "excluded_missing_text"

        dispositions[disposition] += 1
        if disposition == "included":
            per_query_included[referencia_query[referencia]] += 1

        records.append({
            "referencia": referencia,
            "query": referencia_query[referencia],
            "publication_id": item["publication_id"],
            "kind_code": parsed.kind_code,
            "publication_date": item["publication_date"],
            "era": _era_from_referencia(referencia),
            "has_abstract": has_abstract,
            "assignees": item["assignees"],
            "classifications_ipc": item["classifications_ipc"],
            "classifications_cpc": item["classifications_cpc"],
            "disposition": disposition,
        })

    total_attempted = len(all_referencias)
    total_harvested = sum(1 for r in records) + dispositions["quarantined_unparseable"]
    pub_id_counts = Counter(r["publication_id"] for r in records)
    duplicates = {pid: n for pid, n in pub_id_counts.items() if n > 1}

    abstract_by_era: dict[str, dict[str, int]] = {}
    for r in records:
        era = r["era"]
        bucket = abstract_by_era.setdefault(era, {"with_abstract": 0, "without_abstract": 0})
        bucket["with_abstract" if r["has_abstract"] else "without_abstract"] += 1

    kind_code_dist = Counter(r["kind_code"] for r in records)
    assignee_dist = Counter(a for r in records for a in r["assignees"])
    ipc_class_dist = Counter(c[:4] for r in records for c in r["classifications_ipc"])  # IPC subclass, e.g. "G01N"

    report = {
        "purpose": "Coverage/scalability characterization of INVENES as a corpus source -- "
                   "NOT a corpus build, NOT input to #104. Disjoint from build_oepm_corpus.py's "
                   "smoke-test referencias by construction.",
        "queries": {
            q: {
                "invenes_reported_total_results": query_total_results[q],
                "page1_referencias_attempted": per_query_attempted[q],
                "included_from_page1": per_query_included[q],
                "page1_inclusion_rate": round(per_query_included[q] / per_query_attempted[q], 3) if per_query_attempted[q] else None,
            }
            for q in referencia_by_query
        },
        "totals": {
            "referencias_attempted": total_attempted,
            "referencias_harvested": total_harvested,
            "dispositions": dict(dispositions),
            "included_rate": round(dispositions["included"] / total_attempted, 3) if total_attempted else None,
        },
        "exact_duplicate_publication_ids": duplicates,
        "kind_code_distribution": dict(kind_code_dist),
        "abstract_presence_by_era": abstract_by_era,
        "top_assignees": assignee_dist.most_common(15),
        "top_ipc_subclasses": ipc_class_dist.most_common(15),
        "invenes_reported_total_results_sum": sum(query_total_results.values()),
        "rate_limit_disclosure": (
            f"{dispositions['not_harvested']}/{total_attempted} referencias were never harvested: "
            "a real, reproducible rate limit/block from OEPM's infrastructure (confirmed in isolation "
            "outside this script -- a previously-successful URL started timing out after ~40-45 "
            "requests within a short window, on both this run and the earlier build_oepm_corpus.py "
            "run). This is itself a characterization finding, not a code defect: INVENES's practical "
            "per-session throughput ceiling appears to be roughly 40-45 detail-page requests before a "
            "cooldown is required. Scaling acquisition to N>=60 net-included records will need either "
            "much slower pacing across a longer wall-clock window, or a different acquisition strategy "
            "(e.g. spread across days), not just more queries."
        ),
        "note_on_population_estimate": (
            "Sum of INVENES 'Number of results' across the 8 queries is "
            f"{sum(query_total_results.values())}, but queries overlap heavily (broad terms) and "
            "include non-domestic/non-eligible records (PCT, EP-ES/T3, foreign Latipat) -- this is "
            "NOT a usable estimate of the eligible accessible population without further "
            "deduplication and eligibility filtering at scale. Reported for context only."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    records_path = out_path.with_name("invenes_coverage_characterization_records.json")
    records_path.write_text(json.dumps(records, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    logger.info("Coverage characterization report: %s", json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    characterize()
