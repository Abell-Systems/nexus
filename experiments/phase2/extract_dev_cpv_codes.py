"""CPV extraction for the 30 frozen Dev demands, step 1 of
docs/phase2-cpv-cpc-concordance-feasibility-contract.md -- extraction and
audit ONLY, no concordance mapping performed here.

Reuses the exact regex already exercised by
experiments/phase2/generate_ted_annotation_dry_run.py's
extract_cpv_code(), re-verified here directly against the raw HTML
markup (code|name|cpv.NNNNNNNN) before trusting it at the full 30-demand
scale. Could not recover a main-vs-additional CPV distinction from this
markup pattern -- every demand's CPV codes are extracted as one
undifferentiated set, disclosed as a limitation, not silently resolved.
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

_CPV_RE = re.compile(r"code\|name\|cpv\.(\d{8})")


def extract_cpv_codes(raw_html: str) -> list[str]:
    """Returns all distinct 8-digit CPV codes found, in first-seen order."""
    seen: list[str] = []
    for m in _CPV_RE.finditer(raw_html):
        code = m.group(1)
        if code not in seen:
            seen.append(code)
    return seen


def _granularity_level(code: str) -> str:
    """CPV codes are hierarchical by trailing-zero count: XX000000=division,
    XXX00000=group, XXXX0000=class, XXXXX000=category, finer below that."""
    trailing_zeros = len(code) - len(code.rstrip("0"))
    if trailing_zeros >= 6:
        return "division"
    if trailing_zeros == 5:
        return "group"
    if trailing_zeros == 4:
        return "class"
    if trailing_zeros == 3:
        return "category"
    return "subcategory_or_finer"


def extract_and_audit(
    devtest_split_path: Path,
    raw_ted_dir: Path,
    out_path: Path,
) -> dict[str, Any]:
    split = json.loads(devtest_split_path.read_text(encoding="utf-8"))
    dev_ids: list[str] = split["dev"]

    by_demand: dict[str, list[str]] = {}
    missing_html: list[str] = []
    zero_cpv: list[str] = []

    for demand_id in dev_ids:
        html_path = raw_ted_dir / f"{demand_id}.html"
        if not html_path.is_file():
            missing_html.append(demand_id)
            by_demand[demand_id] = []
            continue
        codes = extract_cpv_codes(html_path.read_text(encoding="utf-8", errors="replace"))
        by_demand[demand_id] = codes
        if not codes:
            zero_cpv.append(demand_id)

    n_with_cpv = sum(1 for c in by_demand.values() if c)
    counts_per_demand = {d: len(c) for d, c in by_demand.items()}

    all_codes: list[str] = [c for codes in by_demand.values() for c in codes]
    from collections import Counter
    code_frequency = Counter(all_codes)

    granularity_counts = Counter(_granularity_level(c) for c in set(all_codes))

    result = {
        "purpose": "CPV extraction + audit for the 30 frozen Dev demands -- STEP 1 ONLY, no CPV->NACE/IPC/CPC mapping performed.",
        "source": "data/raw/phase2_candidates_ted/ted/<demand_id>.html (raw TED postings, already harvested)",
        "extraction_method": "regex code\\|name\\|cpv\\.(\\d{8}), first-seen order, deduplicated per demand",
        "limitation_disclosed": "Could not recover a main-vs-additional CPV field distinction from this markup; all codes per demand are reported as one undifferentiated set.",
        "n_dev_demands": len(dev_ids),
        "n_demands_with_missing_html": len(missing_html),
        "missing_html_demand_ids": missing_html,
        "n_demands_with_zero_cpv": len(zero_cpv),
        "zero_cpv_demand_ids": zero_cpv,
        "coverage_rate": round(n_with_cpv / len(dev_ids), 4),
        "cpv_count_per_demand": counts_per_demand,
        "cpv_count_distribution": dict(Counter(counts_per_demand.values())),
        "n_distinct_cpv_codes_total": len(set(all_codes)),
        "cpv_code_frequency": dict(code_frequency.most_common()),
        "granularity_distribution": dict(granularity_counts),
        "cpv_codes_by_demand": by_demand,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    out_path.write_bytes(json_bytes)
    sha256_hex = hashlib.sha256(json_bytes).hexdigest()
    out_path.with_suffix(".sha256").write_text(f"{sha256_hex}  {out_path.name}\n", encoding="utf-8")

    return result


def main(argv: list[str] | None = None) -> int:
    result = extract_and_audit(
        devtest_split_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_devtest_split_v1.json",
        raw_ted_dir=REPO_ROOT / "data" / "raw" / "phase2_candidates_ted" / "ted",
        out_path=REPO_ROOT / "data" / "experiments" / "phase2_v4" / "ted_dev_cpv_codes_v1.json",
    )
    print(json.dumps({k: v for k, v in result.items() if k != "cpv_codes_by_demand"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
