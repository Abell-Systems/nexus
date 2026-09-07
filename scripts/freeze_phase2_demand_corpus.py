#!/usr/bin/env python3
"""Freezes the Phase 2 demand corpus (N=39) into a hashed, reproducible dataset artifact.

Re-extracts every record live through the real, tested production pipeline
(InnoGetExtractor/LombardiaExtractor -> DefaultOriginResolver -> *HtmlNormalizer) --
it does not copy counts or fields from the prior feasibility audit
(docs/phase2-demand-acquisition-audit.md). The 39-record eligible set (37 InnoGet +
2 Lombardia) was already closed by that audit's corrections (PR #53, #54); this script
converts that closed decision into a frozen dataset, it does not reopen it -- any
record that fails re-verification here is a hard error, not a silent count adjustment.

Outputs (data/evaluation/):
- dataset_phase2_demand_corpus_n39.json           canonical demand corpus (DemandCorpus)
- dataset_phase2_demand_corpus_n39.manifest.json  identity/hash manifest
- dataset_phase2_demand_corpus_n39.sha256          sha256sum-compatible sidecar
- dataset_phase2_demand_corpus_n39.origin_audit.json  full OriginAssessment/FieldObservation
  evidence per demand, retained for audit outside the frozen dataset's minimal schema.
"""

import hashlib
import json
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.ingestion.extractors.lombardia_extractor import LombardiaExtractor  # noqa: E402
from application.ingestion.normalizers.innoget_html_normalizer import InnogetHtmlNormalizer  # noqa: E402
from application.ingestion.normalizers.lombardia_html_normalizer import LombardiaHtmlNormalizer  # noqa: E402
from application.ingestion.origin_resolver import DefaultOriginResolver  # noqa: E402
from domain.models.demand import DemandDisposition  # noqa: E402
from domain.models.evaluation import DataModality, DemandCorpus, EvaluationDemand, EvaluationProvenance  # noqa: E402
from domain.models.origin_policy import OriginPolicyConfig  # noqa: E402
from domain.protocols.sources import RawPayload  # noqa: E402

HEADERS = {"User-Agent": "Mozilla/5.0 (NexusPhase2CorpusFreeze/1.0)"}
POLICY_PATH = REPO_ROOT / "config" / "policies" / "data" / "jurisdiction_policy.json"
OUT_DIR = REPO_ROOT / "data" / "evaluation"
OUT_BASENAME = "dataset_phase2_demand_corpus_n39"

DATASET_ID = "nexus-phase2-demand-corpus-n39-v1"
SCHEMA_VERSION = "1.0.0"
DATASET_VERSION = "1.0.0"
DESCRIPTION = (
    "Nexus Phase 2 frozen demand corpus (N=39): 37 InnoGet + 2 Open Innovation Lombardia "
    "Spain-origin, content-complete Technology request demands. See "
    "docs/phase2-demand-acquisition-audit.md and docs/phase2-sample-size-amendment.md "
    "for the acquisition and eligibility record this corpus materializes."
)

