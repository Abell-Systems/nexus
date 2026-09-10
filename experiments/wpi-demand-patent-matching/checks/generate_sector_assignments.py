#!/usr/bin/env python3
"""Emits the WPI paper's N=24 per-demand sector assignment (protocol §4.1's `sector`,
closed per phase2_sector_taxonomy_v1 / #83, D4 procedure per
docs/phase2-sector-taxonomy-amendment.md, artifact contract per
docs/phase2-sector-assignment-protocol.md / #89 / #91).

This is experiment tooling: it supplies Auditor A's concrete D4 judgments
(ASSIGNMENT_ENTRIES, NO_COVERAGE_ENTRIES below) as data and persists the resulting
frozen artifact. It does not implement or automate D4 -- D4 is a text-judgment
procedure over each demand's title/description (permitted information per D3), applied
by a human reader, not a computable rule (see docs/phase2-sector-assignment-protocol.md,
"Why this exists"). NO_COVERAGE_ENTRIES' demand_ids are exactly
phase2_sector_coverage_decision_v1.json's declared set (#90/#91) -- verified below,
not re-decided here.

None of the 13 assignments below reach D4 step >= 4 (a genuine tie surviving steps 1-3),
so none require this protocol's mandatory Auditor B review; each resolves at step 1 or
2 on the demand's own text. No entry is flagged borderline for optional Auditor B
review either -- each resolution is defensible from the permitted text alone, and
fabricating a second "independent" reviewer pass with no actual second reader would be
audit theater, not auditability. Unflagged records resting on Auditor A alone is a
protocol-documented, deliberate scope decision (Roles section), not a shortcut taken
here.
"""

import hashlib
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

ELIGIBLE_NAME = "dataset_phase2_eligible_corpus_n24_v1.json"
ELIGIBLE_SHA_NAME = "dataset_phase2_eligible_corpus_n24_v1.sha256"
TAXONOMY_NAME = "phase2_sector_taxonomy_v1.json"
TAXONOMY_SHA_NAME = "phase2_sector_taxonomy_v1.sha256"
COVERAGE_DECISION_NAME = "phase2_sector_coverage_decision_v1.json"
COVERAGE_DECISION_SHA_NAME = "phase2_sector_coverage_decision_v1.sha256"
ASSIGNMENTS_NAME = "sector_assignments_n24_v1.json"
ASSIGNMENTS_SHA_NAME = "sector_assignments_n24_v1.sha256"
ASSIGNMENTS_MANIFEST_NAME = "sector_assignments_n24_v1.manifest.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _empty_trace() -> dict:
    return {
        "primary_technical_problem": None,
        "application_domain": None,
        "candidates_after_step_3": None,
        "joint_reread_result": None,
        "title_first_object": None,
    }


def _no_audit() -> dict:
    return {
        "needs_auditor_b": False,
        "auditor_b_reviewer": None,
        "auditor_b_status": None,
        "agreement": None,
        "adjudication_required": False,
        "adjudication": None,
    }


