"""Conformance tests for the WIPO IPC8 Technology Concordance freeze (#104 follow-on).

Verifies config/policies/data/wipo_ipc8_technology_concordance_v1.json against its own
sha256 sidecar, against the frozen source PDF's sha256, and against the freeze doc's
sha256 -- all three pinned inside the register's own provenance block, per
docs/phase2-wipo-ipc-technology-concordance-freeze.md. Does not validate any
application of the register to the corpus -- none exists yet (SS3 of that document).
"""

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTER_PATH = REPO_ROOT / "config/policies/data/wipo_ipc8_technology_concordance_v1.json"
REGISTER_SHA_PATH = REPO_ROOT / "config/policies/data/wipo_ipc8_technology_concordance_v1.sha256"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_register() -> dict:
    return json.loads(REGISTER_PATH.read_text(encoding="utf-8"))


def test_register_bytes_match_its_own_sha256_sidecar():
    declared_sha, declared_name = REGISTER_SHA_PATH.read_text(encoding="utf-8").strip().split(maxsplit=1)
    assert declared_sha == _sha256(REGISTER_PATH)
    assert declared_name == REGISTER_PATH.name


def test_source_pdf_matches_its_pinned_sha256():
    register = _load_register()
    pdf_path = REPO_ROOT / register["provenance"]["source_pdf_path"]
    assert pdf_path.is_file(), f"Frozen source PDF missing: {pdf_path}"
    assert _sha256(pdf_path) == register["provenance"]["source_pdf_sha256"]


def test_freeze_doc_matches_its_pinned_sha256():
    register = _load_register()
    doc_path = REPO_ROOT / register["provenance"]["freeze_doc_path"]
    assert doc_path.is_file(), f"Freeze doc missing: {doc_path}"
    assert _sha256(doc_path) == register["provenance"]["freeze_doc_sha256"]


def test_exactly_35_fields_numbered_1_through_35_no_gaps_no_duplicates():
    register = _load_register()
    numbers = sorted(f["field_number"] for f in register["fields"])
    assert numbers == list(range(1, 36))


def test_exactly_5_sectors_covering_all_35_fields_disjointly():
    register = _load_register()
    seen: set[int] = set()
    for sector in register["sectors"]:
        overlap = seen & set(sector["field_numbers"])
        assert not overlap, f"Field(s) {overlap} assigned to more than one sector"
        seen |= set(sector["field_numbers"])
    assert seen == set(range(1, 36))
    assert len(register["sectors"]) == 5


def test_every_field_belongs_to_the_sector_that_lists_it():
    register = _load_register()
    sector_of_field = {}
    for sector in register["sectors"]:
        for n in sector["field_numbers"]:
            sector_of_field[n] = sector["code"]
    for field in register["fields"]:
        assert field["sector"] == sector_of_field[field["field_number"]], (
            f"Field {field['field_number']} ({field['label']}) declares sector "
            f"{field['sector']} but sectors block assigns it to {sector_of_field[field['field_number']]}"
        )


def test_every_field_has_a_non_empty_include_list():
    register = _load_register()
    for field in register["fields"]:
        assert field["include"], f"Field {field['field_number']} ({field['label']}) has no IPC codes"


def test_exclude_entries_match_the_two_patterns_the_source_text_documents():
    """The source PDF (p.13) documents exactly two kinds of 'not' clause:

    (a) Sub-code exclusion within the field's own include family -- e.g. field 16
        'A61K not A61K-008' (A61K-008 IS a sub-group of A61K), field 10 'G01N not
        G01N-033', field 6 '(G06# not G06Q)'. Here the exclude code must be a
        refinement of something the field itself includes.

    (b) Cross-classification exclusion -- e.g. field 14 excludes 'A61K',
        'A61K-008', 'A61Q' to drop documents co-classified in pharmaceuticals
        (p.13: "all documents with co-classification in A61K were excluded"),
        field 15 excludes 'A61K' for the same reason (p.13: "applications with
        explicit co-classification in A61K are excluded"). Here the exclude
        code is deliberately NOT in the field's own include list -- it names a
        different field's code entirely.

    Fields 6, 10, 16, 24 use pattern (a); fields 14, 15 use pattern (b). Every
    exclude entry in the register must fall into one of these two documented
    patterns -- an exclude that fits neither would be an untranscribed error.
    """
    register = _load_register()
    cross_classification_excludes = {14, 15}
    for field in register["fields"]:
        for excl in field["exclude"]:
            if field["field_number"] in cross_classification_excludes:
                continue  # pattern (b): deliberately not in this field's own include list
            base = excl.split("-")[0].rstrip("#")
            covered = any(
                excl == inc or base == inc.rstrip("#") or excl.startswith(inc.rstrip("#"))
                for inc in field["include"]
            )
            assert covered, (
                f"Field {field['field_number']} ({field['label']}) excludes '{excl}' "
                "which no include entry in the same field actually covers (pattern (a) violated)"
            )


def test_no_ipc_code_literally_repeated_as_an_include_entry_across_two_fields():
    """Schmoch's own requirement 5 (source PDF p.4): field contents must be
    distinct. A literal duplicate top-level include code across two fields would
    indicate a transcription slip, not an intentional design choice -- legitimate
    overlap is expressed via a narrower include in one field plus an exclude in
    the broader one (e.g. field 10 includes G01N, excludes G01N-033; field 11
    includes G01N-033), never by the same code appearing verbatim in two
    'include' lists."""
    register = _load_register()
    owner: dict[str, int] = {}
    for field in register["fields"]:
        for code in field["include"]:
            assert code not in owner, (
                f"IPC code '{code}' appears in both field {owner[code]} and "
                f"field {field['field_number']} ({field['label']})'s include list"
            )
            owner[code] = field["field_number"]


def test_note_on_technological_complexity_is_present_and_marks_it_unacquired():
    register = _load_register()
    note = register["provenance"]["note_on_related_but_distinct_artifact"]
    assert "technological_complexity" in note
    assert "SEPARATE" in note
