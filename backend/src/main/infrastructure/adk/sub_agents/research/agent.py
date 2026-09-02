from google.adk.agents import LlmAgent
from infrastructure.adk.config import get_agent_model
from application.state_keys import RESEARCH_OUTPUT
from infrastructure.adk.tools import search_patents_tool, get_similar_patents_tool, get_citations_tool
from .prompt import RESEARCH_AGENT_INSTRUCTION


def build_research_agent() -> LlmAgent:
    return LlmAgent(
        name="research_agent",
        model=get_agent_model("research"),
        instruction=RESEARCH_AGENT_INSTRUCTION,
        tools=[search_patents_tool, get_similar_patents_tool, get_citations_tool],
        output_key=RESEARCH_OUTPUT,
        include_contents="none",
    )


research_agent = build_research_agent()
