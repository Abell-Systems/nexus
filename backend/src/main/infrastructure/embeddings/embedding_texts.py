"""The exact texts that are embedded. One definition shared by generation and retrieval, so the
string a retriever looks up is byte-identical to the string the generator encoded."""


def demand_embedding_text(title: str, description: str) -> str:
    return f"{title} {description}".strip()


def patent_embedding_text(title: str, abstract: str) -> str:
    return f"{title} {abstract}".strip()
