from types import SimpleNamespace

from domain.models.patent import PatentDocument


def _p(country, title, abstract):
    return SimpleNamespace(patent=PatentDocument(publication_id=f"{country}-{title}", country_code=country, doc_number="1", kind_code="A1",
                                                 title=title, abstract=abstract))


def assets_for_policy():
    return [_p("ES", "t", "a"), _p("EP", "t", "a"), _p("ES", "", "a"), _p("ES", "u", "b")]
