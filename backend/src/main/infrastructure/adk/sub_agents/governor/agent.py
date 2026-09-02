from google.adk.agents import LlmAgent

from application.state_keys import SCORED_CANDIDATES
from domain.models.runtime_schemas import ScoreCard
from infrastructure.adk.config import get_agent_model

from .prompt import GOVERNOR_AGENT_INSTRUCTION


def build_governor_agent() -> LlmAgent:
    return LlmAgent(
        name="governor_agent",
        model=get_agent_model("governor"),
        instruction=GOVERNOR_AGENT_INSTRUCTION,
        output_key=SCORED_CANDIDATES,
        output_schema=ScoreCard,
        include_contents="none",
    )


governor_agent = build_governor_agent()
