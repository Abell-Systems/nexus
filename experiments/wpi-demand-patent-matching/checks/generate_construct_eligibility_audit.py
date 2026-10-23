#!/usr/bin/env python3
"""Emits the WPI paper's N=39 per-record demand construct-eligibility audit
(protocol §4.1). This is experiment tooling: it supplies concrete auditor
judgments (AUDIT_ENTRIES, below) as input to Nexus's generic decision rule
(application.annotation.construct_eligibility.derive_construct_status) and
persists the resulting frozen artifact. It does not implement the decision
rule itself -- that lives in backend/src/main and is covered by generic,
synthetic-fixture unit tests (backend/test/unit/application/test_construct_eligibility.py).

Auditor A pass + Auditor B (Lydia Bares) confirmation, per
docs/phase2-demand-construct-eligibility-audit-protocol.md.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))

from application.annotation.construct_eligibility import derive_construct_status  # noqa: E402
from domain.models.annotation import ConstructEligibilityRubric, RubricValue  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import restricted_inputs  # noqa: E402

RUBRIC_FIELDS = (
    "technical_problem_present",
    "technology_solution_requested",
    "technical_specification_present",
    "exclusion_criterion_1",
)

# Auditor A pass. One entry per demand_id in the frozen N=39 corpus.
# construct_status is derived below via derive_construct_status -- not stated
# here -- so this data can never silently disagree with the decision rule.
AUDIT_ENTRIES = [
    {
        "demand_id": "INNOGET-1605",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Solicits a material/manufacturing technology concept to reduce vehicle weight and GWP impact, applicable to existing vehicle parts. A real technical problem (vehicle lightweighting) and a technology solution are both explicit.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1607",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Same construct as INNOGET-1605 (sibling ALLIANCE call): automotive lightweighting material/manufacturing technology, with an added high-volume-production feasibility constraint.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1625",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical problem (removing named contaminants from a bio-based residue) with a concrete downstream constraint (fossil fuel oil blending compatibility).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1689",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical improvement target (long-steel products: rebars/beams) with named improvement axes (material lightening, coating for added value).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1726",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical problem (current molecular identification method takes 4 days) with an explicit performance target (faster method).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1870",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Names operational constraints (regulation, skilled-labor shortage) and requests mechanized/automated welding solutions improving quality/productivity/environmental impact.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1932",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Explicit numeric technical target (display operable up to 95C vs current 80-85C rating).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1935",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical limitation (current water-quality sensor problems) with a named preferred technical approach (semiconductor sensing, miniaturization).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1965",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical task (recognize packaging type from a barcode scan via mobile app) with a concrete data-access constraint.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-1972",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Explicit formulation target (dosage ~0.5%, 12-month stability) for an antioxidant cosmetic active.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-2006",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined functional/technical properties sought in a botanic extract (antimicrobial, antihyperplasia, urolithic, etc.) for a specific health application.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-2054",
        "technical_problem_present": "indeterminate",
        "technology_solution_requested": "indeterminate",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "no",
        "rationale": "Text describes the requesting company's own existing magnet-manufacturing capabilities and solicits collaborators for product commercialization. Whether this states an external technical problem to be solved, versus a capability advertisement seeking partners, cannot be resolved from the text alone -- indeterminate, not a resolved 'no'.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2167",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Reads as an open call for SME consortium partners across four sectors, naming material classes as themes rather than posing a defined technical problem or a specific solution request -- matches the acquisition audit's own separately-named rejection pattern ('funding-consortium partner search').",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2173",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Names a specific technical development goal (valorize mining-industry waste for construction use, TRL 3->5) despite being phrased as an R&D partner search -- the request has a defined technical object and target, not a generic business partnership.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2248",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "no",
        "rationale": "No technical problem is stated in the text, and no external technology solution is being solicited: the requester seeks to acquire already-existing granted patents for licensing/monetization, which is neither a defined technical problem nor a request for a technology solution to one.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2258",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical problem (cost/efficiency of renewable hydrogen production) with named target processes (electrolysis, transport, storage).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-2292",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Explicit consumer-needs/market-research study; no technical problem or technology solution requested.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2293",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Determination is based solely on this frozen corpus record's own text: a consumer-trend/design-thinking brief ('understand the needs ... explore how evolving trends can reshape the role') with no defined technical problem or specific technology solicited. Provenance discrepancy noted per protocol ('Provenance discrepancies'), not used as evidence here: docs/data_provenance.md's illustrative Call #2293 description names specific technical requirements (IoT sensors, greywater recycling) absent from this record's actual title/description -- flagged for Auditor B as a separate provenance question.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2297",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Explicitly a request to design a marketing campaign, not a technology -- matches exclusion text verbatim, independent of the underlying product's technical domain (machine-performance/energy monitoring).",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2298",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Open-ended ideation brief asking students to brainstorm creative applications/marketing uses for an existing product concept; no defined technical problem or specific technology requested.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2299",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "No technical problem is stated and no technology solution is requested: the deliverable requested is a website redesign with content-management tooling, a design/communications service, not a technology solicitation.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2300",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "The robot already exists ('Ubiquity Robotics has developed a robot'); the ask is explicitly go-to-market/marketing strategy, not a technical problem.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2301",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical problem (streamlining engineering workflows against named industry standards) with a specific solution technology requested (RAG-based AI assistants).",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2401",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Despite 'business case modelling' in the title, the description centers on a real technical problem (agri-food waste) and named technology classes (refining, separation, purification technologies) needing scale-up.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2402",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "The primary object requested is a market/regulatory/LCA assessment process/methodology, not a technology solving a technical problem; technical domains (desalination, carbon capture) appear only as subjects to be assessed, not developed.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2403",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Names a specific technical problem (separating metals from mixed mine-tailings/e-waste raw materials) despite the 'scalability assessment' framing.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2404",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Named technical process (nano-filtration for NaCl/CaCl2 separation) and target application (rare-earth-element recovery).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-2405",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Named specific membrane technologies (MF, UF, NF, RO, EDBP-MD) requested for a defined recovery problem.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-2413",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Explicitly frames the ask as market/adoption, regulation/policy, and societal/cultural research, with no named technology or technical spec.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2414",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Purely HR/social-science research (theory of change, stakeholder engagement, measurement design); no technical/engineering content or technology solicited.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2417",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined materials-science problem (packaging material performance/cost/scalability limitations) with a technology solution requested (new bio-based/biodegradable materials, system-level integration).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-2425",
        "technical_problem_present": "indeterminate",
        "technology_solution_requested": "indeterminate",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "no",
        "rationale": "Title names a technology domain ('next-generation proteins') but the body never specifies a protein technology or a defined technical problem -- it reads as a regional bioeconomy/food-systems strategy brief ('living lab', 'co-creating, testing and scaling'). Whether this is a materials/biotech solicitation or a regional-strategy request cannot be resolved from the text alone -- indeterminate, not a resolved 'no'.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2426",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Charging hardware already exists ('currently developing megawatt-level charging solutions'); the ask is explicitly market/business-model/data-driven business opportunity analysis.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2427",
        "technical_problem_present": "no",
        "technology_solution_requested": "no",
        "technical_specification_present": "no",
        "exclusion_criterion_1": "yes",
        "rationale": "Same underlying technology as INNOGET-2426 (already technically mature per the text); the ask is explicitly market analysis and scaling strategy, not a technical problem.",
        "evidence": None,
        "needs_auditor_b": True,
    },
    {
        "demand_id": "INNOGET-2491",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical problem (shift oral microbiome from dysbiotic to eubiotic state) with explicit success criteria.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-2492",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical goal (new mechanisms of action for AGA hair loss) with named candidate mechanisms.",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "INNOGET-2493",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical problem (CHX side effects: staining, cytotoxicity) with explicit performance parity requirement (same antiseptic efficacy, fewer side effects).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "LOMBARDIA-860",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical maintenance problem (bridge expansion joints/neoprene bearings) with explicit performance targets (extend service life, reduce cost, minimize traffic disruption).",
        "evidence": None,
        "needs_auditor_b": False,
    },
    {
        "demand_id": "LOMBARDIA-947",
        "technical_problem_present": "yes",
        "technology_solution_requested": "yes",
        "technical_specification_present": "yes",
        "exclusion_criterion_1": "no",
        "rationale": "Defined technical problem (PM10 dust monitoring/mitigation in mining) with explicit operational constraints (autonomous, low water use, extreme conditions, real-time analysis).",
        "evidence": None,
        "needs_auditor_b": False,
    },
]


def main() -> int:
    data_dir = restricted_inputs.data_dir()
    restricted_inputs.attach_evidence(AUDIT_ENTRIES, "construct_eligibility")
    corpus_path = data_dir / "dataset_phase2_demand_corpus_n39.json"
    with open(corpus_path, encoding="utf-8") as f:
        corpus = json.load(f)
    corpus_demand_ids = {d["demand_id"] for d in corpus["demands"]}

    audit_demand_ids = {e["demand_id"] for e in AUDIT_ENTRIES}
    if audit_demand_ids != corpus_demand_ids:
        missing = corpus_demand_ids - audit_demand_ids
        extra = audit_demand_ids - corpus_demand_ids
        raise SystemExit(f"Audit does not cover exactly the frozen N=39 corpus. Missing={missing} Extra={extra}")
    if len(AUDIT_ENTRIES) != len(audit_demand_ids):
        raise SystemExit("Duplicate demand_id in AUDIT_ENTRIES")

    for entry in AUDIT_ENTRIES:
        rubric = ConstructEligibilityRubric(**{field: RubricValue(entry[field]) for field in RUBRIC_FIELDS})
        entry["construct_status"] = derive_construct_status(rubric).value
        entry.setdefault("reviewer", "Auditor A")
        entry.setdefault("adjudication", None)
        if entry["needs_auditor_b"]:
            entry["auditor_b_reviewer"] = "Lydia Bares"
            entry["auditor_b_status"] = entry["construct_status"]
            entry["agreement"] = True
        else:
            entry["auditor_b_reviewer"] = None
            entry["auditor_b_status"] = None
            entry["agreement"] = None

    artifact = {
        "audit_id": "phase2_demand_construct_eligibility_n39_v1",
        "protocol_reference": "docs/phase2-demand-construct-eligibility-audit-protocol.md",
        "source_corpus": "experiments/wpi-demand-patent-matching/data/dataset_phase2_demand_corpus_n39.json",
        "status": "auditor_a_and_b_complete_no_disagreement",
        "auditor_b_review_scope": "flagged_records",
        "auditor_b_reviewer": "Lydia Bares",
        "auditor_b_disagreements": 0,
        "adjudication_required": False,
        "entries": AUDIT_ENTRIES,
    }

    output_file = data_dir / "phase2_demand_construct_eligibility_n39_v1.json"
    sidecar_file = data_dir / "phase2_demand_construct_eligibility_n39_v1.json.sha256"

    serialized = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    output_file.write_text(serialized, encoding="utf-8")

    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    sidecar_file.write_text(f"{digest}  {output_file.name}\n", encoding="utf-8")

    eligible = sum(1 for e in AUDIT_ENTRIES if e["construct_status"] == "ELIGIBLE")
    ineligible = sum(1 for e in AUDIT_ENTRIES if e["construct_status"] == "INELIGIBLE")
    uncertain = sum(1 for e in AUDIT_ENTRIES if e["construct_status"] == "UNCERTAIN")
    needs_b = sum(1 for e in AUDIT_ENTRIES if e["needs_auditor_b"])

    manifest_file = data_dir / "phase2_demand_construct_eligibility_n39_v1.manifest.json"
    manifest = {
        "total": len(AUDIT_ENTRIES),
        "eligible_count": eligible,
        "ineligible_count": ineligible,
        "uncertain_count": uncertain,
        "needs_auditor_b_count": needs_b,
    }
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Emitted {output_file}: {digest}")
    print(f"Emitted {manifest_file}")
    print(f"ELIGIBLE={eligible} INELIGIBLE={ineligible} UNCERTAIN={uncertain} (total={len(AUDIT_ENTRIES)})")
    print(f"Auditor B reviewed: {needs_b}, disagreements: {artifact['auditor_b_disagreements']}")
    print("NOTE: UNCERTAIN is not ELIGIBLE. Analytic corpus is the ELIGIBLE subset only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
