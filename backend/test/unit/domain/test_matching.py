import pytest
from pydantic import ValidationError

from domain.models.matching import (
    Candidate,
    CandidatePool,
    EligibilityReason,
    EligibilityResult,
    RankedCandidate,
    RankerWeights,
    RetrievalMethod,
)


def test_candidate_valid_and_provenance():
    cand = Candidate(
        publication_id="ES-2849102-B2",
        retrieval_scores={RetrievalMethod.LEXICAL: 12.5, RetrievalMethod.SEMANTIC: 0.85},
    )
    assert cand.publication_id == "ES-2849102-B2"
    assert cand.retrieval_scores[RetrievalMethod.LEXICAL] == 12.5
    assert cand.retrieval_scores[RetrievalMethod.SEMANTIC] == 0.85


def test_candidate_rejects_empty_id_or_negative_score():
    with pytest.raises(ValidationError):
        Candidate(publication_id="", retrieval_scores={RetrievalMethod.LEXICAL: 1.0})

    with pytest.raises(ValidationError):
        Candidate(publication_id="ES-2849102-B2", retrieval_scores={RetrievalMethod.LEXICAL: -0.5})


def test_candidate_pool_deduplication_and_provenance_preservation():
    cand_lex_1 = Candidate(publication_id="ES-1", retrieval_scores={RetrievalMethod.LEXICAL: 10.0})
    cand_lex_2 = Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.LEXICAL: 8.0})

    cand_sem_2 = Candidate(publication_id="ES-2", retrieval_scores={RetrievalMethod.SEMANTIC: 0.90})
    cand_sem_3 = Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.SEMANTIC: 0.75})

    cand_cpc_3 = Candidate(publication_id="ES-3", retrieval_scores={RetrievalMethod.CPC: 1.0})
    cand_cpc_4 = Candidate(publication_id="ES-4", retrieval_scores={RetrievalMethod.CPC: 0.50})

    pool = CandidatePool.from_retrievals(
        demand_id="INNOGET-2292",
        lexical_candidates=[cand_lex_1, cand_lex_2],
        semantic_candidates=[cand_sem_2, cand_sem_3],
        cpc_candidates=[cand_cpc_3, cand_cpc_4],
    )

    assert pool.demand_id == "INNOGET-2292"
    assert len(pool.candidates) == 4
    # Check deterministic sorted order by publication_id
    assert [c.publication_id for c in pool.candidates] == ["ES-1", "ES-2", "ES-3", "ES-4"]

    # Check provenance merge
    es_2 = next(c for c in pool.candidates if c.publication_id == "ES-2")
    assert es_2.retrieval_scores[RetrievalMethod.LEXICAL] == 8.0
    assert es_2.retrieval_scores[RetrievalMethod.SEMANTIC] == 0.90
    assert RetrievalMethod.CPC not in es_2.retrieval_scores

    es_3 = next(c for c in pool.candidates if c.publication_id == "ES-3")
    assert es_3.retrieval_scores[RetrievalMethod.SEMANTIC] == 0.75
    assert es_3.retrieval_scores[RetrievalMethod.CPC] == 1.0


def test_candidate_pool_rejects_duplicate_candidates_in_direct_init():
    with pytest.raises(ValidationError):
        CandidatePool(
            demand_id="D-1",
            candidates=[
                Candidate(publication_id="ES-1"),
                Candidate(publication_id="ES-1"),
            ],
        )


def test_candidate_pool_rejects_more_than_300():
    candidates = [Candidate(publication_id=f"ES-{i}") for i in range(301)]
    with pytest.raises(ValidationError):
        CandidatePool(demand_id="D-1", candidates=candidates)


def test_ranker_weights_validation_exact_sum():
    # Valid weights summing exactly to 1.0
    w = RankerWeights(alpha=0.35, beta=0.45, gamma=0.20)
    assert w.alpha == 0.35
    assert w.beta == 0.45
    assert w.gamma == 0.20

    # Negative weight
    with pytest.raises(ValidationError):
        RankerWeights(alpha=-0.1, beta=0.6, gamma=0.5)

    # Sum != 1.0
    with pytest.raises(ValidationError):
        RankerWeights(alpha=0.5, beta=0.5, gamma=0.5)

    with pytest.raises(ValidationError):
        RankerWeights(alpha=0.2, beta=0.2, gamma=0.2)


def test_ranked_candidate_validation():
    rc = RankedCandidate(publication_id="ES-1", rank=1, score=0.95, components={"lexical": 0.8})
    assert rc.rank == 1
    assert rc.score == 0.95

    with pytest.raises(ValidationError):
        RankedCandidate(publication_id="ES-1", rank=0, score=0.95)


def test_eligibility_result_creation():
    res = EligibilityResult(
        publication_id="ES-1",
        is_eligible=False,
        reason=EligibilityReason.EXCLUDED_TEMPORAL,
        details="Published after demand solicitation date",
    )
    assert not res.is_eligible
    assert res.reason == EligibilityReason.EXCLUDED_TEMPORAL