# Auditor A pass over the 13 demands with a defensible sector under D4.
# One entry per demand_id in dataset_phase2_eligible_corpus_n24_v1.json's order,
# restricted to the sector-coverable subset (#90/#91).
ASSIGNMENT_ENTRIES = [
    {
        "demand_id": "INNOGET-1689",
        "sector_code": "METALLURGY",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "Improvement of long-steel products (rebars, beams) -- a lighter material "
            "and/or a value-adding coating for existing steel product lines."
        ),
        "rationale": (
            "The demand is explicitly a top-4 long-steel producer (Celsa Group) seeking "
            "to improve its own steel products (material or coating). The primary "
            "technical object is a steel-product improvement -- METALLURGY is the only "
            "defensible category, resolved at step 1."
        ),
        "evidence": [
            "\"Celsa Group is among top 4 long-steel producers ... Our main products are "
            "rebars and beams ... It can be an improvement of the material itself, to "
            "make it more light for example, or any special coating.\""
        ],
    },
    {
        "demand_id": "INNOGET-1726",
        "sector_code": "BIOTECHNOLOGY",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "A faster molecular (DNA-based) method to identify/quantify the yeast strain "
            "actively fermenting during alcoholic fermentation."
        ),
        "rationale": (
            "The object sought is explicitly a molecular biology method (mitochondrial "
            "DNA extraction and electrophoresis) applied to yeast during fermentation -- "
            "a biotechnological method, resolved at step 1."
        ),
        "evidence": [
            "\"The molecular method we use is long ... 1 day to obtain de mitocondrial "
            "DNA and do the electrophoresis to know the result. We would like to go "
            "faster.\""
        ],
    },
    {
        "demand_id": "INNOGET-1870",
        "sector_code": "INDUSTRIAL_MACHINERY_IOT",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "Innovative, mechanized/automated solutions for the arc welding "
            "manufacturing process."
        ),
        "rationale": (
            "The demand seeks innovation in an industrial manufacturing process (arc "
            "welding), specifically mechanized and automated solutions -- an industrial "
            "machinery/process-automation object, resolved at step 1."
        ),
        "evidence": [
            "\"...requirements for innovative products and mechanized and automated "
            "solutions, offering improved quality and productivity...\""
        ],
    },
    {
        "demand_id": "INNOGET-1935",
        "sector_code": "INDUSTRIAL_MACHINERY_IOT",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "Water-quality sensor technology, particularly semiconductor-based sensing "
            "and miniaturization."
        ),
        "rationale": (
            "The object sought is a sensing technology (single/multiparameter water "
            "quality sensors), explicitly naming semiconductor sensing and "
            "miniaturization -- an industrial sensing/IoT object, resolved at step 1."
        ),
        "evidence": [
            "\"We are especially interested in solutions based on semiconductor sensing "
            "and miniaturization technologies.\""
        ],
    },
    {
        "demand_id": "INNOGET-1972",
        "sector_code": "BIOTECHNOLOGY",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "An antioxidant extract or blend produced from a micro-algae species/species "
            "mix."
        ),
        "rationale": (
            "The primary object sought is the biological extract itself -- an "
            "antioxidant substance produced from micro-algae -- a bio-extraction/"
            "bio-production object, resolved at step 1. The cosmetics/personal-care use "
            "is the application domain (D4 step 3), not the primary object, and is not "
            "reached because step 1 already resolves to exactly one sector."
        ),
        "evidence": [
            "\"Develop an Anti oxidant solution from Micro Algae specie or species with "
            "an antioxidant action for cosmetics.\""
        ],
    },
    {
        "demand_id": "INNOGET-2006",
        "sector_code": "BIOTECHNOLOGY",
        "resolved_at_step": 1,
        "primary_technical_object": "An innovative botanic (plant-derived) extract with urinary-health functional effects.",
        "rationale": (
            "The primary object sought is a botanic extract -- a plant-derived bioactive "
            "-- resolved at step 1. Supplement/OTC/Pharma end-use is the application "
            "domain (step 3), not reached because step 1 already resolves to exactly one "
            "sector."
        ),
        "evidence": [
            "\"...seeking an innovative botanic extracts with functional effects on the "
            "urinary functions.\""
        ],
    },
    {
        "demand_id": "INNOGET-2258",
        "sector_code": "ENERGY_STORAGE",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "Advanced electrolytic processes for renewable hydrogen production, plus "
            "hydrogen transport and storage technology."
        ),
        "rationale": (
            "The object sought is hydrogen production/storage/transport technology -- "
            "directly within Energy/Renewable Energy Storage as named by the taxonomy, "
            "resolved at step 1."
        ),
        "evidence": [
            "\"...looking for technological solutions to develop advanced electrolytic "
            "processes in addition to options to facilitate secure hydrogen transport "
            "and storage.\""
        ],
    },
    {
        "demand_id": "INNOGET-2403",
        "sector_code": "METALLURGY",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "Separation/recovery of metals from mine tailings, metallurgical-industry "
            "waste, and urban e-waste (alongside brine-based Cl2/Mg(OH)2 production)."
        ),
        "rationale": (
            "Although the demand also mentions brine-based inorganic chemical "
            "production, its own stated central problem is metal separation/recovery "
            "from mining and metallurgical waste streams -- METALLURGY is the only "
            "defensible category among the six, resolved at step 1."
        ),
        "evidence": [
            "\"Pure separation of metals from mine tailings and industrial waste from "
            "metallurgical industries and urban e-waste remains a big problem.\""
        ],
    },
    {
        "demand_id": "INNOGET-2404",
        "sector_code": "METALLURGY",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "Recovery and reuse of critical raw materials from industrial waste, "
            "including rare earth elements (REE)."
        ),
        "rationale": (
            "The object sought is critical raw material / metal recovery from waste "
            "(explicitly naming REE recovery) -- METALLURGY, resolved at step 1."
        ),
        "evidence": [
            "\"...how critical raw matericals can be recovered and applied/reused in "
            "industry, e.g., rare earth elements (REE) recovery.\""
        ],
    },
    {
        "demand_id": "INNOGET-2491",
        "sector_code": "SANITARY_MATERIALS",
        "resolved_at_step": 2,
        "primary_technical_object": (
            "A solution that actively restores oral microbiome balance (eubiosis) as "
            "the mechanism of action."
        ),
        "primary_technical_problem": (
            "Gingivitis -- an oral health/hygiene condition -- addressed at its root "
            "cause rather than by broad antiseptic bacterial reduction."
        ),
        "rationale": (
            "Step 1 (object = a microbiome-modulating solution) does not disambiguate "
            "alone: it reads equally as BIOTECHNOLOGY (the mechanism is microbiome "
            "science) and SANITARY_MATERIALS (an oral-care health product). Step 2's "
            "primary technical problem -- gingivitis, a clinical oral-health condition "
            "-- names a health/hygiene problem, not a biotechnology-domain problem; "
            "BIOTECHNOLOGY describes the solution's mechanism, not the problem being "
            "solved. Resolved at step 2: SANITARY_MATERIALS."
        ),
        "evidence": [
            "\"Lacer is seeking to identify and develop innovative solutions that "
            "address the root cause of gingivitis by actively restoring oral microbiome "
            "balance (eubiosis), moving beyond traditional 'kill bacteria' strategies.\""
        ],
    },
    {
        "demand_id": "INNOGET-2492",
        "sector_code": "BIOTECHNOLOGY",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "Novel active ingredients and bio-technologies targeting new mechanisms of "
            "action (e.g. senescence targeting) for androgenetic alopecia."
        ),
        "rationale": (
            "The demand's own title and text explicitly frame the object sought as "
            "'novel active ingredients and Bio-Technologies' targeting biological "
            "mechanisms (senescence) -- resolved at step 1, BIOTECHNOLOGY. Consumer "
            "hair-care end-use (the Pilexil product line) is the application domain "
            "(step 3), not reached."
        ),
        "evidence": [
            "\"Seeking Novel Active Ingredients and Bio-Technologies Targeting New "
            "Mechanisms for Androgenetic Alopecia (AGA)\" ... \"uncover new mechanisms "
            "of action, such as senescence targeting or novel hair growth boosters.\""
        ],
    },
    {
        "demand_id": "INNOGET-2493",
        "sector_code": "SANITARY_MATERIALS",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "A substitute antimicrobial ingredient/formulation for the oral antiseptic "
            "Chlorhexidine (CHX), without CHX's side effects."
        ),
        "rationale": (
            "The object sought is an oral-care antiseptic ingredient/formulation "
            "replacement -- unlike INNOGET-2491, nothing in the text signals a specific "
            "biological mechanism (CHX itself is a small-molecule antiseptic and the "
            "demand is open to 'an ingredient or mix of ingredients' of any origin) -- "
            "resolved at step 1, SANITARY_MATERIALS (an oral-hygiene health product)."
        ),
        "evidence": [
            "\"Lacer seeks substitute ingredients or formulations that deliver the same "
            "antiseptic efficacy as Chlorhexidine (CHX). The solution must reduce plaque "
            "and gingivitis with significantly fewer side effects.\""
        ],
    },
    {
        "demand_id": "LOMBARDIA-947",
        "sector_code": "INDUSTRIAL_MACHINERY_IOT",
        "resolved_at_step": 1,
        "primary_technical_object": (
            "Autonomous, real-time PM10 dust monitoring and mitigation technology for "
            "open-pit/underground mining."
        ),
        "rationale": (
            "The object sought is an autonomous, real-time monitoring-and-mitigation "
            "system (sensing + actuation) -- an industrial monitoring/IoT object, "
            "resolved at step 1."
        ),
        "evidence": [
            "\"Richieste soluzioni autonome, basse in acqua, resistenti a condizioni "
            "estreme e con analisi realtime.\" (Autonomous, low-water, extreme-condition-"
            "resistant solutions with real-time analysis requested.)"
        ],
    },
]

