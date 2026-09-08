from domain.models.demand import DemandRecord
from domain.models.evaluation import DemandCorpusItem


def demand_corpus_item_to_demand_record(item: DemandCorpusItem) -> DemandRecord:
    """Maps a frozen Phase-2 DemandCorpusItem to the live-matching DemandRecord type.

    DemandCorpusItem's eligibility criterion is Spanish origin (that's what makes
    it a member of the corpus), so is_spanish_demand is always True here — it is
    not re-derived from spanish_origin_level.
    """
    posted_date = item.posted_date.isoformat() if item.posted_date else None
    return DemandRecord(
        demand_id=item.demand_id,
        title=item.title,
        description=item.description,
        origin_country=item.origin_country,
        spanish_origin_level=item.spanish_origin_level,
        is_spanish_demand=True,
        cpc_prefix=item.target_cpc_prefixes[0] if item.target_cpc_prefixes else None,
        posted_date=posted_date,
        url=item.provenance.source_uri,
    )
