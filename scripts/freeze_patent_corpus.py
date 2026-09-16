#!/usr/bin/env python3
# scripts/freeze_patent_corpus.py
"""Freezes PatentCorpus (`P`), ADR 0020's demand-blind, jurisdiction/grant/window-
determined patent artifact, into a hashed, reproducible dataset artifact.

Mirrors scripts/freeze_phase2_demand_corpus.py's freezing discipline: reproducible
acquisition -> committed dataset file -> manifest JSON -> sha256 sidecar. Unlike that
script, this one is fixture-testable end-to-end without live credentials (ADR 0020 §6);
`main()` requires EPO_OPS_KEY/EPO_OPS_SECRET for the real ~50,000-record run.

Outputs (experiments/wpi-demand-patent-matching/data/):
- dataset_patent_corpus_p.json            canonical patent corpus (PatentCorpus)
- dataset_patent_corpus_p.manifest.json   identity/hash manifest
- dataset_patent_corpus_p.sha256          sha256sum-compatible sidecar
"""

import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.evaluation.patent_corpus_builder import select_frozen_patents  # noqa: E402
from application.ingestion.normalizers.oepm_xml_normalizer import OepmXmlNormalizer  # noqa: E402
from application.ingestion.validator import PatentValidator  # noqa: E402
from domain.models.evaluation import DataModality, EvaluationProvenance, PatentCorpus, PatentCorpusItem  # noqa: E402
from domain.models.ingestion import RecordDisposition  # noqa: E402
from domain.models.patent import PatentDocument  # noqa: E402
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient  # noqa: E402
from infrastructure.sources.patent.ops_partitioning import (  # noqa: E402
    OPS_RETRIEVAL_CEILING,
    enumerate_partition_tree,
)

OUT_DIR = REPO_ROOT / "experiments" / "wpi-demand-patent-matching" / "data"
OUT_BASENAME = "dataset_patent_corpus_p"

JURISDICTIONS = ["EP", "US", "JP", "CN", "KR", "WO"]
GRANT_KIND_CODES = frozenset({"B1", "B2"})
TARGET_N = 50000
MINIMUM_ACCEPTABLE_N = 5000
DATASET_ID = "nexus-patent-corpus-p-v1"
SCHEMA_VERSION = "1.0.0"
DATASET_VERSION = "1.0.0"

# ponytail: OepmXmlNormalizer's own min/max_publication_year defaults (2016-2024) are
# tuned for the OEPM Spain pipeline it was built for, not this multi-jurisdiction EPO
# OPS pipeline. The window here is ALREADY enforced by ops_partitioning.build_partition_cql
# (pd within ...) -- passing the normalizer's defaults through unchanged would silently
# re-apply a second, stale window and drop valid documents once run past 2024. Widen the
# normalizer's own window check to a no-op so window enforcement has exactly one source
# of truth: the CQL query.
NORMALIZER_MIN_YEAR = 1
NORMALIZER_MAX_YEAR = 9999


@dataclass
class PatentCorpusBuildResult:
    """Return value of build_patent_corpus: the frozen corpus plus the attrition
    counts needed for observability (Fix B) and manifest completeness (Fix C)."""

    corpus: PatentCorpus
    disposition_counts: dict[str, int]
    eligible_available_records: int
    leaf_count: int


