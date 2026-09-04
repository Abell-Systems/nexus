import math
import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RetrievalMethod(StrEnum):
    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    CPC = "cpc"


class CPCModality(StrEnum):
    AUTO = "auto"
    CURATED = "curated"


class DemandCPC(BaseModel):
    """Taxonomic CPC representation derived from a demand under a specific modality."""

    symbols: list[str] = Field(default_factory=list)
    modality: CPCModality = CPCModality.AUTO
    provenance: str = "automated_rule"


class Candidate(BaseModel):
    """A patent candidate retrieved for a specific demand, preserving retrieval evidence."""

    publication_id: str
    retrieval_scores: dict[RetrievalMethod, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scores_and_id(self) -> "Candidate":
        if not self.publication_id.strip():
            raise ValueError("publication_id cannot be empty")
        for method, score in self.retrieval_scores.items():
            if score < 0.0:
                raise ValueError(f"Retrieval score for {method} must be non-negative, got {score}")
        return self


class CandidatePool(BaseModel):
    """Shared fixed candidate pool (P_shared) constructed strictly as the union of first-stage baselines."""

    demand_id: str
    candidates: list[Candidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_invariants(self) -> "CandidatePool":
        if not self.demand_id.strip():
            raise ValueError("demand_id cannot be empty")
        seen_ids: set[str] = set()
        for cand in self.candidates:
            if cand.publication_id in seen_ids:
                raise ValueError(f"Duplicate publication_id '{cand.publication_id}' in candidate pool")
            seen_ids.add(cand.publication_id)
        if len(self.candidates) > 300:
            raise ValueError(f"CandidatePool exceeds maximum capacity of 300 candidates (got {len(self.candidates)})")
            # NOTE: This 300 is a STRUCTURAL CAPACITY LIMIT of the model — an absolute maximum
            # that prevents memory abuse regardless of policy. It is NOT the same as
            # MatchingPolicyConfig.operational_limits.max_candidate_pool_size, which is an
            # OPERATIONAL LIMIT that configures how many candidates the matching service retrieves
            # at runtime. Two distinct concepts:
            #   - 300 (structural): "a CandidatePool cannot physically hold more than this"
            #   - max_candidate_pool_size (policy): "the service should not construct pools larger than this"
            # The operational limit should always be <= 300 to avoid triggering the structural limit.
        return self

    @classmethod
    def from_retrievals(
        cls,
        demand_id: str,
        lexical_candidates: list[Candidate],
        semantic_candidates: list[Candidate],
        cpc_candidates: list[Candidate],
    ) -> "CandidatePool":
        """Deduplicates candidates across the 3 independent baselines preserving provenance."""
        merged: dict[str, dict[RetrievalMethod, float]] = {}

        for cand in lexical_candidates:
            scores = merged.setdefault(cand.publication_id, {})
            scores[RetrievalMethod.LEXICAL] = cand.retrieval_scores.get(RetrievalMethod.LEXICAL, 0.0)

        for cand in semantic_candidates:
            scores = merged.setdefault(cand.publication_id, {})
            scores[RetrievalMethod.SEMANTIC] = cand.retrieval_scores.get(RetrievalMethod.SEMANTIC, 0.0)

        for cand in cpc_candidates:
            scores = merged.setdefault(cand.publication_id, {})
            scores[RetrievalMethod.CPC] = cand.retrieval_scores.get(RetrievalMethod.CPC, 0.0)

        # Deterministic sorting of pool by publication_id
        sorted_candidates = [
            Candidate(publication_id=pub_id, retrieval_scores=scores)
            for pub_id, scores in sorted(merged.items(), key=lambda item: item[0])
        ]
        return cls(demand_id=demand_id, candidates=sorted_candidates)


class RankedCandidate(BaseModel):
    """A scored and ranked candidate within the shared candidate pool."""

    publication_id: str
    rank: int
    score: float
    components: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_rank_and_score(self) -> "RankedCandidate":
        if self.rank < 1:
            raise ValueError(f"Rank must be >= 1, got {self.rank}")
        return self


class RankerWeights(BaseModel):
    """Frozen linear fusion weights (alpha, beta, gamma)."""

    alpha: float
    beta: float
    gamma: float

    @model_validator(mode="after")
    def validate_weights(self) -> "RankerWeights":
        if self.alpha < 0.0 or self.beta < 0.0 or self.gamma < 0.0:
            raise ValueError(
                f"Ranker weights must be non-negative, got alpha={self.alpha}, beta={self.beta}, gamma={self.gamma}"
            )
        total = self.alpha + self.beta + self.gamma
        if not math.isclose(total, 1.0, rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError(f"Ranker weights must sum exactly to 1.0, got {total}")
        return self


class EligibilityReason(StrEnum):
    ELIGIBLE = "eligible"
    EXCLUDED_TEMPORAL = "excluded_temporal"
    EXCLUDED_JURISDICTION = "excluded_jurisdiction"
    EXCLUDED_MISSING_TEXT = "excluded_missing_text"


class EligibilityResult(BaseModel):
    """Provenance and verdict of patent eligibility against a demand."""

    publication_id: str
    is_eligible: bool
    reason: EligibilityReason
    details: str | None = None


class MatchingResult(BaseModel):
    """Result of Stage 1 Retrieval + Stage 2 Ranking over the shared fixed pool."""

    demand_id: str
    pool: CandidatePool
    rankings: dict[str, list[RankedCandidate]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedCPCSymbol(BaseModel):
    """Structured representation of a CPC classification symbol.
    
    Hierarchy:
    Section: e.g. 'C'
    Class: e.g. 'C11'
    Subclass: e.g. 'C11D'
    Main Group: e.g. 'C11D1'
    Subgroup: e.g. 'C11D1/02'
    """

    raw_symbol: str
    section: str
    class_code: str
    subclass: str
    main_group: str
    subgroup: str

    @classmethod
    def from_symbol(cls, raw: str) -> "ParsedCPCSymbol":
        cleaned = raw.strip().upper().replace(" ", "")
        # e.g., C11D1/02, C11D1/00, C11D, C
        match = re.match(r"^([A-HY])(?:(\d{2})([A-Z]))?(?:(\d+)(?:/(\d+))?)?", cleaned)
        if not match:
            # Fallback for coarse symbols
            section = cleaned[:1] if cleaned else ""
            return cls(
                raw_symbol=cleaned,
                section=section,
                class_code="",
                subclass="",
                main_group="",
                subgroup="",
            )

        sec, cl, sub, mg, sg = match.groups()
        section = sec or ""
        class_code = f"{section}{cl}" if cl else ""
        subclass = f"{class_code}{sub}" if sub else ""
        main_group = f"{subclass}{mg}" if (subclass and mg) else ""
        subgroup = f"{main_group}/{sg}" if (main_group and sg) else (main_group if main_group else subclass)

        return cls(
            raw_symbol=cleaned,
            section=section,
            class_code=class_code,
            subclass=subclass,
            main_group=main_group,
            subgroup=subgroup,
        )


class CPCConcordanceLevels(BaseModel):
    subgroup: float
    main_group: float
    subclass: float
    section: float
    none: float


def compute_cpc_symbol_similarity_from_levels(
    sym_a: str,
    sym_b: str,
    levels: CPCConcordanceLevels,
) -> float:
    """Computes hierarchical CPC similarity between two classification symbols using policy levels.

    Levels are injected strictly from MatchingPolicyConfig (single source of truth).
    """
    pa = ParsedCPCSymbol.from_symbol(sym_a)
    pb = ParsedCPCSymbol.from_symbol(sym_b)

    if not pa.section or not pb.section:
        return levels.none

    if pa.subgroup and pb.subgroup and pa.subgroup == pb.subgroup:
        return levels.subgroup
    if pa.main_group and pb.main_group and pa.main_group == pb.main_group:
        return levels.main_group
    if pa.subclass and pb.subclass and pa.subclass == pb.subclass:
        return levels.subclass
    if pa.section == pb.section:
        return levels.section
    return levels.none


def compute_cpc_symbol_similarity(
    sym_a: str,
    sym_b: str,
    levels: CPCConcordanceLevels,
) -> float:
    """Computes hierarchical CPC similarity using explicitly injected policy levels."""
    return compute_cpc_symbol_similarity_from_levels(sym_a, sym_b, levels)


def compute_max_cpc_similarity(
    demand_symbols: list[str],
    patent_symbols: list[str],
    levels: CPCConcordanceLevels,
) -> float:
    """Computes the maximum hierarchical concordance between a demand and a patent."""
    if not demand_symbols or not patent_symbols:
        return 0.0
    return max(
        (compute_cpc_symbol_similarity(d_sym, p_sym, levels) for d_sym in demand_symbols for p_sym in patent_symbols),
        default=0.0,
    )


# Common functional/stop words in patent and demand texts (English and Spanish).
# Single source of truth for BM25 tokenization: infrastructure/matching/duckdb_bm25.py
# imports compute_bm25_scores from here rather than keeping its own copy.
_BM25_STOPWORDS = {
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con", "contra",
    "cual", "cuando", "de", "del", "desde", "donde", "durante", "e", "el", "ella",
    "ellas", "ellos", "en", "entre", "era", "erais", "eran", "eras", "eres", "es",
    "esa", "esas", "ese", "eso", "esos", "esta", "estas", "este", "esto", "estos",
    "ha", "habeis", "haber", "habia", "han", "has", "hasta", "hay", "la", "las", "le",
    "les", "lo", "los", "me", "mi", "mis", "mucho", "muchos", "muy", "mas", "nos",
    "nosotras", "nosotros", "o", "os", "otra", "otras", "otro", "otros", "para", "pero",
    "por", "porque", "que", "quien", "quienes", "se", "sea", "sean", "segun", "ser",
    "si", "sido", "siendo", "sin", "sobre", "sois", "solamente", "solo", "somos", "son",
    "soy", "su", "sus", "tambien", "tanto", "te", "tenemos", "tener", "tenga", "tengan",
    "tengo", "ti", "tiene", "tienen", "toda", "todas", "todo", "todos", "tu", "tus",
    "un", "una", "unas", "uno", "unos", "va", "vais", "vamos", "van", "vaya", "yo",
    "and", "the", "for", "of", "in", "to", "with", "on", "at", "from", "by", "an", "as",
    "is", "are", "was", "were", "or", "that", "this", "be", "it",
}

_BM25_TOKEN_PATTERN = re.compile(r"\b[a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ]{2,}\b")


def _tokenize_for_bm25(text: str) -> list[str]:
    """Lowercase tokenization filtering stopwords and punctuation."""
    tokens = _BM25_TOKEN_PATTERN.findall(text.lower())
    return [t for t in tokens if t not in _BM25_STOPWORDS]


def compute_bm25_scores(
    query_text: str,
    documents: dict[str, str],
    k1: float = 1.5,
    b: float = 0.75,
) -> dict[str, float]:
    """Computes Okapi BM25 relevance scores for every document against a query (ADR 0013).

    `documents` maps publication_id to its full text (e.g. title + ' ' + abstract) —
    observed evidence only, never annotations or relevance grades: this function's
    signature has no parameter through which either could reach it. Every publication_id
    in `documents` is present in the result, scored 0.0 when there is no term overlap —
    this function performs no filtering, ranking, or truncation of its own, and never
    excludes a document regardless of its score.

    k1=1.5, b=0.75 are the same fixed values already used by the live DuckDbBM25Retriever —
    pre-existing defaults, not tuned against this benchmark. The default matching policy's
    alpha/beta/gamma weights govern fusion across signals; they are a separate concern from
    these BM25-internal constants. Deterministic and reproducible from these declared inputs,
    the Okapi BM25 algorithm, and Python's standard math operations: no network access, no
    randomness, no wall-clock dependence.

    infrastructure/matching/duckdb_bm25.py's DuckDbBM25Retriever calls this same function for
    its scoring core, then applies its own eligibility filtering and top-K truncation for live
    candidate generation — behavior a closed evaluation benchmark must not have (ADR 0013).

    Raises:
        ValueError: if k1 or b is outside Okapi BM25's valid domain (k1 >= 0, 0 <= b <= 1) or
            not finite. This is a contract check on the algorithm's parameters, not a runtime
            path exercised by the current fixed defaults.
    """
    if not math.isfinite(k1) or k1 < 0.0:
        raise ValueError(f"k1 must be a finite number >= 0, got {k1}")
    if not math.isfinite(b) or not (0.0 <= b <= 1.0):
        raise ValueError(f"b must be a finite number in [0, 1], got {b}")

    if not documents:
        return {}

    doc_tokens = {pub_id: _tokenize_for_bm25(text) for pub_id, text in documents.items()}
    doc_lengths = {pub_id: len(tokens) for pub_id, tokens in doc_tokens.items()}
    n = len(doc_tokens)
    avgdl = sum(doc_lengths.values()) / n if n > 0 else 0.0

    query_terms = set(_tokenize_for_bm25(query_text))

    document_frequency: dict[str, int] = {}
    for tokens in doc_tokens.values():
        unique_terms = set(tokens)
        for term in query_terms:
            if term in unique_terms:
                document_frequency[term] = document_frequency.get(term, 0) + 1

    scores: dict[str, float] = {}
    for pub_id, tokens in doc_tokens.items():
        doc_len = doc_lengths[pub_id]
        term_frequency: dict[str, int] = {}
        for token in tokens:
            term_frequency[token] = term_frequency.get(token, 0) + 1

        bm25_score = 0.0
        for term in query_terms:
            f_term = term_frequency.get(term, 0)
            if f_term == 0:
                continue
            n_term = document_frequency.get(term, 0)
            idf = math.log((n - n_term + 0.5) / (n_term + 0.5) + 1.0)
            denominator = f_term + k1 * (1.0 - b + b * (doc_len / avgdl if avgdl > 0 else 1.0))
            bm25_score += idf * (f_term * (k1 + 1.0) / denominator)

        scores[pub_id] = bm25_score

    return scores


class MatchConfidence(StrEnum):
    """Categorical confidence level of a technology match under ADR 0004."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


class EvidenceSufficiency(StrEnum):
    """Classification of whether observed facts justify a matching evaluation."""

    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INELIGIBLE_TEMPORAL = "ineligible_temporal"
    INELIGIBLE_JURISDICTION = "ineligible_jurisdiction"


class PatentCandidateEvidence(BaseModel):
    """Canonical model for patent candidate evidence observed during matching."""

    publication_id: str
    publication_date: str | None = None
    classifications_cpc: list[str] = Field(default_factory=list)
    shared_terms: tuple[str, ...] = Field(default_factory=tuple)
    title: str = ""
    abstract: str = ""


class MatchFeatures(BaseModel):
    """Deterministic, explainable features extracted between a demand and a patent."""

    lexical_score: float = Field(ge=0.0, default=0.0)
    semantic_score: float = Field(ge=0.0, le=1.0, default=0.0)
    cpc_concordance: float = Field(ge=0.0, le=1.0, default=0.0)
    temporal_valid: bool = True
    delta_days: int | None = None
    shared_terms: tuple[str, ...] = Field(default_factory=tuple)
    concordant_cpc_pairs: tuple[tuple[str, str], ...] = Field(default_factory=tuple)


class MatchAssessment(BaseModel):
    """Auditable, explainable verdict of evaluating a demand against a candidate patent."""

    demand_id: str
    publication_id: str
    overall_score: float = Field(ge=0.0, le=1.0)
    confidence: MatchConfidence
    sufficiency: EvidenceSufficiency
    features: MatchFeatures
    rationale: str
    policy_id: str
    policy_version: str
    policy_sha256: str = Field(min_length=64, max_length=64)


class OperationalLimits(BaseModel):
    retrieval_limit: int = Field(ge=1, le=1000)
    max_candidate_pool_size: int = Field(ge=1, le=1000)


class ConfidenceThresholds(BaseModel):
    strong: float
    moderate: float
    weak: float


class SufficiencyRules(BaseModel):
    min_active_signals: int
    min_signals_for_sufficient: int
    require_temporal_validity: bool


class MatchingPolicyConfig(BaseModel):
    """Externalized, versioned, cryptographically sealed matching policy."""

    policy_id: str
    policy_version: str
    description: str = ""
    weights: RankerWeights
    operational_limits: OperationalLimits
    cpc_concordance_levels: CPCConcordanceLevels
    confidence_thresholds: ConfidenceThresholds
    sufficiency_rules: SufficiencyRules
    concept_to_cpc_taxonomy: dict[str, list[str]]
    cpc_taxonomy_descriptions: dict[str, dict[str, str]] = Field(default_factory=dict)
    policy_sha256: str = Field(min_length=64, max_length=64)

    @classmethod
    def load_from_json(cls, file_path: str | Any) -> "MatchingPolicyConfig":
        import hashlib
        import json
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Matching policy configuration not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as err:
            raise ValueError(f"Corrupt matching policy JSON: {path}") from err

        declared_sha = data.pop("policy_sha256", None)
        if not declared_sha:
            raise ValueError(
                f"Cryptographic integrity verification failed for {path}: "
                f"missing mandatory declared 'policy_sha256'"
            )

        # Compute canonical hash over rest of payload
        canonical_bytes = json.dumps(data, sort_keys=True, indent=2).encode("utf-8")
        computed_sha = hashlib.sha256(canonical_bytes).hexdigest()

        if declared_sha.lower() != computed_sha.lower():
            raise ValueError(
                f"Cryptographic integrity verification failed for {path}: "
                f"declared {declared_sha}, computed {computed_sha}"
            )

        data["policy_sha256"] = computed_sha
        return cls(**data)
