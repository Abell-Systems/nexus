"""End-to-end fixture test for scripts/freeze_patent_corpus.py's build_patent_corpus(),
now driven by the partition tree (PR-E0.1) instead of a single CQL query.

No live EPO OPS credentials required -- runs entirely against the multi-jurisdiction
fixture from PR #57's Task 5.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from freeze_patent_corpus import build_patent_corpus, main  # noqa: E402

from application.evaluation.patent_corpus_builder import PatentCorpusConstructionError  # noqa: E402
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient  # noqa: E402
from infrastructure.sources.patent.ops_partitioning import NonEnumerablePartitionError  # noqa: E402

FIXTURE = REPO_ROOT / "backend" / "test" / "fixtures" / "epo_ops_multi_jurisdiction_sample.xml"
JURISDICTIONS = ["EP", "US", "JP", "CN", "KR", "WO"]


def test_build_patent_corpus_from_fixture_succeeds_below_target():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    result = build_patent_corpus(
        client=client,
        jurisdictions=JURISDICTIONS,
        window_start=date(2016, 1, 1),
        window_end=date(2026, 12, 31),
        ceiling=2000,
        target_n=50000,
        minimum_acceptable_n=1,
        dataset_id="nexus-patent-corpus-p-test",
        dataset_version="0.0.1-test",
        description="test run over fixture, partitioned",
    )

    # Fixture has 6 docs; CN (kind=B) and WO (kind=A1) are excluded by grants-only filter.
    assert len(result.corpus.patents) == 4
    assert {p.country_code for p in result.corpus.patents} == {"EP", "US", "JP", "KR"}
    assert result.leaf_count == 6  # one jurisdiction-level leaf each, no subdivision needed


def test_build_patent_corpus_raises_below_floor():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    with pytest.raises(PatentCorpusConstructionError):
        build_patent_corpus(
            client=client,
            jurisdictions=["EP"],
            window_start=date(2016, 1, 1),
            window_end=date(2026, 12, 31),
            ceiling=2000,
            target_n=50000,
            minimum_acceptable_n=1000,  # far above the 4 grants the fixture yields
            dataset_id="nexus-patent-corpus-p-test",
            dataset_version="0.0.1-test",
            description="test run over fixture, partitioned",
        )


def test_build_patent_corpus_produces_no_output_on_non_enumerable_partition(tmp_path, monkeypatch):
    """Fail-closed, end-to-end (PR-E0.1 contract §5.4): if a single partition ends up
    NON_ENUMERABLE, main() must write NO dataset file, NO manifest, NO sha256 sidecar --
    not a partial PatentCorpus."""
    import freeze_patent_corpus as script

    class _AlwaysHugeClient:
        """Every peek reports a total-result-count far above any ceiling, at every
        partition level -- forces NON_ENUMERABLE once month-level is reached."""

        def fetch_batches(self, cql_query="", range_start=1, range_end=25):
            from domain.protocols.sources import RawPayload

            xml = (
                b'<?xml version="1.0"?><ops:world-patent-data xmlns:ops="http://ops.epo.org">'
                b'<ops:biblio-search total-result-count="999999999"/></ops:world-patent-data>'
            )
            yield RawPayload(source_id="epo_ops", batch_id="huge", payload_bytes=xml, metadata={})

    monkeypatch.setattr(script, "EpoOpsClient", lambda: _AlwaysHugeClient())
    monkeypatch.setattr(script, "OUT_DIR", tmp_path)

    with pytest.raises(NonEnumerablePartitionError):
        main()

    assert list(tmp_path.iterdir()) == []
