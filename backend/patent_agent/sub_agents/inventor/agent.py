from google.adk.agents import LlmAgent

from ...config import get_agent_model
from ...shared.state_keys import CANDIDATE_INVENTIONS
from ...tools.schemas import InventionCandidate
from .prompt import INVENTOR_AGENT_INSTRUCTION

def build_inventor_agent() -> LlmAgent:
    """Factory, not a singleton: ADK agents can only have one parent, so each
    graph that wants an inventor_agent (the interactive root_agent, the
    lighter API-only pipeline) needs its own instance."""
    return LlmAgent(
        name="inventor_agent",
        model=get_agent_model(),
        instruction=INVENTOR_AGENT_INSTRUCTION,
        tools=[],
        output_key=CANDIDATE_INVENTIONS,
        output_schema=InventionCandidate,
        # ponytail: full conversation replay (default) drags research_agent's raw
        # tool-call history (20 patents + citations) into every inventor call,
        # blowing free-tier TPM budgets. The compact cluster context and prior
        # verdict are injected via state placeholders in the instruction instead.
        include_contents="none",
    )


inventor_agent = build_inventor_agent()