# The 37 eligible InnoGet demands, closed by docs/phase2-demand-acquisition-audit.md's
# InnoGet content-completeness correction (excludes INNOGET-1864, -1701, -1725, -1741).
INNOGET_URLS = [
    "https://www.innoget.com/technology-calls/1605/seeking-lightweight-innovators-for-open-innovation-challenge-from-6-leading-automotive-oems",
    "https://www.innoget.com/technology-calls/1607/seeking-innovative-material-and-manufacturing-technologies-to-enable-cost-efficient-lightweighting-in-high-volume-automotive-appli",
    "https://www.innoget.com/technology-calls/1625/seeking-for-a-method-to-remove-sodium-and-trapped-water-from-residual-fuel-oil",
    "https://www.innoget.com/technology-calls/1689/seeking-for-how-to-improve-long-steel-products",
    "https://www.innoget.com/technology-calls/1726/seeking-a-method-for-controlling-the-implantation-of-yeasts-during-alcoholic-fermentation",
    "https://www.innoget.com/technology-calls/1870/seeking-innovative-proposals-in-the-arc-welding-processes",
    "https://www.innoget.com/technology-calls/1932/seeking-for-solutions-to-make-lcd-displays-or-similar-withstand-temperatures-above-85-c-working-properly",
    "https://www.innoget.com/technology-calls/1935/seeking-for-new-available-technologies-for-water-quality-measurement",
    "https://www.innoget.com/technology-calls/1965/seeking-barcode-product-packaging-recognition",
    "https://www.innoget.com/technology-calls/1972/seeking-anti-oxidant-extract-or-blend-from-micro-algae-with-anti-aging-properties",
    "https://www.innoget.com/technology-calls/2006/seeking-a-botanic-extract-for-urinary-health",
    "https://www.innoget.com/technology-calls/2054/seeking-electromagnetic-applications-to-be-converted-into-a-final-product",
    "https://www.innoget.com/technology-calls/2167/seeking-partners-smes-to-contribute-to-co2-emissions-reduction-and-resource-efficiency-in-eu",
    "https://www.innoget.com/technology-calls/2173/seeking-for-a-partner-in-the-building-sector",
    "https://www.innoget.com/technology-calls/2248/seeking-patents-for-license-de-ep-and-us-issued-patents",
    "https://www.innoget.com/technology-calls/2258/seeking-how-can-we-reduce-costs-and-increase-efficiency-when-obtaining-renewable-hydrogen",
    "https://www.innoget.com/technology-calls/2292/project-3in1-innovative-approaches-to-discovering-consumer-needs-an-in-depth-detergent-market-overview-and-trend-analysis-call",
    "https://www.innoget.com/technology-calls/2293/seeking-kitchen-sink-the-centerpiece-of-your-kitchen-call-for-eu-university-students-only",
    "https://www.innoget.com/technology-calls/2297/seeking-green-efficiency-designing-the-future-marketing-campaign-for-connect-iq-call-for-eu-university-students-only",
    "https://www.innoget.com/technology-calls/2298/seeking-beyond-traditional-envelopes-redefining-communication-with-smartenvelope-call-for-eu-university-students-only",
    "https://www.innoget.com/technology-calls/2299/seeking-redesign-and-updating-envit-s-resoil-website-to-enhance-global-engagement-and-accessibility-call-for-eu-university-stud",
    "https://www.innoget.com/technology-calls/2300/seeking-the-next-wave-of-growth-for-robots-in-warehouse-call-for-eu-university-students-only",
    "https://www.innoget.com/technology-calls/2301/seeking-ai-assistants-automating-and-streamlining-engineering-processes-call-for-eu-university-students-only",
    "https://www.innoget.com/technology-calls/2401/upcycling-agri-food-waste-through-upscaling-industrial-applicability-and-business-case-modelling-upc-barcelonatech-spain",
    "https://www.innoget.com/technology-calls/2402/processes-for-market-assessment-lca-and-regulatory-assessment-upc-barcelonatech-spain",
    "https://www.innoget.com/technology-calls/2403/assessment-of-scalability-processes-for-industrial-decarbonization-upc-barcelonatech-spain",
    "https://www.innoget.com/technology-calls/2404/scaling-industrial-processes-of-critical-raw-materials-recovery-and-application-upc-barcelonatech-spain",
    "https://www.innoget.com/technology-calls/2405/development-of-multi-scale-approaches-for-testing-separation-removal-and-recovery-of-valuable-components-water-and-energy-thr",
    "https://www.innoget.com/technology-calls/2413/application-of-circular-economy-principles-in-housing-construction-development-taltech-estonia",
    "https://www.innoget.com/technology-calls/2414/improving-resilience-of-multifunctional-neighborhoods-within-15-minutes-city-concept-workplaces-perspective-pare-estonia",
    "https://www.innoget.com/technology-calls/2417/sustainable-packaging-challenge-new-materials-for-food-ifm-engage-institute-for-manufacturing-university-of-cambridge-uk",
    "https://www.innoget.com/technology-calls/2425/next-generation-proteins-for-resilient-and-regenerative-food-systems-lut-university-kouvola-finland",
    "https://www.innoget.com/technology-calls/2426/kempower-ev-charging-dataset-exploring-data-driven-opportunities-for-new-business-kempower-finland",
    "https://www.innoget.com/technology-calls/2427/exploring-the-applicability-of-kempower-solutions-in-heavy-electric-traffic-market-analysis-for-scaling-kempower-finland",
    "https://www.innoget.com/technology-calls/2491/seeking-solutions-that-address-the-root-cause-of-gingivitis-by-actively-restoring-oral-microbiome-balance",
    "https://www.innoget.com/technology-calls/2492/seeking-novel-active-ingredients-and-bio-technologies-targeting-new-mechanisms-for-androgenetic-alopecia-aga",
    "https://www.innoget.com/technology-calls/2493/seeking-highly-effective-antimicrobial-alternatives-to-chlorhexidine-chx-without-the-side-effects",
]

# The 2 eligible Lombardia demands (net-new after POD-reference dedup against EEN).
LOMBARDIA_URLS = [
    "https://www.openinnovation.regione.lombardia.it/en/collaborations/collaboration-proposals/860/manutenzione-giunti-di-ponti",
    "https://www.openinnovation.regione.lombardia.it/en/collaborations/collaboration-proposals/947/soluzioni-per-monitorare-e-mitigare-polveri-pm10-in-miniere",
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=20).read()


