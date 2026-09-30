import json
from pathlib import Path

import pytest

from infrastructure.operational.selection import parse_selection

SHIPPED = Path(__file__).resolve().parents[5] / "backend" / "src" / "main" / "infrastructure" / "operational" / "demo_selection_v1.json"


def _doc(**overrides):
    doc = {"rule": "r", "included": {"D-1": "why", "D-2": "why"}}
    doc.update(overrides)
    return doc


class ParseSelectionTest:
    def test_should_return_included_ids_when_document_is_well_formed(self):
        assert parse_selection(_doc()).included == frozenset({"D-1", "D-2"})

    def test_should_reject_when_document_is_not_an_object(self):
        with pytest.raises(ValueError, match="object"):
            parse_selection(["D-1"])

    def test_should_reject_when_included_is_a_list_instead_of_an_id_to_reason_object(self):
        with pytest.raises(ValueError, match="included"):
            parse_selection(_doc(included=["D-1", "D-2"]))

    def test_should_reject_when_included_is_empty(self):
        with pytest.raises(ValueError, match="empty"):
            parse_selection(_doc(included={}))

    def test_should_reject_when_a_reason_is_not_a_string(self):
        with pytest.raises(ValueError, match="reason"):
            parse_selection(_doc(included={"D-1": 3}))

    def test_should_reject_when_a_reason_is_blank(self):
        with pytest.raises(ValueError, match="reason"):
            parse_selection(_doc(included={"D-1": "   "}))

    def test_should_reject_when_the_rule_is_missing_or_blank(self):
        with pytest.raises(ValueError, match="rule"):
            parse_selection(_doc(rule=" "))

    def test_should_reject_when_a_demand_is_in_two_groups(self):
        with pytest.raises(ValueError, match="more than one group"):
            parse_selection(_doc(excluded={"D-1": "no"}))

    def test_should_reject_when_an_excluded_group_is_malformed(self):
        with pytest.raises(ValueError, match="excluded"):
            parse_selection(_doc(excluded=["D-3"]))

    def test_should_reject_when_a_journey_is_not_an_included_demand(self):
        with pytest.raises(ValueError, match="journey"):
            parse_selection(_doc(demo_journeys={"primary": ["D-9"], "secondary": []}))

    def test_should_expose_journeys_when_present(self):
        selection = parse_selection(_doc(demo_journeys={"primary": ["D-1"], "secondary": ["D-2"]}))
        assert selection.primary == ("D-1",) and selection.secondary == ("D-2",)

    def test_should_accept_the_shipped_selection_file(self):
        selection = parse_selection(json.loads(SHIPPED.read_text(encoding="utf-8")))
        assert len(selection.included) == 21 and len(selection.primary) == 3
