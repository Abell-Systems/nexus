from google.adk.agents import LlmAgent

from ...config import get_agent_model
from ...shared.state_keys import ADVERSARIAL_VERDICTS
from ...tools import exit_loop, get_citations_tool, get_similar_patents_tool, search_patents_tool
from ...tools.schemas import AdversarialVerdict
from .prompt import ADVERSARIAL_AGENT_INSTRUCTION

def build_adversarial_agent() -> LlmAgent:
    """Factory, not a singleton — see build_inventor_agent's docstring."""
    return LlmAgent(
        name="adversarial_agent",
        model=get_agent_model(),
        instruction=ADVERSARIAL_AGENT_INSTRUCTION,
        tools=[search_patents_tool, get_similar_patents_tool, get_citations_tool, exit_loop],
        output_key=ADVERSARIAL_VERDICTS,
        # this ADK build supports output_schema alongside tools: it injects a
        # set_model_response tool the model must call for its final answer,
        # so the verdict is schema-validated instead of parsed from free text.
        output_schema=AdversarialVerdict,
        # ponytail: same fix as inventor_agent — see its include_contents comment.
        include_contents="none",
    )


adversarial_agent = build_adversarial_agent()
