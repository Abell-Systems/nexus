from domain.models.demand import SpanishOriginLevel
from domain.models.evaluation import DemandCorpusItem, EvaluationProvenance
from application.matching.demand_corpus_adapter import demand_corpus_item_to_demand_record


def _corpus_item(**overrides) -> DemandCorpusItem:
    defaults = dict(
        demand_id="INNOGET-1605",
        title="Seeking lightweight innovators",
        description="Do you have a specific idea on how to design lighter vehicles?",
        posted_date=None,
        target_cpc_prefixes=["B60"],
        origin_country="Spain",
        spanish_origin_level=SpanishOriginLevel.LEVEL_1_DIRECT_METADATA,
        external_reference=None,
        provenance=EvaluationProvenance(
            source_authority="innoget",
            source_uri="https://www.innoget.com/technology-calls/1605/example",
            extraction_timestamp="2026-09-07T15:59:43.773584Z",
            raw_payload_sha256="a" * 64,
            modality="observed",
        ),
    )
    defaults.update(overrides)
    return DemandCorpusItem(**defaults)


class DemandCorpusAdapterTest:
    def test_should_map_core_fields(self):
        record = demand_corpus_item_to_demand_record(_corpus_item())
        assert record.demand_id == "INNOGET-1605"
        assert record.title == "Seeking lightweight innovators"
        assert record.description.startswith("Do you have a specific idea")
        assert record.url == "https://www.innoget.com/technology-calls/1605/example"

    def test_should_mark_is_spanish_demand_true_always(self):
        record = demand_corpus_item_to_demand_record(_corpus_item())
        assert record.is_spanish_demand is True

    def test_should_take_first_cpc_prefix(self):
        record = demand_corpus_item_to_demand_record(_corpus_item(target_cpc_prefixes=["B60", "C11"]))
        assert record.cpc_prefix == "B60"

    def test_should_leave_cpc_prefix_none_when_no_prefixes(self):
        record = demand_corpus_item_to_demand_record(_corpus_item(target_cpc_prefixes=[]))
        assert record.cpc_prefix is None

    def test_should_pass_through_null_posted_date(self):
        record = demand_corpus_item_to_demand_record(_corpus_item(posted_date=None))
        assert record.posted_date is None
