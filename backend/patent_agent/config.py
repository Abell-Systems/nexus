"""Environment-driven configuration shared by all agents."""

import os
from .provider import LLMProvider

USE_MOCK_BIGQUERY = os.getenv("USE_MOCK_BIGQUERY", "true").lower() == "true"
USE_MOCK_DEMAND = os.getenv("USE_MOCK_DEMAND", "true").lower() == "true"
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

INVENTION_LOOP_MAX_ITERATIONS = int(os.getenv("INVENTION_LOOP_MAX_ITERATIONS", "4"))

# The demo's patent data (real BigQuery domain index and mock fixtures alike) only
# covers this domain. Any other domain silently returns irrelevant results and can
# make the LLM fabricate prior-art citations instead of citing real search hits.
SUPPORTED_DOMAIN_KEYWORDS = [
    kw.strip().lower()
    for kw in os.getenv("SUPPORTED_DOMAIN_KEYWORDS", "electrolyte,batter").split(",")
    if kw.strip()
]


def is_supported_domain(domain: str) -> bool:
    domain_lower = domain.lower()
    return any(kw in domain_lower for kw in SUPPORTED_DOMAIN_KEYWORDS)


def get_agent_model():
    """Returns the model value every LlmAgent is constructed with."""
    return LLMProvider.get_agent_model()
