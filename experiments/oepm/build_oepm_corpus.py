"""ADR 0035 SS11.3: production-scale OEPM corpus acquisition via INVENES.

Reuses OepmRawSource + OepmNormalizer + IngestionPipeline UNMODIFIED. Applies
ADR 0035's exclusions (T3/EP-ES kind code, ADR 0035 SS3; missing critical text,
ADR 0035 SS9) as a pre-ingestion classification step here, writing a real,
disclosed exclusion manifest -- since OepmNormalizer itself has no kind-code
filter or disposition split (see ADR 0035 SS11.2 commit c913e7a, which
deliberately left OepmNormalizer untouched to avoid changing its behavior for
existing callers).

Sequence: harvest (real, no registration) -> classify (INCLUDED / EXCLUDED /
QUARANTINED) -> write OEPM JSON payload (INCLUDED only) -> run through the
existing IngestionPipeline -> sealed canonical corpus + EnhancedManifest.
"""

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "backend" / "src" / "main"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from application.ingestion.normalizers.oepm_normalizer import OepmNormalizer  # noqa: E402
from application.ingestion.pipeline import IngestionPipeline  # noqa: E402
from application.ingestion.validator import PatentValidator  # noqa: E402
from infrastructure.sources.patent.oepm_raw_source import OepmRawSource  # noqa: E402
from infrastructure.storage.parquet_store import ParquetCanonicalStore  # noqa: E402
from infrastructure.storage.raw_store import FilesystemRawStore  # noqa: E402

from experiments.oepm.invenes_detail_parser import parse_invenes_detail  # noqa: E402
from experiments.oepm.invenes_harvester import SOURCE_ID, InvenesHarvester  # noqa: E402

logger = logging.getLogger("experiments.oepm.build_oepm_corpus")

# Real, deliberately diverse referencias discovered via public INVENES search
# (no registration) on 2026-09-14 -- three queries chosen to overlap with the
# TED demand corpus's own topics (wastewater treatment, electricity metering,
# software/register-management platforms; see
# experiments/phase2/generate_ted_annotation_dry_run.py's DRY_RUN_DEMAND_IDS),
# so the retrieval smoke test (step 5) has a real chance of non-empty pools.
REFERENCIAS: tuple[str, ...] = (
    "E12152341", "E13178884", "E13182860", "E14153728", "E15191653",
    "E16157581", "E18191904", "E18213242", "P0247493", "P0319897",
    "P0357922", "P0361390", "P0380899", "P0381934", "P0388674",
    "P0390307", "P0403218", "P0425629", "P0426380", "P0440183",
    "P0445787", "P0474376", "P0507161", "P0539601", "P0540743",
    "P200402351", "P200800795", "P201132156", "P201430830", "P201530552",
    "P201630316", "P201630580", "P201830321", "P9101245", "P9600407",
    "U0170520", "U200302832", "U201330385", "U201631167", "U9400490",
)

# Scaled acquisition, session 1 (docs/phase2-invenes-scaled-acquisition.md).
# Mechanical continuation of the population-adequacy probe's 10 queries
# (docs/phase2-invenes-population-adequacy-probe-preregistration.md): each
# query's *next* unused non-PCT referencias, in INVENES's own result order
# (positions 5-8, or further into page 2 where a query's page 1 ran short),
# read from the live search UI on 2026-09-15. No new query design, no
# curation -- this batch's purpose (qualifying the corpus to N>=60) is kept
# distinct from the probe's own purpose (testing yield), per the existing
# workstream-isolation rule; it only reuses the query strategy the probe
# validated as SCENARIO_A_SIGNAL.
SESSION_1_REFERENCIAS: tuple[str, ...] = (
    "P0510444", "P0522840", "P0437308", "P0336549",  # sistema de refrigeracion por absorcion
    "P201600627", "P201600626", "E13161632", "P202030337",  # dispositivo de monitorizacion de constantes vitales
    "E22195067", "U202530259", "E21168148", "E19187407",  # metodo de reciclaje de baterias de litio
    "E93400913", "P200300459", "P200902064", "P200603078",  # estructura modular de vivienda prefabricada
    "U201730784", "E20160990", "P202230020", "E92121367",  # sistema de purificacion de aire mediante fotocatalisis
    "E15195725", "E12182148", "E93402560", "E87400489",  # algoritmo de deteccion de fraude en transacciones
    "P200200420", "P201200352", "P201531105", "P201530431",  # revestimiento anticorrosivo para estructuras metalicas
    "E13158984", "E13158995", "P201730461", "P200401883",  # sistema de riego automatizado por goteo
    "P202030202", "U202000367", "E18214549", "U202130811",  # dispositivo de asistencia para movilidad reducida
    "E17167536", "E20214203", "E22382482", "P202330826",  # metodo de fabricacion aditiva de piezas metalicas
)

