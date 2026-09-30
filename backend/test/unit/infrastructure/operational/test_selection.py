import json
from pathlib import Path

import pytest

from infrastructure.operational.artifacts import load_operational_artifacts
from infrastructure.operational.selection import parse_selection, read_demo_selection, validate_against_demands

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

    def test_should_reject_when_demo_journeys_is_not_an_object(self):
        with pytest.raises(ValueError, match="demo_journeys"):
            parse_selection(_doc(demo_journeys=[]))

    def test_should_expose_journeys_when_present(self):
        selection = parse_selection(_doc(demo_journeys={"primary": ["D-1"], "secondary": ["D-2"]}))
        assert selection.primary == ("D-1",) and selection.secondary == ("D-2",)

    def test_should_accept_the_shipped_selection_file(self):
        selection = parse_selection(json.loads(SHIPPED.read_text(encoding="utf-8")))
        assert len(selection.included) == 21 and len(selection.primary) == 3


class ValidateAgainstDemandsTest:
    def _selection(self, **groups):
        doc = {"rule": "r", "included": {"D-1": "y"}, "borderline_excluded_by_default": {"D-2": "b"}, "excluded": {"D-3": "e"}}
        doc.update(groups)
        return parse_selection(doc)

    def test_should_pass_when_the_three_groups_cover_every_demand_exactly_once(self):
        validate_against_demands(self._selection(), {"D-1", "D-2", "D-3"})

    def test_should_fail_when_an_excluded_id_is_unknown(self):
        with pytest.raises(ValueError, match="unknown.*DEMAND-DOES-NOT-EXIST"):
            validate_against_demands(self._selection(excluded={"D-3": "e", "DEMAND-DOES-NOT-EXIST": "e"}), {"D-1", "D-2", "D-3"})

    def test_should_fail_when_a_borderline_id_is_unknown(self):
        with pytest.raises(ValueError, match="unknown.*D-9"):
            validate_against_demands(self._selection(borderline_excluded_by_default={"D-2": "b", "D-9": "b"}), {"D-1", "D-2", "D-3"})

    def test_should_fail_when_a_demand_is_in_none_of_the_three_groups(self):
        with pytest.raises(ValueError, match="no group.*D-4"):
            validate_against_demands(self._selection(), {"D-1", "D-2", "D-3", "D-4"})

    def test_should_pass_the_shipped_selection_against_a_repository_with_exactly_its_39_ids(self):
        doc = json.loads(SHIPPED.read_text(encoding="utf-8"))
        ids = set(doc["included"]) | set(doc["borderline_excluded_by_default"]) | set(doc["excluded"])
        assert len(ids) == 39
        validate_against_demands(parse_selection(doc), ids)

    def test_should_fail_the_shipped_selection_when_one_demand_is_removed_from_it(self):
        doc = json.loads(SHIPPED.read_text(encoding="utf-8"))
        ids = set(doc["included"]) | set(doc["borderline_excluded_by_default"]) | set(doc["excluded"])
        del doc["excluded"]["INNOGET-2299"]
        with pytest.raises(ValueError, match="no group.*INNOGET-2299"):
            validate_against_demands(parse_selection(doc), ids)


class ReadDemoSelectionTest:
    @pytest.fixture
    def demands(self, operational_dir):
        return load_operational_artifacts(operational_dir).demands

    def _selection(self, tmp_path, included):
        path = tmp_path / "demo_selection_v1.json"
        rest = {"D-1", "D-2"} - set(included)
        doc = {"rule": "r", "included": {i: "reason" for i in included}, "excluded": {i: "reason" for i in rest}}
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def test_should_return_the_included_demands_when_selection_covers_every_demand(self, demands, tmp_path):
        assert read_demo_selection(self._selection(tmp_path, ["D-2"]), demands) == frozenset({"D-2"})

    def test_should_abort_when_selection_names_a_demand_that_does_not_exist(self, demands, tmp_path):
        with pytest.raises(ValueError, match="D-9"):
            read_demo_selection(self._selection(tmp_path, ["D-9"]), demands)

    def test_should_abort_when_selection_included_is_not_an_object(self, demands, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"rule": "r", "included": ["D-1"]}), encoding="utf-8")
        with pytest.raises(ValueError, match="included"):
            read_demo_selection(path, demands)

    def test_should_abort_when_selection_leaves_a_served_demand_in_no_group(self, demands, tmp_path):
        path = tmp_path / "partial.json"
        path.write_text(json.dumps({"rule": "r", "included": {"D-1": "reason"}}), encoding="utf-8")
        with pytest.raises(ValueError, match="no group.*D-2"):
            read_demo_selection(path, demands)

    def test_should_abort_when_selection_excluded_group_names_an_unknown_demand(self, demands, tmp_path):
        path = tmp_path / "ghost.json"
        doc = {"rule": "r", "included": {"D-1": "r"}, "excluded": {"D-2": "r", "GHOST": "r"}}
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(ValueError, match="unknown.*GHOST"):
            read_demo_selection(path, demands)

    def test_should_abort_when_selection_is_empty(self, demands, tmp_path):
        with pytest.raises(ValueError, match="empty"):
            read_demo_selection(self._selection(tmp_path, []), demands)
