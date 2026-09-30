"""The exact texts that are embedded. One definition shared by generation and retrieval, so the
string a retriever looks up is byte-identical to the string the generator encoded."""

import hashlib
import json
from collections.abc import Sequence


def demand_embedding_text(title: str, description: str) -> str:
    return f"{title} {description}".strip()


def patent_embedding_text(title: str, abstract: str) -> str:
    return f"{title} {abstract}".strip()


def texts_sha256(texts: Sequence[str]) -> str:
    """Content hash of an ordered list of embedding texts (length-delimited, so ["ab","c"] != ["a","bc"])."""
    return hashlib.sha256(json.dumps(list(texts), ensure_ascii=False).encode("utf-8")).hexdigest()
