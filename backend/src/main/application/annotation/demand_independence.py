"""Pure demand-independence grouping decision (ADR 0029)."""

from domain.models.annotation import (
    DemandIndependenceGroupEntry,
    DemandIndependenceStatus,
    DemandOrganizationObservation,
)


def derive_independence_groups(
    observations: list[DemandOrganizationObservation],
    non_identifying_values: frozenset[str],
) -> list[DemandIndependenceGroupEntry]:
    """ADR 0029's independence-grouping decision rule, as a pure function of the
    observed organization identities. This is the only place the rule is
    implemented -- any independence audit derives its groupings here rather
    than recording them as an independent, unverified judgment.

    Two demands are grouped together (one INDEPENDENT, the rest
    PSEUDOREPLICATE) iff their `requesting_organization` values are identical,
    non-None, and not listed in `non_identifying_values` -- exact string match
    only, never inferred from name/text similarity. `non_identifying_values` is
    supplied by the caller (an experiment-specific, documented, literal
    exclusion list of known placeholder values from the source data, e.g.
    "Anonymous Organization") -- this function never hardcodes such values
    itself, since what counts as a non-identifying placeholder is a property of
    a specific data source, not of this decision rule.

    Within a group, the lexicographically smallest `demand_id` is marked
    INDEPENDENT and every other member PSEUDOREPLICATE -- a deterministic,
    arbitrary tie-break (mirrors ADR 0027 §2's `collapse` representative
    selection), not a claim that the selected demand is scientifically more
    representative than its group-mates.

    A demand whose `requesting_organization` is None or in
    `non_identifying_values` always receives `independence_group_id=None` and
    `status=INDEPENDENT`, and is never grouped with any other such demand.

    Returns entries in the same order as `observations`.
    """
    groups: dict[str, list[DemandOrganizationObservation]] = {}
    ungrouped: list[DemandOrganizationObservation] = []

    for obs in observations:
        org = obs.requesting_organization
        if org is None or org in non_identifying_values:
            ungrouped.append(obs)
        else:
            groups.setdefault(org, []).append(obs)

    entries_by_id: dict[str, DemandIndependenceGroupEntry] = {}

    for obs in ungrouped:
        entries_by_id[obs.demand_id] = DemandIndependenceGroupEntry(
            demand_id=obs.demand_id,
            requesting_organization=obs.requesting_organization,
            independence_group_id=None,
            status=DemandIndependenceStatus.INDEPENDENT,
        )

    for org, members in groups.items():
        members_sorted = sorted(members, key=lambda o: o.demand_id)
        for idx, obs in enumerate(members_sorted):
            status = (
                DemandIndependenceStatus.INDEPENDENT
                if idx == 0
                else DemandIndependenceStatus.PSEUDOREPLICATE
            )
            entries_by_id[obs.demand_id] = DemandIndependenceGroupEntry(
                demand_id=obs.demand_id,
                requesting_organization=org,
                independence_group_id=org,
                status=status,
            )

    return [entries_by_id[obs.demand_id] for obs in observations]