# The 11 demands with no defensible sector (#90, declared in
# phase2_sector_coverage_decision_v1.json -- verified to match exactly, not re-decided,
# in main() below).
NO_COVERAGE_ENTRIES = [
    {
        "demand_id": "INNOGET-1605",
        "rationale": (
            "Automotive lightweighting material/manufacturing concept: material- and "
            "process-agnostic (\"material or manufacturing\"), not a consumer product "
            "(CONSUMER_CHEMISTRY), not sector-specific to metals (METALLURGY would "
            "require a metal-specific object, which this demand does not state)."
        ),
        "evidence": [
            "\"Do you have a specific idea or concept (material or manufacturing) on "
            "how to design lighter vehicles?\""
        ],
    },
    {
        "demand_id": "INNOGET-1607",
        "rationale": (
            "Sibling ALLIANCE call to INNOGET-1605, same automotive lightweighting "
            "material/manufacturing object, same absence of a defensible category."
        ),
        "evidence": [
            "\"Do you have a specific idea or concept (material or manufacturing) on "
            "how to achieve lightweighting in vehicles?\""
        ],
    },
    {
        "demand_id": "INNOGET-1625",
        "rationale": (
            "Industrial fuel-oil purification chemistry (removing sodium/water "
            "contaminants for fossil-fuel blending) -- not a consumer product "
            "(CONSUMER_CHEMISTRY), not an energy-storage object (ENERGY_STORAGE); no "
            "other category names industrial fuel purification."
        ),
        "evidence": [
            "\"we are looking for a method to remove contaminants from a bio-based "
            "residue (fuel oil), so it could be incorporated in a fossil fuel oil "
            "blending.\""
        ],
    },
    {
        "demand_id": "INNOGET-1932",
        "rationale": (
            "High-temperature display/LCD material engineering -- electronics/display "
            "materials science, not named by any of the six categories."
        ),
        "evidence": [
            "\"We need to find alternate display technologies for high temp (up to "
            "95ºC) displays.\""
        ],
    },
    {
        "demand_id": "INNOGET-1965",
        "rationale": (
            "Barcode/packaging recognition via a mobile application -- pure software, "
            "not matching any of the six physical-domain categories."
        ),
        "evidence": [
            "\"We are seeking a solution able to recognise the product packaging type "
            "after scanning the product barcode through a mobile app.\""
        ],
    },
    {
        "demand_id": "INNOGET-2173",
        "rationale": (
            "Mining-waste valorization for construction applications, framed as a "
            "partner search for experimental development (TRL 3→5) rather than a "
            "specific technical solution -- neither mining nor construction is a "
            "taxonomy category, and METALLURGY would require a metal-recovery object, "
            "which this demand does not state (it is waste-to-construction-material "
            "valorization, not metal recovery)."
        ),
        "evidence": [
            "\"A proposal development with the valorization of waste products of the "
            "mining industry ... these by-products would be applied in the construction "
            "sector.\""
        ],
    },
    {
        "demand_id": "INNOGET-2301",
        "rationale": (
            "AI assistant/RAG software to automate engineering-compliance processes "
            "(Automotive SPICE, ISO 26262, FMEA) -- pure software/process-automation "
            "tooling, not industrial machinery/IoT hardware; no other category applies."
        ),
        "evidence": [
            "\"We seek to develop custom AI assistants using RAG (Retrieval-Augmented "
            "Generation) technology to streamline engineering workflows.\""
        ],
    },
    {
        "demand_id": "INNOGET-2401",
        "rationale": (
            "Agri-food waste upcycling via refining/separation/purification "
            "technologies, described at a program level (secondments, industrial "
            "pilots) rather than a specific technical object -- too generic against the "
            "permitted text to defensibly place in BIOTECHNOLOGY or any other category "
            "without stretching the evidence beyond what D4 step 1-3 can support."
        ),
        "evidence": [
            "\"...working on tackling the problem of agri-food waste, as well as "
            "refining, separation and purification technologies in the labs.\""
        ],
    },
    {
        "demand_id": "INNOGET-2405",
        "rationale": (
            "Multi-scale water/energy recovery via hybrid membrane processes (MF, UF, "
            "NF, RO, EDBP-MD) -- neither ENERGY_STORAGE (this is recovery/treatment, "
            "not storage) nor METALLURGY (no metal-recovery object stated) fits "
            "cleanly; no other category applies."
        ),
        "evidence": [
            "\"...revolutionary approaches for maximizing water reuse and water "
            "recovery ... integration of MF, UF, NF, RO, EDBP-MD.\""
        ],
    },
    {
        "demand_id": "INNOGET-2417",
        "rationale": (
            "Sustainable/regenerative food-packaging materials -- not itself a consumer "
            "product (CONSUMER_CHEMISTRY) nor a health/hygiene product "
            "(SANITARY_MATERIALS); packaging materials science is not named by any of "
            "the six categories."
        ),
        "evidence": [
            "\"...looking for innovative approaches to support the development and "
            "adoption of sustainable and regenerative food packaging solutions, with a "
            "focus on new materials.\""
        ],
    },
    {
        "demand_id": "LOMBARDIA-860",
        "rationale": (
            "Bridge expansion-joint and elastomeric-bearing maintenance technology -- "
            "civil infrastructure maintenance, not named by any of the six categories "
            "(not metal-specific, not a consumer/sanitary product, not industrial "
            "process machinery in the manufacturing sense)."
        ),
        "evidence": [
            "\"Una società spagnola cerca tecnologie di manutenzione per giunti di "
            "dilatazione elastomerici e appoggi in neoprene di ponti stradali.\""
        ],
    },
]


