from google.adk.agents import LlmAgent

from ...config import get_agent_model
from ...shared.state_keys import SCORED_CANDIDATES
from ...tools.schemas import ScoreCardList
from .prompt import GOVERNOR_AGENT_INSTRUCTION

def build_governor_agent() -> LlmAgent:
    """Factory, not a singleton — see build_inventor_agent's docstring."""
    return LlmAgent(
        name="governor_agent",
        model=get_agent_model(),
        instruction=GOVERNOR_AGENT_INSTRUCTION,
        tools=[],
        output_key=SCORED_CANDIDATES,
        output_schema=ScoreCardList,
        # ponytail: same fix as inventor_agent — see its include_contents comment.
        include_contents="none",
    )


governor_agent = build_governor_agent()
