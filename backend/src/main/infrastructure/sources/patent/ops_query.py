"""EPO OPS CQL query construction for PatentCorpus's jurisdiction+grant+window inclusion
contract (ADR 0020 §2). Pure and deterministic -- given the same arguments, always
produces the same query string, independent of any demand-side information."""


def build_patent_corpus_cql(
    jurisdictions: list[str],
    min_publication_year: int,
    max_publication_year: int,
) -> str:
    """Build a CQL query for EPO OPS `published-data/search/biblio` scoped to the given
    jurisdictions and publication-year window. Grant-vs-application filtering is NOT
    encoded here -- OPS's CQL kind-code filtering is unreliable across offices, so
    grants-only is enforced downstream by the normalizer (see oepm_xml_normalizer.py's
    `allowed_kind_codes`), not by this query.
    """
    if not jurisdictions:
        raise ValueError("jurisdictions must be a non-empty list")
    if min_publication_year > max_publication_year:
        raise ValueError(
            f"min_publication_year ({min_publication_year}) must be <= "
            f"max_publication_year ({max_publication_year})"
        )

    jurisdiction_clause = " or ".join(f"pn={j.upper()}" for j in jurisdictions)
    window_clause = f'pd within "{min_publication_year}0101 {max_publication_year}1231"'
    return f"({jurisdiction_clause}) and {window_clause}"
