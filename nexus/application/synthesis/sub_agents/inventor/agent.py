from google.adk.agents import LlmAgent
from nexus.application.synthesis.config import get_agent_model
from nexus.application.state_keys import CANDIDATE_INVENTIONS
from nexus.domain.models.runtime_schemas import InventionCandidate
from .prompt import INVENTOR_AGENT_INSTRUCTION


def build_inventor_agent() -> LlmAgent:
    return LlmAgent(
        name="inventor_agent",
        model=get_agent_model("inventor"),
        instruction=INVENTOR_AGENT_INSTRUCTION,
        output_key=CANDIDATE_INVENTIONS,
        output_schema=InventionCandidate,
        include_contents="none",
    )


inventor_agent = build_inventor_agent()