def test_hierarchical_cpc_similarity_levels():
    from domain.models.matching import CPCConcordanceLevels, compute_cpc_symbol_similarity

    levels = CPCConcordanceLevels(
        subgroup=1.00,
        main_group=0.75,
        subclass=0.50,
        section=0.25,
        none=0.00,
    )

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


def test_compute_max_cpc_similarity_multi_symbols():
    from domain.models.matching import CPCConcordanceLevels, compute_max_cpc_similarity

    levels = CPCConcordanceLevels(
        subgroup=1.00,
        main_group=0.75,
        subclass=0.50,
        section=0.25,
        none=0.00,
    )

    demand_cpcs = ["C11D1/00", "B01F17/00"]
    patent_cpcs = ["H01M4/00", "C11D3/386", "A47K1/00"]

    # Best match between demand and patent is C11D1/00 vs C11D3/386 (same subclass C11D) -> 0.50
    assert compute_max_cpc_similarity(demand_cpcs, patent_cpcs, levels=levels) == 0.50

    # No overlap
    assert compute_max_cpc_similarity(["C11D1/00"], ["H01M4/00"], levels=levels) == 0.00

    # Empty inputs
    assert compute_max_cpc_similarity([], ["C11D1/00"], levels=levels) == 0.00
    assert compute_max_cpc_similarity(["C11D1/00"], [], levels=levels) == 0.00


class BM25ScoringTest:
    """Guards for compute_bm25_scores (ADR 0013 derived_ranking_feature)."""

    def test_should_compute_deterministic_scores_when_called_twice_with_same_input(self):
        from domain.models.matching import compute_bm25_scores

        query = "biodegradable surfactant for low-temperature washing"
        documents = {
            "EP-1": "Detergent composition with biodegradable surfactant for cold water washing",
            "EP-2": "Metallurgical alloy for high-strength steel fasteners",
            "EP-3": "Encapsulated fragrance for laundry detergent",
        }

        first = compute_bm25_scores(query, documents)
        second = compute_bm25_scores(query, documents)

        assert first == second
        assert set(first.keys()) == set(documents.keys()), (
            "Every input publication_id must be present in the result, regardless of score."
        )
        assert first["EP-1"] > first["EP-2"], (
            "The document with real term overlap must outscore the document with none."
        )
        assert first["EP-2"] == 0.0, "No term overlap must score exactly 0.0, not be omitted."

    def test_should_not_depend_on_annotations_when_scoring(self):
        import inspect

        from domain.models.matching import compute_bm25_scores

        params = set(inspect.signature(compute_bm25_scores).parameters)
        assert "annotations" not in params
        assert "relevance_grade" not in params
        assert "grade" not in params
        assert params == {"query_text", "documents", "k1", "b"}, (
            "compute_bm25_scores must take only observed query/document text and scoring "
            "parameters — no parameter through which ground truth could reach it."
        )

    def test_should_match_independently_derived_okapi_bm25_values_when_scoring_known_corpus(self):
        """Pins the Okapi BM25 formula itself, not just its properties.

        Expected values computed by hand from the standard Robertson-Sparck Jones formula
        (idf = ln((N - n + 0.5) / (n + 0.5) + 1), k1=1.5, b=0.75) in a scratch script kept
        outside this test — not by calling compute_bm25_scores and asserting its own output.
        Corpus: A="cat cat dog" (len 3), B="cat" (len 1), C="fish bird" (len 2); avgdl=2.0.
        Query "cat dog" -> query_terms={"cat", "dog"}, df(cat)=2 (A, B), df(dog)=1 (A only).
        A regression in the formula (wrong IDF, wrong length normalization, wrong k1/b
        application) would change these values even though determinism, full-coverage, and
        zero-for-no-overlap would all still hold.
        """
        from domain.models.matching import compute_bm25_scores

        documents = {
            "A": "cat cat dog",
            "B": "cat",
            "C": "fish bird",
        }

        scores = compute_bm25_scores("cat dog", documents)

        assert scores["A"] == pytest.approx(1.379142946459583)
        assert scores["B"] == pytest.approx(0.6064562958009492)
        assert scores["C"] == 0.0

    def test_should_reject_invalid_k1_or_b_when_scoring(self):
        from domain.models.matching import compute_bm25_scores

        documents = {"A": "cat dog"}

        with pytest.raises(ValueError, match="k1"):
            compute_bm25_scores("cat", documents, k1=-1.0)

        with pytest.raises(ValueError, match="b"):
            compute_bm25_scores("cat", documents, b=1.5)

        with pytest.raises(ValueError, match="b"):
            compute_bm25_scores("cat", documents, b=-0.1)

        with pytest.raises(ValueError, match="k1"):
            compute_bm25_scores("cat", documents, k1=float("nan"))
