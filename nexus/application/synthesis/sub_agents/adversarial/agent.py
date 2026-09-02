from google.adk.agents import LlmAgent
from nexus.application.synthesis.config import get_agent_model
from nexus.application.state_keys import ADVERSARIAL_VERDICTS
from nexus.application.synthesis.tools import exit_loop, get_citations_tool, get_similar_patents_tool, search_patents_tool
from nexus.domain.models.runtime_schemas import AdversarialVerdict
from .prompt import ADVERSARIAL_AGENT_INSTRUCTION


def build_adversarial_agent() -> LlmAgent:
    return LlmAgent(
        name="adversarial_agent",
        model=get_agent_model("adversarial"),
        instruction=ADVERSARIAL_AGENT_INSTRUCTION,
        tools=[search_patents_tool, get_similar_patents_tool, get_citations_tool, exit_loop],
        output_key=ADVERSARIAL_VERDICTS,
        output_schema=AdversarialVerdict,
        include_contents="none",
    )


adversarial_agent = build_adversarial_agent()
