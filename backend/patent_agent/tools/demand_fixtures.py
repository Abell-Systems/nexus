"""Deterministic fake demand-signal generator used by MockDemandDataSource.

Same (query, domain) always yields the same set, so demo runs are reproducible
without live SBIR.gov/CORDIS credentials.
"""

import random

from .schemas import DemandSignal

_CPC_PREFIXES = ["H01M", "C01B", "B01J", "H01L", "C08L", "G01N", "A61K"]

_SOURCES = ["sbir", "cordis"]

_TITLE_TEMPLATES = [
    "Request for proposals: next-generation {domain}",
    "Open topic: improving manufacturability of {domain}",
    "Funded research call on {domain} performance and safety",
    "Technology need: cost-reduced {domain} at scale",
]

_DESCRIPTION_TEMPLATES = [
    "Seeking novel approaches to {domain} that improve performance while reducing "
    "manufacturing cost and material risk.",
    "Agency/consortium is soliciting proposals addressing durability and safety "
    "limitations of current {domain} approaches.",
    "Funded call for research into scalable {domain} techniques suitable for "
    "commercial deployment within 3-5 years.",
]


def _rng_for(query: str, domain: str) -> random.Random:
    seed = hash(("demand", query, domain)) & 0xFFFFFFFF
    return random.Random(seed)


def generate_demand_signals(query: str, domain: str, count: int) -> list[DemandSignal]:
    rng = _rng_for(query, domain)
    signals: list[DemandSignal] = []
    for i in range(count):
        source = rng.choice(_SOURCES)
        year = rng.randint(2022, 2026)
        month = rng.randint(1, 12)
        signals.append(
            DemandSignal(
                source=source,
                id=f"{source}-{rng.randint(10000, 99999)}-{i}",
                title=_TITLE_TEMPLATES[i % len(_TITLE_TEMPLATES)].format(domain=domain),
                description=rng.choice(_DESCRIPTION_TEMPLATES).format(domain=domain),
                cpc_prefix=rng.choice(_CPC_PREFIXES),
                posted_date=f"{year}-{month:02d}-01",
                url=f"https://example.invalid/{source}/{i}",
            )
        )
    return signals
