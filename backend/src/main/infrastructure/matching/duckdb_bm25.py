import math
import re
from collections import Counter

import duckdb

from domain.models.demand import DemandSignal
from domain.models.matching import (
    Candidate,
    EligibilityReason,
    RetrievalMethod,
)
from domain.models.patent import PatentDocument
from domain.protocols.matching import (
    PatentCandidateRetriever,
    PatentEligibilityPolicy,
)

from .duckdb_helpers import resolve_patent_columns
from .eligibility import DefaultPatentEligibilityPolicy

# Common functional/stop words in patent and demand texts (English and Spanish)
STOPWORDS = {
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


def _tokenize(text: str) -> list[str]:
    """Lowercase tokenization filtering stopwords and punctuation."""
    tokens = re.findall(r"\b[a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ]{2,}\b", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


class DuckDbBM25Retriever(PatentCandidateRetriever):
    """Real vertical slice executing Okapi BM25 retrieval over a DuckDB database or in-memory connection.

    Invariants:
    - Pre-filters eligible patents using PatentEligibilityPolicy before BM25 ranking.
    - Okapi BM25 scoring with k1=1.5, b=0.75 over (title + ' ' + abstract).
    - Returns up to `limit` candidates with score > 0.
    - Ties broken deterministically by (score DESC, publication_id ASC).
    - Produces domain Candidate objects with RetrievalMethod.LEXICAL score.
    """

    def __init__(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str = "patents",
        eligibility_policy: PatentEligibilityPolicy | None = None,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self._con = connection
        self._table_name = table_name
        self._eligibility_policy = eligibility_policy or DefaultPatentEligibilityPolicy()
        self._k1 = k1
        self._b = b

    def retrieve(
        self,
        demand: DemandSignal,
        *,
        limit: int = 100,
    ) -> list[Candidate]:
        # 1. Fetch all documents from DuckDB
        query = resolve_patent_columns(self._con, self._table_name)
        cursor = self._con.execute(query)
        rows = cursor.fetchall()

        # 2. Filter documents using strict eligibility policy
        eligible_docs: list[tuple[str, list[str], int]] = []  # (pub_id, doc_tokens, doc_len)
        doc_lengths: list[int] = []

        for row in rows:
            pub_id = str(row[0])
            country_code = str(row[1]) if row[1] is not None else ""
            doc_number = str(row[2]) if row[2] is not None else ""
            kind_code = str(row[3]) if row[3] is not None else ""
            title = str(row[4]) if row[4] is not None else ""
            abstract = str(row[5]) if row[5] is not None else ""
            publication_date = str(row[6]) if row[6] is not None else ""

            patent = PatentDocument(
                publication_id=pub_id,
                country_code=country_code,
                doc_number=doc_number,
                kind_code=kind_code,
                title=title,
                abstract=abstract,
                publication_date=publication_date,
            )

            eval_res = self._eligibility_policy.evaluate(patent, demand)
            if eval_res.reason != EligibilityReason.ELIGIBLE:
                continue

            full_text = f"{title} {abstract}"
            tokens = _tokenize(full_text)
            doc_len = len(tokens)
            eligible_docs.append((pub_id, tokens, doc_len))
            doc_lengths.append(doc_len)

        if not eligible_docs:
            return []

        # 3. Compute Corpus-Level Statistics over Eligible Subcorpus
        N = len(eligible_docs)
        avgdl = sum(doc_lengths) / N if N > 0 else 0.0

        query_text = f"{demand.title} {demand.description}"
        query_tokens = _tokenize(query_text)
        query_counter = Counter(query_tokens)

        # Inverted document frequency over eligible docs
        df: Counter[str] = Counter()
        for _, tokens, _ in eligible_docs:
            unique_tokens = set(tokens)
            for q_term in query_counter:
                if q_term in unique_tokens:
                    df[q_term] += 1

        # 4. Compute BM25 Score per Eligible Document
        candidates: list[tuple[str, float]] = []
        for pub_id, tokens, doc_len in eligible_docs:
            doc_counter = Counter(tokens)
            bm25_score = 0.0

            for q_term, _ in query_counter.items():
                if q_term not in doc_counter:
                    continue
                n_term = df[q_term]
                # Standard Robertson-Spärck Jones IDF
                idf = math.log((N - n_term + 0.5) / (n_term + 0.5) + 1.0)
                f_term = doc_counter[q_term]
                numerator = f_term * (self._k1 + 1.0)
                denominator = f_term + self._k1 * (1.0 - self._b + self._b * (doc_len / avgdl if avgdl > 0 else 1.0))
                bm25_score += idf * (numerator / denominator)

            if bm25_score > 0.0:
                candidates.append((pub_id, round(bm25_score, 6)))

        # 5. Deterministic sorting: (score DESC, publication_id ASC)
        sorted_candidates = sorted(candidates, key=lambda item: (-item[1], item[0]))[:limit]

        return [
            Candidate(
                publication_id=pub_id,
                retrieval_scores={RetrievalMethod.LEXICAL: score},
            )
            for pub_id, score in sorted_candidates
        ]
