"""The transcribed contract (config) must say what the published characterization says."""

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[6]
CONTRACT = json.loads((REPO / "config/whitespace/oepm_biblio_2000_2025.json").read_text(encoding="utf-8"))
DOCUMENT = (REPO / "docs/whitespace/oepm-biblio-corpus-characterization.md").read_text(encoding="utf-8")


def test_shouldListTheSameFilesHashesAndSizesAsThePublishedTableWhenComparingContractAndDocument():
    published = {
        name: {"sha256": digest, "bytes": int(size.replace(",", ""))}
        for name, size, digest in re.findall(
            r"^\| `(BIBLIO_\d{4}\.zip)` \| ([\d,]+) \| `([0-9a-f]{64})` \|", DOCUMENT, re.M
        )
    }

    assert len(published) == 26
    assert CONTRACT["files"] == published


def test_shouldAddUpToTheTotalRecordsWhenSummingFilesAndYears():
    figures = CONTRACT["figures"]

    assert sum(f["records"] for f in figures["by_file"].values()) == figures["records"]
    assert sum(y["records"] for y in figures["by_publication_year"].values()) == figures["records"]
    assert sum(figures["kind_groups"].values()) == figures["records"]
    assert sum(f["rejected"] for f in figures["by_file"].values()) == figures["rejected"]


def test_shouldMarkTheYearWithoutRecordsAsMissingWhenPublishingTheGap():
    figures = CONTRACT["figures"]

    assert figures["years_without_records"] == [2010]
    assert "2010" not in figures["by_publication_year"]
