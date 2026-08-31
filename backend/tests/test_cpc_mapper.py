from patent_agent.tools.cpc_mapper import map_cpc_prefix


def test_cpc_mapper_h01m_batteries():
    assert map_cpc_prefix(["solid-state electrolyte for EV batteries", "battery storage"]) == "H01M"


def test_cpc_mapper_c01b_non_metallic():
    assert map_cpc_prefix(["halogenation of inorganic borate compounds", "silicon synthesis"]) == "C01B"


def test_cpc_mapper_b01j_catalysts():
    assert map_cpc_prefix(["heterogeneous catalyst design for chemical reactor"]) == "B01J"


def test_cpc_mapper_a61k_pharma_bio():
    assert map_cpc_prefix(["antibiotic production technology for microbial infection", "cellular biology"]) == "A61K"


def test_cpc_mapper_ambiguous_returns_none():
    assert map_cpc_prefix(["kitchen sink centerpiece marketing campaign", "student challenge"]) is None
    assert map_cpc_prefix(["unclear general requirement"]) is None


def test_cpc_mapper_multiple_matches_returns_none():
    # Contains both battery (H01M) and food (A23L) keywords -> ambiguous, must return None
    assert map_cpc_prefix(["battery storage for frozen food logistics"]) is None

