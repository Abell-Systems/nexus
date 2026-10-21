import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _script():
    spec = importlib.util.spec_from_file_location(
        "audit_oepm_authority_file", REPO_ROOT / "scripts" / "audit_oepm_authority_file.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entry(kind: str, date: str, exception: str = "", number: str = "1") -> str:
    code = f"<afp:ExceptionCode>{exception}</afp:ExceptionCode>" if exception else ""
    return (
        "<afp:AuthorityFileEntry><pat:PatentPublicationIdentification><com:IPOfficeCode>ES</com:IPOfficeCode>"
        f"<pat:PublicationNumber>{number}</pat:PublicationNumber><com:PatentDocumentKindCode>{kind}</com:PatentDocumentKindCode>\n"
        f"<com:PublicationDate>{date}</com:PublicationDate></pat:PatentPublicationIdentification>{code}"
        "</afp:AuthorityFileEntry>"
    )


def test_shouldCountEntriesByPublicationYearAndGroupWhenReadingAnAuthorityFile():
    xml = _entry("T3", "20100105") + _entry("T3", "20101231") + _entry("B1", "20100301", "X") + _entry("A1", "20110101")
    by_year, exceptions = _script().count_entries(xml)
    assert by_year == {(2010, "ep_translation"): 2, (2010, "national"): 1, (2011, "national"): 1}
    assert exceptions == {"-": 3, "X": 1}


def test_shouldIgnoreAnEntryWithoutAPublicationDateWhenCounting():
    by_year, _ = _script().count_entries("<afp:AuthorityFileEntry><x/></afp:AuthorityFileEntry>")
    assert not by_year


def test_shouldMatchPublicationsOneByOneWhenComparingWithTheCorpus():
    script = _script()
    authority = script.publication_keys(
        _entry("B1", "20100301", "X", "10")
        + _entry("B1", "20100302", number="11")
        + _entry("A1", "20110101", number="12")
    )
    corpus = {("11", "B1", "20100302"), ("99", "B1", "20110105")}
    match = script.match_corpus(authority, corpus)
    assert match["by_year"] == {2010: {"only_authority": 1, "both": 1}, 2011: {"only_authority": 1, "only_corpus": 1}}
    assert match["missing_by_exception_2000_2025"] == {"X": 1, "-": 1}