def _build_assignment_entry(a: dict) -> dict:
    trace = _empty_trace()
    trace["resolved_at_step"] = a["resolved_at_step"]
    trace["primary_technical_object"] = a["primary_technical_object"]
    if "primary_technical_problem" in a:
        trace["primary_technical_problem"] = a["primary_technical_problem"]
    if "application_domain" in a:
        trace["application_domain"] = a["application_domain"]
    return {
        "demand_id": a["demand_id"],
        "sector_code": a["sector_code"],
        "decision_trace": trace,
        "rationale": a["rationale"],
        "evidence": a["evidence"],
        "assignment": {"reviewer": "Auditor A"},
        "audit": _no_audit(),
    }


def _build_no_coverage_entry(n: dict) -> dict:
    return {
        "demand_id": n["demand_id"],
        "rationale": n["rationale"],
        "evidence": n["evidence"],
        "reviewer": "Auditor A",
    }


def main() -> int:
    coverage_decision = json.loads((CONFIG_DIR / COVERAGE_DECISION_NAME).read_text(encoding="utf-8"))
    declared_no_coverage_ids = set(coverage_decision["no_sector_coverage_demand_ids"])
    generated_no_coverage_ids = {e["demand_id"] for e in NO_COVERAGE_ENTRIES}
    assert generated_no_coverage_ids == declared_no_coverage_ids, (
        "NO_COVERAGE_ENTRIES does not match phase2_sector_coverage_decision_v1.json's "
        f"declared set: missing={declared_no_coverage_ids - generated_no_coverage_ids}, "
        f"extra={generated_no_coverage_ids - declared_no_coverage_ids}"
    )

    eligible = json.loads((DATA_DIR / ELIGIBLE_NAME).read_text(encoding="utf-8"))
    eligible_ids = {d["demand_id"] for d in eligible["demands"]}
    assignment_ids = {e["demand_id"] for e in ASSIGNMENT_ENTRIES}
    assert assignment_ids | generated_no_coverage_ids == eligible_ids
    assert not (assignment_ids & generated_no_coverage_ids)

    assignments_out = [_build_assignment_entry(a) for a in ASSIGNMENT_ENTRIES]
    no_coverage_out = [_build_no_coverage_entry(n) for n in NO_COVERAGE_ENTRIES]

    dataset = {
        "dataset_id": "nexus-phase2-sector-assignments-n24-v1",
        "assignments": assignments_out,
        "no_sector_coverage": no_coverage_out,
    }

    assignments_path = DATA_DIR / ASSIGNMENTS_NAME
    assignments_path.write_text(json.dumps(dataset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    assignments_sha = _sha256_file(assignments_path)

    per_sector_counts: dict[str, int] = {}
    for a in ASSIGNMENT_ENTRIES:
        per_sector_counts[a["sector_code"]] = per_sector_counts.get(a["sector_code"], 0) + 1

    manifest = {
        "demand_count": len(assignments_out),
        "no_sector_coverage_count": len(no_coverage_out),
        "no_sector_coverage_demand_ids": sorted(generated_no_coverage_ids),
        "content_sha256": assignments_sha,
        "per_sector_counts": per_sector_counts,
        "derived_from": {
            "eligible_corpus_sha256": _sha256_file(DATA_DIR / ELIGIBLE_NAME),
            "taxonomy_config_sha256": _sha256_file(CONFIG_DIR / TAXONOMY_NAME),
            "coverage_decision_sha256": _sha256_file(CONFIG_DIR / COVERAGE_DECISION_NAME),
        },
    }
    (DATA_DIR / ASSIGNMENTS_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (DATA_DIR / ASSIGNMENTS_SHA_NAME).write_text(f"{assignments_sha}  {ASSIGNMENTS_NAME}\n", encoding="utf-8")

    print(
        f"Wrote {len(assignments_out)} sector assignments + {len(no_coverage_out)} "
        f"no_sector_coverage -> {assignments_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
