"""Deterministic fake patent data generator used by MockPatentsDataSource.

Same (query, domain) always yields the same corpus, so demo runs are reproducible
without live BigQuery credentials.
"""

import random

from .schemas import PatentRecord

_ASSIGNEES = [
    "Northwind Materials Corp",
    "Blue Harbor Technologies",
    "Cascade Research Institute",
    "Ironleaf Industries",
    "Solstice Labs",
    "Redshift Dynamics",
    "Kestrel Applied Sciences",
]

_INVENTOR_FIRST = ["Amara", "Liang", "Priya", "Tomas", "Sofia", "Kenji", "Nadia", "Omar"]
_INVENTOR_LAST = ["Chen", "Okafor", "Novak", "Patel", "Ibarra", "Fischer", "Haddad", "Kim"]

_CPC_PREFIXES = ["H01M", "C01B", "B01J", "H01L", "C08L", "G01N", "A61K"]

_ABSTRACT_TEMPLATES = [
    "A method and system for {domain} comprising a novel arrangement that improves "
    "efficiency and stability relative to prior approaches.",
    "Disclosed is a {domain} composition and associated process for manufacturing, "
    "offering improved performance under a range of operating conditions.",
    "This disclosure relates to {domain} devices and methods for their fabrication, "
    "addressing limitations of conventional designs.",
    "A {domain} apparatus is described that reduces material cost while maintaining "
    "or improving key performance metrics.",
]

_COUNTRIES = ["US", "EP", "CN", "JP", "KR"]


def _rng_for(query: str, domain: str) -> random.Random:
    seed = hash((query, domain)) & 0xFFFFFFFF
    return random.Random(seed)


def generate_patents(query: str, domain: str, count: int) -> list[PatentRecord]:
    rng = _rng_for(query, domain)
    records: list[PatentRecord] = []
    for i in range(count):
        year = rng.randint(2005, 2025)
        pub_number = f"US-{rng.randint(10_000_000, 11_999_999)}-B2"
        assignee = rng.choice(_ASSIGNEES)
        inventors = [
            f"{rng.choice(_INVENTOR_FIRST)} {rng.choice(_INVENTOR_LAST)}"
            for _ in range(rng.randint(1, 3))
        ]
        cpc_codes = [
            f"{rng.choice(_CPC_PREFIXES)}{rng.randint(1, 99)}/{rng.randint(0, 9999):04d}"
            for _ in range(rng.randint(1, 3))
        ]
        abstract = rng.choice(_ABSTRACT_TEMPLATES).format(domain=domain)
        records.append(
            PatentRecord(
                publication_number=f"{pub_number}-{i}",
                title=f"{domain.title()}: {query.title()} Variant {i + 1}",
                abstract=abstract,
                assignee=[assignee],
                inventors=inventors,
                filing_date=f"{year}-01-15",
                publication_date=f"{year + 1}-06-01",
                priority_date=f"{year - 1}-01-15",
                country_code=rng.choice(_COUNTRIES),
                cpc_codes=cpc_codes,
                family_id=f"FAM-{rng.randint(100000, 999999)}",
                citation_count=rng.randint(0, 200),
                similarity_score=None,
            )
        )
    return records