REFERENCIAS = REFERENCIAS + SESSION_1_REFERENCIAS

# Scaled acquisition, session 2. Same mechanical rule as session 1: each
# query's next unused non-PCT referencias (positions 9-12, paging further
# where a query ran short), read live on 2026-09-15, deduplicated against
# every referencia already in REFERENCIAS (a handful of these 10 queries'
# result sets overlap -- e.g. U202130811 recurred and was skipped here since
# session 1 already used it via a different query).
SESSION_2_REFERENCIAS: tuple[str, ...] = (
    "P0287857", "P0249335", "P0264027", "P0248684",  # sistema de refrigeracion por absorcion
    "U202032572", "P202230830", "P200402387", "E08100922",  # dispositivo de monitorizacion de constantes vitales
    "E20211167", "E20206690", "E23217198", "P202031224",  # metodo de reciclaje de baterias de litio
    "P200700383", "P201000554", "P201000537", "P9500597",  # estructura modular de vivienda prefabricada
    "P201100554", "U201230434", "P201530572", "U201630647",  # sistema de purificacion de aire mediante fotocatalisis
    "E90300209", "E04023180", "E99303410", "E11192137",  # algoritmo de deteccion de fraude en transacciones
    "E13163753", "E17201687", "E88305292", "E89304937",  # revestimiento anticorrosivo para estructuras metalicas
    "P201231090", "U201600456", "E11010161", "E17174628",  # sistema de riego automatizado por goteo
    "U202000365", "U202130218", "U202131094", "U202130217",  # dispositivo de asistencia para movilidad reducida
    "P202430515", "E10154811", "U201431364", "P201600082",  # metodo de fabricacion aditiva de piezas metalicas
)

REFERENCIAS = REFERENCIAS + SESSION_2_REFERENCIAS

# T3 (EP-ES) is out of "domestic" scope by default -- ADR 0035 SS3, mirroring
# the same NORMATIVE_KIND_CODES-minus-T3 default already applied to
# OepmXmlNormalizer (commit c913e7a).
ALLOWED_KIND_CODES = frozenset({"A1", "A2", "B1", "B2", "U"})


