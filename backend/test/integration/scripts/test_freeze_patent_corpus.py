"""End-to-end fixture test for scripts/freeze_patent_corpus.py's build_patent_corpus().

No live EPO OPS credentials required (ADR 0020 §6) -- runs entirely against the
multi-jurisdiction fixture from Task 5.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src" / "main"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from freeze_patent_corpus import build_patent_corpus  # noqa: E402

from application.evaluation.patent_corpus_builder import PatentCorpusConstructionError  # noqa: E402
from infrastructure.sources.patent.epo_ops_client import EpoOpsClient  # noqa: E402

FIXTURE = REPO_ROOT / "backend" / "test" / "fixtures" / "epo_ops_multi_jurisdiction_sample.xml"


def test_build_patent_corpus_from_fixture_succeeds_below_target():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    corpus = build_patent_corpus(
        client=client,
        cql_query="(pn=EP or pn=US or pn=JP or pn=CN or pn=KR or pn=WO) and pd within \"20160101 20261231\"",
        target_n=50000,
        minimum_acceptable_n=1,
        dataset_id="nexus-patent-corpus-p-test",
        dataset_version="0.0.1-test",
        description="test run over fixture",
    )

    # Fixture has 6 docs; CN (kind=B) and WO (kind=A1) are excluded by grants-only filter.
    assert len(corpus.patents) == 4
    assert {p.country_code for p in corpus.patents} == {"EP", "US", "JP", "KR"}


def test_build_patent_corpus_raises_below_floor():
    client = EpoOpsClient.from_fixture_file(FIXTURE)
    with pytest.raises(PatentCorpusConstructionError):
        build_patent_corpus(
            client=client,
            cql_query="(pn=EP) and pd within \"20160101 20261231\"",
            target_n=50000,
            minimum_acceptable_n=1000,  # far above the 4 grants the fixture yields
            dataset_id="nexus-patent-corpus-p-test",
            dataset_version="0.0.1-test",
            description="test run over fixture",
        )