def build_patent_corpus(
    client: EpoOpsClient,
    jurisdictions: list[str],
    window_start: date,
    window_end: date,
    ceiling: int,
    target_n: int,
    minimum_acceptable_n: int,
    dataset_id: str,
    dataset_version: str,
    description: str,
) -> PatentCorpusBuildResult:
    """Fetch (enumerability-verified), normalize (grants-only, multi-jurisdiction),
    dedupe, select (sha256-order, ADR 0020 §3), and assemble a PatentCorpus. Raises
    PatentCorpusConstructionError if the eligible universe is below the floor.

    `jurisdictions` is the ADR 0020 §2 whitelist: a document surviving the normalizer
    and validator is only kept if its country_code is in this list and it carries a
    parseable publication_date. target_country="" on the normalizer means a document
    with no resolvable jurisdiction normalizes to country_code="" -- which is never in
    `jurisdictions` -- rather than silently falling back to a valid-looking code.
    """
    normalizer = OepmXmlNormalizer(
        allowed_kind_codes=GRANT_KIND_CODES,
        target_country="",
        min_publication_year=NORMALIZER_MIN_YEAR,
        max_publication_year=NORMALIZER_MAX_YEAR,
    )
    validator = PatentValidator()

    documents: list[PatentDocument] = []
    provenance_by_pub_id: dict[str, EvaluationProvenance] = {}
    disposition_counts: Counter[str] = Counter()
    excluded_jurisdiction_or_window = 0

    partition_result = enumerate_partition_tree(client, jurisdictions, window_start, window_end, ceiling)
    for raw_payload in partition_result.batches:
        for result in normalizer.normalize_results(raw_payload):
            validated = validator.validate_normalization_result(result)
            disposition_counts[validated.disposition.value] += 1
            if validated.disposition != RecordDisposition.INCLUDED or validated.document is None:
                continue

            doc = validated.document
            if doc.country_code not in jurisdictions or not _has_parseable_publication_date(doc):
                excluded_jurisdiction_or_window += 1
                continue

            documents.append(doc)
            provenance_by_pub_id[doc.publication_id] = EvaluationProvenance(
                source_authority="European Patent Office (EPO OPS 3.2)",
                source_uri="https://ops.epo.org",
                extraction_timestamp=raw_payload.retrieval_timestamp,
                raw_payload_sha256=raw_payload.payload_sha256,
                modality=DataModality.OBSERVED,
            )

    eligible_available_records = len(documents)
    selected = select_frozen_patents(documents, target_n=target_n, minimum_acceptable_n=minimum_acceptable_n)

    items = [
        PatentCorpusItem(
            publication_id=doc.publication_id,
            country_code=doc.country_code,
            kind_code=doc.kind_code,
            title=doc.title,
            abstract=doc.abstract,
            publication_date=doc.publication_date,
            classifications_cpc=doc.classifications_cpc,
            provenance=provenance_by_pub_id[doc.publication_id],
        )
        for doc in selected
    ]

    corpus = PatentCorpus(
        dataset_id=dataset_id,
        schema_version=SCHEMA_VERSION,
        dataset_version=dataset_version,
        description=description,
        patents=items,
    )

    counts = {
        "included": disposition_counts.get(RecordDisposition.INCLUDED.value, 0),
        "excluded": disposition_counts.get(RecordDisposition.EXCLUDED.value, 0),
        "quarantined": disposition_counts.get(RecordDisposition.QUARANTINED.value, 0),
        "duplicate": disposition_counts.get(RecordDisposition.DUPLICATE.value, 0),
        "excluded_jurisdiction_or_window": excluded_jurisdiction_or_window,
    }
    return PatentCorpusBuildResult(
        corpus=corpus,
        disposition_counts=counts,
        eligible_available_records=eligible_available_records,
        leaf_count=partition_result.leaf_count,
    )


def _has_parseable_publication_date(doc: PatentDocument) -> bool:
    """publication_date is already ISO YYYY-MM-DD by the time it reaches here
    (OepmXmlNormalizer._normalize_date), so this is a cheap presence + format guard,
    not a second date-parsing implementation."""
    if not doc.publication_date:
        return False
    try:
        datetime.fromisoformat(doc.publication_date)
    except ValueError:
        return False
    return True


