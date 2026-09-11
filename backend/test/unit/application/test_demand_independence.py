"""Tests for application.annotation.demand_independence.derive_independence_groups
(ADR 0029). Synthetic fixtures only -- no real demand_id or organization name
from the WPI corpus appears here; that data lives entirely under
experiments/wpi-demand-patent-matching/ and is exercised by that directory's
own check scripts (Task 2)."""

from application.annotation.demand_independence import derive_independence_groups
from domain.models.annotation import DemandIndependenceStatus, DemandOrganizationObservation


def _obs(demand_id: str, org: str | None) -> DemandOrganizationObservation:
    return DemandOrganizationObservation(demand_id=demand_id, requesting_organization=org)


def test_single_demand_with_organization_is_independent():
    entries = derive_independence_groups([_obs("D-1", "Acme Corp")], frozenset())
    assert entries[0].status == DemandIndependenceStatus.INDEPENDENT
    assert entries[0].independence_group_id == "Acme Corp"


def test_two_demands_same_organization_one_independent_one_pseudoreplicate():
    entries = derive_independence_groups(
        [_obs("D-2", "Acme Corp"), _obs("D-1", "Acme Corp")], frozenset()
    )
    by_id = {e.demand_id: e for e in entries}
    assert by_id["D-1"].status == DemandIndependenceStatus.INDEPENDENT
    assert by_id["D-2"].status == DemandIndependenceStatus.PSEUDOREPLICATE
    assert by_id["D-1"].independence_group_id == by_id["D-2"].independence_group_id == "Acme Corp"


def test_three_demands_same_organization_only_lexicographically_first_is_independent():
    entries = derive_independence_groups(
        [_obs("D-3", "Acme Corp"), _obs("D-1", "Acme Corp"), _obs("D-2", "Acme Corp")], frozenset()
    )
    by_id = {e.demand_id: e for e in entries}
    assert by_id["D-1"].status == DemandIndependenceStatus.INDEPENDENT
    assert by_id["D-2"].status == DemandIndependenceStatus.PSEUDOREPLICATE
    assert by_id["D-3"].status == DemandIndependenceStatus.PSEUDOREPLICATE


def test_representative_selection_is_independent_of_input_order():
    entries_order_a = derive_independence_groups(
        [_obs("D-1", "Acme Corp"), _obs("D-2", "Acme Corp")], frozenset()
    )
    entries_order_b = derive_independence_groups(
        [_obs("D-2", "Acme Corp"), _obs("D-1", "Acme Corp")], frozenset()
    )
    statuses_a = {e.demand_id: e.status for e in entries_order_a}
    statuses_b = {e.demand_id: e.status for e in entries_order_b}
    assert statuses_a == statuses_b == {
        "D-1": DemandIndependenceStatus.INDEPENDENT,
        "D-2": DemandIndependenceStatus.PSEUDOREPLICATE,
    }


def test_demand_with_none_organization_is_always_independent_and_ungrouped():
    entries = derive_independence_groups([_obs("D-1", None), _obs("D-2", None)], frozenset())
    for e in entries:
        assert e.status == DemandIndependenceStatus.INDEPENDENT
        assert e.independence_group_id is None


def test_demands_with_shared_non_identifying_value_are_not_grouped_with_each_other():
    entries = derive_independence_groups(
        [_obs("D-1", "Anonymous Organization"), _obs("D-2", "Anonymous Organization")],
        frozenset({"Anonymous Organization"}),
    )
    for e in entries:
        assert e.status == DemandIndependenceStatus.INDEPENDENT
        assert e.independence_group_id is None


def test_near_duplicate_organization_names_are_not_grouped_exact_match_only():
    """ADR 0029: exact string match only, never name-similarity inference. Each
    demand keeps its own organization as its group id (per
    DemandIndependenceGroupEntry's contract: group_id is None only for a
    missing/excluded org) -- the two must NOT share a group id with each
    other, which is what "not grouped" means here."""
    entries = derive_independence_groups(
        [_obs("D-1", "Bax & Company"), _obs("D-2", "Indira from Bax&Co")], frozenset()
    )
    by_id = {e.demand_id: e for e in entries}
    assert by_id["D-1"].status == DemandIndependenceStatus.INDEPENDENT
    assert by_id["D-2"].status == DemandIndependenceStatus.INDEPENDENT
    assert by_id["D-1"].independence_group_id == "Bax & Company"
    assert by_id["D-2"].independence_group_id == "Indira from Bax&Co"
    assert by_id["D-1"].independence_group_id != by_id["D-2"].independence_group_id


