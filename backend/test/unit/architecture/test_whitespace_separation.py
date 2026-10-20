"""White-space analysis and offer-demand matching stay independent in both directions (ADR 0036, audit §8)."""

import configparser
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
WHITESPACE = {
    "domain.models.whitespace",
    "domain.protocols.whitespace",
    "application.whitespace",
    "infrastructure.sources.patent.oepm_biblio",
}
MATCHING = {
    "domain.models.matching",
    "domain.models.demand",
    "domain.models.evaluation",
    "domain.protocols.matching",
    "domain.protocols.evaluation",
    "application.matching",
    "application.evaluation",
    "infrastructure.matching",
    "infrastructure.operational",
}


def _contract(name: str) -> tuple[set[str], set[str], str]:
    config = configparser.ConfigParser()
    config.read(REPO / ".importlinter")
    section = f"importlinter:contract:{name}"
    return (
        set(config.get(section, "source_modules").split()),
        set(config.get(section, "forbidden_modules").split()),
        config.get(section, "type"),
    )


def test_shouldForbidWhitespaceFromImportingMatchingWhenReadingTheImportContract():
    sources, forbidden, kind = _contract("whitespace-independent-of-matching")

    assert (kind, sources, forbidden) == ("forbidden", WHITESPACE, MATCHING)


def test_shouldForbidMatchingFromImportingWhitespaceWhenReadingTheImportContract():
    sources, forbidden, kind = _contract("matching-independent-of-whitespace")

    assert (kind, sources, forbidden) == ("forbidden", MATCHING, WHITESPACE)
