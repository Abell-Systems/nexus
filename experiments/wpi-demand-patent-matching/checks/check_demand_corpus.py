#!/usr/bin/env python3
"""Manifest-conformance check for the WPI Phase 2 demand corpus (N=39).

Verifies the frozen dataset_phase2_demand_corpus_n39.json artifact against its
own recorded manifest and sha256 sidecar, and against the generic
DemandCorpus/DemandCorpusItem domain contract (domain.models.evaluation).
Expected counts (total, per-provenance breakdown) are read from the manifest,
never hardcoded here -- this validates one scientific artifact's evidence,
not a Nexus domain invariant.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from domain.models.demand import SpanishOriginLevel  # noqa: E402
from domain.models.evaluation import DemandCorpus  # noqa: E402

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    dataset_path = DATA_DIR / "dataset_phase2_demand_corpus_n39.json"
    checksum_path = DATA_DIR / "dataset_phase2_demand_corpus_n39.sha256"
    manifest = _load("dataset_phase2_demand_corpus_n39.manifest.json")

    file_bytes = dataset_path.read_bytes()
    computed = hashlib.sha256(file_bytes).hexdigest()
    sidecar_line = checksum_path.read_text(encoding="utf-8").strip()
    declared_sha, declared_name = sidecar_line.split(maxsplit=1)
    assert declared_sha == computed, "Frozen dataset bytes do not match the committed .sha256 sidecar"
    assert declared_name == dataset_path.name

    corpus = DemandCorpus.model_validate_json(file_bytes)

    assert manifest["dataset_id"] == corpus.dataset_id
    assert manifest["demand_count"] == len(corpus.demands)
    assert manifest["patent_count"] == 0
    assert manifest["content_sha256"] == computed

    for demand in corpus.demands:
        assert demand.spanish_origin_level in (
            SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
            SpanishOriginLevel.LEVEL_2_ORGANIZATION_METADATA,
            SpanishOriginLevel.LEVEL_3_REGISTRY_CROSS_CHECK,
        )
        word_count = len(demand.description.split())
        assert word_count >= 25, (
            f"{demand.demand_id} has {word_count} words, below the protocol's 25-word "
            "minimum -- this demand should not be in the frozen corpus"
        )

    prefix_counts = manifest["demand_id_prefix_counts"]
    for prefix, expected_count in prefix_counts.items():
        actual = [d for d in corpus.demands if d.demand_id.startswith(prefix)]
        assert len(actual) == expected_count, (prefix, len(actual), expected_count)

    lombardia = [d for d in corpus.demands if d.demand_id.startswith("LOMBARDIA-")]
    for demand in lombardia:
        assert demand.external_reference is not None
        assert demand.external_reference.startswith("TRES")
        assert demand.origin_country == "ES"

    print(f"OK: {len(corpus.demands)} demands, prefix counts={prefix_counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