def classify_records(
    raw_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (included_items, exclusion_manifest_entries)."""
    included: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []

    for referencia in REFERENCIAS:
        # save_raw_payload collapses out_dir/source_id into out_dir itself when
        # out_dir's own name already equals source_id (see BaseHarvester.save_raw_payload) --
        # raw_dir here is exactly that source_id-named directory.
        html_path = raw_dir / f"{referencia}.html"
        if not html_path.exists():
            exclusions.append({
                "referencia": referencia, "reason": "not_harvested",
                "detail": f"No raw payload found at {html_path}",
            })
            continue

        parsed = parse_invenes_detail(html_path.read_bytes(), referencia=referencia)
        if parsed is None:
            exclusions.append({
                "referencia": referencia, "reason": "quarantined_unparseable",
                "detail": "Detail page did not match the expected bibliographic structure",
            })
            continue

        if parsed.kind_code not in ALLOWED_KIND_CODES:
            exclusions.append({
                "referencia": referencia,
                "publication_id": parsed.item["publication_id"],
                "kind_code": parsed.kind_code,
                "reason": "unsupported_kind_code",
                "detail": f"Kind code '{parsed.kind_code}' outside domestic scope (ADR 0035 SS3): {sorted(ALLOWED_KIND_CODES)}",
            })
            continue

        if not parsed.item["title"].strip() or not parsed.item["abstract"].strip():
            exclusions.append({
                "referencia": referencia,
                "publication_id": parsed.item["publication_id"],
                "kind_code": parsed.kind_code,
                "reason": "missing_critical_text",
                "detail": f"title={'present' if parsed.item['title'].strip() else 'MISSING'}, "
                          f"abstract={'present' if parsed.item['abstract'].strip() else 'MISSING'} (ADR 0035 SS9)",
            })
            continue

        included.append(parsed.item)

    return included, exclusions


def build_corpus(
    out_root: Path = REPO_ROOT / "data",
    dataset_id: str = "OEPM-INVENES-CORPUS-2026-V1",
) -> dict[str, Any]:
    raw_harvest_dir = out_root / "raw" / "oepm_invenes"
    raw_store_dir = out_root / "raw" / "oepm_invenes_ingest"
    canonical_dir = out_root / "snapshots" / "oepm_invenes_corpus_v1"
    manifest_dir = out_root / "experiments" / "oepm_v1"

    # 1. Harvest (real, no registration, idempotent)
    harvester = InvenesHarvester()
    harvester.harvest(list(REFERENCIAS), out_dir=raw_harvest_dir)
    if harvester.acquisition_errors:
        harvester.dump_errors(manifest_dir / "harvest_errors.json")

    # 2. Classify (ADR 0035 SS3/SS9)
    included_items, exclusions = classify_records(raw_harvest_dir)

    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "exclusion_manifest.json").write_text(
        json.dumps(exclusions, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # 3. Write the OEPM JSON payload (INCLUDED only) in the shape OepmRawSource
    #    / OepmNormalizer already consume, unmodified.
    payload = {
        "dataset_metadata": {
            "dataset_id": dataset_id,
            "dataset_title": "Oficina Española de Patentes y Marcas (OEPM) -- INVENES public search, ADR 0035",
            "official_catalog_url": "https://consultas2.oepm.es/InvenesWeb/faces/busquedaInternet.jsp",
        },
        "publications": included_items,
    }
    raw_json_path = out_root / "raw" / "oepm_invenes_corpus_v1.json"
    raw_json_path.parent.mkdir(parents=True, exist_ok=True)
    raw_json_bytes = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    raw_json_path.write_bytes(raw_json_bytes)
    raw_json_path.with_suffix(".sha256").write_text(
        f"{hashlib.sha256(raw_json_bytes).hexdigest()}  {raw_json_path.name}\n", encoding="utf-8"
    )

    # 4. Ingest via the existing, unmodified pipeline -> sealed canonical corpus.
    pipeline = IngestionPipeline(
        raw_store=FilesystemRawStore(base_dir=raw_store_dir),
        canonical_store=ParquetCanonicalStore(base_dir=canonical_dir),
        validator=PatentValidator(),
    )
    summary = pipeline.ingest_patent_source(
        source=OepmRawSource(file_path=raw_json_path, source_id="oepm_invenes_corpus", batch_id="oepm_invenes_v1_batch"),
        normalizer=OepmNormalizer(extraction_version="1.0.0"),
        dataset_id=dataset_id,
        manifest_output_dir=manifest_dir,
        transformation_version="1.0.0",
    )

    report = {
        "dataset_id": dataset_id,
        "referencias_attempted": len(REFERENCIAS),
        "included_count": len(included_items),
        "excluded_count": len(exclusions),
        "exclusion_reasons": _count_reasons(exclusions),
        "ingested_records": summary.processed_records,
        "canonical_sha256": summary.enhanced_manifest.canonical_sha256 if summary.enhanced_manifest else None,
        "canonical_dir": str(canonical_dir),
        "manifest_dir": str(manifest_dir),
    }
    (manifest_dir / "build_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def _count_reasons(exclusions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in exclusions:
        counts[e["reason"]] = counts.get(e["reason"], 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="ADR 0035 SS11.3 OEPM corpus acquisition (INVENES).")
    parser.parse_args(argv)
    report = build_corpus()
    logger.info("Build report: %s", json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
