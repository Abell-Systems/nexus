import hashlib
import json
from pathlib import Path

VALID_STATUSES = {"ELIGIBLE", "INELIGIBLE", "UNCERTAIN"}
VALID_RUBRIC_VALUES = {"yes", "no", "indeterminate"}
RUBRIC_FIELDS = (
    "technical_problem_present",
    "technology_solution_requested",
    "technical_specification_present",
    "exclusion_criterion_1",
)


class TestPhase2ConstructEligibilityAudit:
    """Contract tests for the Phase 2 N=39 per-record demand construct eligibility
    audit (#84), independent of phase2_sector_taxonomy_v1 (#83) and of #80."""

    def _root_path(self) -> Path:
        return Path(__file__).resolve().parents[5]

    def _load_audit(self) -> dict:
        path = (
            self._root_path()
            / "data"
            / "evaluation"
            / "phase2_demand_construct_eligibility_n39_v1.json"
        )
        assert path.exists(), f"Audit artifact missing at {path}"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _load_corpus_demand_ids(self) -> set[str]:
        path = self._root_path() / "data" / "evaluation" / "dataset_phase2_demand_corpus_n39.json"
        with open(path, encoding="utf-8") as f:
            corpus = json.load(f)
        return {d["demand_id"] for d in corpus["demands"]}

    def test_should_cover_exactly_the_frozen_n39_corpus(self) -> None:
        audit = self._load_audit()
        audit_ids = {e["demand_id"] for e in audit["entries"]}
        corpus_ids = self._load_corpus_demand_ids()

        assert len(corpus_ids) == 39
        assert audit_ids == corpus_ids

    def test_should_have_no_duplicate_demand_ids(self) -> None:
        audit = self._load_audit()
        ids = [e["demand_id"] for e in audit["entries"]]
        assert len(ids) == len(set(ids)) == 39

    def test_every_entry_has_a_valid_construct_status(self) -> None:
        audit = self._load_audit()
        for entry in audit["entries"]:
            assert entry["construct_status"] in VALID_STATUSES, entry["demand_id"]

    def test_every_entry_has_a_non_empty_rationale_and_evidence(self) -> None:
        audit = self._load_audit()
        for entry in audit["entries"]:
            assert entry["rationale"].strip(), f"{entry['demand_id']}: empty rationale"
            assert entry["evidence"].strip(), f"{entry['demand_id']}: empty evidence"

    def test_every_rubric_field_is_a_valid_value(self) -> None:
        audit = self._load_audit()
        for entry in audit["entries"]:
            for field in RUBRIC_FIELDS:
                assert entry[field] in VALID_RUBRIC_VALUES, f"{entry['demand_id']}.{field}"

    def test_decision_rule_is_applied_consistently(self) -> None:
        """construct_status must be a pure function of the four rubric fields, per
        the protocol's decision rule (docs/
        phase2-demand-construct-eligibility-audit-protocol.md, 'Decision rule').
        There is no path to any construct_status, including UNCERTAIN, that bypasses
        this rule."""
        audit = self._load_audit()
        for entry in audit["entries"]:
            values = {field: entry[field] for field in RUBRIC_FIELDS}

            if "indeterminate" in values.values():
                expected = "UNCERTAIN"
            elif (
                values["exclusion_criterion_1"] == "yes"
                or values["technical_problem_present"] == "no"
                or values["technology_solution_requested"] == "no"
                or values["technical_specification_present"] == "no"
            ):
                expected = "INELIGIBLE"
            else:
                expected = "ELIGIBLE"

            assert entry["construct_status"] == expected, (
                f"{entry['demand_id']}: rule implies {expected}, got {entry['construct_status']}"
            )

    def test_uncertain_status_always_has_an_indeterminate_field(self) -> None:
        """UNCERTAIN must be traceable to a specific field the text couldn't
        resolve -- never a bare auditor judgment call detached from the rubric."""
        audit = self._load_audit()
        for entry in audit["entries"]:
            if entry["construct_status"] == "UNCERTAIN":
                assert any(entry[f] == "indeterminate" for f in RUBRIC_FIELDS), (
                    f"{entry['demand_id']}: UNCERTAIN but no rubric field is indeterminate"
                )
            else:
                assert all(entry[f] != "indeterminate" for f in RUBRIC_FIELDS), (
                    f"{entry['demand_id']}: has an indeterminate field but status is not UNCERTAIN"
                )

    def test_ineligible_and_uncertain_entries_are_flagged_for_auditor_b(self) -> None:
        audit = self._load_audit()
        for entry in audit["entries"]:
            if entry["construct_status"] in ("INELIGIBLE", "UNCERTAIN"):
                assert entry["needs_auditor_b"] is True, entry["demand_id"]

    def test_audit_status_declares_auditor_b_pending(self) -> None:
        audit = self._load_audit()
        assert audit["status"] == "auditor_a_pass_complete__auditor_b_pending"

    def test_artifact_matches_its_sha256_sidecar(self) -> None:
        root = self._root_path()
        artifact_path = root / "data" / "evaluation" / "phase2_demand_construct_eligibility_n39_v1.json"
        sidecar_path = root / "data" / "evaluation" / "phase2_demand_construct_eligibility_n39_v1.json.sha256"

        content = artifact_path.read_bytes()
        computed = hashlib.sha256(content).hexdigest()
        expected = sidecar_path.read_text(encoding="utf-8").split()[0]
        assert computed == expected

    def test_sector_taxonomy_is_not_referenced_by_the_audit(self) -> None:
        """This audit must be independent of phase2_sector_taxonomy_v1 (#83) --
        sector fit is not eligibility evidence (protocol doc, 'Explicit separation
        from sector fit')."""
        audit = self._load_audit()
        serialized = json.dumps(audit).lower()
        for forbidden in (
            "consumer_chemistry",
            "sanitary_materials",
            "industrial_machinery_iot",
            "energy_storage",
            "metallurgy",
            "biotechnology",
        ):
            assert forbidden not in serialized, f"Audit references taxonomy category: {forbidden}"

    def test_original_n39_corpus_is_unmodified(self) -> None:
        """This audit must not mutate the acquisition artifact it audits (protocol
        doc, 'What this protocol does not do')."""
        root = self._root_path()
        corpus_path = root / "data" / "evaluation" / "dataset_phase2_demand_corpus_n39.json"
        sha_path = root / "data" / "evaluation" / "dataset_phase2_demand_corpus_n39.sha256"

        computed = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
        expected = sha_path.read_text(encoding="utf-8").split()[0]
        assert computed == expected