def test_output_preserves_input_order():
    observations = [_obs("D-3", "X"), _obs("D-1", "Y"), _obs("D-2", "X")]
    entries = derive_independence_groups(observations, frozenset())
    assert [e.demand_id for e in entries] == ["D-3", "D-1", "D-2"]


def test_real_n24_eligible_corpus_organizations_reproduce_expected_grouping():
    """Regression pin using the WPI corpus's real, already-extracted
    requesting_organization values for the frozen N=24 eligible corpus (from
    dataset_phase2_demand_corpus_n39.origin_audit.json) -- confirms this pure
    function's real-world result before Task 2 freezes it as an artifact.
    18 INDEPENDENT (24 - 4 SMAR3TS pseudoreplicates - 2 Lacer pseudoreplicates),
    6 PSEUDOREPLICATE."""
    real_data = [
        ("INNOGET-1605", "Bax & Company"),
        ("INNOGET-1607", "ALLIANCE project"),
        ("INNOGET-1625", "Anonymous Organization"),
        ("INNOGET-1689", "Celsa Group"),
        ("INNOGET-1726", "Familia Torres"),
        ("INNOGET-1870", "Fundingbox"),
        ("INNOGET-1932", "Anonymous Organization"),
        ("INNOGET-1935", "Anonymous Organization"),
        ("INNOGET-1965", "Blue Room Innovation"),
        ("INNOGET-1972", "Anonymous Organization"),
        ("INNOGET-2006", "Alberto from Pharmactive Biotech Products"),
        ("INNOGET-2173", "Indira from Bax&Co"),
        ("INNOGET-2258", "Repsol"),
        ("INNOGET-2301", "INDUSAC"),
        ("INNOGET-2401", "SMAR3TS"),
        ("INNOGET-2403", "SMAR3TS"),
        ("INNOGET-2404", "SMAR3TS"),
        ("INNOGET-2405", "SMAR3TS"),
        ("INNOGET-2417", "SMAR3TS"),
        ("INNOGET-2491", "Lacer, S.A"),
        ("INNOGET-2492", "Lacer, S.A"),
        ("INNOGET-2493", "Lacer, S.A"),
        ("LOMBARDIA-860", None),
        ("LOMBARDIA-947", None),
    ]
    observations = [_obs(did, org) for did, org in real_data]
    entries = derive_independence_groups(observations, frozenset({"Anonymous Organization"}))
    by_id = {e.demand_id: e for e in entries}

    independent = {did for did, e in by_id.items() if e.status == DemandIndependenceStatus.INDEPENDENT}
    pseudoreplicate = {did for did, e in by_id.items() if e.status == DemandIndependenceStatus.PSEUDOREPLICATE}

    assert pseudoreplicate == {
        "INNOGET-2403", "INNOGET-2404", "INNOGET-2405", "INNOGET-2417",  # SMAR3TS, keep 2401
        "INNOGET-2492", "INNOGET-2493",  # Lacer, S.A, keep 2491
    }
    assert len(independent) == 18
    assert len(pseudoreplicate) == 6
    assert by_id["INNOGET-2401"].status == DemandIndependenceStatus.INDEPENDENT
    assert by_id["INNOGET-2491"].status == DemandIndependenceStatus.INDEPENDENT
    # The 4 "Anonymous Organization" demands and both None-organization demands
    # must all be INDEPENDENT with no group_id, never merged with each other.
    for did in ("INNOGET-1625", "INNOGET-1932", "INNOGET-1935", "INNOGET-1972", "LOMBARDIA-860", "LOMBARDIA-947"):
        assert by_id[did].status == DemandIndependenceStatus.INDEPENDENT
        assert by_id[did].independence_group_id is None