def main() -> None:
    """Run the real EPO OPS ingestion. Requires EPO_OPS_KEY/EPO_OPS_SECRET.

    Decomposes ADR 0020 §2's universe down to month granularity via jurisdiction/date
    partitioning (PR-E0.1, docs/superpowers/specs/
    2026-09-08-ops-enumeration-partitioning-contract.md) -- see enumerate_partition_tree.
    This does NOT guarantee a real run against the full 6-jurisdiction/10-year scope
    completes: a real run is EXPECTED to raise NonEnumerablePartitionError for
    high-volume jurisdictions (US/CN/JP are likely candidates, since their monthly
    grant+application volume plausibly exceeds the ~2000-record OPS retrieval ceiling
    even at month level). That is correct fail-closed behavior, not a bug -- resolving
    it requires an explicit human decision per contract §4 (narrowing the inclusion
    contract, or a new partitioning approach agreed with the ADR owner), not a code fix.
    On any NonEnumerablePartitionError this produces no output files.

    OPERATIONAL DEBT before attempting a real run (neither is a correctness bug --
    both are recorded here so PR-E0.2 doesn't discover them live):
    - EpoOpsClient (infrastructure/sources/patent/epo_ops_client.py, unmodified by
      PR-E0/PR-E0.1) never refreshes its OAuth token or retries on 401. A real run
      issues far more requests than the single-query design this client was written
      for (see the next point), and OPS access tokens expire in roughly 20 minutes --
      a long run can plausibly outlive its own token and abort mid-flight.
    - enumerate_partition_tree issues one peek_total_result_count request per
      candidate partition PLUS a full fetch_all_ops_batches run per eligible leaf --
      roughly double the request count a single combined fetch+count call would need.
      Contract §5.3 deliberately keeps eligibility and completeness as separate
      concerns, so this is not something to silently optimize away here, but it
      compounds the token-lifetime risk above and should factor into PR-E0.2's
      request-budget planning.
    """
    window_end = datetime.now(UTC).date()
    try:
        window_start = window_end.replace(year=window_end.year - 10)
    except ValueError:
        # window_end is Feb 29 with no Feb 29 ten years prior
        window_start = window_end.replace(year=window_end.year - 10, day=28)
    client = EpoOpsClient()  # reads EPO_OPS_KEY/EPO_OPS_SECRET from env

    print(f"Fetching PatentCorpus universe: {JURISDICTIONS} x [{window_start}, {window_end}]")
    result = build_patent_corpus(
        client=client,
        jurisdictions=JURISDICTIONS,
        window_start=window_start,
        window_end=window_end,
        ceiling=OPS_RETRIEVAL_CEILING,
        target_n=TARGET_N,
        minimum_acceptable_n=MINIMUM_ACCEPTABLE_N,
        dataset_id=DATASET_ID,
        dataset_version=DATASET_VERSION,
        description=(
            f"Nexus PatentCorpus (P): {', '.join(JURISDICTIONS)} grants, "
            f"{window_start} to {window_end}. See docs/adr/"
            "0020-experimental-corpus-architecture-demand-times-patent.md."
        ),
    )
    corpus = result.corpus
    frozen_at = datetime.now(UTC).isoformat()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = OUT_DIR / f"{OUT_BASENAME}.json"
    dataset_json = corpus.model_dump_json(indent=2) + "\n"
    dataset_path.write_text(dataset_json, encoding="utf-8")

    content_sha256 = hashlib.sha256(dataset_json.encode("utf-8")).hexdigest()

    manifest_path = OUT_DIR / f"{OUT_BASENAME}.manifest.json"
    manifest = {
        "dataset_id": DATASET_ID,
        "schema_version": SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "source_authorities": ["European Patent Office (EPO OPS 3.2)"],
        "jurisdictions": JURISDICTIONS,
        "patent_count": len(corpus.patents),
        "content_sha256": content_sha256,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "ops_retrieval_ceiling": OPS_RETRIEVAL_CEILING,
        "leaf_count": result.leaf_count,
        "grant_kind_codes": sorted(GRANT_KIND_CODES),
        "target_n": TARGET_N,
        "minimum_acceptable_n": MINIMUM_ACCEPTABLE_N,
        "eligible_available_records": result.eligible_available_records,
        "disposition_counts": result.disposition_counts,
        "frozen_at": frozen_at,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    sha256_path = OUT_DIR / f"{OUT_BASENAME}.sha256"
    sha256_path.write_text(f"{content_sha256}  {dataset_path.name}\n", encoding="utf-8")

    print(f"\nFrozen {len(corpus.patents)} patents.")
    print(f"  {dataset_path}")
    print(f"  {manifest_path}")
    print(f"  {sha256_path}")
    print(f"  content_sha256={content_sha256}")
    print(f"  eligible_available_records={result.eligible_available_records}")
    print(f"  disposition_counts={result.disposition_counts}")
    print(f"  leaf_count={result.leaf_count}")


if __name__ == "__main__":
    main()