def main() -> None:
    policy = OriginPolicyConfig.load_from_json(POLICY_PATH)
    resolver = DefaultOriginResolver(policy=policy)
    innoget_normalizer = InnogetHtmlNormalizer(origin_resolver=resolver)
    lombardia_normalizer = LombardiaHtmlNormalizer(origin_resolver=resolver, extractor=LombardiaExtractor())

    demands: list[EvaluationDemand] = []
    audit_records: list[dict] = []
    seen_ids: set[str] = set()
    seen_pod_refs: set[str] = set()

    def process(url: str, normalizer, source_authority: str) -> None:
        print(f"  fetching {url}")
        html_bytes = fetch(url)
        payload = RawPayload(
            source_id=source_authority,
            batch_id=url,
            payload_bytes=html_bytes,
            metadata={"url": url},
        )
        results = list(normalizer.normalize_results(payload))
        if len(results) != 1:
            raise RuntimeError(f"Expected exactly 1 normalization result for {url}, got {len(results)}")
        result = results[0]
        if result.disposition != DemandDisposition.INCLUDED:
            raise RuntimeError(
                f"Eligibility regression: {url} re-verified as {result.disposition.value}, "
                f"expected INCLUDED. The closed 39-record set (docs/phase2-demand-acquisition-audit.md) "
                f"no longer holds -- do not silently drop this record; stop and re-open the audit."
            )
        demand = result.demand
        assert demand is not None

        word_count = len(demand.description.split())
        if word_count < 25:
            raise RuntimeError(
                f"Content-completeness regression: {demand.demand_id} has {word_count} words "
                f"(<25), but was closed as eligible. Stop and re-open the audit."
            )

        if demand.demand_id in seen_ids:
            raise RuntimeError(f"Duplicate demand_id across sources: {demand.demand_id}")
        seen_ids.add(demand.demand_id)

        pod_ref = demand.metadata.get("pod_reference")
        if pod_ref:
            if pod_ref in seen_pod_refs:
                raise RuntimeError(f"Duplicate POD reference across sources: {pod_ref} ({demand.demand_id})")
            seen_pod_refs.add(pod_ref)

        provenance = EvaluationProvenance(
            source_authority=source_authority,
            source_uri=url,
            extraction_timestamp=payload.retrieval_timestamp,
            raw_payload_sha256=payload.payload_sha256,
            modality=DataModality.OBSERVED,
        )
        demands.append(
            EvaluationDemand(
                demand_id=demand.demand_id,
                title=demand.title,
                description=demand.description,
                posted_date=None,
                target_cpc_prefixes=[],
                provenance=provenance,
            )
        )
        audit_records.append(
            {
                "demand_id": demand.demand_id,
                "source_authority": source_authority,
                "source_uri": url,
                "origin_level": result.origin_assessment.level.value,
                "is_target_origin": result.origin_assessment.is_target_origin,
                "origin_country": demand.origin_country,
                "requesting_organization": demand.requesting_organization,
                "pod_reference": pod_ref,
                "description_word_count": word_count,
                "field_observations": [obs.model_dump(mode="json") for obs in result.field_observations],
            }
        )
        time.sleep(0.2)

    print(f"Freezing InnoGet demands ({len(INNOGET_URLS)})...")
    for url in INNOGET_URLS:
        process(url, innoget_normalizer, "innoget")

    print(f"Freezing Lombardia demands ({len(LOMBARDIA_URLS)})...")
    for url in LOMBARDIA_URLS:
        process(url, lombardia_normalizer, "openinnovation-lombardia")

    if len(demands) != 39:
        raise RuntimeError(f"Expected exactly 39 frozen demands, got {len(demands)}")

    corpus = DemandCorpus(
        dataset_id=DATASET_ID,
        schema_version=SCHEMA_VERSION,
        dataset_version=DATASET_VERSION,
        description=DESCRIPTION,
        demands=demands,
    )

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
        "source_authorities": ["innoget", "openinnovation-lombardia"],
        "demand_count": len(demands),
        "patent_count": 0,
        "annotation_count": 0,
        "content_sha256": content_sha256,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    sha256_path = OUT_DIR / f"{OUT_BASENAME}.sha256"
    sha256_path.write_text(f"{content_sha256}  {dataset_path.name}\n", encoding="utf-8")

    audit_path = OUT_DIR / f"{OUT_BASENAME}.origin_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "dataset_id": DATASET_ID,
                "note": "Full origin-verification and FieldObservation evidence per frozen demand, "
                "retained outside the minimal frozen-dataset schema for audit purposes.",
                "records": audit_records,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"\nFrozen {len(demands)} demands.")
    print(f"  {dataset_path}")
    print(f"  {manifest_path}")
    print(f"  {sha256_path}")
    print(f"  {audit_path}")
    print(f"  content_sha256={content_sha256}")


if __name__ == "__main__":
    main()
