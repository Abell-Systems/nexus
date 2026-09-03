"""Domain unit tests for hierarchical CPC similarity under ADR 0004 and ADR 0005.

Verifies that CPC symbol similarity functions strictly require injected CPCConcordanceLevels.
"""

import pytest

from domain.models.matching import (
    CPCConcordanceLevels,
    compute_cpc_symbol_similarity,
    compute_max_cpc_similarity,
)


@pytest.fixture
def levels():
    return CPCConcordanceLevels(
        subgroup=1.00,
        main_group=0.75,
        subclass=0.50,
        section=0.25,
        none=0.00,
    )


def test_hierarchical_cpc_similarity_levels(levels):
    # 1. Exact subgroup match -> 1.00
    assert compute_cpc_symbol_similarity("C11D1/02", "C11D1/02", levels=levels) == 1.00
    assert compute_cpc_symbol_similarity("C11D1/00", "C11D1/00", levels=levels) == 1.00

    # 2. Same main group, different subgroup -> 0.75
    assert compute_cpc_symbol_similarity("C11D1/02", "C11D1/66", levels=levels) == 0.75
    assert compute_cpc_symbol_similarity("C11D1", "C11D1/02", levels=levels) == 0.75

    # 3. Same subclass, different main group -> 0.50
    assert compute_cpc_symbol_similarity("C11D1/02", "C11D3/386", levels=levels) == 0.50
    assert compute_cpc_symbol_similarity("C11D", "C11D3/00", levels=levels) == 0.50

    # 4. Same section, different class/subclass -> 0.25
    assert compute_cpc_symbol_similarity("C11D1/02", "C22C1/00", levels=levels) == 0.25
    assert compute_cpc_symbol_similarity("C11D", "C08L1/00", levels=levels) == 0.25

    # 5. Different section -> 0.00
    assert compute_cpc_symbol_similarity("C11D1/02", "H01M10/0525", levels=levels) == 0.00
    assert compute_cpc_symbol_similarity("C11D", "E03C1/00", levels=levels) == 0.00


def test_compute_max_cpc_similarity_multi_symbols(levels):
    demand_cpcs = ["C11D1/00", "B01F17/00"]
    patent_cpcs = ["H01M4/00", "C11D3/386", "A47K1/00"]

    # Best match between demand and patent is C11D1/00 vs C11D3/386 (same subclass C11D) -> 0.50
    assert compute_max_cpc_similarity(demand_cpcs, patent_cpcs, levels=levels) == 0.50

    # No overlap
    assert compute_max_cpc_similarity(["C11D1/00"], ["H01M4/00"], levels=levels) == 0.00

    # Empty inputs
    assert compute_max_cpc_similarity([], ["C11D1/00"], levels=levels) == 0.00
    assert compute_max_cpc_similarity(["C11D1/00"], [], levels=levels) == 0.00
