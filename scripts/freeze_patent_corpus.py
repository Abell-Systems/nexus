#!/usr/bin/env python3
# scripts/freeze_patent_corpus.py
"""Freezes PatentCorpus (`P`), ADR 0020's demand-blind, jurisdiction/grant/window-
determined patent artifact, into a hashed, reproducible dataset artifact.

Mirrors scripts/freeze_phase2_demand_corpus.py's freezing discipline: reproducible
acquisition -> committed dataset file -> manifest JSON -> sha256 sidecar. Unlike that
script, this one is fixture-testable end-to-end without live credentials (ADR 0020 §6);
`main()` requires EPO_OPS_KEY/EPO_OPS_SECRET for the real ~50,000-record run.

Outputs (data/evaluation/):
- dataset_patent_corpus_p.json            canonical patent corpus (PatentCorpus)
- dataset_patent_corpus_p.manifest.json   identity/hash manifest
- dataset_patent_corpus_p.sha256          sha256sum-compatible sidecar
"""

import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
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
from infrastructure.sources.patent.ops_pagination import fetch_all_ops_batches  # noqa: E402
from infrastructure.sources.patent.ops_query import build_patent_corpus_cql  # noqa: E402

OUT_DIR = REPO_ROOT / "data" / "evaluation"
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
# OPS pipeline. The window here is ALREADY enforced by ops_query.build_patent_corpus_cql
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


def build_patent_corpus(
    client: EpoOpsClient,
    cql_query: str,
    jurisdictions: list[str],
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

    for raw_payload in fetch_all_ops_batches(client, cql_query=cql_query):
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

    KNOWN LIMITATION (as of this writing): this issues ONE unpartitioned CQL query
    across all 6 jurisdictions x the full 10-year window. EP+US+JP+CN+KR+WO grants
    (and applications -- CQL cannot filter grants-only reliably, see ops_query.py)
    over 10 years is on the order of 10^7 candidate records. fetch_all_ops_batches's
    enumerability guard (ops_pagination.py) will raise RuntimeError once pagination's
    max_records default (60000) is exceeded, well before reaching that volume -- this
    fails safely (no truncated/silent corpus), but means main() as currently written
    cannot complete a real run at the scale ADR 0020 targets. Before attempting a real
    run: this needs a query-partitioning strategy (e.g. per-jurisdiction, or per-
    jurisdiction-per-year sub-queries, unioned before select_frozen_patents -- sha256
    ordering over the union is identical to ordering over the whole, so ADR 0020 §3's
    determinism is unaffected by how the union is assembled) that is not yet designed
    or implemented. This is a deliberate scope boundary, not an oversight -- see the
    implementation plan's Task 7 and the final-review ledger for the ruling.
    """
    current_year = datetime.now(UTC).year
    min_publication_year = current_year - 10
    max_publication_year = current_year
    cql_query = build_patent_corpus_cql(
        jurisdictions=JURISDICTIONS,
        min_publication_year=min_publication_year,
        max_publication_year=max_publication_year,
    )
    client = EpoOpsClient()  # reads EPO_OPS_KEY/EPO_OPS_SECRET from env

    print(f"Fetching PatentCorpus universe: {cql_query}")
    result = build_patent_corpus(
        client=client,
        cql_query=cql_query,
        jurisdictions=JURISDICTIONS,
        target_n=TARGET_N,
        minimum_acceptable_n=MINIMUM_ACCEPTABLE_N,
        dataset_id=DATASET_ID,
        dataset_version=DATASET_VERSION,
        description=(
            f"Nexus PatentCorpus (P): {', '.join(JURISDICTIONS)} grants, "
            f"{current_year - 10}-{current_year}. See docs/adr/"
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
        "cql_query": cql_query,
        "min_publication_year": min_publication_year,
        "max_publication_year": max_publication_year,
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


if __name__ == "__main__":
    main()
