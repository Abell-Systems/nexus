#!/usr/bin/env python3
"""Canonical dataset identity & temporal audit (PR #43).

Read-only audit over the sealed pilot inputs. Verifies that the evaluation
dataset, its manifest, its checksum sidecar, the frozen M1 embedding artifact,
and the snapshots baseline all point at the same corpus — and scans every
annotated demand-patent pair against the strict prior-art rule
(t_pub < t_demand, empirical-study-protocol §5.3).

Stdlib only (no repository imports): the audit must run even where backend
dependencies are unavailable, and must never import the code it audits.

Temporal rule for invalid pairs (explicit, traceable, non-destructive):
- Sealed data is NEVER modified or silently pruned by this script.
- Pairs with t_pub >= t_demand are reported as TEMPORAL_VIOLATION with both
  dates, the annotated grade, and the affected ids.
- At evaluation time the matching engine already treats such pairs as
  ineligible (overall 0.0, INELIGIBLE_TEMPORAL); pool-construction exclusion
  for Phase 2 belongs to a later PR, not to this audit.
- On the current sealed data no pair shares t_pub == t_demand, so the strict
  protocol rule (t_pub < t_demand) and the lenient reading (t_pub <= t_demand)
  agree exactly; the strict rule is applied as the canonical one.

Exit code is always 0: this script reports truth, it does not gate. The
machine-readable verdict field (PASS/FAIL) is what a future CI gate — enabled
only after the documented violations are remediated in a new dataset version —
will enforce. Re-running with the same inputs yields byte-identical output
except for the generated_at field; canonical_fingerprint covers everything
else and is the reproducibility assertion.
"""

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DATASET_PATH = REPO_ROOT / "data" / "evaluation" / "dataset_pilot_benchmark.json"
CHECKSUM_PATH = REPO_ROOT / "data" / "evaluation" / "dataset_pilot_benchmark.sha256"
MANIFEST_PATH = REPO_ROOT / "data" / "evaluation" / "dataset_pilot_benchmark.manifest.json"
EMBEDDINGS_PATH = REPO_ROOT / "data" / "evaluation" / "embeddings_pilot_benchmark.json"
RAW_PATH = REPO_ROOT / "data" / "raw" / "oepm_open_data_es.json"
SNAPSHOT_JSONL_PATH = REPO_ROOT / "data" / "snapshots" / "patents_es_corpus.jsonl"
SNAPSHOT_MANIFEST_PATH = REPO_ROOT / "data" / "snapshots" / "patents_es_manifest.json"

EXPECTED_EMBEDDING_DIMENSION = 768


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _check(name: str, ok: bool, detail: str, checks: list, failures: list) -> None:
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    if not ok:
        failures.append(name)


def audit() -> dict:
    checks: list = []
    failures: list = []

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    embeddings = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))
    snapshot_manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))

    # 1. Dataset byte identity: file SHA vs sidecar vs manifest.
    file_sha = _sha256_file(DATASET_PATH)
    sidecar = CHECKSUM_PATH.read_text(encoding="utf-8").strip().split()
    _check(
        "dataset_sha_sidecar",
        len(sidecar) == 2 and sidecar[0] == file_sha and sidecar[1] == DATASET_PATH.name,
        f"file={file_sha[:12]}... sidecar={sidecar}",
        checks, failures,
    )
    _check(
        "dataset_sha_manifest",
        manifest.get("content_sha256") == file_sha,
        f"manifest={str(manifest.get('content_sha256'))[:12]}... file={file_sha[:12]}...",
        checks, failures,
    )

    # 2. Counts: manifest vs actual content.
    demands = dataset.get("demands", [])
    patents = dataset.get("patents", [])
    annotations = dataset.get("annotations", [])
    _check(
        "manifest_counts",
        manifest.get("demand_count") == len(demands)
        and manifest.get("patent_count") == len(patents)
        and manifest.get("annotation_count") == len(annotations),
        f"manifest=({manifest.get('demand_count')},{manifest.get('patent_count')},"
        f"{manifest.get('annotation_count')}) actual=({len(demands)},{len(patents)},{len(annotations)})",
        checks, failures,
    )

    # 3. No duplicate ids.
    demand_ids = [d["demand_id"] for d in demands]
    patent_ids = [p["publication_id"] for p in patents]
    _check("no_duplicate_demand_ids", len(set(demand_ids)) == len(demand_ids),
           f"{len(demand_ids)} demands", checks, failures)
    _check("no_duplicate_patent_ids", len(set(patent_ids)) == len(patent_ids),
           f"{len(patents)} patents", checks, failures)

    # 4. Annotations reference known demands and patents only.
    dangling = [
        (a.get("demand_id"), a.get("publication_id"))
        for a in annotations
        if a.get("demand_id") not in set(demand_ids)
        or a.get("publication_id") not in set(patent_ids)
    ]
    _check("annotations_reference_known_ids", not dangling, f"dangling={dangling}", checks, failures)

    # 5. Embedding artifact binds to this exact dataset.
    emb_payload = {k: v for k, v in embeddings.items() if k != "artifact_sha256"}
    emb_canonical = json.dumps(emb_payload, sort_keys=True, indent=2).encode("utf-8")
    _check(
        "embeddings_artifact_sha",
        hashlib.sha256(emb_canonical).hexdigest() == embeddings.get("artifact_sha256"),
        f"declared={str(embeddings.get('artifact_sha256'))[:12]}...",
        checks, failures,
    )
    _check(
        "embeddings_dataset_sha",
        embeddings.get("dataset_sha256") == file_sha,
        f"artifact_ds={str(embeddings.get('dataset_sha256'))[:12]}... dataset={file_sha[:12]}...",
        checks, failures,
    )
    _check(
        "embeddings_demand_ids",
        set(embeddings.get("demand_embeddings", {})) == set(demand_ids),
        f"artifact={sorted(embeddings.get('demand_embeddings', {}))}",
        checks, failures,
    )
    _check(
        "embeddings_patent_ids",
        set(embeddings.get("patent_embeddings", {})) == set(patent_ids),
        f"artifact={len(embeddings.get('patent_embeddings', {}))} dataset={len(patent_ids)}",
        checks, failures,
    )
    dims_ok = all(
        len(v) == EXPECTED_EMBEDDING_DIMENSION
        for v in list(embeddings.get("demand_embeddings", {}).values())
        + list(embeddings.get("patent_embeddings", {}).values())
    )
    _check("embeddings_dimension", dims_ok and embeddings.get("embedding_dimension") == EXPECTED_EMBEDDING_DIMENSION,
           f"expected_dim={EXPECTED_EMBEDDING_DIMENSION}", checks, failures)

    # 6. Snapshots baseline relationship (proof-of-method corpus, not the sealed set).
    raw_sha = _sha256_file(RAW_PATH)
    _check(
        "snapshots_raw_sha",
        snapshot_manifest.get("raw_source_sha256") == raw_sha,
        f"manifest={str(snapshot_manifest.get('raw_source_sha256'))[:12]}... file={raw_sha[:12]}...",
        checks, failures,
    )
    snapshot_ids = set()
    snapshot_count = 0
    with SNAPSHOT_JSONL_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                snapshot_count += 1
                snapshot_ids.add(json.loads(line).get("publication_number"))
    _check(
        "snapshots_count",
        snapshot_manifest.get("total_records") == snapshot_count,
        f"manifest={snapshot_manifest.get('total_records')} jsonl={snapshot_count}",
        checks, failures,
    )
    extra_ids = sorted(snapshot_ids - set(patent_ids))
    missing_ids = sorted(set(patent_ids) - snapshot_ids)
    _check(
        "evaluation_subset_of_snapshots",
        not missing_ids,
        f"snapshot_only={extra_ids} evaluation_only={missing_ids}",
        checks, failures,
    )

    # 7. Temporal scan over every annotated pair (strict rule: t_pub < t_demand).
    demand_dates = {d["demand_id"]: d["posted_date"] for d in demands}
    patent_dates = {p["publication_id"]: p["publication_date"] for p in patents}
    violations = []
    for a in annotations:
        t_pub = patent_dates[a["publication_id"]]
        t_dem = demand_dates[a["demand_id"]]
        if t_pub >= t_dem:
            violations.append(
                {
                    "demand_id": a["demand_id"],
                    "publication_id": a["publication_id"],
                    "grade": a["grade"],
                    "publication_date": t_pub,
                    "demand_posted_date": t_dem,
                    "status": "TEMPORAL_VIOLATION",
                }
            )
    violations.sort(key=lambda v: (v["demand_id"], v["publication_id"]))
    _check(
        "temporal_eligibility",
        not violations,
        f"{len(violations)} of {len(annotations)} annotated pairs violate t_pub < t_demand",
        checks, failures,
    )

    verdict = "PASS" if not failures else "FAIL"
    report = {
        "audit_id": "nexus-dataset-identity-temporal-audit-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_id": dataset.get("dataset_id"),
        "dataset_sha256": file_sha,
        "counts": {
            "demands": len(demands),
            "patents": len(patents),
            "annotations": len(annotations),
        },
        "demand_ids": sorted(demand_ids),
        "embedding_artifact_id": embeddings.get("artifact_id"),
        "embedding_artifact_sha256": embeddings.get("artifact_sha256"),
        "snapshots_total_records": snapshot_count,
        "snapshots_only_ids": extra_ids,
        "temporal_rule": "t_pub < t_demand (strict; equivalent to <= on current data: no equal-date pairs)",
        "temporal_violations": violations,
        "temporal_violation_count": len(violations),
        "checks": checks,
        "failed_checks": failures,
        "verdict": verdict,
    }
    canonical = {k: v for k, v in report.items() if k != "generated_at"}
    report["canonical_fingerprint"] = hashlib.sha256(
        json.dumps(canonical, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=None, help="Optional path for the JSON audit report.")
    args = parser.parse_args()

    for path in (DATASET_PATH, CHECKSUM_PATH, MANIFEST_PATH, EMBEDDINGS_PATH,
                 RAW_PATH, SNAPSHOT_JSONL_PATH, SNAPSHOT_MANIFEST_PATH):
        if not path.exists():
            print(f"Audit input missing: {path}", file=sys.stderr)
            return 2

    report = audit()
    print(f"Dataset: {report['dataset_id']} (SHA {report['dataset_sha256'][:12]}...)")
    print(f"Counts: {report['counts']}")
    print(f"Temporal violations: {report['temporal_violation_count']}")
    for v in report["temporal_violations"]:
        print(f"  TEMPORAL_VIOLATION demand={v['demand_id']} patent={v['publication_id']} "
              f"grade={v['grade']} t_pub={v['publication_date']} t_demand={v['demand_posted_date']}")
    for c in report["checks"]:
        print(f"  [{c['status']}] {c['check']}: {c['detail']}")
    print(f"Verdict: {report['verdict']}")
    print(f"Canonical fingerprint: {report['canonical_fingerprint']}")

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Audit report written to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
